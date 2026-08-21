#!/usr/bin/env python3
"""지금 브라우저에 떠 있는 화면의 클릭 가능 요소와 좌석 후보를 덤프한다.

selectors.yaml 의 로그인 이후 항목(인원 선택, 좌석, 결제)을 확정할 때 쓴다.

    python tools/inspect_page.py            # 버튼/링크 목록
    python tools/inspect_page.py --seats    # 좌석처럼 생긴 요소 분석
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import browser  # noqa: E402

CLICKABLE_JS = r"""
const out = [];
document.querySelectorAll('button, a, input, label, [role="button"]').forEach(el => {
  const r = el.getBoundingClientRect();
  if (r.width <= 0 || r.height <= 0) return;
  out.push({
    tag: el.tagName.toLowerCase(),
    type: el.getAttribute('type') || '',
    text: (el.innerText || el.value || '').trim().slice(0, 40),
    cls: (el.className || '').toString().trim().replace(/\s+/g, ' ').slice(0, 90),
    aria: el.getAttribute('aria-label') || '',
    disabled: el.disabled === true || el.getAttribute('aria-disabled') === 'true'
  });
});
return JSON.stringify(out);
"""

SEAT_JS = r"""
// 같은 클래스 접두사를 가진 요소가 20개 이상 모여 있으면 좌석맵일 가능성이 높다
const groups = {};
document.querySelectorAll('*').forEach(el => {
  const r = el.getBoundingClientRect();
  if (r.width < 6 || r.width > 60 || r.height < 6 || r.height > 60) return;
  const cls = (el.className || '').toString().trim().split(/\s+/)[0] || '(무클래스)';
  const key = el.tagName.toLowerCase() + '.' + cls.replace(/__[A-Za-z0-9]+$/, '__*');
  (groups[key] = groups[key] || []).push({
    label: (el.getAttribute('aria-label') || el.dataset.seatNm || el.title || el.innerText || '').trim().slice(0, 20),
    disabled: el.disabled === true || el.getAttribute('aria-disabled') === 'true',
    x: Math.round(r.x), y: Math.round(r.y)
  });
});
const big = Object.entries(groups).filter(([, v]) => v.length >= 20)
  .sort((a, b) => b[1].length - a[1].length).slice(0, 5);
return JSON.stringify(big.map(([k, v]) => ({
  selector: k, count: v.length,
  enabled: v.filter(s => !s.disabled).length,
  samples: v.slice(0, 8)
})));
"""


def main() -> int:
    driver = browser.attach_driver()
    print(f"현재 화면: {driver.current_url}\n")

    if "--seats" in sys.argv:
        groups = json.loads(driver.execute_script(SEAT_JS))
        if not groups:
            print("좌석맵처럼 보이는 요소 묶음이 없습니다. 좌석 선택 화면인지 확인하세요.")
            return 1
        for g in groups:
            print(f"[{g['count']}개 / 선택가능 {g['enabled']}개] {g['selector']}")
            for s in g["samples"]:
                print(f"    label={s['label']!r} disabled={s['disabled']} ({s['x']},{s['y']})")
            print()
        print("가장 위 묶음을 selectors.yaml 의 seatmap.seat 에 넣으면 됩니다.")
        print("클래스 해시는 배포마다 바뀌므로 [class*=\"접두사\"] 형태로 적으세요.")
        return 0

    items = json.loads(driver.execute_script(CLICKABLE_JS))
    print(f"클릭 가능 요소 {len(items)}개\n")
    for it in items:
        mark = "x" if it["disabled"] else " "
        label = it["text"] or it["aria"] or "(빈 텍스트)"
        print(f" [{mark}] <{it['tag']}{'/' + it['type'] if it['type'] else ''}> {label:<42} {it['cls']}")

    print("\n자주 쓰이는 클래스 접두사:")
    prefixes = Counter(
        c.split("__")[0] for it in items for c in it["cls"].split() if "__" in c
    )
    for prefix, n in prefixes.most_common(15):
        print(f"  {n:>3}  [class*=\"{prefix}\"]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
