"""로그인 세션 감시.

감시에 쓰는 상영시간표 API는 비로그인으로도 잘 응답한다. 그래서 세션이 끊겨도
봇은 아무 일 없다는 듯 계속 돌다가, 정작 좌석을 잡는 순간에야 실패한다.
그 사이에 표를 놓치므로 세션 자체를 따로 지켜본다.

두 가지를 한다.
  - 주기적으로 인증 엔드포인트를 건드려 세션이 유휴로 만료되지 않게 한다.
  - 그럼에도 끊기면 즉시 디스코드로 알린다. 재로그인은 사람만 할 수 있다.
"""

from __future__ import annotations

import time

from .cgv import ApiStatusError, BlockedError, CgvError, QueueWaitError


class SessionGuard:
    def __init__(
        self,
        api,
        notifier,
        check_every_sec: float = 60.0,
        keepalive_every_sec: float = 600.0,
        renotify_every_sec: float = 1800.0,
    ):
        self.api = api
        self.notify = notifier
        self.check_every = check_every_sec
        self.keepalive_every = keepalive_every_sec
        self.renotify_every = renotify_every_sec

        self.logged_in = True
        self.expired_since = 0.0
        self._last_check = 0.0
        self._last_keepalive = time.time()
        self._last_alert = 0.0
        self._keepalive_broken = False

    # ---- 내부 ----------------------------------------------------------

    def _keepalive(self) -> None:
        """세션을 살려두려고 인증 엔드포인트를 한 번 건드린다."""
        if not self._keepalive_broken:
            try:
                self.api.call("session_keepalive")
                return
            except BlockedError:
                raise
            except ApiStatusError as exc:
                if exc.needs_login:
                    return
                self._keepalive_broken = True
                print(f"  [세션] keepalive 엔드포인트가 바뀐 듯합니다. login_check로 대체: {exc}")
            except QueueWaitError:
                raise
            except CgvError as exc:
                self._keepalive_broken = True
                print(f"  [세션] keepalive 실패, login_check로 대체합니다: {exc}")
        self.api.is_logged_in()

    def _on_expired(self) -> None:
        self.logged_in = False
        self.expired_since = time.time()
        self._last_alert = time.time()
        self.notify.session_expired()

    def _on_restored(self) -> None:
        down = time.time() - self.expired_since if self.expired_since else 0.0
        self.logged_in = True
        self.expired_since = 0.0
        self.notify.session_restored(down)

    # ---- 공개 ----------------------------------------------------------

    def force_check(self) -> bool:
        """다음 턴을 기다리지 않고 지금 확인한다.

        예매를 시도하다 로그인 안내창을 만났을 때처럼 세션이 끊긴 정황이
        이미 잡힌 경우에 쓴다.
        """
        self._last_check = 0.0
        return self.tick()

    def tick(self) -> bool:
        """감시 루프가 매 턴 부른다. 현재 로그인 상태를 돌려준다."""
        now = time.time()

        if now - self._last_check >= self.check_every:
            self._last_check = now
            try:
                state = self.api.is_logged_in()
            except BlockedError:
                return self.logged_in  # 차단은 감시 루프가 따로 처리한다
            except QueueWaitError:
                raise
            except CgvError:
                return self.logged_in

            if self.logged_in and not state:
                self._on_expired()
            elif not self.logged_in and state:
                self._on_restored()
            elif not self.logged_in and now - self._last_alert >= self.renotify_every:
                # 알림을 놓쳤을 수 있으니 끊긴 동안 주기적으로 다시 부른다
                self._last_alert = now
                self.notify.session_expired(down_sec=now - self.expired_since)

        if self.logged_in and now - self._last_keepalive >= self.keepalive_every:
            self._last_keepalive = now
            try:
                self._keepalive()
            except QueueWaitError:
                raise
            except CgvError:
                pass

        return self.logged_in
