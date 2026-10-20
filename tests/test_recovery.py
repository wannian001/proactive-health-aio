"""Recovery: workout effort from Apple Health, the training load built from it, soreness check-ins, and the page.

Rules under test (healthaio/importers/apple_health.py, healthaio/checkin.py, healthaio/modules/recovery.py,
healthaio/modules/actions.py):
- a workout's effort is your own rating when there is one, else the watch's estimate; an effort sample belongs to the
  workout it starts within two minutes of, or covers for at least half; a phone package carries it the same way
- load = effort x minutes per day; the last 7 days against the weekly average of the 28 before; minutes without an
  effort are left out and counted, and with under half of the minutes rated the load says it is unsure
- a check-in replaces that morning's rows only; nothing tapped writes "none"; a day without rows is unknown; the
  feeling (2, 5 or 8) goes into that morning's self_report row and leaves energy, focus and the note alone
- the morning after a training day scores four parts against your normal (5 = usual), averaged; it needs two parts,
  one from the body
- only this app's own page may save a check-in
- a region clearly or very sore this morning, with training planned, gives "spare the sore parts"
- after a strength or hard workout (effort 7+), every page asks what it trained, for 36 hours or until it is noted
  (an empty note counts: "not this time"); a note's words suggest regions; the check-ins of the two mornings after
  ask about the noted regions first; each training day shows what it trained and how sore that was the next morning
"""
import json
import re
import shutil
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta
from http.server import ThreadingHTTPServer
from pathlib import Path

from healthaio import capture, checkin, config, demo, schema
from healthaio.config import Config
from healthaio.context import Context
from healthaio.importers import apple_health
from healthaio.modules import actions, followup, recovery, today
from healthaio.server import make_handler, payload
from healthaio.store import Store, write_table

TZ = "Australia/Melbourne"
TODAY = date(2026, 10, 12)
NOW = datetime(2026, 10, 12, 18, 40)
HEAD = '<?xml version="1.0" encoding="UTF-8"?>\n<HealthData locale="en_AU">\n <ExportDate value="2026-10-12 14:30:00 +1100"/>\n'
WEB = Path(__file__).resolve().parents[1] / "healthaio" / "web"


def workout(kind, start, end, minutes):
    return (f' <Workout workoutActivityType="HKWorkoutActivityType{kind}" duration="{minutes}" durationUnit="min" '
            f'sourceName="Apple Watch" startDate="{start}" endDate="{end}"/>\n')


def effort(start, end, value, rated=True, source="Apple Watch"):
    kind = apple_health.EFFORT_RATED if rated else apple_health.EFFORT_ESTIMATED
    return (f' <Record type="{kind}" sourceName="{source}" unit="appleEffortScore" '
            f'startDate="{start}" endDate="{end}" value="{value}"/>\n')


class Folder(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="healthaio-recovery-"))
        self.cfg = Config(root=self.tmp, data_dir=self.tmp / "data", timezone=TZ)
        self.cfg.data_dir.mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def ctx(self):
        return Context(self.cfg, now=NOW)

    def workouts(self):
        loaded = Store(self.cfg.data_dir).load("workouts")
        self.assertEqual(loaded.problems, [])
        return loaded.rows


