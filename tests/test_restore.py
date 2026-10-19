"""Rest is an actual, optional activity log; reports never overwrite observations."""
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from http.server import ThreadingHTTPServer
from pathlib import Path

from healthaio import config, restore_log
from healthaio.context import Context
from healthaio.modules import restore
from healthaio.server import make_handler, payload
from healthaio.store import write_table

NOW = datetime(2026, 10, 18, 10)


class Rest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="aio-restore-test-")
        self.root = Path(self.temp.name)
        self.cfg = config.Config(root=self.root, data_dir=self.root / "data", timezone="Australia/Melbourne", check_updates=False)
        self.n = 0

    def tearDown(self):
        self.temp.cleanup()

    def write(self, op, when=NOW, **kw):
        self.n += 1
        return restore_log.from_browser(self.cfg, {"op": op, "request_id": f"request-{self.n:06d}", **kw}, when)

    def page(self, now=NOW):
        return restore.build(Context(self.cfg, now=now))

    def body(self, low=False, stale=0):
        rows = []
        for n in range(35, -1, -1):
            day = NOW.date() - timedelta(days=n)
            if n < stale:
                continue
            bad = low and n < 3
            rows.append({"date": day, "hrv_ms": 22 if bad else 55 + n % 5,
                         "resting_hr": 78 if bad else 54 + n % 4, "sleep_min": 330 if bad else 470 + n % 10,
                         "complete": True})
        write_table(self.cfg.data_dir, "body_daily", rows)

    def test_read_only_page_creates_no_ledger_or_lock(self):
        p = self.page()
        self.assertEqual(p["situation"]["key"], "unknown")
        self.assertEqual(p["sessions"], [])
        self.assertFalse(list(self.root.iterdir()))

    def test_start_finish_feedback_preserves_measurements_and_snapshot(self):
        self.body(low=True)
        original = (self.cfg.data_dir / "body_daily.csv").read_bytes()
        session = self.write("start", activity="sit")["id"]
        self.assertEqual(self.page()["active"]["context"]["key"], "trend")
        with self.assertRaises(ValueError):
            self.write("feedback", ref=session, change="better")
        with self.assertRaises(ValueError):
            self.write("start", activity="walk")
        self.write("finish", ref=session, when=NOW + timedelta(minutes=15))
        self.assertIsNone(self.page(NOW + timedelta(minutes=15))["sessions"][0]["feedback"])
        self.write("feedback", ref=session, change="better", enjoyment="yes", when=NOW + timedelta(minutes=16))
        p = self.page(NOW + timedelta(minutes=16))
        self.assertEqual(p["sessions"][0]["feedback"]["change"], "better")
        self.assertEqual(p["sessions"][0]["context"]["key"], "trend")
        self.assertEqual(p["situation"]["key"], "trend")
        self.assertEqual((self.cfg.data_dir / "body_daily.csv").read_bytes(), original)
        self.assertFalse((self.cfg.data_dir / "self_report.csv").exists())

    def test_retries_are_idempotent_even_concurrently(self):
        request = {"op": "start", "activity": "music", "request_id": "stable-request-001"}
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda _: restore_log.from_browser(self.cfg, request, NOW), range(4)))
        self.assertEqual(len({r["id"] for r in results}), 1)
        self.assertEqual(len(restore_log.read(self.cfg)), 1)
        with self.assertRaises(ValueError):
            restore_log.from_browser(self.cfg, {**request, "activity": "walk"}, NOW)

    def test_cancel_is_not_completion_and_unknown_feedback_is_not_failure(self):
        sid = self.write("start", activity="play")["id"]
        self.write("cancel", ref=sid)
        self.assertEqual(self.page()["sessions"][0]["status"], "cancelled")
        with self.assertRaises(ValueError):
            self.write("feedback", ref=sid, change="better")
        sid = self.write("start", activity="sit")["id"]
        self.write("finish", ref=sid)
        self.assertIsNone(self.page()["sessions"][0]["feedback"])

    def test_feedback_can_be_corrected_without_erasing_history(self):
        sid = self.write("start", activity="walk")["id"]
        self.write("finish", ref=sid)
        self.write("feedback", ref=sid, change="better")
        self.write("feedback", ref=sid, change="worse", enjoyment="no")
        self.assertEqual(self.page()["situation"]["key"], "gentler")
        self.assertEqual(len([e for e in restore_log.read(self.cfg) if e["op"] == "feedback"]), 2)

    def test_signals_staleness_and_subjective_distress_are_separate(self):
        self.body(low=True, stale=2)
        self.assertEqual(self.page()["situation"]["key"], "unknown")
        self.assertEqual(self.page()["situation"]["recovery"]["verdict"], "low")
        self.write("checkin", mind="tense")
        self.assertEqual(self.page()["situation"]["key"], "reported")
        self.assertIsNone(self.page(NOW + timedelta(hours=4))["situation"]["checkin"])
        self.assertIsNotNone(self.page(NOW + timedelta(hours=4))["situation"]["last_checkin"])
        self.assertEqual(self.page(NOW + timedelta(hours=4))["situation"]["key"], "unknown")

    def test_quiet_and_focus_do_not_assign_work(self):
        self.write("checkin", mind="engaged")
        self.assertEqual(self.page()["situation"]["key"], "engaged")
        self.write("quiet")
        self.assertEqual(self.page()["situation"]["key"], "quiet")
        self.assertEqual(self.page(NOW + timedelta(hours=2))["situation"]["key"], "engaged")
        self.write("resume")
        self.assertIsNone(self.page()["situation"]["quiet_until"])
        self.write("checkin", mind="bored")
        self.assertNotEqual(self.page()["situation"]["key"], "challenge")
        self.write("checkin", body="comfortable", mind="bored")
        self.assertEqual(self.page()["situation"]["key"], "challenge")
        self.write("checkin", body="tired", task="hard")
        self.assertEqual(self.page()["situation"]["key"], "reported")

    def test_rewards_are_plans_until_reported_done_and_never_gate_rest(self):
        rid = self.write("reward_plan", title="Take photographs", note="Finished a difficult week")["id"]
        self.assertEqual(self.page()["rewards"][0]["status"], "planned")
        self.write("start", activity="sit")
        self.write("reward_done", ref=rid)
        self.assertEqual(self.page()["rewards"][0]["status"], "done")
        with self.assertRaises(ValueError):
            self.write("reward_done", ref=rid)

    def test_schedule_overlap_is_not_double_counted_and_meals_are_partial(self):
        write_table(self.cfg.data_dir, "events", [
            {"start": NOW + timedelta(hours=1), "end": NOW + timedelta(hours=3), "kind": "class", "title": "Class"},
            {"start": NOW + timedelta(hours=2), "end": NOW + timedelta(hours=4), "kind": "work", "title": "Work"}])
        write_table(self.cfg.data_dir, "meals", [
            {"time": NOW - timedelta(hours=1), "meal": "breakfast", "title": "Food", "carbs_g": 25},
            {"time": NOW + timedelta(hours=1), "meal": "lunch", "title": "Future food", "carbs_g": 60}])
        s = self.page()["situation"]
        self.assertEqual(s["schedule"]["hours"], 3)
        self.assertIsNone(s["schedule"]["deadlines"])
        self.assertEqual(s["food"]["logged_carbs_g"], 25)
        self.assertEqual(s["food"]["carb_entries"], 1)
        self.assertEqual(s["key"], "unknown")

    def test_corrupt_log_blocks_writes_without_destroying_evidence(self):
        file = restore_log.path(self.cfg)
        file.write_text('{"broken":', encoding="utf-8")
        before = file.read_bytes()
        with self.assertRaises(ValueError):
            self.write("quiet")
        self.assertEqual(file.read_bytes(), before)

    def test_bad_fields_and_timestamps_do_not_enter_log(self):
        for kwargs in ({"op": "checkin", "mind": "depression"}, {"op": "start", "activity": "invalid"},
                       {"op": "reward_plan", "title": " "}, {"op": "quiet", "at": "1999-01-01"},
                       {"op": "checkin"}):
            with self.assertRaises(ValueError):
                self.write(**kwargs)
        self.assertEqual(restore_log.read(self.cfg), [])
        self.write("quiet")
        with self.assertRaises(ValueError):
            self.write("resume", when=NOW - timedelta(minutes=1))

    def test_same_data_on_existing_pages(self):
        self.body()
        sid = self.write("start", activity="sit")["id"]
        for page in ("today", "recovery", "followup"):
            self.assertEqual(payload(self.cfg, page, now=NOW)["restore"]["active"]["id"], sid)
        self.assertIsNone(payload(self.cfg, "today", "2026-10-17", NOW)["restore"])


