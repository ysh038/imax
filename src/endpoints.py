"""녹화한 트래픽에서 예매에 필요한 엔드포인트 역할을 추정하고 파일로 관리한다.

CGV가 개편되며 API 경로가 공개된 적이 없으므로, 이름을 하드코딩하지 않고
녹화 결과에서 역할별로 골라 endpoints.yaml에 적어 둔다. 추정이 틀리면 그 파일만
손보면 되고 코드는 건드릴 필요가 없다.
"""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import urlsplit

import yaml

from .paths import ENDPOINTS_PATH, GUESS_ENDPOINTS_PATH

# 역할별 (URL 키워드, 응답 본문 키워드, 선호 HTTP 메서드)
ROLE_HINTS: dict[str, dict[str, Any]] = {
    "me": {
        "url": ["/member", "/user/me", "/me", "/mypage", "/profile", "/session", "/auth"],
        "body": ["memberNo", "memberId", "userId", "nickname", "custNo"],
        "methods": ["GET"],
    },
    "theaters": {
        "url": ["theater", "cinema", "site", "brch", "branch"],
        "body": ["theaterCd", "theaterCode", "siteCd", "theaterNm", "theaterName"],
        "methods": ["GET", "POST"],
    },
    "showtimes": {
        "url": ["showtime", "schedule", "sched", "timetable", "playtime", "round", "movieBook"],
        "body": ["playYmd", "screenCd", "playStartTm", "showtime", "scheduleNo", "playSchedule", "remainSeat"],
        "methods": ["GET", "POST"],
    },
    "seatmap": {
        "url": ["seat"],
        "body": ["seatNo", "seatCd", "seatRow", "rowNo", "colNo", "seatStatus", "seatList"],
        "methods": ["GET", "POST"],
    },
    "hold": {
        "url": ["seat", "hold", "occupy", "lock", "select", "temp", "reserve", "assign"],
        "body": ["holdNo", "reserveNo", "tempNo", "expire", "holdSeat"],
        "methods": ["POST", "PUT"],
    },
    "payment": {
        "url": ["pay", "settle", "order", "purchase", "checkout", "billing"],
        "body": ["payAmt", "totalAmount", "orderNo", "payMethod", "settleAmt"],
        "methods": ["POST"],
    },
}


def _score(rec: dict, role: str, hints: dict) -> int:
    url = (rec.get("url") or "").lower()
    path = urlsplit(url).path
    method = (rec.get("method") or "GET").upper()
    body = (rec.get("resBody") or "") + (rec.get("reqBody") or "")

    score = 0
    for kw in hints["url"]:
        if kw.lower() in path:
            score += 6
    for kw in hints["body"]:
        if kw.lower() in body.lower():
            score += 4
    if method in hints["methods"]:
        score += 2
    else:
        score -= 3

    if rec.get("status") == 200:
        score += 2
    if "api." in url:
        score += 2
    if role in ("hold", "payment") and method == "GET":
        score -= 6
    if role in ("showtimes", "seatmap", "theaters") and not rec.get("resBody"):
        score -= 4
    return score


def _templatize(url: str) -> str:
    split = urlsplit(url)
    path = re.sub(r"/\d{8}(?=/|$)", "/{date}", split.path)
    path = re.sub(r"/\d{3,}(?=/|$)", "/{id}", path)
    base = f"{split.scheme}://{split.netloc}{path}"
    if split.query:
        keys = [p.split("=", 1)[0] for p in split.query.split("&") if p]
        base += "?" + "&".join(f"{k}={{{k}}}" for k in keys)
    return base


def _query_keys(url: str) -> list[str]:
    q = urlsplit(url).query
    return [p.split("=", 1)[0] for p in q.split("&") if p]


def guess_endpoints(records: list[dict]) -> dict[str, dict]:
    result: dict[str, dict] = {}
    for role, hints in ROLE_HINTS.items():
        best, best_score = None, 0
        for rec in records:
            s = _score(rec, role, hints)
            if s > best_score:
                best, best_score = rec, s
        if best is None:
            result[role] = {"method": "", "url": "", "template": "", "confidence": 0}
            continue
        result[role] = {
            "method": (best.get("method") or "GET").upper(),
            "url": best.get("url", ""),
            "template": _templatize(best.get("url", "")),
            "query_keys": _query_keys(best.get("url", "")),
            "req_body": (best.get("reqBody") or "")[:600] or None,
            "confidence": best_score,
        }
    return result


HEADER = """# 녹화 결과에서 자동 추정한 엔드포인트 후보 (참고용).
# 실제로 코드가 쓰는 값은 저장소 루트의 endpoints.yaml 입니다.
# 여기 추정이 더 정확해 보이면 그 값을 endpoints.yaml로 옮기세요.
"""


def write_endpoints(guessed: dict[str, dict], path=GUESS_ENDPOINTS_PATH):
    origins = {
        urlsplit(v["url"]).netloc
        for v in guessed.values()
        if v.get("url")
    }
    payload = {
        "api_origin": f"https://{sorted(origins)[0]}" if origins else "",
        "roles": guessed,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(HEADER + yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return path


def load_endpoints(path=ENDPOINTS_PATH) -> dict:
    if not path.exists():
        raise FileNotFoundError(
            f"{path.name}이 없습니다. 먼저 `python tools/record_api.py`로 디스커버리를 실행하세요."
        )
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def load_records(jsonl_path) -> list[dict]:
    records = []
    with open(jsonl_path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except ValueError:
                    continue
    return records
