"""The Drain page: seven signals against your normal and your plan, never a total score."""
import json
import math
import shutil
import subprocess
import tempfile
import unittest
from datetime import date, datetime, time, timedelta
from pathlib import Path

from healthaio import config, demo, server
from healthaio.context import Context
from healthaio.modules import drain, static_params
from healthaio.server import payload
from healthaio.store import write_table

TODAY = date(2026, 10, 12)
NOW = datetime(2026, 10, 12, 18, 40)


def synthetic(folder: Path, rhr_jump: float = 0.0, screen_days: int = 40, bedtime: str = "23:30") -> config.Config:
    """40 ordinary days: asleep 00:30, up 08:00, RHR 60; the last 7 days can carry a jump in resting HR."""
    body, sessions = [], []
    for k in range(40):
        d = TODAY - timedelta(days=40 - k)
        start = datetime.combine(d - timedelta(days=1), time(0, 30)) + timedelta(days=1) + timedelta(minutes=(k % 5) * 6)
        body.append({"date": d, "sleep_start": start, "sleep_end": start + timedelta(hours=7.5), "sleep_min": 450,
                     "hrv_ms": 45 + (k % 3), "resting_hr": 60 + (k % 3) * 0.5 + (rhr_jump if k >= 33 else 0), "complete": True})
        if k >= 40 - screen_days:
            sessions.append({"start": datetime.combine(d, time(20, 0)), "end": datetime.combine(d, time(22, 0)),
                             "device": "phone", "app": "Video", "category": "entertainment"})
            sessions.append({"start": datetime.combine(d, time(10, 0)), "end": datetime.combine(d, time(12, 0)),
                             "device": "laptop", "app": "Editor", "category": "work"})
    write_table(folder, "body_daily", body)
    write_table(folder, "screen_sessions", sessions)
    cfg = config.Config(root=folder, data_dir=folder)
    cfg.sleep.bedtime = time(*map(int, bedtime.split(":")))
    cfg.screen.entertainment_max_hours = 1.5
    return cfg


def bedtime_screens(folder: Path, missing=(), last_import=None, copies=("phone",)) -> config.Config:
    """40 nights asleep at 23:30 with 45 minutes of video right before bed and a work block in the morning.
    ``missing``: days Screen Time has no record for. ``last_import``: the import ran then and nothing came later.
    ``copies``: the device names each session is stored under (two = the same stream imported twice)."""
    body, sessions = [], []
    for k in range(1, 41):
        d = TODAY - timedelta(days=k)
        start = datetime.combine(d - timedelta(days=1), time(23, 30))
        body.append({"date": d, "sleep_start": start, "sleep_end": start + timedelta(hours=8), "sleep_min": 480,
                     "hrv_ms": 50, "resting_hr": 60, "complete": True})
        if d in missing or (last_import and d > last_import.date()):
            continue
        for device in copies:
            for a, b, app, cat in ((time(10, 0), time(12, 0), "Editor", "work"), (time(12, 0), time(12, 30), "Chat", "social"),
                                   (time(20, 0), time(22, 0), "Video", "entertainment"),
                                   (time(22, 45), time(23, 30), "Video", "entertainment")):
                s, e = datetime.combine(d, a), datetime.combine(d, b)
                if last_import and d == last_import.date():
                    if s >= last_import:
                        continue
                    e = min(e, last_import)
                sessions.append({"start": s, "end": e, "device": device, "app": app, "category": cat})
    write_table(folder, "body_daily", body)
    write_table(folder, "screen_sessions", sessions)
    cfg = config.Config(root=folder, data_dir=folder)
    cfg.screen.entertainment_max_hours = 3.0  # 3 h 15 of entertainment & social a day: over it
    return cfg


def row(page, key):
    return next(r for r in page["rows"] if r["key"] == key)


