"""Sitting: stretches at the computer from Screen Time, right now from the Mac app, the reminder, and the short moves."""
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path

from healthaio import care_log, config, demo, restore_log, routines
from healthaio.config import Config
from healthaio.context import Context
from healthaio.modules import sitting
from healthaio.store import write_table

DAY = date(2026, 10, 14)
NOW = datetime(2026, 10, 14, 16, 0)


def session(start, minutes, device="laptop", app="Code"):
    s = datetime.combine(DAY, datetime.min.time()) + timedelta(minutes=start)
    return {"start": s, "end": s + timedelta(minutes=minutes), "device": device, "app": app, "category": "work"}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.cfg = Config(root=root, data_dir=root / "data", timezone="Australia/Melbourne")
        self.cfg.data_dir.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def ctx(self, now=NOW):
        return Context(self.cfg, now=now)


class Stretches(Base):
    def test_short_gaps_join_long_gaps_split_and_phones_do_not_count(self):
        write_table(self.cfg.data_dir, "screen_sessions", [
            session(9 * 60, 40), session(9 * 60 + 44, 30),       # 4 minutes apart: one stretch, 9:00–10:14
            session(10 * 60 + 20, 20),                            # 6 minutes after: a new one
            session(10 * 60 + 25, 10, device="phone", app="Instagram"),  # a phone is not the desk
        ])
        s = sitting.stretches(self.ctx(), DAY)
        self.assertEqual([x["minutes"] for x in s], [74, 20])
        summary = sitting.day_summary(self.ctx(), DAY)
        self.assertEqual((summary["longest"], summary["long"], summary["total"]), (74, 1, 94))

    def test_no_computer_time_is_no_summary_not_zero(self):
        self.assertIsNone(sitting.day_summary(self.ctx(), DAY))
        self.assertIsNone(sitting.light(self.ctx(), DAY)["longest"])


class Live(Base):
    def test_right_now_needs_a_recent_word_from_the_mac_app(self):
        self.assertIsNone(sitting.live(self.ctx()))
        sitting.note(self.cfg, NOW - timedelta(minutes=55), NOW - timedelta(minutes=1))
        self.assertEqual(sitting.live(self.ctx())["minutes"], 55)
        sitting.note(self.cfg, NOW - timedelta(minutes=55), NOW - timedelta(minutes=sitting.FRESH_MIN + 1))
        self.assertIsNone(sitting.live(self.ctx()))  # not heard from lately: not known, no reminder
        sitting.note(self.cfg, None)
        self.assertIsNone(sitting.live(self.ctx()))

    def test_times_with_a_zone_as_the_mac_app_sends_them(self):
        from zoneinfo import ZoneInfo
        mel = ZoneInfo("Australia/Melbourne")
        start = (NOW - timedelta(minutes=70)).replace(tzinfo=mel)
        sitting.note(self.cfg, start, NOW.replace(tzinfo=mel) - timedelta(minutes=1))
        self.assertEqual(sitting.live(self.ctx())["minutes"], 70)
        sitting.note(self.cfg, None, NOW.replace(tzinfo=mel), off_since=NOW.replace(tzinfo=mel))
        back = (NOW + timedelta(minutes=6)).replace(tzinfo=mel)
        sitting.note(self.cfg, back, back)
        self.assertEqual([s["after"] for s in restore_log.replay(restore_log.read(self.cfg))["sessions"]], [70])

    def test_the_reminder_comes_at_fifty_minutes_and_again_every_thirty(self):
        sitting.note(self.cfg, NOW - timedelta(minutes=49), NOW)
        self.assertIsNone(sitting.nudge(self.ctx())["kind"])
        sitting.note(self.cfg, NOW - timedelta(minutes=50), NOW)
        n = sitting.nudge(self.ctx())
        self.assertEqual((n["kind"], n["round"]), ("sitting", 1))
        self.assertEqual(n["routines"][-1], "walk_break")
        self.assertTrue(routines.BY_ID[n["routines"][0]].get("sitting"))
        self.assertEqual(set(n["info"]), set(n["routines"]))
        sitting.note(self.cfg, NOW - timedelta(minutes=81), NOW)
        self.assertEqual(sitting.nudge(self.ctx())["round"], 2)

    def test_quiet_hours_keep_it_quiet(self):
        sitting.note(self.cfg, NOW - timedelta(minutes=60), NOW)
        restore_log.from_browser(self.cfg, {"op": "quiet", "request_id": "quiet-000001"}, NOW - timedelta(minutes=5))
        n = sitting.nudge(self.ctx())
        self.assertEqual((n["kind"], n["why"]), (None, "quiet"))

    def test_where_it_was_tight_today_picks_the_desk_move(self):
        sitting.note(self.cfg, NOW - timedelta(minutes=55), NOW)
        care_log.from_browser(self.cfg, {"op": "report", "request_id": "report-00001", "tight": {"neck": "tight"}}, NOW - timedelta(hours=2))
        self.assertEqual(routines.BY_ID[sitting.nudge(self.ctx())["routines"][0]]["regions"][0], "neck")

    def test_the_mac_app_command(self):
        cfgfile = Path(self.tmp.name) / "healthaio.toml"
        cfgfile.write_text(f'[healthaio]\ndata_dir = "data"\ntimezone = "Australia/Melbourne"\n', encoding="utf-8")
        run = lambda *a: json.loads(subprocess.run([sys.executable, "-B", "-m", "healthaio", "--config", str(cfgfile), "sitting", *a],
                                                   capture_output=True, text=True, check=True).stdout)
        out = run("--since", "2026-10-14T15:05", "--now", "2026-10-14T16:00")
        self.assertEqual((out["kind"], out["minutes"]), ("sitting", 55))
        self.assertTrue((Path(self.tmp.name) / ".healthaio" / "sitting.json").exists())
        self.assertIsNone(run("--off", "--now", "2026-10-14T16:01")["kind"])
        kept = json.loads((Path(self.tmp.name) / ".healthaio" / "sitting.json").read_text())
        self.assertEqual((kept["off_since"][:16], kept["after"]), ("2026-10-14T16:01", 56))  # the break, for the rest written down later


