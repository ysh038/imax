"""예매 오픈 때 뜨는 접속 대기열.

CGV는 트래픽이 몰리면 NetFunnel(넷퍼넬) 같은 대기열을 띄운다. 화면 문구는 배포마다
바뀌고, 대기 중에 안내 팝업이 겹쳐 뜨기도 한다. 그래서 특정 버튼을 찾아 누르기보다

  1) 대기 중으로 보이면 새로고침/클릭을 하지 않고 기다린다
  2) 예매를 진행하는 버튼이 아닌 안내 팝업만 닫는다
  3) 대기가 풀리면 호출자에게 돌려준다

처음 걸렸을 때(그리고 대기 중 UI가 바뀌었을 때) 화면을 logs/queue/ 에 남겨 둔다.
다음번에 그 덤프로 감지 문구와 닫을 버튼을 맞춘다.

대기열은 좌석 선점 전에 일어나므로, 기다린 시간만큼 선점 제한시간을 늘려야 한다.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path

from selenium.common.exceptions import WebDriverException

from .browser import screenshot
from .paths import LOGS_DIR


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

_HTML_LIMIT = 400_000
_API_BODY_LIMIT = 200_000
_MAX_CHANGE_DUMPS = 8
_api_dumps = 0


def looks_like_queue(driver) -> bool:
    """지금 화면이 접속 대기열로 보이면 True."""
    try:
        blob = inspect(driver, full=False)
    except WebDriverException:
        return False
    return bool(_match_reasons(blob))


def inspect(driver, full: bool = False) -> dict:
    """대기열 판정과 덤프에 쓰는 화면 스냅샷.

    full=False 이면 HTML을 안 긁는다. 매 클릭마다 부르므로 가볍게 유지한다.
    """
    blob = driver.execute_script(_INSPECT_JS, bool(full)) or {}
    blob["matched"] = _match_reasons(blob)
    return blob


def wait_out(
    driver,
    notifier=None,
    timeout: float = 1800.0,
    poll: float = 2.5,
) -> float:
    """대기가 풀릴 때까지 기다린다. 기다린 초를 돌려준다. 대기가 없으면 0."""
    blob = inspect(driver, full=False)
    if not blob.get("matched"):
        return 0.0

    started = time.time()
    deadline = started + timeout
    session_dir = _new_session_dir()
    dump_dir = _dump_page(driver, session_dir, "enter")
    print("  [대기열] 접속 대기가 감지됐습니다. 화면을 건드리지 않고 기다립니다.", flush=True)
    print(f"  [대기열] 감지 근거: {', '.join(blob['matched'])}", flush=True)
    print(f"  [대기열] 덤프: {dump_dir}", flush=True)
    if notifier:
        shot = dump_dir / "screenshot.png"
        notifier.queue_entered(
            image=shot if shot.exists() else None,
            dump_dir=dump_dir,
            reasons=blob["matched"],
        )

    last_fp = _fingerprint(blob)
    changes = 0
    last_log = 0.0
    while time.time() < deadline:
        _dismiss_notices(driver)
        blob = inspect(driver, full=False)
        if not blob.get("matched"):
            waited = time.time() - started
            _dump_page(driver, session_dir, "cleared")
            print(f"  [대기열] 통과 ({waited:.0f}초)", flush=True)
            if notifier:
                notifier.queue_cleared(waited)
            time.sleep(1.5)
            return waited

        fp = _fingerprint(blob)
        if fp != last_fp and changes < _MAX_CHANGE_DUMPS:
            last_fp = fp
            changes += 1
            extra = _dump_page(driver, session_dir, f"change-{changes:02d}")
            print(f"  [대기열] 화면이 바뀌었습니다. 추가 덤프: {extra}", flush=True)

        now = time.time()
        if now - last_log >= 30:
            last_log = now
            left = deadline - now
            print(f"  [대기열] 대기 중… 남은 제한 {left:.0f}초", flush=True)
        time.sleep(poll)

    stuck = _dump_page(driver, session_dir, "timeout")
    raise QueueError(
        f"접속 대기가 {timeout:.0f}초 안에 끝나지 않았습니다. 덤프: {stuck}"
    )


def dump_api_body(url: str, status: int, body: str) -> Path | None:
    """API가 대기열 HTML을 줬을 때 본문을 남긴다. 프로세스당 몇 번만."""
    global _api_dumps
    if _api_dumps >= 3:
        return None
    _api_dumps += 1
    folder = _new_session_dir() / f"api-{_api_dumps:02d}"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "meta.json").write_text(
        json.dumps(
            {
                "url": url,
                "status": status,
                "body_len": len(body),
                "matched": _match_reasons({"url": url, "title": "", "text": body[:5000], "iframes": []}),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (folder / "body.html").write_text(body[:_API_BODY_LIMIT], encoding="utf-8", errors="replace")
    print(f"  [대기열] API 대기 응답 덤프: {folder}", flush=True)
    return folder


def _match_reasons(blob: dict) -> list[str]:
    text = (str(blob.get("text", "")) + " " + str(blob.get("title", ""))).lower()
    text_ns = text.replace(" ", "")
    src_parts = [str(blob.get("url", ""))]
    for frame in blob.get("iframes") or []:
        if isinstance(frame, dict):
            src_parts.append(str(frame.get("src", "")))
        else:
            src_parts.append(str(frame))
    src = " ".join(src_parts).lower()

    reasons = []
    for m in _TEXT_MARKERS:
        if m.replace(" ", "") in text_ns:
            reasons.append(f"text:{m}")
    for m in _SRC_MARKERS:
        if m in src:
            reasons.append(f"src:{m}")
    return reasons


def _fingerprint(blob: dict) -> str:
    """숫자가 바뀌는 대기 인원 때문에 매초 덤프가 생기지 않게, 구조를 본다."""
    text = re.sub(r"\d+", "#", str(blob.get("text", "")))[:1200]
    buttons = "|".join(
        re.sub(r"\d+", "#", str(b.get("text", ""))) for b in (blob.get("buttons") or [])
    )
    frames = "|".join(
        str(f.get("src", f) if isinstance(f, dict) else f) for f in (blob.get("iframes") or [])
    )
    raw = f"{blob.get('url','')}\n{blob.get('title','')}\n{frames}\n{buttons}\n{text}"
    return hashlib.sha1(raw.encode("utf-8", errors="replace")).hexdigest()


def _new_session_dir() -> Path:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    folder = LOGS_DIR / "queue" / stamp
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _dump_page(driver, session_dir: Path, reason: str) -> Path:
    blob = inspect(driver, full=True)
    folder = session_dir / reason
    folder.mkdir(parents=True, exist_ok=True)

    slim = dict(blob)
    html = slim.pop("html", "") or ""
    overlays = slim.pop("overlayHtml", "") or ""
    (folder / "dump.json").write_text(
        json.dumps(slim, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if html:
        (folder / "page.html").write_text(html[:_HTML_LIMIT], encoding="utf-8", errors="replace")
    if overlays:
        (folder / "overlays.html").write_text(
            overlays[:_HTML_LIMIT], encoding="utf-8", errors="replace"
        )
    (folder / "summary.txt").write_text(_summary_text(reason, slim), encoding="utf-8")

    try:
        screenshot(driver, f"queue-{reason}")
        driver.save_screenshot(str(folder / "screenshot.png"))
    except WebDriverException:
        pass

    print(_summary_text(reason, slim), flush=True)
    return folder


def _summary_text(reason: str, blob: dict) -> str:
    buttons = blob.get("buttons") or []
    frames = blob.get("iframes") or []
    dialogs = blob.get("dialogs") or []
    lines = [
        f"reason: {reason}",
        f"url: {blob.get('url', '')}",
        f"title: {blob.get('title', '')}",
        f"matched: {', '.join(blob.get('matched') or []) or '(없음)'}",
        f"readyState: {blob.get('readyState', '')}",
        "",
        "iframes:",
    ]
    if frames:
        for f in frames:
            if isinstance(f, dict):
                lines.append(f"  - src={f.get('src', '')} id={f.get('id', '')} name={f.get('name', '')}")
            else:
                lines.append(f"  - {f}")
    else:
        lines.append("  (없음)")
    lines.append("")
    lines.append("보이는 버튼:")
    if buttons:
        for b in buttons:
            lines.append(f"  - [{b.get('tag','')}] {b.get('text', '')!r}  class={b.get('className','')}")
    else:
        lines.append("  (없음)")
    lines.append("")
    lines.append("레이어/다이얼로그:")
    if dialogs:
        for d in dialogs:
            snippet = re.sub(r"\s+", " ", str(d.get("text", "")))[:200]
            lines.append(f"  - {d.get('className', '')}: {snippet}")
    else:
        lines.append("  (없음)")
    lines.append("")
    lines.append("본문:")
    lines.append(str(blob.get("text", ""))[:2000])
    lines.append("")
    return "\n".join(lines) + "\n"


def _dismiss_notices(driver) -> None:
    """예매와 무관한 안내/광고 팝업만 닫는다. 실패해도 무시한다."""
    try:
        driver.execute_script(_DISMISS_JS, _NEVER_CLICK.pattern, _SAFE_DISMISS.pattern)
    except WebDriverException:
        pass


_INSPECT_JS = r"""
const full = !!arguments[0];
function vis(el) {
  const r = el.getBoundingClientRect();
  return r.width >= 8 && r.height >= 8;
}
const iframes = Array.from(document.querySelectorAll('iframe')).map(f => {
  let inner = '';
  try { inner = (f.contentDocument && f.contentDocument.body && f.contentDocument.body.innerText || '').slice(0, 1500); }
  catch (e) { inner = '(cross-origin)'; }
  return { src: f.src || '', id: f.id || '', name: f.name || '', className: String(f.className || '').slice(0, 120), innerText: inner };
});
const buttons = Array.from(document.querySelectorAll('button, a, [role="button"], input[type="button"], input[type="submit"]'))
  .filter(vis)
  .slice(0, 80)
  .map(el => ({
    tag: el.tagName,
    id: el.id || '',
    className: String(el.className || '').slice(0, 160),
    text: (el.innerText || el.value || el.getAttribute('aria-label') || '').trim().slice(0, 80)
  }));
