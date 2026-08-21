"""CGV API 클라이언트.

요청은 전부 브라우저 페이지 안에서 fetch로 날린다. Python에서 직접 쏘면
Cloudflare가 403으로 막지만, 페이지 컨텍스트에서는 인증 쿠키와 통과 쿠키가
그대로 실려 정상 응답을 받는다.
"""

from __future__ import annotations

import json
import urllib.parse
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

import yaml

from .paths import ENDPOINTS_PATH
from .seatpick import Seat

# 페이지 안에서 fetch를 실행하고 결과를 콜백으로 돌려준다.
_FETCH_JS = r"""
const done = arguments[arguments.length - 1];
const url = arguments[0], method = arguments[1], body = arguments[2];
const opts = { method: method, credentials: 'include', headers: { 'Accept': 'application/json' } };
if (body) { opts.headers['Content-Type'] = 'application/json'; opts.body = body; }
fetch(url, opts)
  .then(r => r.text().then(t => done(JSON.stringify({ ok: true, status: r.status, body: t }))))
  .catch(e => done(JSON.stringify({ ok: false, status: 0, body: String(e) })));
"""


class CgvError(RuntimeError):
    pass


class QueueWaitError(CgvError):
    """API 응답이 대기열 페이지다. 호출자는 잠시 쉬고 다시 보면 된다."""


class BlockedError(CgvError):
    """Cloudflare 차단 또는 레이트리밋. 호출자가 백오프해야 한다."""


def _as_int(value, default: int | None = None) -> int | None:
    """CGV는 성공하면 statusCode를 정수 0으로, 실패하면 문자열 "401"로 준다."""
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


class ApiStatusError(CgvError):
    """CGV가 statusCode로 실패를 알려준 경우. 401이면 로그인이 필요하다는 뜻."""

    def __init__(self, role: str, code, message: str):
        super().__init__(f"{role}: statusCode={code} {message}")
        self.role = role
        self.code = _as_int(code)

    @property
    def needs_login(self) -> bool:
        return self.code in (401, 403)


def load_spec(path=ENDPOINTS_PATH) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"{path}가 없습니다.")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _hhmm(raw: str | None) -> str:
    """'2430' -> '24:30'. CGV는 심야 회차를 24시 이후로 표기한다."""
    if not raw or len(raw) < 3:
        return "--:--"
    raw = raw.zfill(4)
    return f"{raw[:-2]}:{raw[-2:]}"


def _minutes(raw: str | None) -> int:
    if not raw:
        return -1
    raw = raw.zfill(4)
    try:
        return int(raw[:-2]) * 60 + int(raw[-2:])
    except ValueError:
        return -1


