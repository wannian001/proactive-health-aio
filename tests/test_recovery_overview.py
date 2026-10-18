"""Overview data keeps original scales, missingness and historical cutoffs."""
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

from healthaio.config import Config
from healthaio.context import Context
from healthaio.modules import body, recovery
from healthaio.store import write_table


class RecoveryOverview(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.cfg = Config(root=root, data_dir=root / "data", timezone="Australia/Melbourne")
        self.cfg.data_dir.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def ctx(self):
        return Context(self.cfg, now=datetime(2026, 10, 14, 18))

    def test_missing_is_not_zero_and_forecast_is_not_invented(self):
        p = recovery.build(self.ctx())
        self.assertIsNone(p["self"])
        self.assertIsNone(p["cardio"]["latest"])
        self.assertFalse(p["soreness"]["today"])
        self.assertNotIn("forecast", p)

    def test_zero_energy_retains_original_scale_and_record_date(self):
        write_table(self.cfg.data_dir, "self_report", [
            {"date": date(2026, 10, 13), "energy": 0},
        ])
        p = recovery.build(self.ctx())
        self.assertEqual(p["self"]["energy"], 0)
        self.assertEqual(p["self"]["date"], "2026-10-13")

    def test_cardio_agrees_with_body_page_and_never_uses_future_records(self):
        write_table(self.cfg.data_dir, "body_daily", [
            {"date": date(2026, 10, 10), "vo2max": 42},
            {"date": date(2026, 10, 14), "vo2max": 48},
        ])
        ctx = self.ctx()
        past = recovery.build(ctx, "2026-10-12")
        self.assertEqual(past["cardio"], body.cardio(ctx, date(2026, 10, 12)))
        self.assertEqual(past["cardio"]["latest"]["level"], 42)
        self.assertEqual(past["cardio"]["latest"]["date"], "2026-10-10")
        self.assertEqual(recovery.build(ctx)["cardio"]["latest"]["level"], 45)
