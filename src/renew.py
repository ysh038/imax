"""로그인이 끊긴 것처럼 보일 때 사람 없이 되살려 본다.

CGV는 수명 짧은 accessToken과 1년짜리 refresh_token을 쿠키로 들고 다닌다.
SPA는 accessToken이 만료되면 refresh_token으로 조용히 재발급받는데, 봇은
페이지 안에서 fetch만 날릴 뿐 화면을 움직이지 않으니 그 갱신을 유발하지
못한다. 그래서 "로그인이 풀렸다"가 아니라 "토큰이 잠깐 비었다"인 경우가
대부분이고, 사람을 부르는 대신 봇이 스스로 메우면 된다.

사다리로 올라간다. 앞 단계가 실패하면 다음으로 넘어간다.
  1. refresh 엔드포인트 직접 호출 (endpoints.yaml 에 session_refresh 가 있을 때)
  2. 탭 리로드 - SPA가 부팅하면서 알아서 갱신한다
  3. (미구현) 로그인 페이지에서 '네이버 로그인' 클릭
  4. 사람 호출 - 여기까지 오면 SessionGuard가 디스코드로 알린다

[선] 어느 단계에서도 아이디나 비밀번호를 입력하지 않는다. 이미 살아 있는
세션을 다시 쓰는 데까지가 자동화의 몫이고, 진짜로 로그인이 필요해지면
사람을 부른다.

[주의] 갱신은 페이지를 이동시킬 수 있다. 예매를 진행하는 중에 부르면 안 된다.
SessionGuard.tick()은 감시 루프 맨 앞에서만 불리므로 예매와 겹치지 않는다.
"""

from __future__ import annotations

import time

from .cgv import CgvError, QueueWaitError

# endpoints.yaml 에 이 역할이 있으면 1단을 쓴다. 없으면 조용히 건너뛴다.
REFRESH_ROLE = "session_refresh"


class SessionRenewer:
    def __init__(
        self,
        api,
        home_url: str,
        settle_sec: float = 3.0,
        verify_timeout_sec: float = 12.0,
        min_interval_sec: float = 60.0,
    ):
        self.api = api
        self.home_url = home_url
        # 리로드 직후엔 SPA가 아직 토큰을 못 받았을 수 있다. 조금 기다린다.
        self.settle = settle_sec
        self.verify_timeout = verify_timeout_sec
        # 실패를 반복할 때 CGV를 두드려 패지 않도록 최소 간격을 둔다.
        self.min_interval = min_interval_sec
        self._last_try = 0.0

    # ---- 내부 ----------------------------------------------------------

    def _verify(self) -> bool:
        """갱신이 먹혔는지 잠깐 폴링하며 확인한다.

        쿠키가 자리잡기 전에 한 번 물어보고 실패로 단정하면 멀쩡한 갱신을
        버리게 된다.
        """
        deadline = time.time() + self.verify_timeout
        while True:
            try:
                if self.api.is_logged_in():
                    return True
            except QueueWaitError:
                raise
            except CgvError:
                pass  # 확인 실패는 '아니오'가 아니다. 시간이 남았으면 다시 본다.
            if time.time() >= deadline:
                return False
            time.sleep(1.0)

    def _by_refresh_endpoint(self) -> bool:
        if REFRESH_ROLE not in (self.api.spec.get("roles") or {}):
            return False
        try:
            self.api.call(REFRESH_ROLE)
        except QueueWaitError:
            raise
        except CgvError as exc:
            print(f"  [갱신] refresh 엔드포인트 실패: {exc}")
            return False
        return self._verify()

    def _by_reload(self) -> bool:
        try:
            self.api.driver.get(self.home_url)
        except Exception as exc:
            print(f"  [갱신] 페이지 리로드 실패: {exc}")
            return False
        time.sleep(self.settle)
        return self._verify()

    # ---- 공개 ----------------------------------------------------------

    def renew(self) -> str | None:
        """되살아났으면 어떤 방법이 먹혔는지, 실패했으면 None."""
        now = time.time()
        if now - self._last_try < self.min_interval:
            return None
        self._last_try = now

        for label, step in (
            ("refresh 엔드포인트", self._by_refresh_endpoint),
            ("페이지 리로드", self._by_reload),
        ):
            print(f"  [갱신] {label} 시도", flush=True)
            if step():
                print(f"  [갱신] {label}(으)로 살아났습니다.", flush=True)
                return label
        return None