@dataclass
class Showtime:
    """회차 하나. raw에 원본 JSON을 그대로 들고 있는다."""

    raw: dict
    fields: dict

    def _f(self, key: str, default: Any = "") -> Any:
        return self.raw.get(self.fields.get(key, key), default)

    @property
    def movie(self) -> str:
        return str(self._f("movie_name") or "")

    @property
    def movie_no(self) -> str:
        return str(self._f("movie_no") or "")

    @property
    def screen(self) -> str:
        return str(self._f("screen_name") or "")

    @property
    def special_grade(self) -> str:
        return str(self._f("special_grade") or "")

    @property
    def fmt(self) -> str:
        return str(self._f("format_name") or "")

    @property
    def product_no(self) -> str:
        return str(self._f("product_no") or "")

    @property
    def date(self) -> str:
        return str(self._f("date") or "")

    @property
    def start_raw(self) -> str:
        return str(self._f("start_time") or "")

    @property
    def start(self) -> str:
        return _hhmm(self.start_raw)

    @property
    def end(self) -> str:
        return _hhmm(str(self._f("end_time") or ""))

    @property
    def start_minutes(self) -> int:
        return _minutes(self.start_raw)

    @property
    def seats_free(self) -> int:
        try:
            return int(self._f("seats_free", 0) or 0)
        except (TypeError, ValueError):
            return 0

    @property
    def seats_free_incl_held(self) -> int:
        try:
            return int(self._f("seats_free_incl_held", 0) or 0)
        except (TypeError, ValueError):
            return 0

    @property
    def seats_total(self) -> int:
        try:
            return int(self._f("seats_total", 0) or 0)
        except (TypeError, ValueError):
            return 0

    @property
    def max_per_booking(self) -> int:
        try:
            return int(self._f("max_per_booking", 8) or 8)
        except (TypeError, ValueError):
            return 8

    @property
    def held_seats(self) -> int:
        """지금 누군가 결제창에 잡아둔 좌석 수. 10분 뒤 풀릴 수 있다."""
        return max(0, self.seats_free_incl_held - self.seats_free)

    @property
    def key(self) -> str:
        return f"{self.date}-{self.product_no}-{self.start_raw}"

    def pretty_date(self) -> str:
        d = self.date
        return f"{d[4:6]}/{d[6:8]}" if len(d) == 8 else d

    def __str__(self) -> str:
        return (
            f"{self.pretty_date()} {self.start} {self.movie} "
            f"[{self.screen}] {self.seats_free}/{self.seats_total}석"
        )


