"""회차 선택부터 결제까지 실제 화면을 조작한다.

감시는 API로 하지만 예매는 DOM을 클릭한다. 예매/결제 API는 서명값과 세션 상태가
얽혀 있어 재현이 까다롭고, 어차피 한 번만 일어나는 동작이라 몇백 ms 차이가
의미 없기 때문이다. 대신 좌석 선점 제한시간(약 10분) 안에 끝내야 한다.
"""

from __future__ import annotations

import base64
import re
import time
from dataclasses import dataclass
from pathlib import Path

import yaml
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By

from . import queue, seatpick
from .browser import screenshot
from .paths import REPO, SHOTS_DIR as SHOTS

SELECTORS_PATH = REPO / "selectors.yaml"


class BookingError(RuntimeError):
    """예매 실패. 감시 루프는 이걸 잡고 계속 돈다."""


class SeatTakenError(BookingError):
    """노리던 좌석을 남이 먼저 가져감."""


class NoSelectableSeats(SeatTakenError):
    """API는 잔여석이 있다는데 좌석맵에서 고를 수 있는 자리가 없다.

    장애인석처럼 늘 비어 있지만 우리가 잡을 수 없는 자리가 잔여석으로 잡히면
    같은 회차에 계속 달려들게 된다. 감시 루프가 기준선을 학습하는 데 쓴다.
    """

    def __init__(self, message: str, available: int = 0):
        super().__init__(message)
        self.available = available


@dataclass
class BookingResult:
    ok: bool
    seats: str = ""
    amount: str = ""
    booking_no: str = ""
    stopped_before_payment: bool = False
    shot: Path | None = None


def load_selectors(path: Path = SELECTORS_PATH) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


