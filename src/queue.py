"""예매 오픈 때 뜨는 접속 대기열.

CGV는 트래픽이 몰리면 NetFunnel(넷퍼넬) 같은 대기열을 띄운다. 화면 문구는 배포마다
바뀌고, 대기 중에 안내 팝업이 겹쳐 뜨기도 한다. 그래서 특정 버튼을 찾아 누르기보다

  1) 대기 중으로 보이면 새로고침/클릭을 하지 않고 기다린다
  2) 예매를 진행하는 버튼이 아닌 안내 팝업만 닫는다
  3) 대기가 풀리면 호출자에게 돌려준다

대기열은 좌석 선점 전에 일어나므로, 기다린 시간만큼 선점 제한시간을 늘려야 한다.
"""

from __future__ import annotations

import re
import time

from selenium.common.exceptions import WebDriverException

from .browser import screenshot


class QueueError(RuntimeError):
    """대기열이 제한 시간 안에 빠지지 않음."""


# 화면 문구. 로딩 스피너('잠시만 기다려 주세요')나 쿠키만으로는 보지 않는다.
# NetFunnel 스크립트는 평소에도 깔려 있는 경우가 많다.
_TEXT_MARKERS = (
    "접속대기",
    "접속 대기",
    "대기열",
    "대기인원",
    "대기 인원",
    "남은 대기",
    "앞 대기",
    "순서를 기다리",
    "접속을 기다리",
    "대기번호",
    "예상 대기",
    "예상대기",
)
# URL·iframe 주소에만 쓴다. 스크립트 src 는 평소에도 있다.
_SRC_MARKERS = ("netfunnel", "nfplus.co.kr", "nfplus.kr")

# 이걸 누르면 예매/결제가 진행되므로 대기 중에는 절대 안 누른다.
_NEVER_CLICK = re.compile(
    r"결제|예매|토스|카드|비밀번호|선택완료|좌석|인원|pay|toss|예약",
    re.I,
)
_SAFE_DISMISS = re.compile(r"^(확인|닫기|close|ok)$", re.I)


def looks_like_queue(driver) -> bool:
    """지금 화면이 접속 대기열로 보이면 True."""
    try:
        blob = driver.execute_script(_INSPECT_JS) or {}
    except WebDriverException:
        return False
    text = (blob.get("text", "") + " " + blob.get("title", "")).lower().replace(" ", "")
    src = (blob.get("url", "") + " " + blob.get("iframes", "")).lower()
    if any(m.replace(" ", "") in text for m in _TEXT_MARKERS):
        return True
    return any(m in src for m in _SRC_MARKERS)


def wait_out(
    driver,
    notifier=None,
    timeout: float = 1800.0,
    poll: float = 2.5,
) -> float:
    """대기가 풀릴 때까지 기다린다. 기다린 초를 돌려준다. 대기가 없으면 0."""
    if not looks_like_queue(driver):
        return 0.0

    started = time.time()
    deadline = started + timeout
    print("  [대기열] 접속 대기가 감지됐습니다. 화면을 건드리지 않고 기다립니다.", flush=True)
    if notifier:
        shot = screenshot(driver, "queue-enter")
        notifier.queue_entered(image=shot)

    last_log = 0.0
    while time.time() < deadline:
        _dismiss_notices(driver)
        if not looks_like_queue(driver):
            waited = time.time() - started
            print(f"  [대기열] 통과 ({waited:.0f}초)", flush=True)
            if notifier:
                notifier.queue_cleared(waited)
            time.sleep(1.5)
            return waited
        now = time.time()
        if now - last_log >= 30:
            last_log = now
            left = deadline - now
            print(f"  [대기열] 대기 중… 남은 제한 {left:.0f}초", flush=True)
        time.sleep(poll)

    shot = screenshot(driver, "queue-timeout")
    raise QueueError(f"접속 대기가 {timeout:.0f}초 안에 끝나지 않았습니다. 화면: {shot}")


def _dismiss_notices(driver) -> None:
    """예매와 무관한 안내/광고 팝업만 닫는다. 실패해도 무시한다."""
    try:
        driver.execute_script(_DISMISS_JS, _NEVER_CLICK.pattern, _SAFE_DISMISS.pattern)
    except WebDriverException:
        pass


_INSPECT_JS = r"""
const iframes = Array.from(document.querySelectorAll('iframe'))
  .map(f => (f.src || '') + ' ' + (f.id || '') + ' ' + (f.name || ''))
  .join(' ');
return {
  url: location.href,
  title: document.title || '',
  text: (document.body && document.body.innerText || '').slice(0, 2500),
  iframes: iframes
};
"""

_DISMISS_JS = r"""
const neverRe = new RegExp(arguments[0], 'i');
const safeRe = new RegExp(arguments[1], 'i');
const nodes = Array.from(document.querySelectorAll('button, a, [role="button"]'));
for (const el of nodes) {
  const r = el.getBoundingClientRect();
  if (r.width < 8 || r.height < 8) continue;
  const t = (el.innerText || el.getAttribute('aria-label') || '').replace(/\s+/g, '');
  if (!t || t.length > 12) continue;
  if (neverRe.test(t)) continue;
  if (!safeRe.test(t)) continue;
  // 본문 예매 버튼이 아니라 떠 있는 레이어 안의 것만
  const layer = el.closest('[role="dialog"], [class*="modal"], [class*="popup"], [class*="layer"]');
  if (!layer) continue;
  el.click();
}
"""
