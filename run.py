#!/usr/bin/env python3
"""CGV 예매 자동화 진입점.

    python run.py                # 감시 + 자동예매
    python run.py --dry-run      # 결제 직전까지만
    python run.py --list         # 지금 조건에 맞는 회차만 출력하고 종료

맥이 잠들면 감시가 멈추므로 실제 운용은 caffeinate로 감싸는 편이 좋다.
    caffeinate -dimsu python run.py
"""

from __future__ import annotations

import argparse
import sys
import time
import traceback
from pathlib import Path

from selenium.common.exceptions import WebDriverException

from src import browser, cgv, config
from src.booker import Booker, BookingError, BookingResult, NoSelectableSeats
from src.notify import Notifier
from src.multi import MultiWatcher
from src.renew import SessionRenewer
from src.session import SessionGuard
from src.watcher import Watcher


class AttemptTracker:
    """회차별 재시도 간격을 관리한다.

    잔여석으로 잡히지만 실제로는 예매할 수 없는 좌석(휠체어석 등)이 남아 있으면
    같은 회차에 무한히 달려들며 디스코드를 도배하게 된다. 실패할수록 그 회차만
    뒤로 미룬다.
    """

    BACKOFF = [20, 60, 300, 900, 1800]

    def __init__(self):
        self.next_try: dict[str, float] = {}
        self.failures: dict[str, int] = {}

    def may_attempt(self, key: str) -> bool:
        return time.time() >= self.next_try.get(key, 0.0)

    def record_failure(self, key: str) -> float:
        n = self.failures.get(key, 0)
        self.failures[key] = n + 1
        wait = self.BACKOFF[min(n, len(self.BACKOFF) - 1)]
        self.next_try[key] = time.time() + wait
        return wait

    def reset(self, key: str) -> None:
        self.failures.pop(key, None)
        self.next_try.pop(key, None)


def build_notifier(cfg, quiet: bool = False) -> Notifier:
    n = cfg.notify
    return Notifier(
        webhook_url=n.webhook_url,
        enabled={
            "on_showtime_open": n.on_showtime_open,
            "on_seat_found": n.on_seat_found,
            "on_success": n.on_success,
            "on_failure": n.on_failure,
            "on_blocked": n.on_blocked,
        },
        quiet=quiet,
    )


def cmd_list(watchers, cfg, notifier) -> int:
    total = 0
    for w in watchers:
        print(f"\n[{w.theater.name}]")
        w.refresh_open_dates()
        print(f"  예매 열린 날짜 {len(w.known_open_dates)}개")
        found = 0
        for ymd in sorted(w.known_open_dates):
            for s in w.scan_date(ymd):
                found += 1
                held = f" (+{s.held_seats}석 선점중)" if s.held_seats else ""
                print(f"    {s}{held}")
        if not found:
            print("    조건에 맞는 회차가 아직 없습니다. 오픈을 기다리면 됩니다.")
        total += found
    print(f"\n합계 {total}건")
    return 0


def build_watchers(driver, cfg, notifier, guard=None):
    """극장마다 API 클라이언트와 감시자를 하나씩 만든다."""
    watchers = []
    for t in cfg.theaters:
        api = cgv.CgvApi(driver, site_no=t.site_no, theater_name=t.name)
        watchers.append(Watcher(api, cfg, notifier, session_guard=guard, theater=t))
    return watchers


