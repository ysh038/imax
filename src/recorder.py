"""CGV 신규 시스템이 실제로 호출하는 API를 녹화한다.

페이지 안에서 window.fetch와 XMLHttpRequest를 감싸 요청/응답을 버퍼에 쌓고,
CDP로 주기적으로 회수한다. 응답 본문을 통째로 얻을 수 있어 CDP Network 이벤트로
requestId를 쫓는 방식보다 확실하다.
"""

from __future__ import annotations

import json
import re
import time
from collections import OrderedDict
from pathlib import Path

from . import cdp
from .paths import DISCOVERY_DIR, DOCS_DIR

HOOK_JS = r"""
(function () {
  if (window.__cgvrec) { return "already"; }
  window.__cgvrec = [];
  var MAX = 800;

  function clip(s, n) {
    n = n || 30000;
    if (typeof s !== "string") return s;
    return s.length > n ? s.slice(0, n) + "...[truncated total=" + s.length + "]" : s;
  }

  function bodyToString(b) {
    try {
      if (b === null || b === undefined) return null;
      if (typeof b === "string") return clip(b);
      if (typeof URLSearchParams !== "undefined" && b instanceof URLSearchParams) return clip(b.toString());
      if (typeof FormData !== "undefined" && b instanceof FormData) {
        var o = {};
        b.forEach(function (v, k) { o[k] = (typeof v === "string") ? v : "[file]"; });
        return clip(JSON.stringify(o));
      }
      return clip("[" + Object.prototype.toString.call(b) + "]");
    } catch (e) { return "[unserializable]"; }
  }

  function headersToObj(h) {
    var o = {};
    try {
      if (!h) return o;
      if (typeof Headers !== "undefined" && h instanceof Headers) { h.forEach(function (v, k) { o[k] = v; }); return o; }
      if (Array.isArray(h)) { h.forEach(function (p) { o[p[0]] = p[1]; }); return o; }
      Object.keys(h).forEach(function (k) { o[k] = String(h[k]); });
    } catch (e) {}
    return o;
  }

  function push(rec) {
    try {
      rec.t = Date.now();
      rec.page = location.href;
      window.__cgvrec.push(rec);
      if (window.__cgvrec.length > MAX) window.__cgvrec.shift();
    } catch (e) {}
  }

  var origFetch = window.fetch;
  if (origFetch) {
    window.fetch = function (input, init) {
      var url = "", method = "GET", reqHeaders = {}, reqBody = null;
      try {
        if (typeof input === "string") { url = input; }
        else if (input && input.url) { url = input.url; method = input.method || "GET"; }
        else { url = String(input); }
        if (init) {
          if (init.method) method = init.method;
          reqHeaders = headersToObj(init.headers);
          reqBody = bodyToString(init.body);
        }
      } catch (e) {}

      var p = origFetch.apply(this, arguments);
      try {
        p.then(function (res) {
          try {
            res.clone().text().then(function (txt) {
              push({ kind: "fetch", method: method, url: res.url || url, status: res.status,
                     reqHeaders: reqHeaders, reqBody: reqBody, resBody: clip(txt) });
            }, function () {});
          } catch (e) {}
        }, function (err) {
          push({ kind: "fetch", method: method, url: url, status: 0,
                 reqHeaders: reqHeaders, reqBody: reqBody, error: String(err) });
        });
      } catch (e) {}
      return p;
    };
  }

  var OrigXHR = window.XMLHttpRequest;
  if (OrigXHR) {
    var PatchedXHR = function () {
      var xhr = new OrigXHR();
      var info = { method: "GET", url: "", reqHeaders: {}, reqBody: null };
      var open = xhr.open, send = xhr.send, setHeader = xhr.setRequestHeader;

      xhr.open = function (m, u) { info.method = m; info.url = u; return open.apply(xhr, arguments); };
      xhr.setRequestHeader = function (k, v) { info.reqHeaders[k] = String(v); return setHeader.apply(xhr, arguments); };
      xhr.send = function (b) {
        info.reqBody = bodyToString(b);
        xhr.addEventListener("loadend", function () {
          var body = null;
          try {
            var rt = xhr.responseType;
            body = (rt === "" || rt === "text") ? xhr.responseText
                 : (rt === "json" ? JSON.stringify(xhr.response) : "[" + rt + "]");
          } catch (e) { body = "[unreadable]"; }
          push({ kind: "xhr", method: info.method, url: xhr.responseURL || info.url, status: xhr.status,
                 reqHeaders: info.reqHeaders, reqBody: info.reqBody, resBody: clip(body) });
        });
        return send.apply(xhr, arguments);
      };
      return xhr;
    };
    PatchedXHR.prototype = OrigXHR.prototype;
    ["UNSENT", "OPENED", "HEADERS_RECEIVED", "LOADING", "DONE"].forEach(function (k, i) { PatchedXHR[k] = i; });
    window.XMLHttpRequest = PatchedXHR;
  }

  return "installed";
})()
"""

