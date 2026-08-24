"""극장 여러 곳 동시 감시에 대한 검증.

브라우저도 CGV도 건드리지 않는다. 전부 가짜 객체로 돈다.

    .venv/bin/python -m unittest discover -s tests -v
"""

import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from src import cgv, config  # noqa: E402
from src.cgv import BlockedError, CgvError, QueueWaitError, Showtime  # noqa: E402
from src.multi import MultiWatcher  # noqa: E402
from src.watcher import Watcher  # noqa: E402

FIELDS = cgv.load_spec()["showtime_fields"]

BASE_YAML = """
movie:
  title_contains: "오디세이"
dates:
  from: "2026-08-28"
  to: "2026-08-30"
showtimes:
  after: "00:00"
  before: "28:00"
  min_lead_hours: 0
seats:
  count: 2
  min_count: 1
polling:
  interval_sec: [4, 9]
booking:
  auto_pay: false
notify:
  heartbeat_min: 60
"""


def write_cfg(extra: str) -> Path:
    f = tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8")
    f.write(BASE_YAML + extra)
    f.close()
    return Path(f.name)


def show(site="0013", name="용산", prod="111", screen="IMAX관", movie="오디세이",
         date="20260829", start="2200", free=10, total=100):
    return Showtime(
        raw={"movNm": movie, "scnsNm": screen, "tcscnsGradNm": "", "movkndDsplNm": "",
             "prodNo": prod, "scnYmd": date, "scnsrtTm": start,
             "frSeatCnt": free, "stcnt": total, "scnSseq": "1"},
        fields=FIELDS, site_no=site, theater_name=name,
    )


class FakeNotify:
    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        def rec(*a, **kw):
            self.calls.append((name, a, kw))
        return rec


class FakeApi:
    """showtimes()/open_dates() 만 흉내낸다."""

    def __init__(self, rows=(), site_no="0013"):
        self.rows = list(rows)
        self.site_no = site_no

    def open_dates(self):
        return sorted({s.date for s in self.rows})

    def showtimes(self, ymd):
        return [s for s in self.rows if s.date == ymd]

    def seat_map(self, s):
        return []


# ----------------------------------------------------------------------
class TestConfig(unittest.TestCase):
    def test_theaters_list(self):
        p = write_cfg("""
theaters:
  - name: CGV 용산아이파크몰
    site_no: "0013"
    screen_keywords: ["IMAX"]
  - name: CGV 천호
    site_no: "0199"
    screen_keywords: ["SCREENX"]
""")
        c = config.load(p)
        c.validate()
        self.assertEqual([t.site_no for t in c.theaters], ["0013", "0199"])
        self.assertEqual(c.theaters[1].screen_keywords, ["SCREENX"])

    def test_singular_theater_still_works(self):
        p = write_cfg("""
theater:
  name: CGV 천호
  site_no: "0199"
  screen_keywords: ["SCREENX"]
""")
        c = config.load(p)
        c.validate()
        self.assertEqual(len(c.theaters), 1)
        self.assertEqual(c.theater.site_no, "0199")

    def test_theater_property_is_first(self):
        p = write_cfg("""
theaters:
  - {name: A, site_no: "1", screen_keywords: ["x"]}
  - {name: B, site_no: "2", screen_keywords: ["y"]}
""")
        self.assertEqual(config.load(p).theater.name, "A")

    def test_both_forms_is_an_error(self):
        p = write_cfg("""
theater: {name: A, site_no: "1"}
theaters:
  - {name: B, site_no: "2"}
""")
        with self.assertRaises(config.ConfigError):
            config.load(p)

    def test_empty_list_is_an_error(self):
        p = write_cfg("theaters: []\n")
        with self.assertRaises(config.ConfigError):
            config.load(p)

    def test_duplicate_site_no_is_an_error(self):
        p = write_cfg("""
theaters:
  - {name: A, site_no: "0013"}
  - {name: B, site_no: "0013"}
""")
        with self.assertRaises(config.ConfigError):
            config.load(p).validate()

    def test_missing_site_no_is_an_error(self):
        p = write_cfg("""
theaters:
  - {name: A, site_no: ""}
""")
        with self.assertRaises(config.ConfigError):
            config.load(p).validate()

    def test_no_theater_key_falls_back_to_default(self):
        c = config.load(write_cfg(""))
        c.validate()
        self.assertEqual(c.theaters[0].site_no, "0013")


