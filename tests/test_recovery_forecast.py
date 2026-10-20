"""Synthetic trajectories only: missingness, chronology, stages and independent inputs."""
import json
import shutil
import subprocess
import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path

from healthaio import checkin
from healthaio.config import Config
from healthaio.context import Context
from healthaio.modules import recovery
from healthaio.modules import recovery_forecast as forecast
from healthaio.store import Store, write_table

DAY = date(2026, 10, 18)
NOW = datetime(2026, 10, 18, 10)
WEB = Path(__file__).resolve().parents[1] / "healthaio/web"


class PersonalForecast(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="aio-forecast-test-")
        self.cfg = Config(root=Path(self.tmp.name), data_dir=Path(self.tmp.name) / "data", demo=True)

    def tearDown(self):
        self.tmp.cleanup()

    def series(self, lengths=(1, 2, 3, 1, 2, 3, 1, 2, 3), phase=1):
        start = DAY - timedelta(days=150)
        energy = {start + timedelta(days=n): 4 for n in range(151)}
        sore = {d: 0 for d in energy}
        for i, length in enumerate(lengths):
            anchor = start + timedelta(days=35 + i * 10)
            for n in range(length):
                energy[anchor + timedelta(days=n)] = 0
                sore[anchor + timedelta(days=n)] = 2
        for n in range(phase):
            energy[DAY - timedelta(days=n)] = 0
            sore[DAY - timedelta(days=n)] = 2
        return energy, sore

    def write(self, energy, sore, body=None):
        write_table(self.cfg.data_dir, "self_report", [{"date": d, "energy": v} for d, v in energy.items()])
        write_table(self.cfg.data_dir, "soreness", [{"date": d, "region": "chest" if v else "none", "level": v} for d, v in sore.items()])
        if body is not None:
            write_table(self.cfg.data_dir, "body_daily", body)

    def result(self, day=DAY):
        ctx = Context(self.cfg, now=NOW)
        return forecast.build(ctx, day, recovery.soreness_log(ctx))

    def test_missing_current_does_not_borrow_old_or_feel_rating(self):
        write_table(self.cfg.data_dir, "self_report", [{"date": DAY, "feel": 8}, {"date": DAY - timedelta(days=1), "energy": 0}])
        result = self.result()
        self.assertEqual(result["energy"]["status"], "missing_current")
        self.assertTrue(all(v["status"] == "missing_current" for v in result["soreness"].values()))

    def test_known_trajectories_yield_personal_windows_and_traceable_backtests(self):
        self.write(*self.series())
        result = self.result()
        for f in (result["energy"], result["soreness"]["chest"]):
            self.assertEqual(f["status"], "estimated")
            self.assertEqual(f["range_days"], [1, 3])
            self.assertEqual(f["median_days"], 2)
            self.assertEqual(f["n"], 9)
            self.assertEqual(f["validation"]["observed"], 4)
            self.assertTrue(all(e["through"] <= DAY.isoformat() for e in f["evidence"]))
        self.assertEqual(result["energy"]["value"], 0)
        self.assertEqual(result["energy"]["target"], 4)
        self.assertEqual(result["soreness"]["chest"]["target"], 1)
        self.assertEqual(result["soreness"]["left_calf_back"]["status"], "at_target")

    def test_same_episode_stage_is_matched_without_duplicate_training_examples(self):
        self.write(*self.series(lengths=(3,) * 9, phase=2))
        f = self.result()["soreness"]["chest"]
        self.assertEqual(f["status"], "estimated")
        self.assertEqual(f["range_days"], [2, 2])
        # Nine past episodes plus one current censored episode, never daily repeated examples.
        self.assertEqual(f["n"], 9)
        self.assertEqual(f["phase_days"], 2)

    def test_soreness_is_allowed_to_worsen_before_easing(self):
        energy, sore = self.series(lengths=(3,) * 9)
        for d, v in list(sore.items()):
            if v == 2 and sore.get(d - timedelta(days=1)) == 2 and sore.get(d - timedelta(days=2)) == 0:
                sore[d] = 3
        self.write(energy, sore)
        self.assertEqual(self.result()["soreness"]["chest"]["range_days"], [3, 3])

    def test_missing_followup_is_censored_not_interpolated_or_recovered(self):
        energy, sore = self.series(lengths=(3,) * 9)
        starts = [d for d in sore if sore[d] == 2 and sore.get(d - timedelta(days=1)) == 0 and d < DAY]
        for d in starts[:6]:
            del sore[d + timedelta(days=2)]
        self.write(energy, sore)
        f = self.result()["soreness"]["chest"]
        self.assertEqual(f["status"], "incomplete")
        self.assertEqual(f["censored"], 6)
        self.assertIsNone(f["range_days"])

    def test_no_followup_cannot_be_discarded_to_select_only_fast_recoveries(self):
        energy, sore = self.series()
        starts = [d for d in sore if sore[d] == 2 and sore.get(d - timedelta(days=1)) == 0 and d < DAY]
        for d in starts[:5]:
            del sore[d + timedelta(days=1)]
        self.write(energy, sore)
        f = self.result()["soreness"]["chest"]
        self.assertNotEqual(f["status"], "estimated")
        self.assertGreater(f["no_followup"], 0)

    def test_other_regions_never_supply_recovery_examples(self):
        energy, sore = self.series()
        self.write(energy, sore)
        rows = Store(self.cfg.data_dir).rows("soreness")
        rows.append({"date": DAY, "region": "left_calf_back", "level": 2})
        write_table(self.cfg.data_dir, "soreness", rows)
        self.assertEqual(self.result()["soreness"]["left_calf_back"]["n"], 0)

    def test_unfinished_long_episodes_prevent_a_false_short_upper_bound(self):
        self.write(*self.series(lengths=(2, 3, 4, 9, 9)))
        f = self.result()["soreness"]["chest"]
        self.assertEqual(f["status"], "beyond_horizon")
        self.assertIsNone(f["range_days"])

    def test_old_matched_histories_are_not_called_current(self):
        energy, sore = self.series()
        old = {d - timedelta(days=110): v for d, v in sore.items() if d < DAY}
        old[DAY - timedelta(days=1)] = 0
        old[DAY] = 2
        self.write(energy, old)
        self.assertEqual(self.result()["soreness"]["chest"]["status"], "old_history")

    def test_history_cutoff_is_unchanged_by_later_ratings_and_context(self):
        energy, sore = self.series()
        self.write(energy, sore)
        before = self.result()
        for n in range(1, 20):
            energy[DAY + timedelta(days=n)] = 5
            sore[DAY + timedelta(days=n)] = 0
        self.write(energy, sore, [{"date": DAY + timedelta(days=1), "sleep_min": 800, "workout_min": 300}])
        self.assertEqual(before, self.result())

    def test_completed_days_only_context_and_explicit_fallback(self):
        energy, sore = self.series()
        body = [{"date": d, "sleep_min": 450, "workout_min": 20, "complete": True} for d in energy]
        self.write(energy, sore, body)
        self.assertEqual(self.result()["energy"]["matched_context"], ["sleep", "training"])
        for r in body:
            r["complete"] = False
        self.write(energy, sore, body)
        self.assertEqual(self.result()["energy"]["matched_context"], [])

    def test_energy_at_baseline_is_not_forced_to_five(self):
        energy, sore = self.series()
        energy[DAY] = 4
        self.write(energy, sore)
        f = self.result()["energy"]
        self.assertEqual(f["status"], "at_target")
        self.assertIsNone(f["range_days"])

    def test_sparse_baseline_and_invalid_rows_abstain(self):
        self.write({DAY: 0}, {DAY: 2})
        self.assertEqual(self.result()["energy"]["status"], "baseline_needed")
        with (self.cfg.data_dir / "self_report.csv").open("a") as stream:
            stream.write("2026-10-17,99,,,\n")
        self.assertEqual(self.result()["energy"]["status"], "invalid_records")

    def test_energy_only_checkin_preserves_unknown_soreness_and_other_fields(self):
        write_table(self.cfg.data_dir, "self_report", [{"date": DAY, "focus": 3, "feel": 8, "note": "test only"}])
        checkin.from_browser(self.cfg, {"date": DAY.isoformat(), "levels": None, "energy": 0}, NOW)
        self.assertFalse((self.cfg.data_dir / "soreness.csv").exists())
        row = Store(self.cfg.data_dir).rows("self_report")[0]
        self.assertEqual((row["energy"], row["focus"], row["feel"], row["note"]), (0, 3, 8, "test only"))
        checkin.from_browser(self.cfg, {"date": DAY.isoformat(), "levels": {"chest": 2}, "feel": 5}, NOW)
        self.assertEqual(Store(self.cfg.data_dir).rows("self_report")[0]["energy"], 0)

    def test_invalid_energy_is_rejected_before_any_write(self):
        for energy in (-1, 6, True, "3", float("nan"), float("inf")):
            with self.assertRaises(checkin.CheckinError):
                checkin.from_browser(self.cfg, {"date": DAY.isoformat(), "levels": {}, "energy": energy}, NOW)
        self.assertFalse(self.cfg.data_dir.exists())

    @unittest.skipUnless(shutil.which("node"), "requires node")
    def test_bilingual_ui_renders_actual_estimates_and_suppresses_unsaved_ones(self):
        self.write(*self.series())
        pack = self.result()
        script = '''
globalThis.document = { documentElement: { dataset: {} } };
const [web, language, raw] = process.argv.slice(1);
const { setLang } = await import(`${web}/js/i18n.js`); setLang(language);
const { forecastHtml } = await import(`${web}/js/recovery-forecast.js`);
const p = {forecast: JSON.parse(raw)};
process.stdout.write(JSON.stringify([forecastHtml(p, 'energy'), forecastHtml(p, 'soreness'), forecastHtml(p, 'energy', {draft:true})]));
'''
        for lang, expected in (("zh", "约 1–3 天后"), ("en", "About 1–3 days")):
            r = subprocess.run(["node", "--input-type=module", "-e", script, "--", str(WEB), lang, json.dumps(pack)], capture_output=True, text=True, check=True)
            a, b, draft = json.loads(r.stdout)
            self.assertIn(expected, a)
            self.assertIn(expected, b)
            self.assertNotIn(expected, draft)
            self.assertNotIn("undefined", a + b + draft)


if __name__ == "__main__":
    unittest.main()
