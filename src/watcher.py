"""취소표 감시와 신규 오픈 대기를 하나의 루프로 돌린다.

두 상황은 결국 같은 질문이다. "조건에 맞으면서 잔여석이 있는 회차가 존재하는가."
차이는 회차 자체가 아직 없느냐뿐이라, 같은 루프에서 처리한다.

요청 수를 아끼려고 날짜를 세 부류로 나눠 다르게 본다.
  - 활성 날짜: 조건에 맞는 회차가 이미 있는 날. 매 턴 확인한다.
  - 후보 날짜: 예매는 열렸지만 조건에 맞는 회차가 없는 날. 매 턴 하나씩 순회한다.
  - 미오픈 날짜: 아직 예매가 안 열린 날. 날짜 목록 API로만 감시한다.
"""

from __future__ import annotations

import random
import time
from datetime import datetime

from . import seatpick
from .cgv import BlockedError, CgvApi, CgvError, Showtime, daterange

OPEN_DATES_EVERY = 6  # N턴마다 예매 가능 날짜 목록을 다시 본다
SEAT_CHECKS_PER_POLL = 8  # 한 턴에 좌석맵까지 확인할 회차 수 상한


class Watcher:
    def __init__(self, api: CgvApi, cfg, notifier, session_guard=None):
        self.api = api
        self.cfg = cfg
        self.notify = notifier
        self.session = session_guard

        self.wanted_dates = set(daterange(cfg.date_from, cfg.date_to))
        if cfg.only_dates:
            self.wanted_dates &= set(cfg.only_dates)

        self.active_dates: list[str] = []
        self.candidate_dates: list[str] = []
        self.known_open_dates: set[str] = set()
        self.known_showtimes: set[str] = set()
        # 회차key -> (그때 본 frSeatCnt, 조건에 맞아 고른 좌석 라벨).
        # 잔여석 숫자가 그대로면 좌석맵을 다시 받지 않는다.
        self._seat_check: dict[str, tuple[int, list[str]]] = {}
        # 예매가 노려야 할 좌석. 감시가 고른 그대로 booker에 넘긴다.
        self.targets: dict[str, list[str]] = {}

        self._tick = 0
        self._rr = 0  # 후보 날짜 순회 위치
        self._backoff = 0.0
        self._first_scan_done = False
        self._last_heartbeat = time.time()

    # ---- 조건 매칭 -----------------------------------------------------

    def matches(self, s: Showtime) -> bool:
        cfg = self.cfg
        if cfg.movie_title and cfg.movie_title not in s.movie:
            return False

        keywords = cfg.theater.screen_keywords
        if keywords:
            haystack = f"{s.screen} {s.special_grade} {s.fmt}".upper()
            if not any(k.upper() in haystack for k in keywords):
                return False

        start = s.start_minutes
        if start < 0 or not (cfg.after_min <= start <= cfg.before_min):
            return False

        if cfg.weekdays_only and len(s.date) == 8:
            try:
                if datetime.strptime(s.date, "%Y%m%d").weekday() >= 5:
                    return False
            except ValueError:
                pass

        return True

    # ---- 스캔 ----------------------------------------------------------

    def scan_date(self, ymd: str) -> list[Showtime]:
        return [s for s in self.api.showtimes(ymd) if self.matches(s)]

    def refresh_open_dates(self) -> list[str]:
        """예매 가능 날짜를 갱신하고, 우리가 기다리던 날짜가 새로 열렸는지 본다."""
        opened = [d for d in self.api.open_dates() if d in self.wanted_dates]
        newly = [d for d in opened if d not in self.known_open_dates]
        self.known_open_dates.update(opened)

        known = set(self.active_dates) | set(self.candidate_dates)
        for d in opened:
            if d not in known:
                self.candidate_dates.append(d)
        # 사라진 날짜(상영 종료) 정리
        self.active_dates = [d for d in self.active_dates if d in self.known_open_dates]
        self.candidate_dates = [d for d in self.candidate_dates if d in self.known_open_dates]
        return newly

    def _promote(self, ymd: str, hits: list[Showtime]) -> None:
        """조건에 맞는 회차가 생긴 날짜는 활성으로 올린다."""
        if hits and ymd not in self.active_dates:
            self.active_dates.append(ymd)
            if ymd in self.candidate_dates:
                self.candidate_dates.remove(ymd)
        elif not hits and ymd in self.active_dates:
            self.active_dates.remove(ymd)
            if ymd not in self.candidate_dates:
                self.candidate_dates.append(ymd)

    def _note_new_showtimes(self, found: list[Showtime]) -> list[Showtime]:
        fresh = [s for s in found if s.key not in self.known_showtimes]
        self.known_showtimes.update(s.key for s in found)
        # 첫 스캔 결과 전체를 "새로 열림"으로 알리면 시끄럽다
        return [] if not self._first_scan_done else fresh

    def poll_once(self) -> tuple[list[Showtime], list[Showtime]]:
        """(예매 가능한 회차, 새로 열린 회차) 를 돌려준다."""
        self._tick += 1
        newly_opened_dates: list[str] = []

        if self._tick == 1 or self._tick % OPEN_DATES_EVERY == 0:
            newly_opened_dates = self.refresh_open_dates()

        dates_to_scan = list(self.active_dates)

        # 첫 턴에는 전부 훑어 기준선을 만든다
        if not self._first_scan_done:
            dates_to_scan = sorted(self.known_open_dates)
        elif newly_opened_dates:
            dates_to_scan += [d for d in newly_opened_dates if d not in dates_to_scan]
        elif self.candidate_dates:
            # 후보는 매 턴 하나씩만 확인해 요청 수를 억제한다
            self._rr %= len(self.candidate_dates)
            pick = self.candidate_dates[self._rr]
            self._rr += 1
            if pick not in dates_to_scan:
                dates_to_scan.append(pick)

        all_hits: list[Showtime] = []
        for ymd in dates_to_scan:
            hits = self.scan_date(ymd)
            self._promote(ymd, hits)
            all_hits.extend(hits)

        fresh = self._note_new_showtimes(all_hits)
        if not self._first_scan_done:
            self._first_scan_done = True

        return self._verify_seats(all_hits), fresh

    # ---- 좌석 실검증 ---------------------------------------------------

    def _verify_seats(self, hits: list[Showtime]) -> list[Showtime]:
        """잔여석이 있어 보이는 회차만 좌석맵으로 진짜인지 확인한다.

        예매를 실제로 할 때와 똑같은 조건(seatpick)으로 고른다. 감시가 "자리 났다"고
        본 근거와 예매가 고르는 자리가 같아야, 조건에 안 맞는 회차에 헛되이 들어갔다
        나오는 일이 없다.
        """
        need = self.cfg.seats.min_count
        candidates = [s for s in hits if s.seats_free >= need]
        # 잔여석이 많은 쪽부터. 한 턴에 너무 많이 조회하면 차단 위험이 커진다.
        candidates.sort(key=lambda s: -s.seats_free)

        bookable, checks = [], 0
        for s in candidates:
            cached = self._seat_check.get(s.key)
            if cached is not None and cached[0] == s.seats_free:
                # 잔여석 숫자가 그대로면 좌석맵도 그대로다. 다시 받지 않는다.
                if cached[1]:
                    self.targets[s.key] = cached[1]
                    bookable.append(s)
                continue
            if checks >= SEAT_CHECKS_PER_POLL:
                continue
            checks += 1
            try:
                chosen = seatpick.choose_best(self.api.seat_map(s), self.cfg.seats)
            except BlockedError:
                raise
            except CgvError as exc:
                print(f"  [좌석 확인 실패] {s}: {exc}", flush=True)
                continue

            labels = [x.label for x in chosen]
            self._seat_check[s.key] = (s.seats_free, labels)
            if labels:
                self.targets[s.key] = labels
                bookable.append(s)
        return bookable

    def invalidate_seats(self, s: Showtime) -> None:
        """예매를 시도했다면 캐시가 낡았으니 다음 턴에 다시 확인하게 한다."""
        self._seat_check.pop(s.key, None)
        self.targets.pop(s.key, None)

    # ---- 대기 시간 -----------------------------------------------------

    def _in_burst_window(self) -> bool:
        at = self.cfg.polling.burst_at
        if not at:
            return False
        try:
            hh, mm = (int(x) for x in at.split(":"))
        except ValueError:
            return False
        now = datetime.now()
        target = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
        delta = (now - target).total_seconds()
        return 0 <= delta <= self.cfg.polling.burst_window_sec

    def sleep_interval(self) -> float:
        if self._backoff > 0:
            wait, self._backoff = self._backoff, 0.0
            return wait
        if self._in_burst_window():
            return self.cfg.polling.burst_interval_sec
        lo, hi = self.cfg.polling.interval_sec
        return random.uniform(lo, hi)

    def _raise_backoff(self) -> float:
        p = self.cfg.polling
        self._backoff = min(
            p.backoff_max_sec,
            max(p.backoff_start_sec, self._backoff * 2 if self._backoff else p.backoff_start_sec),
        )
        return self._backoff

    def _maybe_heartbeat(self) -> None:
        every = self.cfg.notify.heartbeat_min
        if not every:
            return
        if time.time() - self._last_heartbeat < every * 60:
            return
        self._last_heartbeat = time.time()
        watching = ", ".join(self.active_dates) or "(조건에 맞는 회차 없음)"
        login = "" if self.session is None else (
            "\n로그인: 정상" if self.session.logged_in else "\n로그인: **끊김 (재로그인 필요)**"
        )
        self.notify.heartbeat(
            f"{self._tick}턴 확인함\n감시 중인 날짜: {watching}\n"
            f"예매 열린 날짜: {len(self.known_open_dates)}개{login}"
        )

    # ---- 메인 루프 -----------------------------------------------------

    def run(self, on_hit) -> None:
        """on_hit(showtime) -> True 면 루프를 끝낸다."""
        while True:
            try:
                can_book = self.session.tick() if self.session else True
                bookable, fresh = self.poll_once()

                if fresh:
                    self.notify.showtime_open(fresh)

                # 로그아웃 상태면 시도해봐야 로그인 안내창만 뜬다. 감시는 계속한다.
                if can_book:
                    for s in sorted(
                        bookable, key=lambda x: (-x.seats_free, x.date, x.start_minutes)
                    ):
                        if on_hit(s):
                            return
                elif bookable:
                    print(
                        f"  [로그인 끊김] 예매 가능 회차 {len(bookable)}건을 찾았지만 시도하지 못함",
                        flush=True,
                    )

                self._maybe_heartbeat()

            except BlockedError as exc:
                wait = self._raise_backoff()
                self.notify.blocked(str(exc), wait)
            except CgvError as exc:
                print(f"  [API 오류] {exc}", flush=True)
                self._backoff = max(self._backoff, 15.0)

            time.sleep(self.sleep_interval())