class Effort(Folder):
    def run_import(self, body):
        path = self.tmp / "export.xml"
        path.write_text(HEAD + body + "</HealthData>\n", encoding="utf-8")
        return apple_health.import_apple_health(path, self.cfg)

    def test_your_rating_wins_over_the_watch_estimate(self):
        a, b = "2026-10-10 17:00:00 +1100", "2026-10-10 17:50:00 +1100"
        self.run_import(workout("TraditionalStrengthTraining", a, b, 50) + effort(a, b, 5, rated=False) + effort(a, b, 7))
        (row,) = self.workouts()
        self.assertEqual((row["effort"], row["effort_source"]), (7, "rated"))

    def test_the_estimate_fills_in_and_a_far_sample_does_not_match(self):
        a, b = "2026-10-10 07:00:00 +1100", "2026-10-10 07:30:00 +1100"
        c, d = "2026-10-11 07:00:00 +1100", "2026-10-11 07:30:00 +1100"
        self.run_import(workout("Running", a, b, 30) + effort(a, b, 4, rated=False)
                        + workout("Running", c, d, 30) + effort("2026-10-11 09:00:00 +1100", "2026-10-11 09:10:00 +1100", 9))
        first, second = sorted(self.workouts(), key=lambda r: r["start"])
        self.assertEqual((first["effort"], first["effort_source"]), (4, "estimated"))
        self.assertIsNone(second["effort"])  # an hour and a half later: another workout's, or nobody's

    def test_a_package_from_the_phone_carries_effort_too(self):
        data = json.loads((Path(__file__).parent / "fixtures" / "capture" / "health_3days.json").read_text())
        run = data["workouts"][0]
        data["package_id"] = "ios-effort-1"
        data["records"].append({"type": apple_health.EFFORT_RATED, "sourceName": "Apple Watch", "device": "Watch",
                                "unit": "appleEffortScore", "startDate": run["startDate"], "endDate": run["endDate"], "value": "6"})
        status, receipt = capture.receive(self.cfg, json.dumps(data).encode(), {"id": "d_1"})
        self.assertEqual((status, receipt["status"]), (200, "projected"))
        self.assertTrue(any(r["effort"] == 6 and r["effort_source"] == "rated" for r in self.workouts()))


class Load(Folder):
    def rows(self, days, effort_of=lambda k: 6, minutes=50):
        out = []
        for k in range(days):
            d = TODAY - timedelta(days=k)
            if k % 2 == 0:
                start = datetime.combine(d, datetime.min.time()).replace(hour=17)
                e = effort_of(k)
                out.append({"start": start, "end": start + timedelta(minutes=minutes), "type": "running",
                            "effort": e, "effort_source": "rated" if e else None})
        return out

    def test_the_week_against_the_four_before(self):
        rows = self.rows(40, effort_of=lambda k: 9 if k < 7 else 5)
        write_table(self.cfg.data_dir, "workouts", rows)
        L = recovery.load_summary(recovery.daily_load(self.ctx(), TODAY), TODAY)
        self.assertEqual(L["acute"], 4 * 9 * 50)  # days 0, 2, 4, 6
        self.assertAlmostEqual(L["chronic"], 14 * 5 * 50 / 4)  # days 8..34, every other day
        self.assertEqual(L["state"], "high")
        self.assertAlmostEqual(L["ratio"], 1800 / 875)

    def test_too_few_ratings_says_so(self):
        write_table(self.cfg.data_dir, "workouts", self.rows(40, effort_of=lambda k: 6 if k % 6 == 0 else None))
        L = recovery.load_summary(recovery.daily_load(self.ctx(), TODAY), TODAY)
        self.assertEqual(L["state"], "few_ratings")
        self.assertGreater(L["unrated_min"], 0)

    def test_without_a_workout_record_there_is_no_load(self):
        page = payload(self.cfg, "load", None, NOW)
        self.assertEqual(page["training"]["state"], "none")
        self.assertTrue(all(d["load"] is None for d in page["training_days"]))
        self.assertEqual(payload(self.cfg, "recovery", None, NOW)["load"]["state"], "none")