const dialogs = Array.from(document.querySelectorAll('[role="dialog"], [class*="modal"], [class*="popup"], [class*="layer"], [class*="overlay"], [class*="wait"]'))
  .filter(vis)
  .slice(0, 15)
  .map(el => ({
    tag: el.tagName,
    id: el.id || '',
    className: String(el.className || '').slice(0, 200),
    text: (el.innerText || '').trim().slice(0, 600)
  }));
const scripts = Array.from(document.querySelectorAll('script[src]'))
  .map(s => s.src || '')
  .filter(s => /netfunnel|nfplus|wait|queue/i.test(s))
  .slice(0, 20);
const cookieNames = (document.cookie || '').split(';').map(c => c.split('=')[0].trim()).filter(Boolean);
const overlayNodes = Array.from(document.querySelectorAll('[role="dialog"], [class*="modal"], [class*="popup"], [class*="layer"], [class*="overlay"]'))
  .filter(vis)
  .slice(0, 8);
return {
  url: location.href,
  title: document.title || '',
  readyState: document.readyState,
  text: (document.body && document.body.innerText || '').slice(0, 4000),
  iframes: iframes,
  buttons: buttons,
  dialogs: dialogs,
  scripts: scripts,
  cookieNames: cookieNames,
  html: full ? (document.documentElement && document.documentElement.outerHTML || '').slice(0, 400000) : '',
  overlayHtml: full ? overlayNodes.map(el => el.outerHTML).join('\n\n<!-- overlay -->\n\n').slice(0, 200000) : ''
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
  const layer = el.closest('[role="dialog"], [class*="modal"], [class*="popup"], [class*="layer"]');
  if (!layer) continue;
  el.click();
}
"""
