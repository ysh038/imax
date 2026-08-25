"""config.yaml 로딩과 검증."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

import yaml
from dotenv import load_dotenv

from .paths import CONFIG_EXAMPLE_PATH, CONFIG_PATH, ENV_PATH


class ConfigError(RuntimeError):
    pass


def _minutes(value: str) -> int:
    """'25:30' -> 1530. CGV 심야 표기(24시 초과)를 그대로 받는다."""
    try:
        hh, mm = str(value).split(":")
        return int(hh) * 60 + int(mm)
    except (ValueError, AttributeError):
        raise ConfigError(f"시각 형식이 잘못됐습니다: {value!r} (예: '18:00', '27:30')") from None


_DAY_INDEX = {
    "mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6,
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
    "월": 0, "화": 1, "수": 2, "목": 3, "금": 4, "토": 5, "일": 6,
}


def _days(values) -> list[int]:
    if not values:
        return []
    out = []
    for raw in values:
        key = str(raw).strip().lower()
        if key not in _DAY_INDEX:
            raise ConfigError(f"알 수 없는 요일입니다: {raw!r} (예: fri, sat, sun)")
        out.append(_DAY_INDEX[key])
    return out


@dataclass
class Theater:
    name: str = "CGV 용산아이파크몰"
    site_no: str = "0013"
    screen_keywords: list[str] = field(default_factory=lambda: ["IMAX", "아이맥스"])


@dataclass
class Seats:
    count: int = 1
    # 원하는 매수를 못 채우면 여기까지 줄여서라도 잡는다. count와 같으면 안 줄인다.
    min_count: int = 0
    adjacent: bool = True
    # 필수 조건. 못 맞추면 자리가 나도 예매하지 않는다.
    min_row: str = ""
    center_ratio: float = 1.0
    # 선호 조건. 통과한 자리들 사이의 순위만 정한다.
    prefer_rows: list[str] = field(default_factory=list)
    avoid_rows: list[str] = field(default_factory=list)
    prefer_center: bool = True


@dataclass
class Polling:
    interval_sec: tuple[float, float] = (4.0, 9.0)
    backoff_start_sec: float = 60.0
    backoff_max_sec: float = 900.0
    burst_at: str = ""
    burst_interval_sec: float = 1.0
    burst_window_sec: float = 120.0


@dataclass
class Booking:
    auto_pay: bool = True
    pay_method: str = ""
    max_price_krw: int = 100000
    max_bookings: int = 1
    hold_timeout_sec: int = 540
    queue_timeout_sec: int = 1800
    render_timeout_sec: float = 180.0


@dataclass
class Session:
    check_every_sec: float = 60.0
    keepalive_every_sec: float = 600.0
    renotify_every_sec: float = 1800.0
    confirm_times: int = 2
    auto_renew: bool = True


@dataclass
class Notify:
    on_showtime_open: bool = True
    on_seat_found: bool = True
    on_success: bool = True
    on_failure: bool = True
    on_blocked: bool = True
    heartbeat_min: int = 60
    webhook_url: str = ""


@dataclass
class Config:
    theater: Theater
    movie_title: str
    date_from: str
    date_to: str
    wait_for_open: bool
    after_min: int
    before_min: int
    weekdays_only: bool
    # 0=월 … 6=일. 비어 있으면 요일 제한 없음.
    days: list[int]
    # 금요일에만 적용. None이면 금요일도 after/before만 본다.
    friday_after_min: int | None
    # 일요일에만 적용. None이면 일요일도 after/before만 본다.
    # 다음날 출근을 감안해 일요일은 이 시각 이전 회차만 본다.
    sunday_before_min: int | None
    # 지금부터 이 시간 안에 시작하는 회차는 아예 안 잡는다. 0이면 제한 없음.
    min_lead_hours: float
    only_dates: list[str]
    seats: Seats
    polling: Polling
    booking: Booking
    notify: Notify
    session: Session
    pay_password: str = ""
    toss_phone: str = ""
    toss_birth: str = ""

    @property
    def pays_with_toss(self) -> bool:
        return self.booking.pay_method.strip().lower() == "toss"

    def validate(self) -> None:
        if not self.movie_title:
            raise ConfigError("movie.title_contains 가 비어 있습니다")
        if not self.theater.site_no:
            raise ConfigError("theater.site_no 가 비어 있습니다")
        if self.seats.count < 1:
            raise ConfigError("seats.count 는 1 이상이어야 합니다")
        if self.after_min > self.before_min:
            raise ConfigError("showtimes.after 가 before 보다 늦습니다")
        if self.friday_after_min is not None and not (0 <= self.friday_after_min <= self.before_min):
            raise ConfigError("showtimes.friday_after 가 before 보다 늦습니다")
        if self.sunday_before_min is not None and not (
            self.after_min <= self.sunday_before_min <= self.before_min
        ):
            raise ConfigError("showtimes.sunday_before 는 after~before 사이여야 합니다")
        if self.days and any(d < 0 or d > 6 for d in self.days):
            raise ConfigError("showtimes.days 는 mon~sun (또는 월~일) 이어야 합니다")
        lo, hi = self.polling.interval_sec
        if lo <= 0 or hi < lo:
            raise ConfigError("polling.interval_sec 은 [작은값, 큰값] 이어야 하고 0보다 커야 합니다")
        if lo < 1.0:
            raise ConfigError("polling.interval_sec 하한이 1초 미만이면 차단 위험이 큽니다")
        if not 1 <= self.seats.min_count <= self.seats.count:
            raise ConfigError("seats.min_count 는 1 이상 seats.count 이하여야 합니다")
        if not 0 < self.seats.center_ratio <= 1.0:
            raise ConfigError("seats.center_ratio 는 0 초과 1 이하여야 합니다 (1이면 제한 없음)")
        if self.min_lead_hours < 0:
            raise ConfigError("showtimes.min_lead_hours 는 0 이상이어야 합니다")
        if self.seats.min_row and not self.seats.min_row.isalpha():
            raise ConfigError("seats.min_row 는 열 이름이어야 합니다 (예: E)")

    def require_payment_ready(self) -> None:
        """실제로 결제까지 갈 때만 확인한다. --list, --dry-run 에는 필요 없다."""
        if not self.booking.auto_pay:
            return
        if not self.booking.pay_method:
            raise ConfigError(
                "booking.auto_pay 가 켜져 있는데 booking.pay_method 가 비어 있습니다.\n"
                "  CGV 결제 화면에 보이는 이름 그대로 적으세요 (권장: toss)."
            )
        if self.pays_with_toss:
            if not (self.toss_phone and self.toss_birth):
                raise ConfigError(
                    "토스 결제에는 .env 의 TOSS_PHONE 과 TOSS_BIRTH6 이 필요합니다."
                )
            if len(self.toss_birth) != 6 or not self.toss_birth.isdigit():
                raise ConfigError("TOSS_BIRTH6 은 숫자 6자리여야 합니다 (예: 910101)")
        elif not self.pay_password:
            raise ConfigError(
                f"'{self.booking.pay_method}' 결제에는 .env 의 CGV_PAY_PASSWORD 가 필요합니다.\n"
                "  카드를 등록하지 않았다면 pay_method: toss 를 쓰세요. 폰으로 승인만 하면 됩니다."
            )


def load(path=CONFIG_PATH) -> Config:
    if not path.exists():
        raise ConfigError(
            f"{path.name}이 없습니다. `cp {CONFIG_EXAMPLE_PATH.name} {path.name}` 후 값을 채우세요."
        )
    load_dotenv(ENV_PATH)
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    t = raw.get("theater") or {}
    s = raw.get("seats") or {}
    p = raw.get("polling") or {}
    b = raw.get("booking") or {}
    n = raw.get("notify") or {}
    d = raw.get("dates") or {}
    st = raw.get("showtimes") or {}
    ss = raw.get("session") or {}

    interval = p.get("interval_sec", [4, 9])
    if isinstance(interval, (int, float)):
        interval = [interval, interval]

    cfg = Config(
        theater=Theater(
            name=t.get("name", "CGV 용산아이파크몰"),
            site_no=str(t.get("site_no", "0013")),
            screen_keywords=[str(k) for k in (t.get("screen_keywords") or ["IMAX", "아이맥스"])],
        ),
        movie_title=str((raw.get("movie") or {}).get("title_contains", "")).strip(),
        date_from=str(d.get("from", "")),
        date_to=str(d.get("to", "")),
        wait_for_open=bool(d.get("wait_for_open", True)),
        after_min=_minutes(st.get("after", "00:00")),
        before_min=_minutes(st.get("before", "28:00")),
        weekdays_only=bool(st.get("weekdays_only", False)),
        days=_days(st.get("days") or []),
        friday_after_min=_minutes(st["friday_after"]) if st.get("friday_after") else None,
        sunday_before_min=_minutes(st["sunday_before"]) if st.get("sunday_before") else None,
        min_lead_hours=float(st.get("min_lead_hours", 0)),
        only_dates=[str(x).replace("-", "") for x in (st.get("only_dates") or [])],
        seats=Seats(
            count=int(s.get("count", 1)),
            min_count=int(s.get("min_count", 0) or s.get("count", 1)),
            adjacent=bool(s.get("adjacent", True)),
            min_row=str(s.get("min_row", "") or "").strip().upper(),
            center_ratio=float(s.get("center_ratio", 1.0)),
            prefer_rows=[str(r).upper() for r in (s.get("prefer_rows") or [])],
            avoid_rows=[str(r).upper() for r in (s.get("avoid_rows") or [])],
            prefer_center=bool(s.get("prefer_center", True)),
        ),
        polling=Polling(
            interval_sec=(float(interval[0]), float(interval[1])),
            backoff_start_sec=float(p.get("backoff_start_sec", 60)),
            backoff_max_sec=float(p.get("backoff_max_sec", 900)),
            burst_at=str(p.get("burst_at", "") or ""),
            burst_interval_sec=float(p.get("burst_interval_sec", 1.0)),
            burst_window_sec=float(p.get("burst_window_sec", 120)),
        ),
        booking=Booking(
            auto_pay=bool(b.get("auto_pay", True)),
            pay_method=str(b.get("pay_method", "") or "").strip(),
            max_price_krw=int(b.get("max_price_krw", 100000)),
            max_bookings=int(b.get("max_bookings", 1)),
            hold_timeout_sec=int(b.get("hold_timeout_sec", 540)),
            queue_timeout_sec=int(b.get("queue_timeout_sec", 1800)),
            render_timeout_sec=float(b.get("render_timeout_sec", 180.0)),
        ),
        notify=Notify(
            on_showtime_open=bool(n.get("on_showtime_open", True)),
            on_seat_found=bool(n.get("on_seat_found", True)),
            on_success=bool(n.get("on_success", True)),
            on_failure=bool(n.get("on_failure", True)),
            on_blocked=bool(n.get("on_blocked", True)),
            heartbeat_min=int(n.get("heartbeat_min", 60)),
            webhook_url=os.getenv("DISCORD_WEBHOOK_URL", "").strip(),
        ),
        session=Session(
            check_every_sec=float(ss.get("check_every_sec", 60)),
            keepalive_every_sec=float(ss.get("keepalive_every_sec", 600)),
            renotify_every_sec=float(ss.get("renotify_every_sec", 1800)),
            confirm_times=int(ss.get("confirm_times", 2)),
            auto_renew=bool(ss.get("auto_renew", True)),
        ),
        pay_password=os.getenv("CGV_PAY_PASSWORD", "").strip(),
        toss_phone=os.getenv("TOSS_PHONE", "").strip(),
        toss_birth=os.getenv("TOSS_BIRTH6", "").strip(),
    )
    cfg.validate()
    return cfg
