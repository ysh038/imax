"""Chrome DevTools Protocol을 웹소켓으로 직접 사용하는 최소 클라이언트.

Selenium의 switch_to.window는 탭을 실제로 활성화시켜 사용자의 조작을 방해한다.
녹화기는 여러 탭을 동시에 들여다봐야 하므로 CDP에 직접 붙어 탭 활성화 없이 읽는다.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

from websocket import WebSocketTimeoutException, create_connection


class CDPError(RuntimeError):
    pass


def _http_json(port: int, path: str, timeout: float = 5.0, method: str = "GET"):
    url = f"http://127.0.0.1:{port}{path}"
    req = urllib.request.Request(url, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def is_up(port: int) -> bool:
    try:
        _http_json(port, "/json/version", timeout=2.0)
        return True
    except (urllib.error.URLError, OSError, ValueError):
        return False


def browser_version(port: int) -> dict:
    return _http_json(port, "/json/version")


def list_page_targets(port: int) -> list[dict]:
    targets = _http_json(port, "/json/list")
    return [
        t
        for t in targets
        if t.get("type") == "page"
        and t.get("webSocketDebuggerUrl")
        and not str(t.get("url", "")).startswith("devtools://")
    ]


def new_tab(port: int, url: str = "about:blank") -> dict:
    """탭을 하나 연다.

    맥에서는 창을 다 닫아도 Chrome 프로세스가 살아 있다. 그 상태로 붙으려 하면
    ChromeDriver가 "unable to discover open pages"로 실패하므로 탭을 만들어 준다.
    """
    return _http_json(port, f"/json/new?{urllib.parse.quote(url, safe='')}", method="PUT")


class CDPSession:
    """단일 페이지 타겟에 붙는 CDP 세션."""

    def __init__(self, ws_url: str, timeout: float = 15.0):
        self.ws_url = ws_url
        self._ws = create_connection(ws_url, timeout=timeout, suppress_origin=True)
        self._id = 0

    def call(self, method: str, params: dict | None = None, timeout: float = 15.0):
        self._id += 1
        msg_id = self._id
        self._ws.send(json.dumps({"id": msg_id, "method": method, "params": params or {}}))
        self._ws.settimeout(timeout)
        while True:
            data = json.loads(self._ws.recv())
            if data.get("id") != msg_id:
                continue  # 이벤트 메시지는 버린다
            if "error" in data:
                raise CDPError(f"{method}: {data['error']}")
            return data.get("result", {})

    def evaluate(self, expression: str, await_promise: bool = False):
        result = self.call(
            "Runtime.evaluate",
            {
                "expression": expression,
                "returnByValue": True,
                "awaitPromise": await_promise,
                "allowUnsafeEvalBlockedByCSP": True,
            },
        )
        if "exceptionDetails" in result:
            detail = result["exceptionDetails"]
            text = detail.get("exception", {}).get("description") or detail.get("text")
            raise CDPError(f"JS 예외: {text}")
        return result.get("result", {}).get("value")

    def add_startup_script(self, source: str) -> str:
        result = self.call("Page.addScriptToEvaluateOnNewDocument", {"source": source})
        return result.get("identifier", "")

    def close(self) -> None:
        try:
            self._ws.close()
        except Exception:
            pass


__all__ = [
    "CDPError",
    "CDPSession",
    "WebSocketTimeoutException",
    "browser_version",
    "is_up",
    "list_page_targets",
    "new_tab",
]
