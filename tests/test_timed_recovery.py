"""Current-time diary behavior and interval estimates; all records synthetic."""
import json
import threading
import tempfile
import unittest
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

from healthaio import recovery_log
from healthaio.config import Config
from healthaio.context import Context
from healthaio.modules import recovery
from healthaio.modules.timed_recovery import forecast
from healthaio.server import Server, make_handler

NOW = datetime(2026, 10, 18, 9, tzinfo=timezone.utc)


def sore_points():
    points = []
    for n in range(7):
        start = NOW - timedelta(days=40 - n * 5)
        points.extend({"at": start + timedelta(hours=h), "value": v} for h, v in ((0, 6), (6, 5), (12, 2), (18, 0)))
    return points + [{"at": NOW, "value": 6}]


def energy_points():
    points = []
    for n in range(60):
        start = NOW - timedelta(days=60 - n)
        low = n in (32, 36, 40, 44, 48, 52, 56)
        for h, v in ((0, 4 if low else 8), (4, 6 if low else 8), (8, 8)):
            points.append({"at": start + timedelta(hours=h), "value": v})
    return points + [{"at": NOW, "value": 4}]


class TimedRecovery(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.cfg = Config(root=Path(self.temp.name), data_dir=Path(self.temp.name)/"data", demo=True)

    def tearDown(self):
        self.temp.cleanup()

    def request(self, kind="energy", value=4, request_id="test-request-001", region=None):
        return dict(kind=kind, value=value, region=region, request_id=request_id)

    def test_current_checkin_retains_original_ten_point_scale_and_utc_time(self):
        result = recovery_log.from_browser(self.cfg, self.request(value=0), NOW)
        self.assertEqual(result["at"], NOW.isoformat(timespec="seconds"))
        r = recovery_log.read(self.cfg)[0]
        self.assertEqual((r["value"], r["scale"]), (0, 10))
        self.assertEqual((Path(self.cfg.root)/recovery_log.FILENAME).stat().st_mode & 0o777, 0o600)
        self.assertFalse(self.cfg.data_dir.exists())

    def test_idempotent_retry_and_reused_id_with_other_value(self):
        a = recovery_log.from_browser(self.cfg, self.request(), NOW)
        b = recovery_log.from_browser(self.cfg, self.request(), NOW + timedelta(minutes=2))
        self.assertEqual(a["id"], b["id"])
        self.assertTrue(b["replayed"])
        with self.assertRaises(ValueError): recovery_log.from_browser(self.cfg, self.request(value=3), NOW)
        self.assertEqual(len(recovery_log.read(self.cfg)), 1)

    def test_invalid_values_and_regions_do_not_write(self):
        for value in (-1, 11, True, float("nan"), float("inf"), "6", [8, 7], [0, 11], [True, 8], [7]):
            with self.assertRaises(ValueError): recovery_log.from_browser(self.cfg, self.request(value=value), NOW)
        with self.assertRaises(ValueError): recovery_log.from_browser(self.cfg, self.request(kind="soreness", region="thigh"), NOW)
        self.assertFalse((self.cfg.root/recovery_log.FILENAME).exists())

    def test_range_is_preserved_and_never_becomes_an_exact_self_rating(self):
        request = dict(self.request(value=[7, 8]), note="synthetic range")
        recovery_log.from_browser(self.cfg, request, NOW)
        self.assertTrue(recovery_log.from_browser(self.cfg, request, NOW)["replayed"])
        row = recovery_log.read(self.cfg)[0]
        self.assertEqual((row["reported_range"], row["note"]), ([7, 8], "synthetic range"))
        p = recovery.build(Context(self.cfg, now=NOW.replace(tzinfo=None)))
        f = p["current_ratings"]["energy"]
        self.assertEqual((f["status"], f["value_range"], f["range_hours"]), ("range_rating", [7, 8], None))

    def test_prior_ranges_cannot_supply_baseline_labels(self):
        points = [{"at": NOW-timedelta(days=i), "value": 7.5, "reported_range": [7, 8]} for i in range(1, 25)]
        points.append({"at": NOW, "value": 4})
        self.assertEqual(forecast(points, "energy", NOW, {})["status"], "baseline_needed")

    def test_current_time_endpoint_requires_same_origin_and_persists_the_rating(self):
        server = Server(("127.0.0.1", 0), make_handler(self.cfg, lambda: NOW.replace(tzinfo=None)))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            for origin in (None, "https://example.invalid", base):
                req = urllib.request.Request(base+"/api/recovery-checkin", data=json.dumps(self.request()).encode(),
                                             headers={"Content-Type":"application/json", **({"Origin":origin} if origin else {})})
                if origin != base:
                    with self.assertRaises(urllib.error.HTTPError) as caught: urllib.request.urlopen(req)
                    self.assertEqual(caught.exception.code, 403)
                else:
                    with urllib.request.urlopen(req) as response: self.assertTrue(json.load(response)["ok"])
            self.assertEqual(len(recovery_log.read(self.cfg)), 1)
        finally:
            server.shutdown()
            server.server_close()

    def test_context_matching_is_reported_and_uses_past_days(self):
        points = sore_points()
        body = {(NOW-timedelta(days=i)).date(): {"sleep_min": 450, "workout_min": 20, "complete": True} for i in range(1, 70)}
        f = forecast(points, "soreness", NOW, body)
        self.assertEqual(f["matched_context"], ["sleep", "training"])
        body[NOW.date()] = {"sleep_min": 10, "workout_min": 200, "complete": True}
        self.assertEqual(f, forecast(points, "soreness", NOW, body))

    def test_corrupt_log_is_not_silently_ignored_or_overwritten(self):
        p = self.cfg.root/recovery_log.FILENAME
        p.write_text('{"v":1}\n')
        before = p.read_bytes()
        with self.assertRaises(ValueError): recovery_log.from_browser(self.cfg, self.request(), NOW)
        self.assertEqual(before, p.read_bytes())

    def test_dense_soreness_history_predicts_interval_and_target(self):
        f = forecast(sore_points(), "soreness", NOW, {})
        self.assertEqual(f["status"], "estimated")
        self.assertEqual(f["target"], 2)
        self.assertEqual(f["resolution"], "hour")
        self.assertEqual(f["range_hours"], [6, 12])
        self.assertEqual(f["n"], 7)

    def test_energy_uses_personal_comparable_time_baseline(self):
        f = forecast(energy_points(), "energy", NOW, {})
        self.assertEqual(f["status"], "estimated")
        self.assertEqual(f["target"], 8)
        self.assertEqual(f["range_hours"], [4, 8])

    def test_future_points_cannot_change_current_forecast(self):
        p = energy_points()
        before = forecast(p, "energy", NOW, {})
        p += [{"at": NOW+timedelta(hours=h), "value": 10} for h in range(1, 8)]
        self.assertEqual(before, forecast(p, "energy", NOW, {}))

    def test_stale_current_and_expired_window_do_not_restart_clock(self):
        f = forecast(sore_points(), "soreness", NOW + timedelta(hours=4), {})
        self.assertEqual(f["range_hours"], [2, 8])
        self.assertEqual(forecast(sore_points(), "soreness", NOW + timedelta(hours=13), {})["status"], "refresh_needed")
        self.assertEqual(forecast(sore_points(), "soreness", NOW + timedelta(hours=25), {})["status"], "missing_current")

    def test_daily_logging_does_not_become_hourly_precision(self):
        p = []
        for n in range(7):
            start = NOW - timedelta(days=60 - n*7)
            p.extend({"at":start+timedelta(days=d),"value":v} for d,v in ((0,6),(1,5),(2,2),(3,0)))
        p.append({"at":NOW,"value":6})
        f = forecast(p,"soreness",NOW,{})
        self.assertEqual(f["resolution"], "day")
        self.assertEqual(f["range_days"], [1, 2])

    def test_frequent_ratings_on_one_day_do_not_supply_ten_baseline_days(self):
        points=[{"at":NOW-timedelta(minutes=i),"value":8} for i in reversed(range(1, 30))]+[{"at":NOW,"value":4}]
        self.assertEqual(forecast(points,"energy",NOW,{})["status"], "baseline_needed")

    def test_individual_region_does_not_mark_other_regions_zero(self):
        recovery_log.from_browser(self.cfg,self.request(kind="soreness",region="torso",value=6),NOW)
        p=recovery.build(Context(self.cfg,now=NOW.replace(tzinfo=None)))
        self.assertEqual(p["current_ratings"]["soreness"]["torso"]["value"],6)
        self.assertNotIn("left_calf",p["current_ratings"]["soreness"])
        self.assertEqual(p["forecast"]["soreness"]["left_calf"]["status"],"missing_current")
        json.dumps(p,default=str,allow_nan=False)


if __name__ == "__main__":
    unittest.main()