class Booker:
    def __init__(self, driver, cfg, notifier, selectors: dict | None = None, dry_run: bool = False):
        self.driver = driver
        self.cfg = cfg
        self.notify = notifier
        self.sel = selectors or load_selectors()
        self.dry_run = dry_run
        self.deadline = 0.0
        # 결제 도중 알림에 쓰려고 들고 있는다
        self._showtime = None
        self._seats = ""

    # ---- DOM 도우미 ----------------------------------------------------

    def _left(self) -> float:
        return self.deadline - time.time()

    def _check_deadline(self, step: str) -> None:
        if self.deadline and self._left() <= 0:
            raise BookingError(f"좌석 선점 제한시간 초과 ({step})")

    def _find(self, candidates: list[str], timeout: float = 8.0, **fmt):
        """후보 셀렉터를 순서대로 시도해 보이는 요소 하나를 찾는다."""
        end = time.time() + timeout
        last = None
        while time.time() < end:
            for raw in candidates:
                spec = raw.format(**fmt) if fmt else raw
                try:
                    if spec.startswith("text:"):
                        el = self._by_text(spec[5:])
                    else:
                        el = next(
                            (
                                e
                                for e in self.driver.find_elements(By.CSS_SELECTOR, spec)
                                if e.is_displayed()
                            ),
                            None,
                        )
                except WebDriverException as exc:
                    last = exc
                    continue
                if el is not None:
                    return el, spec
            time.sleep(0.25)
        raise BookingError(f"요소를 못 찾음: {candidates} ({last or '시간 초과'})")

    def _by_text(self, needle: str):
        # 정확히 일치하는 요소를 먼저 찾는다. "용산아이파크몰"을 찾을 때
        # "미션브레이크 용산아이파크몰"이 먼저 걸리면 엉뚱한 곳으로 간다.
        js = """
        const needle = arguments[0];
        const nodes = Array.from(document.querySelectorAll('button, a, li, label, [role="button"]'))
          .filter(el => {
            const r = el.getBoundingClientRect();
            return r.width > 0 && r.height > 0;
          });
        for (const el of nodes) {
          if ((el.innerText || '').trim() === needle) return el;
        }
        for (const el of nodes) {
          const t = (el.innerText || '').trim();
          if (t && t.length <= 60 && t.includes(needle)) return el;
        }
        return null;
        """
        return self.driver.execute_script(js, needle)

    def _click(self, candidates: list[str], timeout: float = 8.0, wait: float = 0.8, **fmt) -> str:
        el, spec = self._find(candidates, timeout, **fmt)
        self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
        time.sleep(0.15)
        try:
            el.click()
        except WebDriverException:
            self.driver.execute_script("arguments[0].click();", el)
        time.sleep(wait)
        self._wait_queue()
        return spec

    def _try_click(self, candidates: list[str], timeout: float = 2.0, **fmt) -> bool:
        try:
            self._click(candidates, timeout=timeout, **fmt)
            return True
        except BookingError:
            return False

    def _text(self) -> str:
        try:
            return self.driver.execute_script("return document.body.innerText") or ""
        except WebDriverException:
            return ""

    # ---- 단계 ----------------------------------------------------------

    def _wait_queue(self) -> None:
        """접속 대기열이면 풀릴 때까지 기다린다. 기다린 시간은 선점 제한에 안 넣는다."""
        timeout = getattr(self.cfg.booking, "queue_timeout_sec", 1800)
        waited = queue.wait_out(self.driver, self.notify, timeout=timeout)
        if waited and self.deadline:
            self.deadline += waited

    def open_showtime(self, showtime) -> None:
        """예매 페이지에서 대상 회차 화면까지 들어간다."""
        self._check_deadline("회차 진입")
        self.driver.get(self.sel["booking_page"])
        time.sleep(2.0)
        self._wait_queue()

        self._click(
            self.sel["theater_picker"], timeout=15, wait=3.0, name=self._theater_needle()
        )
        self._wait_queue()

        self._click_date(showtime.date)
        self._wait_queue()
        self._click_matching_showtime(showtime)
        self._wait_queue()

        # 비로그인 상태면 여기서 로그인 안내창이 뜬다
        if "로그인이 필요한 서비스" in self._text():
            raise BookingError("로그인이 풀렸습니다. Chrome 창에서 다시 로그인해 주세요.")

    def _theater_needle(self) -> str:
        """극장 선택 목록에는 'CGV' 접두사 없이 '용산아이파크몰'로만 나온다."""
        return re.sub(r"^\s*CGV\s*", "", self.cfg.theater.name).strip()

    def _click_date(self, ymd: str) -> None:
        """날짜 탭을 누른다. 이미 선택돼 있으면 건너뛴다."""
        cfg = self.sel["date_tab"]
        day = str(int(ymd[6:8]))
        js = """
        const [btnSel, numSel, activeMark, day] = arguments;
        for (const btn of document.querySelectorAll(btnSel)) {
          const num = btn.querySelector(numSel);
          if (!num || num.textContent.trim() !== day) continue;
          if ((btn.className || '').includes(activeMark)) return 'already';
          btn.scrollIntoView({block: 'nearest', inline: 'center'});
          btn.click();
          return 'clicked';
        }
        return 'notfound';
        """
        outcome = self.driver.execute_script(
            js, cfg["button"], cfg["number"], cfg["active_marker"], day
        )
        if outcome == "notfound":
            raise BookingError(f"{ymd} 날짜 탭이 없습니다. 예매가 아직 열리지 않았을 수 있습니다.")
        if outcome == "clicked":
            time.sleep(2.5)

    def _click_matching_showtime(self, showtime) -> None:
        """시작 시각과 상영관 이름이 모두 맞는 회차 버튼을 누른다."""
        js = """
        const want = arguments[0], screen = arguments[1], sel = arguments[2];
        const btns = Array.from(document.querySelectorAll(sel));
        for (const b of btns) {
          const t = (b.innerText || '');
          if (!t.includes(want)) continue;
          const block = b.closest('[class*="contentWrap"], [class*="accordion"], section, div');
          const ctx = block ? block.innerText : t;
          if (screen && !ctx.includes(screen)) continue;
          b.scrollIntoView({block:'center'});
          b.click();
          return t.replace(/\\n/g, ' | ');
        }
        return null;
        """
        spec = self.sel["showtime_button"][0]
        hit = self.driver.execute_script(js, showtime.start, showtime.screen, spec)
        if not hit:
            raise SeatTakenError(
                f"회차 버튼을 못 찾음 ({showtime.start} {showtime.screen}). 이미 닫혔을 수 있습니다."
            )
        time.sleep(3.0)

    def select_visitor_count(self, count: int) -> None:
        """'일반' 그룹에서 인원 수 버튼을 누르고 좌석 모달을 연다."""
        self._check_deadline("인원 선택")
        vc = self.sel["visitor_count"]
        js = """
        const [groupSel, labelSel, btnSel, want] = arguments;
        for (const g of document.querySelectorAll(groupSel)) {
          const label = g.querySelector(labelSel);
          if (!label || !label.textContent.trim().startsWith('일반')) continue;
          const btn = Array.from(g.querySelectorAll(btnSel))
            .find(b => b.textContent.trim() === want);
          if (!btn) return 'nobutton';
          btn.click();
          return 'ok';
        }
        return 'nogroup';
        """
        outcome = self.driver.execute_script(
            js, vc["group"], vc["label"], vc["button"], str(count)
        )
        if outcome != "ok":
            raise BookingError(f"관람인원 {count}명 버튼을 못 찾음 ({outcome})")
        time.sleep(1.0)

        self._click(vc["open_seatmap"], timeout=10, wait=2.5)

    def _pick_with_fallback(self, count: int, targets: list[str] | None) -> list[str]:
        """원하는 매수부터 시작해 안 되면 한 장씩 줄여가며 잡는다.

        관람인원을 먼저 고르고 나서야 좌석맵이 열리는 구조라, 2연석이 없다는 걸
        좌석맵을 열어 봐야 아는 경우가 있다. 그때는 '인원변경'으로 되돌아간다.
        """
        floor = self.cfg.seats.min_count
        for n in range(count, floor - 1, -1):
            self._check_deadline("인원 선택")
            print(f"      일반 {n}명으로 시도", flush=True)
            self.select_visitor_count(n)
            try:
                return self.pick_seats(n, targets if n == count else None)
            except NoSelectableSeats:
                if n == floor:
                    raise
                print(f"      {n}석 실패, 인원을 줄여 다시 시도", flush=True)
                self._reopen_visitor_count()
        return []

    def _reopen_visitor_count(self) -> None:
        """좌석 모달을 닫고 인원 선택 화면으로 돌아간다."""
        self._click(self.sel["visitor_count"]["change"], timeout=10, wait=2.0)

    def pick_seats(self, count: int, targets: list[str] | None = None) -> list[str]:
        """좌석을 고른다.

        감시 루프가 좌석 API로 이미 골라 둔 자리(targets)가 있으면 그대로 누른다.
        같은 조건으로 판단했으니 다시 고를 이유가 없고, 선점 시간도 아낀다.
        그 사이 남이 채갔으면 화면에서 다시 고른다.
        """
        self._check_deadline("좌석 선택")

        chosen = self._verify_targets(targets) if targets else []
        if not chosen:
            picked = seatpick.choose(self._read_seatmap(), self.cfg.seats, count)
            chosen = [s.label for s in picked]
        if len(chosen) != count:
            raise NoSelectableSeats(
                f"조건에 맞는 {count}석이 없습니다 "
                f"({self._seat_rule_text()} 조건을 만족하는 자리 {len(chosen)}석)",
                available=len(chosen),
            )

        for label in chosen:
            self._click_seat(label)

        self._verify_selected(chosen)
        self._click(self.sel["seatmap"]["done"], timeout=10, wait=2.5)
        return chosen

    def _seat_rule_text(self) -> str:
        cfg = self.cfg.seats
        parts = []
        if cfg.min_row:
            parts.append(f"{cfg.min_row}열 이후")
        if cfg.center_ratio < 1.0:
            parts.append(f"가운데 {cfg.center_ratio:.0%}")
        if cfg.adjacent:
            parts.append("연석")
        return "·".join(parts) or "설정된"

    def _verify_targets(self, targets: list[str]) -> list[str]:
        """미리 골라 둔 자리가 화면에서도 아직 고를 수 있는지 확인한다."""
        js = """
        const [sel, disabledMark, labels] = arguments;
        const ok = new Set();
        for (const el of document.querySelectorAll(sel)) {
          if ((el.className || '').toString().includes(disabledMark)) continue;
          ok.add(el.textContent.trim());
        }
        return labels.filter(l => ok.has(l));
        """
        cfg = self.sel["seatmap"]
        alive = self.driver.execute_script(
            js, cfg["seat"], cfg["disabled_marker"], targets
        )
        return alive if len(alive) == len(targets) else []

    def _read_seatmap(self) -> list[seatpick.Seat]:
        """화면의 좌석을 좌석 API와 같은 형태로 읽는다.

        같은 좌석이 미니맵과 본지도에 하나씩, 총 두 벌 렌더링된다. 라벨로 중복을
        걸러 내되 좌우 위치는 큰 쪽(본지도) 기준이어야 중앙 판정이 맞는다.
        가운데 자리를 재려면 팔린 자리도 있어야 하므로 전부 읽는다.
        """
        js = """
        const [sel, disabledMark, skipMarks] = arguments;
        const best = new Map();
        for (const el of document.querySelectorAll(sel)) {
          const label = (el.textContent || '').trim();
          if (!label) continue;
          const r = el.getBoundingClientRect();
          if (r.width <= 0) continue;
          const prev = best.get(label);
          if (prev && prev.w >= Math.round(r.width)) continue;
          const cls = (el.className || '').toString();
          best.set(label, {
            label,
            x: Math.round(r.x),
            w: Math.round(r.width),
            available: !cls.includes(disabledMark) && !skipMarks.some(m => cls.includes(m)),
          });
        }
        return Array.from(best.values());
        """
        cfg = self.sel["seatmap"]
        raw = (
            self.driver.execute_script(
                js, cfg["seat"], cfg["disabled_marker"], cfg.get("skip_markers", [])
            )
            or []
        )
        seats = []
        for s in raw:
            row, col = seatpick.parse_label(s["label"])
            if not row:
                continue
            seats.append(
                seatpick.Seat(row=row, col=col, x=s["x"], available=s["available"])
            )
        return seats

    def _verify_selected(self, labels: list[str]) -> None:
        """클릭이 실제로 먹었는지 선택 표시 클래스로 확인한다."""
        cfg = self.sel["seatmap"]
        js = """
        const [sel, mark, labels] = arguments;
        const hit = new Set();
        for (const el of document.querySelectorAll(sel)) {
          if ((el.className || '').toString().includes(mark)) hit.add(el.textContent.trim());
        }
        return labels.filter(l => !hit.has(l));
        """
        missing = self.driver.execute_script(
            js, cfg["seat"], cfg["selected_marker"], labels
        )
        if missing:
            raise SeatTakenError(f"좌석 선택이 반영되지 않았습니다: {', '.join(missing)}")

    def _click_seat(self, label: str) -> None:
        js = """
        const [sel, label, disabledMark] = arguments;
        const el = Array.from(document.querySelectorAll(sel)).find(e =>
          e.textContent.trim() === label && !(e.className || '').toString().includes(disabledMark));
        if (!el) return false;
        el.scrollIntoView({block: 'center'});
        el.click();
        return true;
        """
        cfg = self.sel["seatmap"]
        if not self.driver.execute_script(js, cfg["seat"], label, cfg["disabled_marker"]):
            raise SeatTakenError(f"좌석 클릭 실패: {label} (남이 먼저 가져간 듯)")
        time.sleep(0.3)

    def enter_payment(self) -> None:
        """'N원 결제하기' → 연령/취소규정 확인 모달 → /mpy/main 결제 페이지."""
        self._check_deadline("결제 진입")
        pay = self.sel["payment"]

        self._click(pay["enter"], timeout=10, wait=2.0)

        # 확인 모달은 안 뜨는 경우도 있어서 실패해도 넘어간다
        js = """
        const want = arguments[0];
        const b = Array.from(document.querySelectorAll('.modal-content button'))
          .find(x => x.innerText.trim() === want);
        if (!b) return false;
        b.click();
        return true;
        """
        self.driver.execute_script(js, pay["confirm_modal_button"])

        end = time.time() + 15
        while time.time() < end:
            if pay["page_url_marker"] in self.driver.current_url:
                time.sleep(1.5)
                return
            time.sleep(0.4)
        raise BookingError(f"결제 페이지로 넘어가지 못했습니다 (현재 {self.driver.current_url})")

    def read_amount(self) -> tuple[str, int]:
        """결제 버튼에 적힌 금액을 읽는다."""
        js = """
        const b = Array.from(document.querySelectorAll('button'))
          .find(x => x.innerText.includes('결제하기') && /[\\d,]+원/.test(x.innerText));
        return b ? b.innerText.replace(/\\s+/g, ' ').trim() : '';
        """
        text = self.driver.execute_script(js) or ""
        m = re.search(r"([\d,]+)\s*원", text)
        if not m:
            return "확인 불가", 0
        return m.group(0), int(m.group(1).replace(",", ""))

    def _select_pay_method(self) -> None:
        method = self.cfg.booking.pay_method
        if not method:
            return
        js = """
        const [sel, want] = arguments;
        for (const b of document.querySelectorAll(sel)) {
          const name = (b.innerText || '').trim() ||
                       (b.querySelector('img') || {}).alt || '';
          if (name.replace(/\\s+/g, '').toUpperCase() === want.replace(/\\s+/g, '').toUpperCase()) {
            b.scrollIntoView({block: 'center'});
            b.click();
            return name;
          }
        }
        return null;
        """
        hit = self.driver.execute_script(js, self.sel["payment"]["method_button"], method)
        if not hit:
            raise BookingError(f"결제수단 '{method}'을 화면에서 못 찾았습니다")
        time.sleep(2.0)

    def pay(self) -> tuple[str, str]:
        """결제 페이지에서 결제수단을 고르고 결제한다. dry-run이면 직전에 멈춘다."""
        self._check_deadline("결제")
        pay = self.sel["payment"]

        if pay["expired_marker"] in self._text():
            raise SeatTakenError("좌석 선점 시간이 만료되어 결제하지 못했습니다")

        self._select_pay_method()
        self._check_agree_all()

        amount_text, amount = self.read_amount()
        limit = self.cfg.booking.max_price_krw
        if amount and amount > limit:
            raise BookingError(f"결제금액 {amount:,}원이 상한 {limit:,}원을 넘어 중단합니다")

        if self.dry_run or not self.cfg.booking.auto_pay:
            return amount_text, ""

        self._click(pay["pay_button"], timeout=10, wait=3.0)

        if self.cfg.pays_with_toss:
            self._pay_toss(amount_text)
        else:
            self._enter_pay_password()
        return amount_text, self._read_booking_no()

    # ---- 토스페이 ------------------------------------------------------

    def _is_toss(self) -> bool:
        return self.sel["toss"]["url_marker"] in self.driver.current_url

    def _pay_toss(self, amount_text: str) -> None:
        """토스 결제 알림을 사용자 폰으로 보내고, 승인될 때까지 기다린다.

        토스는 카드 정보를 우리가 들고 있을 필요가 없다. 번호와 생년월일만 넣으면
        앱으로 알림이 가고, 승인은 사람이 폰에서 한다. 밖에 있어도 예매가 된다.
        """
        toss = self.sel["toss"]
        phone, birth = self.cfg.toss_phone, self.cfg.toss_birth
        if not (phone and birth):
            raise BookingError(
                "토스 결제에는 .env 의 TOSS_PHONE 과 TOSS_BIRTH6 이 필요합니다"
            )

        self._switch_to_toss()
        self._open_toss_phone_tab()

        self._fill(toss["phone_input"], self._digits_or_self(phone, phone=True))
        self._fill(toss["birth_input"], birth)
        self._submit_toss_form()
        time.sleep(2.0)

        shot = self._toss_qr() or screenshot(self.driver, "toss-approve")
        self.notify.toss_pending(
            self._showtime, self._seats, amount_text, self._left(), image=shot
        )
        print(f"      토스 알림 발송. 폰에서 승인 대기 (남은 {self._left():.0f}초)", flush=True)

        self._wait_for_toss_approval()

    def _open_toss_phone_tab(self) -> None:
        if not self._try_click([f"text:{self.sel['toss']['phone_tab']}"], timeout=5):
            js = """
            const el = Array.from(document.querySelectorAll('*'))
              .find(e => e.children.length === 0 && (e.textContent || '').trim() === arguments[0]);
            if (!el) return false;
            (el.closest('button, a, li, [role="tab"]') || el).click();
            return true;
            """
            if not self.driver.execute_script(js, self.sel["toss"]["phone_tab"]):
                raise BookingError("토스 '휴대폰번호' 탭을 못 찾았습니다")
        time.sleep(1.5)

    @staticmethod
    def _digits_or_self(value: str, phone: bool = False) -> str:
        digits = re.sub(r"\D", "", value)
        if phone and len(digits) == 11:
            return f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"
        return value

    def _submit_toss_form(self) -> None:
        """번호와 생년월일을 넣은 뒤 알림을 보낸다.

        두 칸을 채우면 바로 알림 대기 화면으로 넘어가는 경우가 있다.
        그때는 보낼 버튼이 이미 없으므로, 대기 화면이면 성공으로 본다.
        """
        if self._toss_waiting_approval():
            print("      토스 전송: 이미 알림 대기 화면", flush=True)
            return
        js = """
        const labels = ['알림 보내기', '보내기', '확인', '다음', '결제하기'];
        const btns = Array.from(document.querySelectorAll('button, [role="button"]'))
          .filter(b => b.getBoundingClientRect().width > 0 && !b.disabled);
        for (const want of labels) {
          const hit = btns.find(b => (b.innerText || '').trim() === want);
          if (hit) { hit.click(); return want; }
        }
        const birth = document.querySelector(arguments[0]);
        if (birth) {
          birth.dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter', bubbles: true}));
          birth.dispatchEvent(new KeyboardEvent('keyup', {key: 'Enter', bubbles: true}));
          if (birth.form) birth.form.dispatchEvent(new Event('submit', {bubbles: true, cancelable: true}));
          return 'enter';
        }
        return null;
        """
        outcome = self.driver.execute_script(js, self.sel["toss"]["birth_input"])
        time.sleep(1.5)
        if self._toss_waiting_approval():
            print(f"      토스 전송: {outcome or '자동이동'}", flush=True)
            return
        if not outcome:
            raise BookingError("토스에서 결제 알림 보내기 버튼을 못 찾았습니다")
        print(f"      토스 전송: {outcome}", flush=True)

    def _toss_waiting_approval(self) -> bool:
        url = self.driver.current_url
        text = self._text()
        return (
            "/app-payment/push" in url
            or "알림을 눌러" in text
            or "결제를 진행해주세요" in text
        )

    def _switch_to_toss(self) -> None:
        """토스가 새 창으로 열리는 경우가 있어 창을 찾아 옮겨간다."""
        marker = self.sel["toss"]["url_marker"]
        end = time.time() + 20
        while time.time() < end:
            for handle in self.driver.window_handles:
                self.driver.switch_to.window(handle)
                if marker in self.driver.current_url:
                    return
            time.sleep(0.5)
        raise BookingError("토스 결제창이 열리지 않았습니다")

    def _fill(self, selector: str, value: str) -> None:
        """React 입력칸은 value를 직접 넣으면 무시당해서 setter + input 이벤트가 필요하다."""
        js = """
        const [sel, val] = arguments;
        const el = document.querySelector(sel);
        if (!el) return false;
        const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
        el.focus();
        setter.call(el, val);
        el.dispatchEvent(new Event('input', { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
        return true;
        """
        end = time.time() + 10
        while time.time() < end:
            if self.driver.execute_script(js, selector, value):
                time.sleep(0.6)
                return
            time.sleep(0.3)
        raise BookingError(f"토스 입력칸을 못 찾음: {selector}")

    def _toss_qr(self) -> Path | None:
        """알림을 못 받았을 때를 대비해 QR코드를 이미지로 남긴다."""
        js = """
        const el = document.querySelector(arguments[0]);
        return el ? el.src : null;
        """
        try:
            self._click([f"text:{self.sel['toss']['qr_tab']}"], timeout=5, wait=1.5)
            src = self.driver.execute_script(js, self.sel["toss"]["qr_image"])
        except (BookingError, WebDriverException):
            return None
        if not src or "," not in src:
            return None
        path = SHOTS / f"{time.strftime('%Y%m%d-%H%M%S')}-toss-qr.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(base64.b64decode(src.split(",", 1)[1]))
        return path

    def _wait_for_toss_approval(self) -> None:
        marker = self.sel["toss"]["done_url_marker"]
        while self._left() > 20:
            for handle in self.driver.window_handles:
                try:
                    self.driver.switch_to.window(handle)
                except WebDriverException:
                    continue
                if marker in self.driver.current_url and self.is_complete():
                    return
            time.sleep(2.0)
        raise BookingError(
            "제한 시간 안에 토스 결제가 승인되지 않았습니다. 좌석이 풀렸을 수 있습니다."
        )

    def _check_agree_all(self) -> None:
        """전체 약관 동의. 이미 체크돼 있으면 두 번 눌러 풀지 않도록 확인한다."""
        js = """
        const el = document.querySelector(arguments[0]);
        if (!el) return 'missing';
        if (el.checked) return 'already';
        (el.closest('label') || el).click();
        return el.checked ? 'checked' : 'failed';
        """
        outcome = self.driver.execute_script(js, self.sel["payment"]["agree_all"])
        if outcome in ("missing", "failed"):
            raise BookingError(f"약관 전체동의를 체크하지 못했습니다 ({outcome})")
        time.sleep(0.5)

    def _enter_pay_password(self) -> None:
        """결제수단이 간편결제 비밀번호를 물어보면 채운다."""
        if not self.cfg.pay_password:
            return
        js = """
        const pw = arguments[0];
        const el = Array.from(document.querySelectorAll('input[type="password"], input[type="tel"]'))
          .find(i => i.getBoundingClientRect().width > 0 && !i.value);
        if (!el) return false;
        const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
        setter.call(el, pw);
        el.dispatchEvent(new Event('input', { bubbles: true }));
        return true;
        """
        for _ in range(12):
            if self.driver.execute_script(js, self.cfg.pay_password):
                time.sleep(2.0)
                return
            time.sleep(0.5)

    def _read_booking_no(self) -> str:
        text = self._text()
        m = re.search(r"예매번호[^\dA-Za-z]{0,8}([A-Za-z0-9-]{6,})", text)
        if m:
            return m.group(1)
        m = re.search(r"[?&]salNo=(\d+)", self.driver.current_url)
        return m.group(1) if m else ""

    def is_complete(self) -> bool:
        marker = self.sel.get("complete", {}).get("page_url_marker", "")
        if marker and marker in self.driver.current_url:
            return True
        text = self._text()
        return any(
            m[5:] in text
            for m in self.sel["complete"]["markers"]
            if m.startswith("text:")
        )

    # ---- 전체 흐름 -----------------------------------------------------

    def book(self, showtime, targets: list[str] | None = None) -> BookingResult:
        # 대기열은 선점 시계가 돌기 전에 빠진다
        self.deadline = 0.0
        self._wait_queue()
        self.deadline = time.time() + self.cfg.booking.hold_timeout_sec
        # 감시가 이미 몇 석을 잡을 수 있는지 확인했다면 그 수를 따른다
        count = len(targets) if targets else self.cfg.seats.count
        self._showtime, self._seats = showtime, ""

        try:
            print(f"  1/6 회차 진입: {showtime}", flush=True)
            self.open_showtime(showtime)

            print("  2~3/6 인원·좌석 선택", flush=True)
            seats = self._pick_with_fallback(count, targets)
            self._seats = ", ".join(seats)
            print(f"      선택: {self._seats} (남은 시간 {self._left():.0f}초)", flush=True)

            print("  4/6 결제 페이지 진입", flush=True)
            self.enter_payment()

            print("  5/6 결제", flush=True)
            amount, booking_no = self.pay()
        except BookingError as exc:
            # 어느 단계에서 막혔는지 눈으로 봐야 셀렉터를 고칠 수 있다
            shot = screenshot(self.driver, "booking-failed")
            print(f"      실패 화면 저장: {shot}", flush=True)
            raise BookingError(f"{exc}\n실패 화면: {shot}") from exc
        except queue.QueueError as exc:
            shot = screenshot(self.driver, "queue-stuck")
            raise BookingError(f"{exc}\n실패 화면: {shot}") from exc

        if self.dry_run or not self.cfg.booking.auto_pay:
            shot = screenshot(self.driver, "dryrun-before-pay")
            print(f"  6/6 dry-run: 결제 직전에서 멈춤. 금액 {amount}", flush=True)
            return BookingResult(
                ok=False,
                seats=", ".join(seats),
                amount=amount,
                stopped_before_payment=True,
                shot=shot,
            )

        ok = self.is_complete() or bool(booking_no)
        shot = screenshot(self.driver, "result-success" if ok else "result-unknown")
        print(f"  6/6 {'완료' if ok else '완료 확인 실패'} / 예매번호 {booking_no or '미확인'}", flush=True)

        if not ok:
            raise BookingError(f"결제 후 완료 화면을 확인하지 못했습니다. 스크린샷: {shot}")

        return BookingResult(
            ok=True, seats=", ".join(seats), amount=amount, booking_no=booking_no, shot=shot
        )