class Soreness(Folder):
    def rows(self):
        return [(r["date"].isoformat(), r["region"], r["level"]) for r in Store(self.cfg.data_dir).rows("soreness")]

    def test_a_check_in_replaces_that_morning_only(self):
        checkin.save(self.cfg, date(2026, 10, 11), {"chest": 2})
        checkin.save(self.cfg, date(2026, 10, 12), {"left_calf_back": 1, "left_glute": 3})
        checkin.save(self.cfg, date(2026, 10, 12), {"right_calf_back": 2})
        self.assertEqual(self.rows(), [("2026-10-11", "chest", 2), ("2026-10-12", "right_calf_back", 2)])

    def test_nothing_tapped_is_a_morning_with_nothing_sore(self):
        checkin.save(self.cfg, date(2026, 10, 12), {})
        self.assertEqual(self.rows(), [("2026-10-12", "none", 0)])
        log = recovery.soreness_log(self.ctx())
        self.assertEqual(log, {date(2026, 10, 12): {}})
        self.assertNotIn(date(2026, 10, 11), log)  # not checked: unknown

    def test_bad_check_ins_are_refused(self):
        for levels in ({"thigh": 1}, {"chest": 4}, {"chest": True}, ["chest"]):
            with self.assertRaises(checkin.CheckinError, msg=levels):
                checkin.check(levels)
        with self.assertRaises(checkin.CheckinError):
            checkin.from_browser(self.cfg, {"date": "2026-10-13", "levels": {}}, NOW)  # tomorrow
        self.assertEqual(checkin.check({"chest": 0, "neck_front": None, "left_calf_back": 2}), {"left_calf_back": 2})

    def test_a_hand_written_row_that_does_not_parse_survives(self):
        (self.cfg.data_dir / "soreness.csv").write_text("date,region,level\n2026-10-01,knee,2\n2026-10-12,chest,1\n")
        checkin.save(self.cfg, date(2026, 10, 12), {"neck_front": 1})
        text = (self.cfg.data_dir / "soreness.csv").read_text()
        self.assertIn("2026-10-01,knee,2", text)
        self.assertNotIn("chest", text)

    def test_spare_the_sore_parts_when_training_is_planned(self):
        self.cfg.training = {"mon": "Gym 50 min"}
        checkin.save(self.cfg, TODAY, {"left_calf_back": 2, "chest": 1})
        ctx = self.ctx()
        out = actions.build(ctx, TODAY, today.recovery(ctx, TODAY), {"worse": []})
        item = next(x for x in out["items"] if x["domain"] == "training")
        self.assertEqual((item["key"], item["params"]["regions"]), ("spare", ["left_calf_back"]))  # only clearly or very sore
        self.assertFalse(followup.check(ctx, item, TODAY, {})["checked"])  # training advice is not checked

    def test_no_advice_for_a_session_already_done(self):
        # sore this morning with 50 minutes planned: "spare" until the planned minutes are mostly done
        self.cfg.training = {"mon": "Gym 50 min"}
        checkin.save(self.cfg, TODAY, {"left_calf_back": 2})
        start = NOW - timedelta(hours=3)

        def training(minutes):
            write_table(self.cfg.data_dir, "workouts", [{"start": start, "end": start + timedelta(minutes=minutes), "type": "strength training"}])
            ctx = self.ctx()
            out = actions.build(ctx, TODAY, today.recovery(ctx, TODAY), {"worse": []})
            return [x["key"] for x in out["items"] if x["domain"] == "training"]

        self.assertEqual(training(20), ["spare"])  # 20 of 50 minutes: the session is not over
        self.assertNotIn("spare", training(45))    # 45 of 50: done, so the advice would come too late
        ctx = self.ctx()  # a past day is rebuilt as its morning saw it (the follow-up page)
        past = actions.build(ctx, TODAY - timedelta(days=7), today.recovery(ctx, TODAY - timedelta(days=7)), {"worse": []})
        self.assertIsNotNone(past)


class Feeling(Folder):
    def test_the_feeling_joins_that_mornings_row(self):
        write_table(self.cfg.data_dir, "self_report", [{"date": TODAY, "energy": 3, "note": "long day"}])
        checkin.save(self.cfg, TODAY, {"chest": 1}, feel=5)
        checkin.save(self.cfg, TODAY - timedelta(days=1), {}, feel=8)
        rows = {r["date"]: r for r in Store(self.cfg.data_dir).rows("self_report")}
        self.assertEqual((rows[TODAY]["feel"], rows[TODAY]["energy"], rows[TODAY]["note"]), (5, 3, "long day"))
        self.assertEqual(rows[TODAY - timedelta(days=1)]["feel"], 8)
        checkin.save(self.cfg, TODAY, {"chest": 2})  # no feeling given: the one saved stays
        self.assertEqual(Store(self.cfg.data_dir).by_date("self_report")[TODAY]["feel"], 5)


