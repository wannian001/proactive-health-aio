"""How you feel is said in one place, Today keeps its day ring on top, and what you tried is listed once.

The rest & rewards work first asked for current feelings on Today, Recovery and Rest & rewards, folded Today's day
ring under a new card and listed past activities on two pages; these tests keep the consolidation that followed.
"""
import json
import re
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

from healthaio import config, demo, recovery_log
from healthaio.context import Context
from healthaio.modules import today

WEB = Path(__file__).resolve().parents[1] / "healthaio" / "web"
read = lambda name: (WEB / name).read_text(encoding="utf-8")


class OneCheckin(unittest.TestCase):
    def test_feelings_are_asked_only_on_recovery(self):
        pages = {p.name: p.read_text(encoding="utf-8") for p in (WEB / "js").rglob("*.js")}
        asking = sorted(name for name, text in pages.items() if 'class="card span-12 rec-now" id="now"' in text)
        self.assertEqual(asking, ["recovery.js"])
        for name, text in pages.items():
            self.assertNotIn('data-rr-form="checkin"', text, name)  # the old rest check-in form
            self.assertNotIn("ov-now-form", text, name)              # the old inline 0–10 forms in the overview
            self.assertNotIn("energy-btn", text, name)               # the 0–5 energy buttons on the morning check-in

    def test_the_card_asks_energy_on_0_to_10_and_soreness_on_the_body(self):
        js = read("js/pages/recovery.js")
        self.assertIn("Array.from({ length: 11 }", js)
        self.assertIn('["recovery-checkin", once("energy"', js)
        self.assertNotIn("figureSvg(", js)  # soreness is chosen on the illustrated body above, not a second figure

    def test_rest_reads_body_from_the_same_answers(self):
        js = read("js/pages/recovery.js")
        self.assertIn('choice.energy <= 3 ? "tired" : choice.energy >= 6 ? "comfortable"', js)
        self.assertIn("Object.values(levels).some((lv) => lv >= 2)", js)

    def test_today_keeps_the_ring_on_top_and_rest_opens_the_list(self):
        js = read("js/pages/today.js")
        self.assertIn('<div class="grid">${morningHtml(daily)}${linesHtml(p)}</div>', js)
        self.assertNotIn("rr-day-overview", js)
        self.assertIn("${now}${body}", js)

    def test_what_was_tried_is_listed_on_follow_up_only(self):
        self.assertNotIn("historyHtml", read("js/pages/restore.js"))
        self.assertIn("historyHtml(p.restore", read("js/pages/followup.js"))

    def test_quiet_for_two_hours_is_still_reachable(self):
        self.assertIn("nextStep(p, { details: true, link: false, controls: true })", read("js/pages/restore.js"))

    def test_hrv_model_is_at_the_bottom_of_recovery(self):
        self.assertNotIn("hrvModelHtml", read("js/recovery-overview.js"))
        js = read("js/pages/recovery.js")
        self.assertLess(js.index("${responseHtml(p)}"), js.index("hrvModelHtml(p.hrv_prediction)"))


class WordsAndFiles(unittest.TestCase):
    def test_words_live_in_i18n(self):
        for gone in ("js/recovery-copy.js", "js/restore-text.js"):
            self.assertFalse((WEB / gone).exists(), gone)
        for name in ("js/recovery-overview.js", "js/recovery-forecast.js", "js/hrv-model.js", "js/restore-ui.js",
                     "js/pages/restore.js", "js/pages/recovery.js", "js/pages/today.js"):
            self.assertFalse(re.search(r"[一-鿿]", read(name)), f"{name} has Chinese words outside i18n.js")

    def test_the_unused_3d_model_is_gone(self):
        self.assertFalse((WEB / "vendor").exists())
        self.assertEqual(sorted(p.name for p in (WEB / "models" / "recovery").iterdir()), ["ILLUSTRATION.md", "body-illustration.png"])


class DemoEnergy(unittest.TestCase):
    def test_demo_rates_energy_on_the_card_scale_including_today(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = demo.generate(Path(tmp), date(2026, 10, 12))
            rows = recovery_log.read(config.load(path))
            self.assertTrue(rows)
            self.assertTrue(all(r["kind"] == "energy" and r["scale"] == 10 and 0 <= r["value"] <= 10 for r in rows))
            self.assertEqual(rows[-1]["at"][:10], "2026-10-12")
            ats = [r["at"] for r in rows]
            self.assertEqual(ats, sorted(ats))
            json.dumps(rows)

    def test_today_shows_the_energy_rated_on_the_card(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = config.load(demo.generate(Path(tmp), date(2026, 10, 12)))
            rated = today.self_report(Context(cfg, now=datetime(2026, 10, 12, 18)), date(2026, 10, 12))["energy_now"]
            self.assertTrue(0 <= rated["value"] <= 10)
            self.assertEqual(rated["at"][:10], "2026-10-12")
            early = today.self_report(Context(cfg, now=datetime(2026, 10, 12, 6)), date(2026, 10, 12))
            self.assertIsNone(early["energy_now"])  # a rating later that morning is not shown before it was made


if __name__ == "__main__":
    unittest.main()
