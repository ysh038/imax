#!/usr/bin/env python3
"""설정한 좌석 조건이 각 극장 배치에서 실제로 통하는지 본다.

    python tools/check_seats.py                      # config.yaml
    python tools/check_seats.py --config config.test.yaml
    python tools/check_seats.py --shows 10           # 극장마다 볼 회차 수

극장을 새로 추가했을 때 쓴다. 관마다 열 구성과 폭이 달라서, 한 극장에 맞춰
둔 min_row / center_ratio 가 다른 극장에서는 아무것도 통과시키지 못할 수 있다.
그러면 감시는 도는데 영원히 예매하지 않는다. 조용히 실패하는 종류라 눈으로
확인해야 한다.

읽기만 한다. 예매하지 않는다.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import browser, cgv, config, seatpick  # noqa: E402
from src.watcher import Watcher  # noqa: E402


class _Quiet:
    def __getattr__(self, _):
        return lambda *a, **kw: None


def _only(min_row="", center_ratio=1.0):
    o = type("O", (), {})()
    o.min_row, o.avoid_rows, o.center_ratio = min_row, [], center_ratio
    return o


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", metavar="PATH")
    ap.add_argument("--shows", type=int, default=8, help="극장마다 좌석맵을 볼 회차 수")
    args = ap.parse_args()

    cfg = config.load(Path(args.config)) if args.config else config.load()
    cfg.validate()
    s = cfg.seats
    print(f"좌석 조건: {s.count}석(최소 {s.min_count}) / 연석={s.adjacent} / "
          f"min_row={s.min_row or '없음'} / center_ratio={s.center_ratio}\n")

    browser.launch_chrome(url=browser.CGV_HOME)
    driver = browser.attach_driver()

    trouble = []
    for t in cfg.theaters:
        api = cgv.CgvApi(driver, site_no=t.site_no, theater_name=t.name)
        w = Watcher(api, cfg, _Quiet(), theater=t)
        w.refresh_open_dates()

        print(f"===== {t.name} =====")
        rows = None
        checked = hit = 0
        for ymd in sorted(w.known_open_dates):
            for show in w.scan_date(ymd):
                if checked >= args.shows:
                    break
                seats = api.seat_map(show)
                if not seats:
                    continue
                checked += 1
                if rows is None:
                    rows = sorted({x.row for x in seats}, key=seatpick.row_key)
                free = [x for x in seats if x.available]
                pool = seatpick.eligible(seats, s)
                best = seatpick.choose_best(seats, s)
                if best:
                    hit += 1
                print(f"  {show.pretty_date()} {show.start}  API {show.seats_free:3}석 / "
                      f"구매가능 {len(free):3}석 / 조건통과 {len(pool):3}석 -> "
                      f"{[x.label for x in best] or '없음'}")
            if checked >= args.shows:
                break

        if rows:
            print(f"  열 구성: {rows[0]}~{rows[-1]} ({len(rows)}개 열)")
        if not checked:
            print("  조건에 맞는 회차가 없어 좌석맵을 못 봤습니다.")
        else:
            print(f"  {checked}건 중 잡을 자리가 나온 회차 {hit}건")
            if hit == 0:
                trouble.append(t.name)
        print()

    if trouble:
        print("[확인 필요] 아래 극장은 본 회차 전부에서 조건 통과 0석이었습니다.")
        for name in trouble:
            print(f"  - {name}")
        print("  남은 자리가 원래 나쁜 자리뿐일 수도 있고(정상), 그 관 배치에")
        print("  min_row / center_ratio 가 안 맞는 것일 수도 있습니다. 위의")
        print("  '구매가능' 대비 '조건통과' 숫자를 보고 판단하세요.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