class AfterTraining(Folder):
    def history(self, after_hrv=50.0, after_rhr=60.0, after_sleep=450, feel=None):
        """30 steady mornings (HRV 50 +-1, resting heart rate 60 +-1, 7.5 h asleep of 8 in bed), a workout on the
        day before the last morning, and that morning as given."""
        body = []
        for k in range(30, 0, -1):
            d = TODAY - timedelta(days=k)
            body.append({"date": d, "hrv_ms": 50.0 + (k % 3) - 1, "resting_hr": 60.0 + (k % 2), "sleep_min": 450, "in_bed_min": 480,
                         "workout_min": 0, "complete": True})
        body.append({"date": TODAY, "hrv_ms": after_hrv, "resting_hr": after_rhr, "sleep_min": after_sleep, "in_bed_min": 480,
                     "workout_min": 0, "complete": False})
        write_table(self.cfg.data_dir, "body_daily", body)
        start = datetime.combine(TODAY - timedelta(days=1), datetime.min.time()).replace(hour=17)
        write_table(self.cfg.data_dir, "workouts", [{"start": start, "end": start + timedelta(minutes=60), "type": "running",
                                                    "effort": 7, "effort_source": "rated"}])
        if feel is not None:
            write_table(self.cfg.data_dir, "self_report", [{"date": TODAY, "feel": feel}])
        ctx = self.ctx()
        return recovery.after_training(ctx, TODAY, recovery.daily_load(ctx, TODAY))

    def test_a_usual_morning_scores_about_five(self):
        latest = self.history(after_hrv=49.0, feel=5)["latest"]
        self.assertEqual(latest["date"], (TODAY - timedelta(days=1)).isoformat())
        self.assertEqual(set(latest["parts"]), {"feel", "hrv", "resting_hr", "sleep"})
        self.assertAlmostEqual(latest["score"], 5, delta=1.0)
        self.assertEqual(latest["band"], "ok")

    def test_a_bad_morning_scores_low_and_says_so(self):
        latest = self.history(after_hrv=40.0, after_rhr=66.0, after_sleep=300, feel=2)["latest"]
        self.assertLess(latest["score"], recovery.LOW)
        self.assertEqual(latest["band"], "low")
        for key in ("hrv", "resting_hr", "sleep"):
            self.assertLess(latest["parts"][key]["score"], 5, key)
        self.assertEqual(latest["parts"]["feel"]["score"], 2)
        self.assertAlmostEqual(latest["score"], sum(p["score"] for p in latest["parts"].values()) / 4)

    def test_parts_stay_between_zero_and_ten(self):
        latest = self.history(after_hrv=90.0, after_rhr=40.0, after_sleep=700, feel=8)["latest"]
        self.assertTrue(all(0 <= p["score"] <= 10 for p in latest["parts"].values()))
        self.assertEqual(latest["band"], "good")

    def test_a_feeling_alone_is_not_a_score(self):
        write_table(self.cfg.data_dir, "self_report", [{"date": TODAY, "feel": 8}])
        start = datetime.combine(TODAY - timedelta(days=1), datetime.min.time()).replace(hour=17)
        write_table(self.cfg.data_dir, "workouts", [{"start": start, "end": start + timedelta(minutes=60), "type": "running", "effort": 7}])
        ctx = self.ctx()
        out = recovery.after_training(ctx, TODAY, recovery.daily_load(ctx, TODAY))
        (day,) = out["days"]
        self.assertIsNone(day["score"])
        self.assertIsNone(out["latest"])


