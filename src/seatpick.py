"""좌석 고르기 규칙.

감시 루프와 예매 실행이 같은 규칙을 써야 한다. 감시가 "자리 났다"고 판단한 근거와
실제로 고르는 자리가 다르면, 조건에 안 맞는 자리를 잡으려고 들어갔다가 실패하고
나오는 일이 반복된다. 그래서 판정과 선택을 여기 한 곳에 모아 둔다.

조건에는 두 종류가 있다.
  - 필수: 못 맞추면 아예 예매하지 않는다 (min_row, center_ratio)
  - 선호: 맞는 것들 중에서 순위를 매길 뿐이다 (prefer_rows, prefer_center)
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Seat:
    row: str
    col: int
    x: int  # 가로 좌표. 열 안에서 어디쯤인지 재는 데만 쓴다.
    available: bool
    # 이 자리 오른쪽이 통로다. 번호가 이어져 있어도 통로 건너면 연석이 아니다.
    aisle_right: bool = False

    @property
    def label(self) -> str:
        return f"{self.row}{self.col}"


def row_key(row: str) -> tuple[int, str]:
    """열 이름 순서. 'Z' 다음이 'AA'인 극장이 있어서 길이를 먼저 본다."""
    return (len(row), row.upper())


def parse_label(label: str) -> tuple[str, int]:
    """'H12' / 'H열 12번' 을 ('H', 12) 로."""
    m = re.search(r"([A-Za-z]{1,2})\s*(?:열)?\s*-?\s*(\d{1,3})", label or "")
    return (m.group(1).upper(), int(m.group(2))) if m else ("", -1)


def _row_bounds(seats: list[Seat]) -> dict[str, tuple[int, int]]:
    """열마다 가로 범위. 팔린 자리까지 넣어야 진짜 가운데를 알 수 있다.

    남은 자리만으로 중앙을 재면, 가장자리 두 자리만 남았을 때 그 둘의 한가운데를
    '중앙'으로 착각한다.
    """
    bounds: dict[str, tuple[int, int]] = {}
    for s in seats:
        lo, hi = bounds.get(s.row, (s.x, s.x))
        bounds[s.row] = (min(lo, s.x), max(hi, s.x))
    return bounds


def eligible(seats: list[Seat], cfg) -> list[Seat]:
    """필수 조건을 통과한 빈 자리만 남긴다."""
    bounds = _row_bounds(seats)
    pool = [s for s in seats if s.available]

    if cfg.min_row:
        floor = row_key(cfg.min_row)
        pool = [s for s in pool if row_key(s.row) >= floor]

    if cfg.avoid_rows:
        avoid = {r.upper() for r in cfg.avoid_rows}
        pool = [s for s in pool if s.row not in avoid]

    if cfg.center_ratio and cfg.center_ratio < 1.0:
        kept = []
        for s in pool:
            lo, hi = bounds.get(s.row, (s.x, s.x))
            if hi == lo:
                kept.append(s)
                continue
            center = (lo + hi) / 2
            if abs(s.x - center) <= (hi - lo) * cfg.center_ratio / 2:
                kept.append(s)
        pool = kept

    return pool


def choose(seats: list[Seat], cfg, count: int) -> list[Seat]:
    """조건에 맞는 자리 중 가장 좋은 조합. 없으면 빈 리스트."""
    pool = eligible(seats, cfg)
    if len(pool) < count:
        return []

    bounds = _row_bounds(seats)

    def rank(s: Seat) -> tuple:
        try:
            pref = [r.upper() for r in cfg.prefer_rows].index(s.row)
        except ValueError:
            pref = len(cfg.prefer_rows) + 1
        if cfg.prefer_center:
            lo, hi = bounds.get(s.row, (s.x, s.x))
            dist = abs(s.x - (lo + hi) / 2)
        else:
            dist = 0
        return (pref, dist, row_key(s.row), s.col)

    if count == 1:
        return [min(pool, key=rank)]

    if not cfg.adjacent:
        return sorted(pool, key=rank)[:count]

    by_row: dict[str, list[Seat]] = {}
    for s in pool:
        by_row.setdefault(s.row, []).append(s)

    groups: list[list[Seat]] = []
    for row_seats in by_row.values():
        row_seats.sort(key=lambda s: s.col)
        run: list[Seat] = []
        for s in row_seats:
            if run and (s.col != run[-1].col + 1 or run[-1].aisle_right):
                run = []
            run.append(s)
            if len(run) >= count:
                groups.append(run[-count:])
    if not groups:
        return []
    return min(groups, key=lambda g: rank(g[0]))


def choose_best(seats: list[Seat], cfg) -> list[Seat]:
    """원하는 매수부터 하나씩 줄여가며 잡을 수 있는 최대 조합을 고른다.

    2연석이 나면 2연석으로, 안 되면 1석으로 잡고 싶을 때 쓴다.
    min_count 까지 내려가도 없으면 빈 리스트.
    """
    floor = max(1, getattr(cfg, "min_count", cfg.count) or cfg.count)
    for count in range(cfg.count, floor - 1, -1):
        picked = choose(seats, cfg, count)
        if picked:
            return picked
    return []