# ----------------------------------------------------------------------
class TestShowtimeIdentity(unittest.TestCase):
    def test_key_is_unique_across_theaters(self):
        a = show(site="0013", prod="111")
        b = show(site="0199", prod="111")
        self.assertNotEqual(a.key, b.key, "극장이 다르면 키도 달라야 한다")

    def test_key_still_separates_showtimes_in_one_theater(self):
        self.assertNotEqual(show(prod="111").key, show(prod="222").key)

    def test_str_names_the_theater(self):
        self.assertIn("천호", str(show(site="0199", name="천호")))

    def test_str_without_theater_has_no_leading_space(self):
        s = Showtime(raw={"scnYmd": "20260829", "scnsrtTm": "2200"}, fields=FIELDS)
        self.assertFalse(str(s).startswith(" "))

    def test_api_stamps_theater_on_showtimes(self):
        class D:
            def set_script_timeout(self, _): pass
        api = cgv.CgvApi(D(), site_no="0199", theater_name="CGV 천호")
        api.call = lambda role, **kw: [{"prodNo": "1", "scnYmd": "20260829",
                                        "scnsrtTm": "2200", "movNm": "x"}]
        got = api.showtimes("20260829")[0]
        self.assertEqual(got.site_no, "0199")
        self.assertEqual(got.theater_name, "CGV 천호")


# ----------------------------------------------------------------------
class TestWatcherPerTheater(unittest.TestCase):
    def setUp(self):
        self.cfg = config.load(write_cfg("""
theaters:
  - {name: CGV 용산아이파크몰, site_no: "0013", screen_keywords: ["IMAX"]}
  - {name: CGV 천호, site_no: "0199", screen_keywords: ["SCREENX"]}
"""))

    def test_each_watcher_uses_its_own_screen_keywords(self):
        imax = show(screen="IMAX관")
        srx = show(screen="2관[SCREENX]")
        w0 = Watcher(FakeApi(), self.cfg, FakeNotify(), theater=self.cfg.theaters[0])
        w1 = Watcher(FakeApi(), self.cfg, FakeNotify(), theater=self.cfg.theaters[1])

        self.assertTrue(w0.matches(imax))
        self.assertFalse(w0.matches(srx), "용산 감시자가 SCREENX를 잡으면 안 된다")
        self.assertTrue(w1.matches(srx))
        self.assertFalse(w1.matches(imax), "천호 감시자가 IMAX를 잡으면 안 된다")

    def test_defaults_to_representative_theater(self):
        w = Watcher(FakeApi(), self.cfg, FakeNotify())
        self.assertEqual(w.theater.site_no, "0013")


# ----------------------------------------------------------------------
class TestWatcherStep(unittest.TestCase):
    def _watcher(self, cfg=None, rows=()):
        cfg = cfg or config.load(write_cfg(""))
        return Watcher(FakeApi(rows), cfg, FakeNotify())

    def test_step_returns_true_when_on_hit_says_stop(self):
        w = self._watcher()
        w.poll_once = lambda: ([show()], [])
        self.assertTrue(w.step(lambda s: True))

    def test_step_returns_false_when_on_hit_says_continue(self):
        w = self._watcher()
        w.poll_once = lambda: ([show()], [])
        self.assertFalse(w.step(lambda s: False))

    def test_queue_wait_becomes_12s_backoff(self):
        w = self._watcher()
        def boom(): raise QueueWaitError("대기열")
        w.poll_once = boom
        self.assertFalse(w.step(lambda s: True))
        self.assertEqual(w.sleep_interval(), 12.0)

    def test_api_error_becomes_15s_backoff(self):
        w = self._watcher()
        def boom(): raise CgvError("서버 오류")
        w.poll_once = boom
        w.step(lambda s: True)
        self.assertEqual(w.sleep_interval(), 15.0)

    def test_blocked_raises_backoff_and_notifies(self):
        w = self._watcher()
        def boom(): raise BlockedError("차단")
        w.poll_once = boom
        w.step(lambda s: True)
        self.assertGreaterEqual(w.sleep_interval(), w.cfg.polling.backoff_start_sec)
        self.assertIn("blocked", [c[0] for c in w.notify.calls])

    def test_logged_out_skips_booking_but_keeps_watching(self):
        w = self._watcher()
        w.poll_once = lambda: ([show()], [])
        w.session = type("G", (), {"tick": lambda self: False, "logged_in": False})()
        tried = []
        self.assertFalse(w.step(lambda s: tried.append(s) or True))
        self.assertEqual(tried, [], "로그아웃 상태에서는 예매를 시도하면 안 된다")


