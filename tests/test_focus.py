"""Focus budget and the sustainable rhythm: deep focus, the budget from days like today, days over, weeks, rewards."""
import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path

from healthaio import restore_log
from healthaio.config import Config
from healthaio.context import Context
from healthaio.modules import focus
from healthaio.store import write_table

TODAY = date(2026, 10, 14)  # a Wednesday


def work(day, start_h, minutes, device="laptop", category="work", app="Code"):
    s = datetime.combine(day, datetime.min.time()) + timedelta(hours=start_h)
    return {"start": s, "end": s + timedelta(minutes=minutes), "device": device, "app": app, "category": category}


class Deep(unittest.TestCase):
    def test_only_stretches_of_25_minutes_count_and_short_gaps_do_not_break_them(self):
        m = {i: "work" for i in range(60, 90)}                  # 30 minutes: counts
        m.update({i: "work" for i in range(200, 220)})          # 20 minutes: does not
        m.update({i: "learning" for i in range(300, 315)})      # 15 + a 2-minute gap + 15 = 32: counts
        m.update({i: "learning" for i in range(317, 332)})
        m.update({i: "work" for i in range(400, 415)})          # 15, then 5 minutes on the phone, then 15: two short ones
        m.update({i: "communication" for i in range(415, 420)})
        m.update({i: "work" for i in range(420, 435)})
        self.assertEqual(focus.deep_minutes(m), 30 + 32)


class Budget(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.cfg = Config(root=root, data_dir=root / "data", timezone="Australia/Melbourne")
        self.cfg.data_dir.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def ctx(self, now=None):
        return Context(self.cfg, now=now or datetime.combine(TODAY, datetime.min.time()).replace(hour=18))

    def history(self, days=60, deep=lambda d: 120 if d.toordinal() % 2 else 40, sleep=lambda d: 480 if d.toordinal() % 2 else 360,
                extra=lambda d: []):
        sessions, body = [], []
        for k in range(days, 0, -1):
            d = TODAY - timedelta(days=k)
            sessions.append(work(d, 9, deep(d)))
            sessions.extend(extra(d))
            body.append({"date": d, "sleep_min": sleep(d), "hrv_ms": 50})
        body.append({"date": TODAY, "sleep_min": 480, "hrv_ms": 50})
        write_table(self.cfg.data_dir, "screen_sessions", sessions)
        write_table(self.cfg.data_dir, "body_daily", body)

    def test_the_budget_is_what_you_managed_on_nights_like_last_night(self):
        self.history()  # eight-hour nights came with two hours of deep focus, six-hour nights with forty minutes
        b = focus.budget(self.ctx(), TODAY)
        self.assertEqual((b["middle"], b["days"], b["weekend"]), (120, focus.K, False))
        self.assertEqual(set(b["matched"]), {"sleep", "hrv"})

    def test_too_little_history_is_no_budget(self):
        self.history(days=5)
        self.assertIsNone(focus.budget(self.ctx(), TODAY))

    def test_weekdays_are_matched_with_weekdays(self):
        self.history(deep=lambda d: 30 if d.weekday() >= 5 else 150, sleep=lambda d: 420)
        self.assertEqual(focus.budget(self.ctx(), TODAY)["middle"], 150)
        self.assertEqual(focus.budget(self.ctx(), date(2026, 10, 11))["middle"], 30)  # a Sunday

    def test_today_says_when_work_was_always_broken_up(self):
        self.history()
        phone = [work(TODAY, 9, 20), work(TODAY, 9 + 20 / 60, 4, device="phone", category="social", app="Instagram"),
                 work(TODAY, 9 + 24 / 60, 20), work(TODAY, 9 + 44 / 60, 4, device="phone", category="social", app="Instagram")]
        rows = [r for r in self.cfg_rows("screen_sessions")] + phone
        write_table(self.cfg.data_dir, "screen_sessions", rows)
        now = focus.today(self.ctx())
        self.assertEqual((now["used"], now["focus_min"]), (0, 40))
        self.assertLess(now["longest"], focus.DEEP_MIN)

    def cfg_rows(self, name):
        return Context(self.cfg).store.rows(name)

    def test_days_over_in_a_row_bring_the_emptiest_half_day(self):
        # the last three days: four hours each, far above days like them
        self.history(deep=lambda d: 240 if (TODAY - d).days <= 3 else 60, sleep=lambda d: 420)
        write_table(self.cfg.data_dir, "events", [{"start": datetime.combine(TODAY + timedelta(days=1), datetime.min.time()).replace(hour=9),
                                                   "end": datetime.combine(TODAY + timedelta(days=1), datetime.min.time()).replace(hour=18),
                                                   "title": "Lab", "kind": "class"}])
        r = focus.rhythm(self.ctx())
        self.assertEqual(r["over_run"], 3)
        self.assertNotEqual(r["light"]["date"], (TODAY + timedelta(days=1)).isoformat())  # the full day is not the light one
        self.assertEqual(r["light"]["booked"], 0)

    def test_weeks_that_kept_the_rhythm_bring_one_celebration(self):
        self.history(days=focus.DAYS, deep=lambda d: 60, sleep=lambda d: 420)
        r = focus.rhythm(self.ctx())
        self.assertGreaterEqual(r["streak"], focus.SUSTAINED_WEEKS)
        self.assertTrue(r["reward_ready"])
        restore_log.from_browser(self.cfg, {"op": "reward_plan", "request_id": "rhythm-00001", "title": "3 sustainable weeks",
                                            "note": "", "for": "rhythm"}, datetime.combine(TODAY, datetime.min.time()).replace(hour=12))
        self.assertFalse(focus.rhythm(self.ctx())["reward_ready"])  # once per run

    def test_a_long_stretch_without_a_rest_is_not_a_sustainable_day(self):
        self.history(days=focus.DAYS, deep=lambda d: 120, sleep=lambda d: 420)  # 2 hours unbroken every day: over 90 minutes
        days = [x for x in focus.rhythm(self.ctx())["days"] if x["known"]]
        self.assertTrue(days and not any(x["breaks"] for x in days))
        self.assertFalse(any(x["sustainable"] for x in days))


if __name__ == "__main__":
    unittest.main()
