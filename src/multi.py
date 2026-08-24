"""극장 여러 곳을 한 프로세스에서 번갈아 감시한다.

감시자(Watcher)는 극장 하나를 맡는다. 여러 극장을 보려면 감시자를 여럿 두고
번갈아 한 턴씩 돌리면 된다. 스레드는 쓰지 않는다. 브라우저가 하나뿐이라
예매는 어차피 한 번에 하나씩만 할 수 있고, 동시에 두 곳이 예매 화면을
조작하면 서로를 밟는다.

[요청 속도] 한 턴 돌 때마다 쉰다. 감시자마다 쉬는 게 아니라 매 턴 쉬므로,
극장이 둘이어도 CGV로 나가는 요청 속도는 한 곳만 볼 때와 같다. 대신 각
극장을 보는 주기는 극장 수만큼 길어진다. 차단당하면 아무것도 못 하므로
이쪽을 택했다.

[차단 전파] 차단은 IP 단위라 한 극장에서 걸리면 다른 극장도 마찬가지다.
한 감시자가 백오프에 들어가면 나머지에게도 같은 백오프를 물린다.
"""

from __future__ import annotations

import time


class MultiWatcher:
    def __init__(self, watchers, cfg, notifier):
        if not watchers:
            raise ValueError("감시자가 하나도 없습니다")
        self.watchers = list(watchers)
        self.cfg = cfg
        self.notify = notifier
        # 생존 신고는 여기서 한 번에 묶어 보낸다
        for w in self.watchers:
            w.heartbeat_enabled = False
        self._last_heartbeat = time.time()

    # ---- 내부 ----------------------------------------------------------

    def _share_backoff(self, source) -> None:
        """한 감시자가 물린 백오프를 나머지에게도 물린다.

        sleep_interval() 이 자기 백오프를 소모해 버리므로 그 전에 나눠야 한다.
        """
        wait = getattr(source, "_backoff", 0.0)
        if wait <= 0:
            return
        for w in self.watchers:
            if w is not source:
                w._backoff = max(w._backoff, wait)

    def _maybe_heartbeat(self) -> None:
        every = self.cfg.notify.heartbeat_min
        if not every:
            return
        if time.time() - self._last_heartbeat < every * 60:
            return
        self._last_heartbeat = time.time()
        body = "\n\n".join(w.status_line() for w in self.watchers)
        self.notify.heartbeat(body + self.watchers[0].login_line())

    # ---- 공개 ----------------------------------------------------------

    def run(self, on_hit) -> None:
        """on_hit(showtime, theater) -> True 면 루프를 끝낸다."""
        i = 0
        while True:
            w = self.watchers[i % len(self.watchers)]
            i += 1

            # 기본 인자로 묶어 두면 나중에 w 가 바뀌어도 이 턴의 극장이 간다
            if w.step(lambda s, t=w.theater: on_hit(s, t)):
                return

            self._share_backoff(w)
            self._maybe_heartbeat()
            time.sleep(w.sleep_interval())