# ----------------------------------------------------------------------
class TestMultiWatcher(unittest.TestCase):
    def setUp(self):
        self.cfg = config.load(write_cfg("""
theaters:
  - {name: A, site_no: "0001", screen_keywords: ["x"]}
  - {name: B, site_no: "0002", screen_keywords: ["x"]}
  - {name: C, site_no: "0003", screen_keywords: ["x"]}
"""))
        self.notify = FakeNotify()
        self.ws = [Watcher(FakeApi(), self.cfg, self.notify, theater=t)
                   for t in self.cfg.theaters]
        for w in self.ws:
            w.poll_once = lambda: ([], [])
            w.sleep_interval = lambda: 0.0

    def test_children_heartbeats_are_disabled(self):
        MultiWatcher(self.ws, self.cfg, self.notify)
        self.assertTrue(all(not w.heartbeat_enabled for w in self.ws))

    def test_round_robin_order(self):
        order = []
        for w in self.ws:
            w.poll_once = lambda w=w: (order.append(w.theater.name), ([], []))[1]
        m = MultiWatcher(self.ws, self.cfg, self.notify)
        stop = {"n": 0}

        def guard():
            stop["n"] += 1
            if stop["n"] > 7:
                raise KeyboardInterrupt
        for w in self.ws:
            base = w.poll_once
            w.poll_once = lambda base=base: (guard(), base())[1]
        with self.assertRaises(KeyboardInterrupt):
            m.run(lambda s, t: False)
        self.assertEqual(order[:6], ["A", "B", "C", "A", "B", "C"])

    def test_passes_the_owning_theater_to_on_hit(self):
        target = show(site="0002", name="B")
        self.ws[1].poll_once = lambda: ([target], [])
        m = MultiWatcher(self.ws, self.cfg, self.notify)
        seen = []
        m.run(lambda s, t: (seen.append((s.site_no, t.site_no)), True)[1])
        self.assertEqual(seen, [("0002", "0002")])

    def test_backoff_is_shared_with_the_others(self):
        def boom(): raise BlockedError("차단")
        self.ws[0].poll_once = boom
        self.ws[0].sleep_interval = lambda: 0.0
        m = MultiWatcher(self.ws, self.cfg, self.notify)
        stop = {"n": 0}
        for w in self.ws[1:]:
            def p(w=w):
                stop["n"] += 1
                raise KeyboardInterrupt
            w.poll_once = p
        with self.assertRaises(KeyboardInterrupt):
            m.run(lambda s, t: False)
        start = self.cfg.polling.backoff_start_sec
        self.assertGreaterEqual(self.ws[1]._backoff, start)
        self.assertGreaterEqual(self.ws[2]._backoff, start)

    def test_empty_watcher_list_is_rejected(self):
        with self.assertRaises(ValueError):
            MultiWatcher([], self.cfg, self.notify)

    def test_combined_heartbeat_mentions_every_theater(self):
        m = MultiWatcher(self.ws, self.cfg, self.notify)
        m._last_heartbeat = 0.0
        m._maybe_heartbeat()
        beats = [c for c in self.notify.calls if c[0] == "heartbeat"]
        self.assertEqual(len(beats), 1, "생존 신고는 극장 수와 무관하게 한 번이어야 한다")
        body = beats[0][1][0]
        for name in ("A", "B", "C"):
            self.assertIn(name, body)


if __name__ == "__main__":
    unittest.main()