def main() -> int:
    parser = argparse.ArgumentParser(description="CGV 용아맥 예매봇")
    parser.add_argument("--dry-run", action="store_true", help="결제 버튼 직전까지만 진행")
    parser.add_argument("--list", action="store_true", help="조건에 맞는 회차를 출력하고 종료")
    parser.add_argument("--port", type=int, default=browser.DEFAULT_PORT)
    parser.add_argument("--quiet", action="store_true", help="콘솔 로그 최소화")
    parser.add_argument("--test-notify", action="store_true", help="디스코드 알림만 시험 발송")
    parser.add_argument(
        "--config",
        metavar="PATH",
        help="쓸 설정 파일. 기본은 config.yaml. 실제 설정을 건드리지 않고 "
             "다른 극장·영화로 예행연습할 때 쓴다 (config.test.yaml 참고)",
    )
    args = parser.parse_args()

    try:
        cfg = config.load(Path(args.config)) if args.config else config.load()
        if args.config:
            print(f"[설정] {args.config}")
        if not (args.dry_run or args.list or args.test_notify):
            cfg.require_payment_ready()
    except config.ConfigError as exc:
        print(f"[설정 오류] {exc}")
        return 2

    notifier = build_notifier(cfg, quiet=args.quiet)

    if args.test_notify:
        if not notifier.active:
            print("[알림] .env 의 DISCORD_WEBHOOK_URL 이 비어 있습니다.")
            return 2
        notifier.send(
            "알림 연결 확인",
            f"{cfg.theater.name} / {cfg.movie_title} 감시 준비 완료.\n"
            "이 메시지가 보이면 웹후크 설정이 정상입니다.",
        )
        print("디스코드로 시험 메시지를 보냈습니다.")
        return 0

    print("Chrome 준비 중...")
    browser.launch_chrome(port=args.port, url=browser.BOOKING_URL)
    driver = browser.attach_driver(args.port)

    # 세션 확인·갱신은 극장과 무관하므로 대표 극장 하나로 충분하다
    api = cgv.CgvApi(driver, site_no=cfg.theater.site_no, theater_name=cfg.theater.name)

    # 조회는 비로그인으로도 되므로 --list는 로그인을 기다리지 않는다
    if args.list:
        return cmd_list(build_watchers(driver, cfg, notifier), cfg, notifier)

    browser.wait_for_login(driver, api.is_logged_in)

    booker = Booker(driver, cfg, notifier, dry_run=args.dry_run)
    guard = SessionGuard(
        api,
        notifier,
        check_every_sec=cfg.session.check_every_sec,
        keepalive_every_sec=cfg.session.keepalive_every_sec or float("inf"),
        renotify_every_sec=cfg.session.renotify_every_sec,
        confirm_times=cfg.session.confirm_times,
        renewer=SessionRenewer(api, browser.CGV_HOME) if cfg.session.auto_renew else None,
    )
    watchers = build_watchers(driver, cfg, notifier, guard)
    by_site = {w.theater.site_no: w for w in watchers}
    driver_loop = MultiWatcher(watchers, cfg, notifier)

    mode = "결제 직전까지 (dry-run)" if args.dry_run else (
        "자동 결제까지" if cfg.booking.auto_pay else "결제 직전까지"
    )
    lo, hi = cfg.polling.interval_sec
    notifier.startup(
        "\n".join(
            f"{t.name} / {'·'.join(t.screen_keywords)}" for t in cfg.theaters
        )
        + f"\n영화: {cfg.movie_title}\n"
        f"{cfg.date_from} ~ {cfg.date_to}, {cfg.seats.count}석\n"
        f"동작: {mode} / 확인 주기 {lo:.0f}~{hi:.0f}초"
        + (f" (극장 {len(cfg.theaters)}곳을 번갈아 봅니다)\n" if len(cfg.theaters) > 1 else "\n")
        +         f"로그인 세션도 {cfg.session.check_every_sec:.0f}초마다 확인합니다"
        + (", 끊기면 스스로 갱신해 보고 안 되면 알립니다." if cfg.session.auto_renew
           else ", 끊기면 알립니다.")
    )

    successes = 0
    tracker = AttemptTracker()

    def on_hit(showtime, theater) -> bool:
        nonlocal successes

        if not tracker.may_attempt(showtime.key):
            return False

        # 회차가 들고 온 site_no 로 주인 감시자를 찾는다. 목록 순서나 클로저에
        # 기대지 않는다. 엉뚱한 감시자의 targets 를 쓰면 다른 극장 좌석을 누른다.
        watcher = by_site.get(showtime.site_no)
        if watcher is None:
            # 여기 오면 회차에 극장 표시가 안 붙은 것이다. 감시를 죽이지는 않는다.
            print(f"  [무시] 극장을 알 수 없는 회차입니다: {showtime}", flush=True)
            return False
        targets = watcher.targets.get(showtime.key) or []
        notifier.seat_found(showtime, len(targets) or showtime.seats_free)
        try:
            result: BookingResult = booker.book(showtime, targets, theater=theater)
        except NoSelectableSeats as exc:
            # 좌석맵 확인과 실제 진입 사이에 남이 채갔거나, 조건(연석·선호열)이 너무 좁다.
            watcher.invalidate_seats(showtime)
            wait = tracker.record_failure(showtime.key)
            # 20초는 '이 회차에 다시 들어가도 되는 최소 간격'일 뿐이다.
            # 실제 재진입은 좌석맵이 바뀌어 다시 후보가 될 때 일어난다.
            print(f"  [건너뜀] {showtime}: {exc} (좌석이 바뀌면 다시 봅니다, 최소 {wait:.0f}초)", flush=True)
            return False
        except BookingError as exc:
            if "로그인" in str(exc):
                guard.force_check()  # 세션 만료 알림을 다음 턴까지 미루지 않는다
            watcher.invalidate_seats(showtime)
            wait = tracker.record_failure(showtime.key)
            notifier.failure(f"{exc}\n좌석이 바뀌면 다시 시도합니다 (최소 {wait:.0f}초).", showtime)
            return False
        except Exception as exc:  # 예상 못한 오류가 나도 감시는 계속한다
            traceback.print_exc()
            wait = tracker.record_failure(showtime.key)
            notifier.failure(f"예기치 못한 오류: {exc}\n{wait:.0f}초 뒤 재시도", showtime)
            return False

        tracker.reset(showtime.key)

        if result.stopped_before_payment:
            notifier.send(
                "dry-run: 결제 직전에서 멈춤",
                f"{showtime}\n좌석 {result.seats} / 금액 {result.amount}\n"
                "10분 안에 직접 결제하거나 창을 닫으세요.",
                image=result.shot,
                mention=True,
            )
            return True

        successes += 1
        notifier.success(showtime, result.seats, result.amount, image=result.shot)
        return successes >= cfg.booking.max_bookings

    try:
        driver_loop.run(on_hit)
    except KeyboardInterrupt:
        print("\n중단했습니다.")
        return 130
    except WebDriverException as exc:
        msg = "브라우저 연결이 끊겼습니다. Chrome 창을 닫았는지 확인하세요."
        print(f"[중단] {msg}\n  {exc}")
        notifier.send("감시 중단", msg, mention=True)
        return 1

    print("목표 예매를 완료했습니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