class AutoBreak(Base):
    """Getting up after a long stretch is written down as a rest by itself, once, and can be taken back."""
    def sessions(self):
        return restore_log.replay(restore_log.read(self.cfg))["sessions"]

    def test_a_break_after_a_long_stretch_is_a_rest(self):
        start = NOW - timedelta(minutes=70)
        sitting.note(self.cfg, start, start)
        sitting.note(self.cfg, None, NOW, off_since=NOW)                          # up after 70 minutes
        sitting.note(self.cfg, NOW + timedelta(minutes=8), NOW + timedelta(minutes=8))  # back 8 minutes later
        s = self.sessions()
        self.assertEqual([(x["activity"], x["status"], x["auto"], x["after"]) for x in s], [("break", "finished", True, 70)])
        sitting.note(self.cfg, NOW + timedelta(minutes=8), NOW + timedelta(minutes=9))  # the same stretch again: once
        self.assertEqual(len(self.sessions()), 1)
        restore_log.from_browser(self.cfg, {"op": "remove", "request_id": "remove-00001", "ref": s[0]["id"]}, NOW + timedelta(minutes=20))
        self.assertEqual(self.sessions()[0]["status"], "removed")

    def test_a_short_stretch_or_a_short_break_is_not(self):
        sitting.note(self.cfg, NOW - timedelta(minutes=30), NOW - timedelta(minutes=30))
        sitting.note(self.cfg, None, NOW, off_since=NOW)
        sitting.note(self.cfg, NOW + timedelta(minutes=10), NOW + timedelta(minutes=10))
        sitting.note(self.cfg, None, NOW + timedelta(minutes=70), off_since=NOW + timedelta(minutes=70))
        sitting.note(self.cfg, NOW + timedelta(minutes=71), NOW + timedelta(minutes=71))  # one minute up: not a break
        self.assertEqual(self.sessions(), [])

    def test_the_page_cannot_write_one(self):
        with self.assertRaises(ValueError):
            restore_log.from_browser(self.cfg, {"op": "auto", "request_id": "auto-000001"}, NOW)


class Routines(unittest.TestCase):
    def test_every_routine_says_what_how_and_how_much_in_both_languages(self):
        ids = [r["id"] for r in routines.ROUTINES]
        self.assertEqual(len(ids), len(set(ids)))
        for r in routines.ROUTINES:
            self.assertTrue(set(r["regions"]) <= set(routines.REGIONS), r["id"])
            for lang in ("zh", "en"):
                self.assertTrue(all(r[lang].get(k) for k in ("name", "how", "dose")), (r["id"], lang))
        for region in routines.REGIONS:
            self.assertTrue(routines.for_regions([region]), region)  # every region on the check-in has a move
        self.assertTrue(routines.STOP["zh"] and routines.STOP["en"])

    def test_picks_are_specific_first_and_never_repeat(self):
        picks = routines.for_regions(["neck", "chest", "neck"], 3)
        self.assertEqual(len(picks), len(set(picks)))
        self.assertIn("chin_tuck", picks)
        self.assertEqual(routines.for_regions(["elbow"]), [])


class CareLog(Base):
    def test_done_needs_a_known_routine_and_a_retry_writes_once(self):
        req = {"op": "done", "request_id": "done-0000001", "routine": "chin_tuck", "why": "sitting"}
        first = care_log.from_browser(self.cfg, req, NOW)
        self.assertEqual(care_log.from_browser(self.cfg, req, NOW)["id"], first["id"])
        self.assertEqual(len(care_log.read(self.cfg)), 1)
        with self.assertRaises(ValueError):
            care_log.from_browser(self.cfg, {**req, "request_id": "done-0000002", "routine": "headstand"}, NOW)


class Demo(unittest.TestCase):
    def test_the_demo_opens_on_the_reminder(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = config.load(demo.generate(Path(tmp), date(2026, 10, 12)))
            ctx = Context(cfg, now=datetime(2026, 10, 12, 18, 40))
            self.assertEqual(sitting.nudge(ctx)["kind"], "sitting")
            card = sitting.build(ctx)
            self.assertIsNotNone(card["usual"])
            self.assertEqual(len(card["days"]), sitting.DAYS)


if __name__ == "__main__":
    unittest.main()
