"""Soreness said when it is felt: one sentence read into places (sore_say.py), saved for the regions named only
(checkin.report), and asked about on the following days until it is fine (recovery.follow_up)."""
import json
import shutil
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta
from http.server import ThreadingHTTPServer
from pathlib import Path

from healthaio import checkin, config, demo, sore_say
from healthaio.config import Config
from healthaio.context import Context
from healthaio.modules import recovery
from healthaio.schema import LEGACY_REGIONS, SORE_REGIONS, sore_region
from healthaio.server import make_handler
from healthaio.store import Store, write_table

TODAY = date(2026, 10, 12)
NOW = datetime(2026, 10, 12, 18, 40)


def read(said):
    return [(i["area"], i["side"], i["face"], i["level"]) for i in sore_say.rules(said)["items"]]


class Regions(unittest.TestCase):
    def test_thirty_one_places_and_the_older_seven_kept_apart(self):
        self.assertEqual(len(SORE_REGIONS), 31)
        self.assertEqual(len(set(SORE_REGIONS)), 31)
        self.assertFalse(set(SORE_REGIONS) & set(LEGACY_REGIONS))  # the upper arms are in both lists of names only once
        self.assertEqual(sore_region("thigh", "left", "back"), "left_thigh_back")
        self.assertEqual(sore_region("neck", "right", "back"), "neck_back_right")
        self.assertEqual(sore_region("neck", None, "front"), "neck_front")
        self.assertEqual(sore_region("low_back"), "low_back")


class Rules(unittest.TestCase):
    def test_places_sides_faces_and_how_much(self):
        self.assertEqual(read("跑完步右边大腿后面有点酸，左肩前面也疼"),
                         [("thigh", "right", "back", 1), ("shoulder", "left", "front", 1)])
        self.assertEqual(read("左肩前面和后面都很疼"), [("shoulder", "left", "front", 3), ("shoulder", "left", "back", 3)])
        self.assertEqual(read("右大腿后侧和小腿有点酸"), [("thigh", "right", "back", 1), ("calf", "right", None, 1)])
        self.assertEqual(read("腰酸背痛"), [("low_back", None, None, None), ("upper_back", None, None, None)])
        self.assertEqual(read("my left hamstring and the back of my right calf are a bit sore"),
                         [("thigh", "left", "back", 1), ("calf", "right", "back", 1)])

    def test_the_neck_has_a_front_and_a_back_with_two_halves(self):
        self.assertEqual(read("脖子后面左边酸"), [("neck", "left", "back", None)])
        self.assertEqual(read("颈后不舒服"), [("neck", None, "back", None)])  # the page takes both halves
        self.assertEqual(read("喉咙前面有点疼"), [("neck", None, "front", 1)])

    def test_words_that_only_look_like_a_place(self):
        self.assertEqual(read("前天跑完后大腿酸"), [("thigh", None, None, None)])  # time, not the front or the back
        self.assertEqual(read("小腿肚子很紧，三天左右了"), [("calf", None, "back", 3)])  # 左右: about, not a side
        self.assertEqual(read("大腿背面酸"), [("thigh", None, "back", None)])  # 背面 is a face, not the upper back
        self.assertEqual(read("腿有点酸"), [("leg", None, None, 1)])  # thigh or calf: the page asks
        self.assertEqual(read("右肩好了"), [("shoulder", "right", None, 0)])

    def test_warning_signs_are_found(self):
        self.assertEqual(sore_say.rules("坐太久后颈好痛，手发麻")["signs"], ["numb"])

    def test_the_assistant_answers_only_with_ids_and_the_rules_stand_in(self):
        cfg = Config(root=Path("."), data_dir=Path("."))
        out = sore_say.parse(cfg, "left thigh", ask_model=lambda c, s: {
            "items": [{"area": "thigh", "side": "left", "face": "inner", "level": "very"},
                      {"area": "knee", "side": "left", "face": "front", "level": "very"}], "signs": ["numb", "x"]})
        self.assertEqual(out["items"], [{"area": "thigh", "side": "left", "face": "inner", "level": 3}])
        self.assertEqual((out["signs"], out["parsed_by"]), (["numb"], "assistant"))

        def broken(c, s):
            raise RuntimeError("declined")
        out = sore_say.parse(cfg, "左大腿内侧很酸", ask_model=broken)
        self.assertEqual((out["parsed_by"], out["assistant"]), ("rules", "declined"))
        self.assertEqual(out["items"][0]["face"], "inner")