class CgvApi:
    def __init__(self, driver, spec: dict | None = None, site_no: str = "0013"):
        self.driver = driver
        self.spec = spec or load_spec()
        self.site_no = site_no
        self.fields = self.spec.get("showtime_fields", {})
        self._vars = {
            "co_cd": self.spec.get("co_cd", "A420"),
            "web_origin": self.spec.get("web_origin", "https://cgv.co.kr"),
            "api_origin": self.spec.get("api_origin", "https://api.cgv.co.kr"),
            "site_no": site_no,
        }
        driver.set_script_timeout(45)

    # ---- 저수준 --------------------------------------------------------

    def _build_url(self, role: str, **extra) -> tuple[str, str]:
        cfg = self.spec["roles"].get(role)
        if cfg is None:
            raise CgvError(f"endpoints.yaml에 '{role}' 역할이 없습니다")
        subs = {**self._vars, **extra}
        url = cfg["url"].format(**subs)
        params = {k: str(v).format(**subs) for k, v in (cfg.get("params") or {}).items()}
        if params:
            url += "?" + urllib.parse.urlencode(params)
        return cfg.get("method", "GET").upper(), url

    def raw_fetch(self, url: str, method: str = "GET", body: str | None = None) -> dict:
        result = json.loads(self.driver.execute_async_script(_FETCH_JS, url, method, body))
        status = result.get("status", 0)
        text = result.get("body", "")

        if status in (403, 429) or "이용이 제한되었어요" in text:
            raise BlockedError(f"차단 감지 (HTTP {status}) {url}")
        lowered = text.lower()
        if any(m in lowered for m in ("netfunnel", "nfplus", "접속 대기", "접속대기", "대기열")):
            raise QueueWaitError(f"접속 대기열 응답 (HTTP {status}) {url}")
        if status == 0:
            raise CgvError(f"네트워크 실패: {text[:200]}")
        if status >= 500:
            raise CgvError(f"CGV 서버 오류 HTTP {status}")
        return {"status": status, "text": text}

    def call(self, role: str, **extra) -> Any:
        method, url = self._build_url(role, **extra)
        res = self.raw_fetch(url, method)
        try:
            payload = json.loads(res["text"])
        except ValueError:
            if any(m in res["text"].lower() for m in ("netfunnel", "nfplus", "접속대기", "대기열")):
                raise QueueWaitError(f"{role}: 대기열 HTML 응답") from None
            raise CgvError(f"{role}: JSON이 아닌 응답 (HTTP {res['status']})") from None

        code = payload.get("statusCode")
        if _as_int(code, -1) != _as_int(self.spec.get("success_code", 0), 0):
            raise ApiStatusError(role, code, str(payload.get("statusMessage", "")))
        return payload.get("data")

    # ---- 고수준 --------------------------------------------------------

    def is_logged_in(self) -> bool:
        """회원 전용 엔드포인트가 실제 데이터를 주는지로 판단한다.

        CGV는 비로그인 요청에도 statusCode 0을 주면서 data만 null로 비운다.
        그래서 HTTP 상태나 statusCode가 아니라 data 유무를 봐야 한다.
        """
        try:
            return self.call("login_check") is not None
        except ApiStatusError as exc:
            if exc.needs_login:
                return False
            raise
        except QueueWaitError:
            raise
        except CgvError:
            return False

    def open_dates(self) -> list[str]:
        """이 극장에서 지금 예매 가능한 날짜(YYYYMMDD) 목록."""
        data = self.call("open_dates") or []
        return [str(row.get("scnYmd")) for row in data if row.get("scnYmd")]

    def showtimes(self, scn_ymd: str) -> list[Showtime]:
        data = self.call("showtimes", scn_ymd=scn_ymd) or []
        return [Showtime(raw=row, fields=self.fields) for row in data]

    def seat_map(self, s: Showtime) -> list[Seat]:
        """회차의 전 좌석 상태. 팔린 자리도 함께 준다.

        상영시간표가 주는 frSeatCnt 는 장애인석까지 포함한 숫자다. 용아맥 IMAX관은
        장애인석 6석이 늘 비어 있어서, 숫자만 믿으면 매진된 회차에 영원히 달려든다.
        가운데 자리인지 판정하려면 팔린 자리까지 있어야 열의 진짜 범위를 알 수 있다.
        """
        rules = self.spec.get("seat_rules", {})
        data = self.call(
            "seat_data",
            scn_ymd=s.date,
            scns_no=str(s.raw.get("scnsNo", "")),
            scn_sseq=str(s.raw.get("scnSseq", "")),
        )
        items = (data or {}).get("items") or []
        if not items:
            return []

        ok_forms = set(rules.get("form_ok", ["01"]))
        sale_field = rules.get("sale_flag_field", "seatSaleYn")
        sale_ok = rules.get("sale_flag_ok", "Y")
        form_field = rules.get("form_field", "seatSalfrmCd")
        row_field = rules.get("row_field", "seatRowNm")
        num_field = rules.get("number_field", "seatNo")

        seats = []
        for raw in items[0].get("seats") or []:
            row = str(raw.get(row_field) or "").upper()
            num = _as_int(raw.get(num_field))
            if not row or num is None:
                continue
            usable = raw.get(form_field) in ok_forms
            seats.append(
                Seat(
                    row=row,
                    col=num,
                    x=_as_int(raw.get("xcoordStartVal"), 0) or 0,
                    available=usable and raw.get(sale_field) == sale_ok,
                    aisle_right=raw.get("rghtPwayYn") == "Y",
                )
            )
        return seats

    def movies(self) -> list[dict]:
        return self.call("movies") or []

    def theaters(self) -> list[dict]:
        return self.call("theaters") or []


def daterange(start: str | date, end: str | date) -> list[str]:
    """'2026-09-01'~'2026-09-30' 같은 범위를 YYYYMMDD 리스트로."""

    def parse(v):
        if isinstance(v, date):
            return v
        v = str(v).strip()
        for fmt in ("%Y-%m-%d", "%Y%m%d", "%Y/%m/%d"):
            try:
                return datetime.strptime(v, fmt).date()
            except ValueError:
                continue
        raise ValueError(f"날짜 형식을 알 수 없습니다: {v}")

    a, b = parse(start), parse(end)
    if b < a:
        a, b = b, a
    return [(a + timedelta(days=i)).strftime("%Y%m%d") for i in range((b - a).days + 1)]