class Trained(Folder):
    def strength(self, start, minutes=50, effort=7, kind="strength training"):
        return {"start": start, "end": start + timedelta(minutes=minutes), "type": kind, "effort": effort, "effort_source": "rated"}

    def asked_now(self):
        return recovery.prompt(self.ctx())["session"]

    def test_the_words_of_a_note_choose_regions(self):
        arms = ["left_upper_arm", "right_upper_arm"]
        self.assertEqual(checkin.regions_in("Bench, rows, curls"),
                         ["left_shoulder_front", "right_shoulder_front", "chest", "upper_back"] + arms)
        self.assertEqual(checkin.regions_in("深蹲、提踵"),
                         ["left_glute", "right_glute", "left_thigh_front", "right_thigh_front", "left_calf_back", "right_calf_back"])
        self.assertEqual(checkin.regions_in("小腿"), ["left_calf_back", "right_calf_back"])  # not also 腿, the whole legs
        self.assertEqual(checkin.regions_in("背和三头"), ["upper_back"] + arms)
        self.assertEqual(checkin.regions_in("rowing machine"), [])  # rowing is not row
        self.assertEqual(checkin.regions_in("bench卧推"), ["left_shoulder_front", "right_shoulder_front", "chest"] + arms)

    def test_a_hard_workout_is_asked_about_until_something_is_written(self):
        start = NOW - timedelta(hours=3)
        write_table(self.cfg.data_dir, "workouts", [self.strength(start)])
        self.assertEqual(self.asked_now()["start"], start.strftime("%Y-%m-%dT%H:%M"))
        checkin.save_trained(self.cfg, start, [], "")  # "not this time"
        self.assertIsNone(self.asked_now())
        checkin.save_trained(self.cfg, start, ["chest"], "bench")  # replaces the row, never adds one
        self.assertEqual(Store(self.cfg.data_dir).load("workout_notes").rows[0]["regions"], "chest")
        self.assertEqual(len(Store(self.cfg.data_dir).rows("workout_notes")), 1)

    def test_easy_old_or_unfinished_workouts_are_not_asked_about(self):
        write_table(self.cfg.data_dir, "workouts", [self.strength(NOW - timedelta(hours=2), effort=3, kind="walking")])
        self.assertIsNone(self.asked_now())
        write_table(self.cfg.data_dir, "workouts", [self.strength(NOW - timedelta(hours=40))])
        self.assertIsNone(self.asked_now())
        write_table(self.cfg.data_dir, "workouts", [self.strength(NOW - timedelta(minutes=20))])  # still going
        self.assertIsNone(self.asked_now())
        write_table(self.cfg.data_dir, "workouts", [self.strength(NOW - timedelta(hours=2), effort=8, kind="running")])
        self.assertIsNotNone(self.asked_now())  # a hard run counts, not only strength

    def test_what_was_trained_and_how_sore_it_was_said_to_be_the_next_morning(self):
        start = datetime.combine(TODAY - timedelta(days=1), datetime.min.time()).replace(hour=17)
        write_table(self.cfg.data_dir, "workouts", [self.strength(start)])
        checkin.save_trained(self.cfg, start, ["chest", "left_upper_arm", "right_upper_arm"], "bench, curls")
        checkin.report(self.cfg, NOW, {"chest": 2, "left_upper_arm": 0})
        page = recovery.build(self.ctx())
        self.assertNotIn("asked", page["soreness"])  # nobody is asked about every region trained
        chest = next(r for r in page["soreness"]["regions"] if r["key"] == "chest")
        self.assertEqual([d["trained"] for d in chest["days"][-2:]], [True, False])
        row = page["after"]["days"][0]
        # what was not said is unknown, not "not sore"
        self.assertEqual(row["sore_next"], {"chest": 2, "left_upper_arm": 0, "right_upper_arm": None})
        self.assertEqual(row["sessions"][0]["note"]["note"], "bench, curls")

    def test_bad_notes_are_refused(self):
        for regions, note in ((["knee"], ""), ("chest", ""), ([], "x" * 501), ([], 5)):
            with self.assertRaises(checkin.CheckinError):
                checkin.check_trained(regions, note)
        with self.assertRaises(checkin.CheckinError):
            checkin.parse_start((NOW + timedelta(hours=1)).isoformat(), NOW)


