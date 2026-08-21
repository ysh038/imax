#!/usr/bin/env python3
"""극장 코드(siteNo)와 상영 중인 영화 번호를 조회한다.

    python tools/list_theaters.py            # 극장 전체
    python tools/list_theaters.py 용산       # 이름으로 걸러 보기
    python tools/list_theaters.py --movies   # 상영작 목록
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import browser, cgv  # noqa: E402


def main() -> int:
    args = [a for a in sys.argv[1:]]
    show_movies = "--movies" in args
    needle = next((a for a in args if not a.startswith("-")), "")

    browser.launch_chrome(url=browser.CGV_HOME)
    driver = browser.attach_driver()
    api = cgv.CgvApi(driver)

    if show_movies:
        print(f"{'movNo':<12}{'상영시간':>6}  영화")
        for m in api.movies():
            print(f"{m.get('movNo', ''):<12}{str(m.get('scnBssTm') or '-'):>6}  {m.get('movNm', '')}")
        return 0

    print(f"{'siteNo':<9}{'지역':<10}극장")
    for region in api.theaters():
        rname = region.get("regnGrpNm", "")
        for site in region.get("siteList") or []:
            name = site.get("siteNm", "")
            if needle and needle not in name:
                continue
            print(f"{site.get('siteNo', ''):<9}{rname:<10}{name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