DRAIN_JS = "JSON.stringify(window.__cgvrec ? window.__cgvrec.splice(0, window.__cgvrec.length) : null)"

# 정적 리소스는 API 분석에 방해만 된다.
_NOISE = re.compile(
    r"\.(?:js|mjs|css|png|jpe?g|gif|svg|webp|avif|woff2?|ttf|ico|map)(?:\?|$)",
    re.IGNORECASE,
)
_TRACKER = re.compile(
    r"(google|doubleclick|facebook|kakao(?!pay)|criteo|adsystem|braze|appsflyer|amplitude|"
    r"datadog|sentry|newrelic|hotjar|clarity|wcs\.naver|analytics|gtm|beacon)",
    re.IGNORECASE,
)


def is_interesting(rec: dict) -> bool:
    url = rec.get("url") or ""
    if not url or url.startswith("data:") or url.startswith("blob:"):
        return False
    if _NOISE.search(url):
        return False
    if _TRACKER.search(url):
        return False
    return True


class Recorder:
    """열려 있는 모든 페이지 탭에 후킹을 심고 기록을 모은다."""

    def __init__(self, port: int, out_path: Path | None = None):
        self.port = port
        self.sessions: dict[str, cdp.CDPSession] = {}
        self.records: list[dict] = []
        DISCOVERY_DIR.mkdir(parents=True, exist_ok=True)
        self.out_path = out_path or DISCOVERY_DIR / f"session-{time.strftime('%Y%m%d-%H%M%S')}.jsonl"
        self._fh = self.out_path.open("a", encoding="utf-8")

    def _session_for(self, target: dict) -> cdp.CDPSession | None:
        tid = target["id"]
        session = self.sessions.get(tid)
        if session is not None:
            return session
        try:
            session = cdp.CDPSession(target["webSocketDebuggerUrl"])
            session.call("Page.enable")
            session.add_startup_script(HOOK_JS)  # 이후 페이지 이동에도 유지
            session.evaluate(HOOK_JS)  # 이미 떠 있는 문서에도 즉시 적용
            self.sessions[tid] = session
            return session
        except Exception:
            return None

    def sync_targets(self) -> int:
        try:
            targets = cdp.list_page_targets(self.port)
        except Exception:
            return len(self.sessions)

        alive = {t["id"] for t in targets}
        for tid in list(self.sessions):
            if tid not in alive:
                self.sessions.pop(tid).close()
        for t in targets:
            self._session_for(t)
        return len(self.sessions)

    def drain(self) -> list[dict]:
        """모든 탭에서 새 기록을 회수한다. 재주입이 필요한 문서도 여기서 처리."""
        fresh: list[dict] = []
        for tid, session in list(self.sessions.items()):
            try:
                raw = session.evaluate(DRAIN_JS)
            except Exception:
                session.close()
                self.sessions.pop(tid, None)
                continue

            try:
                batch = json.loads(raw) if raw else None
            except (TypeError, ValueError):
                continue

            if batch is None:
                # 새 문서로 넘어가 후킹이 사라졌다. 다시 심고 다음 턴에 회수한다.
                try:
                    session.evaluate(HOOK_JS)
                except Exception:
                    pass
                continue

            for rec in batch:
                if is_interesting(rec):
                    fresh.append(rec)
                    self._fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

        if fresh:
            self._fh.flush()
            self.records.extend(fresh)
        return fresh

    def close(self) -> None:
        for session in self.sessions.values():
            session.close()
        self.sessions.clear()
        self._fh.close()