class Report(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="healthaio-say-"))
        self.cfg = Config(root=self.tmp, data_dir=self.tmp / "data", timezone="Australia/Melbourne")
        self.cfg.data_dir.mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def rows(self):
        return [(r["date"].isoformat(), r["region"], r["level"]) for r in Store(self.cfg.data_dir).rows("soreness")]

    def test_only_the_regions_named_change(self):
        write_table(self.cfg.data_dir, "soreness", [{"date": TODAY, "region": "none", "level": 0},
                                                    {"date": TODAY - timedelta(days=1), "region": "torso", "level": 2}])
        checkin.report(self.cfg, NOW, {"chest": 2, "left_thigh_back": 1}, "chest and the back of my left thigh")
        checkin.report(self.cfg, NOW + timedelta(hours=1), {"chest": 0})  # fine again, later that day
        self.assertEqual(self.rows(), [("2026-10-11", "torso", 2), ("2026-10-12", "chest", 0), ("2026-10-12", "left_thigh_back", 1)])
        row = next(r for r in Store(self.cfg.data_dir).rows("soreness") if r["region"] == "left_thigh_back")
        self.assertEqual((row["at"], row["said"]), (datetime(2026, 10, 12, 18, 40), "chest and the back of my left thigh"))

    def test_bad_reports_are_refused(self):
        for levels in ({}, {"torso": 2}, {"knee": 1}, {"chest": 4}, {"chest": True}, ["chest"]):
            with self.assertRaises(checkin.CheckinError, msg=levels):
                checkin.report_from_browser(self.cfg, {"levels": levels}, NOW)
        with self.assertRaises(checkin.CheckinError):
            checkin.report_from_browser(self.cfg, {"levels": {"chest": 1}, "said": "x" * 281}, NOW)
        with self.assertRaises(checkin.CheckinError):
            checkin.report_from_browser(self.cfg, {"levels": {"chest": 1}, "date": "2026-10-01"}, NOW)

    def test_a_sore_place_is_asked_about_until_it_is_fine(self):
        ctx = lambda now: Context(self.cfg, now=now)
        checkin.report(self.cfg, NOW - timedelta(days=2), {"left_calf_back": 2, "chest": 1})
        ask = recovery.follow_up(ctx(NOW), TODAY)
        self.assertEqual([(f["region"], f["level"]) for f in ask], [("chest", 1), ("left_calf_back", 2)])
        checkin.report(self.cfg, NOW - timedelta(days=1), {"chest": 0, "left_calf_back": 1})
        self.assertEqual([(f["region"], f["level"], f["date"]) for f in recovery.follow_up(ctx(NOW), TODAY)],
                         [("left_calf_back", 1, "2026-10-11")])
        checkin.report(self.cfg, NOW, {"left_calf_back": 1})  # answered today: not asked again today
        self.assertEqual(recovery.follow_up(ctx(NOW), TODAY), [])
        later = TODAY + timedelta(days=recovery.FOLLOW_DAYS + 1)
        self.assertEqual(recovery.follow_up(ctx(datetime.combine(later, NOW.time())), later), [])  # too long ago

    def test_a_region_not_said_is_unknown_for_the_estimate(self):
        checkin.report(self.cfg, NOW - timedelta(days=1), {"chest": 2})
        checkin.report(self.cfg, NOW, {"left_calf_back": 1})
        page = recovery.build(Context(self.cfg, now=NOW))
        self.assertEqual(page["forecast"]["soreness"]["chest"]["status"], "missing_current")  # not said today
        self.assertEqual(page["soreness"]["levels"], {"left_calf_back": 1})


class Endpoints(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="healthaio-say-"))
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

    def post(self, path, body, origin="same"):
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

    def test_read_then_save(self):
        before = (self.cfg.data_dir / "soreness.csv").read_text()
        status, out = self.post("sore-parse", {"said": "右小腿外侧很酸"})
        self.assertEqual((status, out["parsed_by"]), (200, "rules"))
        self.assertEqual(out["items"], [{"area": "calf", "side": "right", "face": "outer", "level": 3}])
        self.assertEqual((self.cfg.data_dir / "soreness.csv").read_text(), before)  # reading writes nothing
        status, out = self.post("sore", {"levels": {"right_calf_outer": 3}, "said": "右小腿外侧很酸", "parsed_by": "rules"})
        self.assertEqual((status, out["levels"]), (200, {"right_calf_outer": 3}))
        self.assertEqual(self.post("sore", {"levels": {"right_calf_outer": 3}}, origin="http://evil.example")[0], 403)
        self.assertEqual(self.post("sore", {"levels": {"head": 1}})[0], 400)
        self.assertEqual(self.post("sore-parse", {"said": "x" * 281})[0], 400)


if __name__ == "__main__":
    unittest.main()
