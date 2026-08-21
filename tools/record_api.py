#!/usr/bin/env python3
"""CGV 예매 흐름을 수동으로 한 번 걸어가며 실제 API를 녹화한다.

    python tools/record_api.py

Chrome이 뜨면 로그인 후 극장 -> 상영시간표 -> 좌석 -> 결제창까지 진행하세요.
Ctrl+C로 끝내면 docs/cgv_api.md와 endpoints.yaml 후보가 생성됩니다.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import browser, recorder  # noqa: E402
from src.endpoints import guess_endpoints, write_endpoints  # noqa: E402

GUIDE = """
====================================================================
 CGV API 녹화기
====================================================================
 열린 Chrome 창에서 아래 순서대로 '천천히' 진행해 주세요.
 각 단계 사이에 1~2초씩 쉬면 요청이 확실히 잡힙니다.

   1. 로그인 (최초 1회. 이후에는 프로필에 저장됩니다)
   2. 예매 -> 극장 선택에서 'CGV 용산아이파크몰' 선택
   3. 날짜를 두세 개 눌러 상영시간표를 불러오기
   4. IMAX 회차 클릭 -> 좌석 선택 화면 진입
   5. 인원 선택 후 좌석 하나 클릭했다가 해제
   6. 결제 단계까지 진입 (결제는 하지 마세요)
   7. 이 터미널에서 Ctrl+C

 [중요] 6번에서 결제수단 화면까지 들어가야 결제 API가 잡힙니다.
====================================================================
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="CGV API 녹화기")
    parser.add_argument("--port", type=int, default=browser.DEFAULT_PORT)
    parser.add_argument("--interval", type=float, default=1.0, help="회수 주기(초)")
    parser.add_argument("--url", default=browser.BOOKING_URL)
    args = parser.parse_args()

    print("Chrome 실행 중...")
    browser.launch_chrome(port=args.port, url=args.url)
    print(GUIDE)

    rec = recorder.Recorder(args.port)
    seen: set[str] = set()
    tabs = 0

    try:
        while True:
            try:
                n = rec.sync_targets()
                if n != tabs:
                    print(f"  [탭 {n}개 감시 중]")
                    tabs = n

                for item in rec.drain():
                    key = f"{item.get('method', 'GET').upper()} {recorder.normalize_url(item.get('url', ''))}"
                    if key in seen:
                        continue
                    seen.add(key)
                    print(f"  [{item.get('status')}] {key}")
            except Exception as exc:
                # 탭이 닫히거나 CDP가 끊겨도 녹화를 통째로 잃지 않는다
                print(f"  [경고] {type(exc).__name__}: {exc}")
                time.sleep(2.0)

            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\n녹화를 종료합니다...")
    finally:
        rec.drain()
        rec.close()

    if not rec.records:
        print("수집된 요청이 없습니다. Chrome에서 실제로 페이지를 이동했는지 확인하세요.")
        return 1

    md = recorder.write_markdown(rec.records)
    guessed = guess_endpoints(rec.records)
    ep = write_endpoints(guessed)

    print(f"\n원본 로그 : {rec.out_path}")
    print(f"분석 문서 : {md}")
    print(f"엔드포인트: {ep}")
    print(f"\n총 {len(rec.records)}건 / 고유 엔드포인트 {len(seen)}개")
    print("\n추정 결과:")
    for role, info in guessed.items():
        mark = "OK " if info.get("url") else "-- "
        print(f"  {mark}{role:<14} {info.get('method', '')} {info.get('url', '(못 찾음)')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
