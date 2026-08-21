"""디스코드 웹후크 알림.

알림 실패가 예매를 망치면 안 되므로 모든 전송은 예외를 삼키고 경고만 남긴다.
"""

from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path

import requests

COLOR_INFO = 0x5865F2
COLOR_GOOD = 0x2ECC71
COLOR_WARN = 0xF1C40F
COLOR_BAD = 0xE74C3C


class Notifier:
    def __init__(self, webhook_url: str = "", enabled: dict | None = None, quiet: bool = False):
        self.url = (webhook_url or "").strip()
        self.enabled = enabled or {}
        self.quiet = quiet
        self._last_error = 0.0

    @property
    def active(self) -> bool:
        return bool(self.url)

    def _log(self, text: str) -> None:
        if not self.quiet:
            print(text, flush=True)

    def _post(self, payload: dict, image: Path | None = None) -> None:
        if not self.url:
            return
        try:
            if image and image.exists():
                with image.open("rb") as fh:
                    files = {
                        "payload_json": (None, json.dumps(payload), "application/json"),
                        "files[0]": (image.name, fh, "image/png"),
                    }
                    resp = requests.post(self.url, files=files, timeout=20)
            else:
                resp = requests.post(self.url, json=payload, timeout=20)

            if resp.status_code == 429:
                wait = float(resp.json().get("retry_after", 1.0))
                time.sleep(min(wait, 5.0))
                requests.post(self.url, json=payload, timeout=20)
            elif resp.status_code >= 400:
                raise RuntimeError(f"HTTP {resp.status_code} {resp.text[:200]}")
        except Exception as exc:
            # 같은 오류로 로그를 도배하지 않는다
            if time.time() - self._last_error > 300:
                self._last_error = time.time()
                self._log(f"  [알림 실패] {exc}")

    def send(
        self,
        title: str,
        description: str = "",
        color: int = COLOR_INFO,
        fields: list[tuple[str, str]] | None = None,
        image: Path | None = None,
        mention: bool = False,
    ) -> None:
        embed = {
            "title": title,
            "description": description[:3900],
            "color": color,
            # 디스코드는 오프셋 없는 시각을 UTC로 읽는다. 로컬 오프셋을 붙여야 제대로 보인다.
            "timestamp": datetime.now().astimezone().isoformat(),
        }
        if fields:
            embed["fields"] = [
                {"name": n[:250], "value": str(v)[:1000], "inline": len(str(v)) < 30}
                for n, v in fields
            ]
        if image is not None:
            embed["image"] = {"url": f"attachment://{image.name}"}

        payload = {"embeds": [embed]}
        if mention:
            payload["content"] = "@here"
        self._post(payload, image)

    # ---- 이벤트별 -----------------------------------------------------

    def _on(self, key: str) -> bool:
        return bool(self.enabled.get(key, True))

    def showtime_open(self, showtimes: list, extra: str = "") -> None:
        lines = "\n".join(f"• {s}" for s in showtimes[:15])
        self._log(f"[회차 오픈] {len(showtimes)}건\n{lines}")
        if self._on("on_showtime_open"):
            self.send(
                f"새 회차 {len(showtimes)}건 오픈",
                f"{lines}\n{extra}".strip(),
                COLOR_INFO,
                mention=True,
            )

    def seat_found(self, showtime, count: int, image: Path | None = None) -> None:
        self._log(f"[좌석 발견] {showtime} -> {count}석")
        if self._on("on_seat_found"):
            self.send(
                "잔여석 발견, 예매 시도",
                str(showtime),
                COLOR_WARN,
                fields=[("잔여", f"{count}석"), ("상영관", showtime.screen)],
                image=image,
                mention=True,
            )

    def success(self, showtime, seats: str, amount: str, image: Path | None = None) -> None:
        self._log(f"[예매 성공] {showtime} / {seats} / {amount}")
        if self._on("on_success"):
            self.send(
                "예매 성공",
                str(showtime),
                COLOR_GOOD,
                fields=[("좌석", seats), ("결제금액", amount)],
                image=image,
                mention=True,
            )

    def toss_pending(self, showtime, seats: str, amount: str, left_sec: float,
                     image: Path | None = None) -> None:
        """토스 결제 알림을 보냈으니 폰에서 승인해 달라는 안내.

        여기서 알림을 놓치면 좌석이 그대로 날아가므로 항상 멘션한다.
        """
        self._log(f"[결제 승인 대기] {showtime} / {seats} / {amount} (남은 {left_sec:.0f}초)")
        self.send(
            "토스로 결제 알림을 보냈습니다. 폰에서 승인해 주세요",
            f"{showtime}\n\n토스 앱 알림을 열어 결제를 승인하면 예매가 끝납니다.\n"
            "알림이 안 보이면 첨부된 QR코드를 폰 기본 카메라로 찍으세요.",
            COLOR_WARN,
            fields=[
                ("좌석", seats),
                ("결제금액", amount),
                ("남은 시간", f"약 {left_sec / 60:.0f}분"),
            ],
            image=image,
            mention=True,
        )

    def failure(self, reason: str, showtime=None, image: Path | None = None) -> None:
        self._log(f"[예매 실패] {reason}")
        if self._on("on_failure"):
            self.send(
                "예매 실패, 감시를 계속합니다",
                f"{showtime}\n{reason}" if showtime else reason,
                COLOR_BAD,
                image=image,
            )

    def blocked(self, reason: str, wait_sec: float) -> None:
        self._log(f"[차단 감지] {reason} -> {wait_sec:.0f}초 대기")
        if self._on("on_blocked"):
            self.send(
                "차단 감지, 대기 후 재시도",
                reason,
                COLOR_BAD,
                fields=[("대기", f"{wait_sec:.0f}초")],
            )

    def session_expired(self, down_sec: float = 0.0) -> None:
        since = f"\n끊긴 지 {down_sec / 60:.0f}분 지났습니다." if down_sec else ""
        self._log(f"[세션 만료] CGV 로그인이 풀렸습니다.{since}")
        self.send(
            "CGV 로그인 세션 만료",
            "감시는 계속하지만 지금은 예매를 할 수 없습니다.\n"
            f"열려 있는 Chrome 창에서 다시 로그인해 주세요.{since}",
            COLOR_BAD,
            mention=True,
        )

    def session_restored(self, down_sec: float = 0.0) -> None:
        text = f"{down_sec / 60:.0f}분 만에 복구됐습니다." if down_sec else "복구됐습니다."
        self._log(f"[세션 복구] {text}")
        self.send("로그인 복구됨", f"예매 시도를 다시 시작합니다. {text}", COLOR_GOOD)

    def heartbeat(self, text: str) -> None:
        self._log(f"[생존] {text}")
        self.send("감시 중", text, COLOR_INFO)

    def startup(self, text: str) -> None:
        self._log(text)
        self.send("예매봇 시작", text, COLOR_INFO)