class DrainPage(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="healthaio-drain-"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_demo_builds_seven_signals_without_a_score(self):
        cfg = config.load(demo.generate(self.tmp / "demo", TODAY, NOW))
        page = payload(cfg, "drain", None, NOW)
        self.assertEqual([r["key"] for r in page["rows"]],
                         ["resting_hr", "hrv", "asleep", "spread", "before_sleep", "fun", "switches"])
        self.assertNotIn("score", json.dumps(page))
        for row in page["rows"]:
            if row["value"] is not None:
                self.assertTrue(math.isfinite(row["value"]))
        self.assertEqual(page["window"]["to"], (TODAY - timedelta(days=1)).isoformat())  # today is not over

    def test_resting_hr_jump_reads_as_worse(self):
        cfg = synthetic(self.tmp, rhr_jump=6)
        page = drain.build(Context(cfg, now=NOW))
        rhr = next(r for r in page["rows"] if r["key"] == "resting_hr")
        self.assertEqual((rhr["state"], rhr["tone"]), ("high", "bad"))
        self.assertIn("resting_hr", page["worse"])

    def test_usual_days_are_within_normal(self):
        page = drain.build(Context(synthetic(self.tmp), now=NOW))
        self.assertEqual(page["worse"], [])

    def test_plan_is_judged_separately_from_normal(self):
        page = drain.build(Context(synthetic(self.tmp), now=NOW))
        asleep = next(r for r in page["rows"] if r["key"] == "asleep")
        fun = next(r for r in page["rows"] if r["key"] == "fun")
        self.assertEqual(asleep["tone"], "neutral")     # as usual ...
        self.assertEqual(asleep["plan_tone"], "bad")    # ... but later than the 23:30 plan
        self.assertGreater(asleep["plan_over"], 55)
        self.assertEqual(fun["plan_tone"], "bad")       # 2 h a day against a 1.5 h limit
        self.assertAlmostEqual(fun["plan_over"], 30, delta=1)

    def test_missing_screen_days_are_not_zero(self):
        page = drain.build(Context(synthetic(self.tmp, screen_days=3), now=NOW))
        fun = next(r for r in page["rows"] if r["key"] == "fun")
        self.assertIsNone(fun["value"])                 # 3 of the last 7 days recorded: too few, not "0 minutes"
        self.assertNotIn("fun", page["worse"])

    def test_today_carries_the_same_summary(self):
        cfg = synthetic(self.tmp, rhr_jump=6)
        today = payload(cfg, "today", None, NOW)
        page = drain.build(Context(cfg, now=NOW))
        self.assertEqual(today["drain"]["worse"], page["worse"])
        self.assertEqual([r["key"] for r in today["drain"]["plan_off"]], page["plan_off"])

    def test_a_missing_screen_day_leaves_that_night_unknown_not_zero(self):
        gaps = {date(2026, 10, 5), date(2026, 10, 7), date(2026, 10, 9)}
        ctx = Context(bedtime_screens(self.tmp, missing=gaps), now=NOW)
        before = drain.daily_series(ctx, TODAY - timedelta(days=1))["before_sleep"]
        for d in gaps:  # the hour before falling asleep on d sits on d: unknown, not 0 minutes
            self.assertNotIn(d + timedelta(days=1), before)
        self.assertEqual(before[date(2026, 10, 11)], 45.0)
        page = drain.build(ctx)
        self.assertEqual(row(page, "before_sleep")["value"], 45.0)
        self.assertEqual(row(page, "before_sleep")["tone"], "neutral")  # not "better than normal"

    def test_an_hour_across_midnight_needs_both_days(self):
        folder = self.tmp / "late"
        cfg = bedtime_screens(folder, missing={date(2026, 10, 8)})
        body = [dict(r) for r in Context(cfg, now=NOW).store.rows("body_daily")]
        for r in body:  # asleep at 00:15 instead: the hour before runs 23:15-00:15, over two days
            r["sleep_start"] += timedelta(minutes=45)
        write_table(folder, "body_daily", body)
        before = drain.daily_series(Context(cfg, now=NOW), TODAY - timedelta(days=1))["before_sleep"]
        self.assertNotIn(date(2026, 10, 8), before)   # 23:15-00:00 on 10-07 is known, 00:00-00:15 on 10-08 is not
        self.assertNotIn(date(2026, 10, 9), before)   # 23:15-00:00 on 10-08 is not known
        self.assertEqual(before[date(2026, 10, 10)], 15.0)  # 23:15-23:30 of video, nothing after midnight

    def test_the_cut_off_last_import_day_is_not_a_whole_day(self):
        cut = datetime(2026, 10, 9, 14, 0)  # imported at 14:00, nothing since: the evening is not in
        ctx = Context(bedtime_screens(self.tmp, last_import=cut), now=NOW)
        self.assertEqual(ctx.screen_partial_day(), date(2026, 10, 9))
        self.assertFalse(ctx.time_days()[date(2026, 10, 9)].known["screen"])  # the Time page's rule, shared
        series = drain.daily_series(ctx, TODAY - timedelta(days=1))
        self.assertNotIn(date(2026, 10, 9), series["fun"])
        self.assertNotIn(date(2026, 10, 9), series["switches"])
        self.assertNotIn(date(2026, 10, 10), series["before_sleep"])  # that evening's hour is on the cut-off day
        fun = row(drain.build(ctx), "fun")
        self.assertEqual(fun["value"], 195.0)  # 3 h 15 every whole day, not dragged down by a half day
        self.assertEqual((fun["tone"], fun["plan_tone"]), ("neutral", "bad"))  # still over the 3 h limit

    def test_a_session_imported_under_two_device_names_is_one_switch(self):
        once = drain.daily_series(Context(bedtime_screens(self.tmp / "a"), now=NOW), TODAY - timedelta(days=1))["switches"]
        twice = drain.daily_series(Context(bedtime_screens(self.tmp / "b", copies=("laptop", "mac")), now=NOW),
                                   TODAY - timedelta(days=1))["switches"]
        self.assertEqual(once, twice)
        self.assertAlmostEqual(once[date(2026, 10, 11)], 4 / (315 / 60))

    def test_a_zero_hour_limit_is_a_plan(self):
        cfg = bedtime_screens(self.tmp)
        cfg.screen.entertainment_max_hours = 0.0
        page = drain.build(Context(cfg, now=NOW))
        self.assertEqual(row(page, "fun")["plan"]["limit"], 0.0)
        self.assertIn("fun", page["plan_off"])

    def test_an_empty_week_compares_nothing(self):
        cfg = config.load(demo.generate(self.tmp / "demo", TODAY, NOW))
        page = payload(cfg, "drain", "2025-01-01", NOW)
        self.assertEqual(page["compared"], 0)
        self.assertEqual(page["worse"], [])
        self.assertTrue(all(r["value"] is None for r in page["rows"]))
        self.assertTrue(all("plan_over" not in r for r in page["rows"]))   # a plan that could not be checked
        today = payload(cfg, "today", "2025-01-01", NOW)
        self.assertEqual((today["drain"]["compared"], today["drain"]["signals"]), (0, 7))
        self.assertEqual(payload(cfg, "drain", None, NOW)["compared"], 7)

    def test_later_from_an_off_grid_window_ends_on_the_latest(self):
        cfg = config.load(demo.generate(self.tmp / "demo", TODAY, NOW))
        page = payload(cfg, "drain", "2026-10-09", NOW)
        self.assertEqual((page["prev"], page["next"], page["latest"]), ("2026-10-02", "2026-10-11", "2026-10-11"))
        self.assertEqual(payload(cfg, "drain", "2026-10-04", NOW)["next"], "2026-10-11")
        self.assertIsNone(payload(cfg, "drain", None, NOW)["next"])

    def test_static_site_has_every_window_its_links_open(self):
        cfg = config.load(demo.generate(self.tmp / "demo", TODAY, NOW))
        ctx = Context(cfg, now=NOW)
        built = set(static_params("drain", ctx))
        dates = sorted(p for p in built if p)
        for param in built:
            page = payload(cfg, "drain", param, NOW)
            if page["next"]:
                self.assertTrue(page["next"] == page["latest"] or page["next"] in built, (param, page["next"]))
            if param and param > dates[0] and page["prev"] >= dates[0]:
                self.assertIn(page["prev"], built)
        for param in static_params("today", ctx):  # each pre-rendered Today's drain card links to its own window
            if param:
                window_to = payload(cfg, "today", param, NOW)["drain"]["window"]["to"]
                self.assertIn(window_to, built)


WEB = Path(__file__).resolve().parents[1] / "healthaio" / "web"
RENDER = """
import { readFileSync } from "node:fs";
globalThis.document = { documentElement: { dataset: {} } };
const [web, lang, page, file] = process.argv.slice(1);
const i18n = await import(`${web}/js/i18n.js`);
i18n.setLang(lang);
const mod = (await import(`${web}/js/pages/${page}.js`)).default;
process.stdout.write(JSON.stringify({ html: mod.render(JSON.parse(readFileSync(file, "utf8"))) }));
"""


@unittest.skipUnless(shutil.which("node"), "needs node to render the page's words")
class DrainWords(unittest.TestCase):
    """What the pages say, rendered by the real page code from the real payload."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="healthaio-drain-words-"))
        cls.cfg = config.load(demo.generate(cls.tmp / "demo", TODAY, NOW))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def render(self, lang, page, param):
        file = self.tmp / f"{page}-{param}.json"
        file.write_text(json.dumps(payload(self.cfg, page, param, NOW), default=str), encoding="utf-8")
        out = subprocess.run(["node", "--input-type=module", "-e", RENDER, "--", str(WEB), lang, page, str(file)],
                             capture_output=True, text=True, timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr)
        return json.loads(out.stdout)["html"]

    def test_an_empty_week_does_not_say_nothing_got_worse(self):
        for lang, unknown, none, plan_none in (
                ("en", "Too few records to set these 7 days against your normal", "nothing got worse",
                 "Everything with a plan is within it"),
                ("zh", "记录不够，这 7 天没法跟平常比", "没有哪项变差", "定了计划的几项都在计划内")):
            html = self.render(lang, "drain", "2025-01-01")
            self.assertIn(unknown, html)
            self.assertNotIn(none, html)
            self.assertNotIn(plan_none, html)
            self.assertIn("Too few records to check against the plan" if lang == "en" else "记录不够，没法跟计划比", html)
            asleep = html.split('class="drain-value"')[3]  # the falling-asleep row: no value, a plan
            caption = asleep.split('<span class="xs muted">')[1].split("</span>")[0]
            self.assertFalse(caption.startswith(" · "), caption)
            today = self.render(lang, "today", "2025-01-01")
            self.assertIn(unknown, today)

    def test_todays_card_opens_the_window_it_shows(self):
        html = self.render("en", "today", "2026-10-05")
        self.assertIn('href="#recovery/2026-10-04/drain"', html)  # Wear and tear is the end of Recovery now
        self.assertIn('href="#recovery/drain"', self.render("en", "today", None))
        self.assertIn('href="#today">Next day', self.render("en", "today", "2026-10-11").replace(" ›", ""))

    def test_english_lists_read_as_sentences(self):
        html = self.render("en", "today", "2026-10-07")  # the 7 days to 6 Oct, with two signals worse than normal
        self.assertIn("Worse than your normal: resting heart rate, app switching", html)
        # Today keeps one line per part; the plan comparison is on the Drain page for the same 7 days
        self.assertIn("Against your plan: falling asleep later than planned by", self.render("en", "drain", "2026-10-06"))
        self.assertIn("跟计划比：入睡时刻比计划晚", self.render("zh", "drain", None))
        self.assertIn("，娱乐和社交比上限多", self.render("zh", "drain", None))  # clauses take a comma, not 、


class Menu(unittest.TestCase):
    def test_menu_follows_the_health_loop(self):
        # one axis: today, what the body shows (recovery with wear and tear at its end, sleep, weight & fitness), what you
        # do every day (exercise, food, stimulation, rest), and what you planned and whether it happened and helped
        # (schedule & load, goals, follow-up with "tomorrow will be better"); where the numbers come from sits under the menu
        app = (Path(__file__).resolve().parents[1] / "healthaio" / "web" / "js" / "app.js").read_text(encoding="utf-8")
        self.assertIn('const NAV = ["today", "body", "life", "plans"];', app)  # Weekly review went into Follow-up, Data under the menu,
        # Schedule and Actions & goals are one item (a plan, and whether it held)
        self.assertIn('review: "followup"', app)  # an old #review link opens Follow-up, where "tomorrow will be better" is
        self.assertIn('body: [["recovery", "nav.recovery"], ["sleep", "nav.sleep_tab"], ["body", "nav.weight_tab"]]', app)
        self.assertIn('life: [["exercise", "nav.exercise"], ["food", "nav.food"], ["time", "nav.time_tab"], ["restore", "nav.restore"]]', app)
        self.assertIn('plans: [["week", "nav.schedule_week"], ["goals", "nav.goals"], ["followup", "nav.followup"]]', app)
        # pages folded into another one keep their old links: Wear and tear into Recovery, Body & mind load into Schedule & load
        self.assertIn('drain: (d) => (d ? `recovery/${d}/drain` : "recovery/drain")', app)
        self.assertIn('load: (d) => (d ? `week/${d}` : "week")', app)
        i18n = (Path(__file__).resolve().parents[1] / "healthaio" / "web" / "js" / "i18n.js").read_text(encoding="utf-8")
        for key in ("nav.body", "nav.life", "nav.plans", "nav.short.plans", "nav.followup"):
            self.assertEqual(i18n.count(f'"{key}"'), 2, key)  # English and Chinese
        for old in ("nav.time", "nav.plan", "nav.short.time", "nav.short.plan", "nav.load", "nav.short.load", "nav.review", "nav.short.review",
                    "nav.sched", "nav.short.sched", "nav.act", "nav.short.act"):
            self.assertNotIn(f'"{old}"', i18n, old)


class Serve(unittest.TestCase):
    def test_backlog_holds_a_page_load(self):
        # the page fetches about a dozen scripts at once; the stdlib backlog of 5 reset some of them
        self.assertGreaterEqual(server.Server.request_queue_size, 64)


if __name__ == "__main__":
    unittest.main()