class Endpoint(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="healthaio-sore-"))
        try:
            self.cfg = config.load(demo.generate(self.tmp, TODAY, NOW))
        except config.ConfigError:
            raise unittest.SkipTest("needs Python 3.11+ or tomli")
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(self.cfg, lambda: NOW))
        self.port = self.httpd.server_address[1]
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def post(self, body, origin="same", path="checkin"):
        headers = {"Content-Type": "application/json"}
        if origin:
            headers["Origin"] = f"http://127.0.0.1:{self.port}" if origin == "same" else origin
        request = urllib.request.Request(f"http://127.0.0.1:{self.port}/api/{path}", data=json.dumps(body).encode(),
                                         headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=10) as res:
                return res.status, json.loads(res.read())
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read() or b"{}")

    def test_the_page_saves_and_recovery_shows_it(self):
        status, out = self.post({"date": TODAY.isoformat(), "levels": {"left_glute": 3}, "feel": 2})
        self.assertEqual((status, out["ok"]), (200, True))
        page = payload(self.cfg, "recovery", None, NOW)
        self.assertEqual((page["soreness"]["today"], page["soreness"]["levels"]), (True, {"left_glute": 3}))
        self.assertEqual(page["feel_today"], 2)
        self.assertEqual(self.post({"date": TODAY.isoformat(), "levels": {}, "feel": 4})[0], 400)

    def test_the_prompt_saves_what_a_workout_trained(self):
        asked = payload(self.cfg, "prompt", None, NOW)["session"]
        self.assertIsNotNone(asked)  # the demo's lunchtime run
        status, out = self.post({"start": asked["start"], "regions": ["left_calf_back", "right_calf_back"], "note": "intervals"}, path="trained")
        self.assertEqual((status, out["regions"]), (200, ["left_calf_back", "right_calf_back"]))
        self.assertIsNone(payload(self.cfg, "prompt", None, NOW)["session"])
        self.assertEqual(self.post({"start": asked["start"], "regions": ["knee"]}, path="trained")[0], 400)
        self.assertEqual(self.post({"start": asked["start"], "regions": []}, origin="http://evil.example", path="trained")[0], 403)

    def test_only_this_apps_own_page_may_write(self):
        before = (self.cfg.data_dir / "soreness.csv").read_text()
        for origin in ("http://evil.example", None):
            self.assertEqual(self.post({"date": TODAY.isoformat(), "levels": {"neck_front": 1}}, origin=origin)[0], 403)
        self.assertEqual(self.post({"date": TODAY.isoformat(), "levels": {"knee": 1}})[0], 400)
        self.assertEqual((self.cfg.data_dir / "soreness.csv").read_text(), before)