class BrowserBoundary(unittest.TestCase):
    setUp = Rest.setUp
    tearDown = Rest.tearDown

    def test_restore_api_requires_own_origin_and_valid_small_json(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(self.cfg, now=lambda: NOW))
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        origin = f"http://127.0.0.1:{server.server_port}"
        body = json.dumps({"op": "start", "activity": "sit", "request_id": "http-request-001"}).encode()
        try:
            for sent_origin in (None, "https://example.test"):
                headers = {"Content-Type": "application/json"}
                if sent_origin:
                    headers["Origin"] = sent_origin
                with self.assertRaises(urllib.error.HTTPError) as error:
                    urllib.request.urlopen(urllib.request.Request(origin + "/api/restore", body, headers))
                self.assertEqual(error.exception.code, 403)
            headers = {"Content-Type": "application/json", "Origin": origin}
            with urllib.request.urlopen(urllib.request.Request(origin + "/api/restore", body, headers)) as response:
                self.assertTrue(json.load(response)["ok"])
            self.assertEqual(len(restore_log.read(self.cfg)), 1)
            with urllib.request.urlopen(origin + "/api/restore") as response:
                self.assertEqual(json.load(response)["active"]["activity"], "sit")
        finally:
            server.shutdown(); server.server_close(); thread.join()


if __name__ == "__main__":
    unittest.main()