def normalize_url(url: str) -> str:
    """숫자/날짜/코드를 자리표시자로 바꿔 같은 엔드포인트끼리 묶는다."""
    url = url.split("#", 1)[0]
    base, _, query = url.partition("?")
    base = re.sub(r"/\d{8,}", "/{date}", base)
    base = re.sub(r"/\d+", "/{id}", base)
    base = re.sub(r"/[0-9a-fA-F]{8}-[0-9a-fA-F-]{27,}", "/{uuid}", base)
    if query:
        keys = sorted({p.split("=", 1)[0] for p in query.split("&") if p})
        return f"{base}?{'&'.join(keys)}"
    return base


def summarize(records: list[dict]) -> "OrderedDict[str, dict]":
    groups: OrderedDict[str, dict] = OrderedDict()
    for rec in records:
        key = f"{rec.get('method', 'GET').upper()} {normalize_url(rec.get('url', ''))}"
        g = groups.setdefault(
            key,
            {"count": 0, "statuses": set(), "sample": rec, "pages": set()},
        )
        g["count"] += 1
        g["statuses"].add(rec.get("status"))
        if rec.get("page"):
            g["pages"].add(rec["page"])
        # 본문이 있는 샘플을 우선 보관한다
        if not g["sample"].get("resBody") and rec.get("resBody"):
            g["sample"] = rec
    return groups


def _pretty(body: str | None, limit: int = 1800) -> str:
    if not body:
        return "(없음)"
    try:
        text = json.dumps(json.loads(body), ensure_ascii=False, indent=2)
    except (TypeError, ValueError):
        text = body
    if len(text) > limit:
        text = text[:limit] + f"\n... (총 {len(text)}자, 원문은 discovery/ 참고)"
    return text


def write_markdown(records: list[dict], out: Path | None = None) -> Path:
    out = out or (DOCS_DIR / "cgv_api.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    groups = summarize(records)

    lines = [
        "# CGV 신규 시스템 API 관찰 기록",
        "",
        f"- 녹화 시각: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 수집 요청: {len(records)}건 / 고유 엔드포인트: {len(groups)}개",
        "",
        "자동 생성 문서입니다. `tools/record_api.py`를 다시 돌리면 갱신됩니다.",
        "",
        "## 엔드포인트 목록",
        "",
        "| 호출수 | 상태 | 엔드포인트 |",
        "| ---: | --- | --- |",
    ]
    for key, g in sorted(groups.items(), key=lambda kv: -kv[1]["count"]):
        statuses = ",".join(str(s) for s in sorted(g["statuses"], key=lambda x: (x is None, x)))
        lines.append(f"| {g['count']} | {statuses} | `{key}` |")

    lines += ["", "## 상세", ""]
    for key, g in sorted(groups.items(), key=lambda kv: -kv[1]["count"]):
        sample = g["sample"]
        lines += [
            f"### `{key}`",
            "",
            f"- 실제 URL: `{sample.get('url', '')}`",
            f"- 호출 페이지: {', '.join(sorted(g['pages'])) or '(미상)'}",
            "",
            "요청 본문:",
            "",
            "```json",
            _pretty(sample.get("reqBody"), limit=1200),
            "```",
            "",
            "응답 본문:",
            "",
            "```json",
            _pretty(sample.get("resBody")),
            "```",
            "",
        ]

    out.write_text("\n".join(lines), encoding="utf-8")
    return out