class Demo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="healthaio-recovery-demo-"))
        try:
            cls.cfg = config.load(demo.generate(cls.tmp, TODAY, NOW))
        except config.ConfigError:
            raise unittest.SkipTest("needs Python 3.11+ or tomli")
        cls.page = payload(cls.cfg, "recovery", None, NOW)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_the_page_agrees_with_today(self):
        p = self.page
        json.dumps(p)
        self.assertEqual(p["recovery"], payload(self.cfg, "today", None, NOW)["recovery"])
        self.assertEqual(len(p["response"]["rows"]), len(recovery.OUTCOMES))
        for row in p["response"]["rows"]:
            if row["status"] == "ok":
                self.assertEqual(row["detected"], row["p_adjusted"] < 0.05)

    def test_the_demo_rates_most_workouts_and_says_where_it_is_sore(self):
        rows = Store(self.cfg.data_dir).rows("workouts")
        rated = [r for r in rows if r["effort"] is not None]
        self.assertGreater(len(rated) / len(rows), 0.8)
        self.assertGreater(self.page["load"]["rated_share"], 0.8)
        S = self.page["soreness"]
        self.assertGreater(S["said_days"], 3)
        self.assertTrue(S["today"])  # Sam says his neck is stiff this morning
        self.assertTrue(S["follow_up"])  # and yesterday's places are asked about
        self.assertLessEqual({r["key"] for r in S["regions"]}, set(recovery.SORE_REGIONS))
        sore = Store(self.cfg.data_dir).load("soreness")
        self.assertEqual(sore.problems, [])
        self.assertTrue(all(r.get("at") for r in sore.rows))

    def test_the_demo_asks_about_todays_run_and_noted_most_sessions(self):
        prompt = payload(self.cfg, "prompt", None, NOW)
        self.assertEqual((prompt["session"]["type"], prompt["session"]["effort"]), ("running", 8.0))
        self.assertEqual(len(prompt["words"]), len(checkin.REGION_WORDS))
        notes = Store(self.cfg.data_dir).load("workout_notes")
        self.assertEqual(notes.problems, [])
        self.assertGreater(len(notes.rows), 20)
        for row in notes.rows:  # the demo's notes say what its regions are
            self.assertEqual(checkin.regions_in(row["note"]), row["regions"].split(), row["note"])

    def test_words_exist_in_both_languages(self):
        i18n = (WEB / "js" / "i18n.js").read_text(encoding="utf-8")
        page = (WEB / "js" / "pages" / "recovery.js").read_text(encoding="utf-8")
        used = set(re.findall(r't\("((?:rec|sore)\.[\w.]+)"', page))
        used |= {f"sore.region.{r}" for r in schema.ALL_SORE_REGIONS} | {f"sore.level.{k}" for k in range(4)}
        used |= {f"sore.area.{a}" for a, _, _ in schema.SORE_AREAS} | {"sore.area.leg"}
        used |= {f"sore.face.{f}" for f in ("front", "back", "outer", "inner", "all")} | {f"sore.side.{x}" for x in ("left", "right", "both")}
        used |= {f"sore.q.{q}" for q in ("leg", "side", "face", "level")}
        used |= {f"sore.one.{a}" for a, sides, _ in schema.SORE_AREAS if sides} | {f"sore.side_btn.{x}" for x in ("left", "right", "both")}
        used |= {f"rec.out.{o}" for o in recovery.OUTCOMES} | {f"rec.out.{o}.{d}" for o in recovery.OUTCOMES for d in ("up", "down")}
        used |= {f"rec.load.{s}" for s in ("high", "low", "steady", "none", "unknown", "few_ratings")}
        used |= {"nav.recovery", "todo.spare", "todo.short.spare", "fu.name.spare", "feel.2", "feel.5", "feel.8", "feel.question"}
        used |= {f"after.band.{b}" for b in ("good", "ok", "low")} | {f"after.part.{k}" for k in recovery.PARTS}
        for key in used:
            self.assertEqual(i18n.count(f'"{key}"'), 2, key)
        more = "".join((WEB / "js" / name).read_text(encoding="utf-8") for name in ("trained.js", "sore-say.js"))
        for key in set(re.findall(r't\("((?:trained|sore|say|fu|after)\.[\w.]+)"', page + more)):
            self.assertEqual(i18n.count(f'"{key}"'), 2, key)
        from healthaio.schema import TABLES
        for name in TABLES:  # the Data page says what each file holds in both languages, not the schema's English
            self.assertEqual(i18n.count(f'"data.table.{name}"'), 2, name)
        self.assertFalse((WEB / "js" / "figure.js").exists())  # the first 2D figure is gone; the 3D body is the only one
        self.assertFalse((WEB / "img").exists())

    def test_an_older_figure_setting_is_still_read(self):
        path = self.tmp / "healthaio.toml"
        text = path.read_text()
        path.write_text(text.replace("[healthaio]\n", '[healthaio]\nfigure = "female"\n', 1))
        try:
            config.load(path)  # the key is ignored, not an error
        finally:
            path.write_text(text)


if __name__ == "__main__":
    unittest.main()
