"""Where it feels tight: reading a sentence (rules, or the optional assistant), the report, its moves, the next day."""
import json
import sys
import tempfile
import types
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path

from healthaio import assistant, care_log, config, demo, routines
from healthaio.config import Config
from healthaio.context import Context
from healthaio.modules import care, sitting
from healthaio.store import write_table

NOW = datetime(2026, 10, 14, 20, 0)


class Rules(unittest.TestCase):
    def test_the_example_sentence(self):
        r = assistant.rules("我现在有久坐导致的颈部前倾、颈部紧张、胸部紧张")
        self.assertEqual(r["tight"], {"neck": "tight", "chest": "tight"})
        self.assertEqual((r["cause"], r["signs"], r["parsed_by"]), ("sitting", [], "rules"))
        self.assertIn("upper_back", r["also_ask"])

    def test_a_word_is_used_once_so_sore_after_training_is_achy_not_pain(self):
        r = assistant.rules("练完腿 大腿后侧酸痛")
        self.assertEqual((r["tight"], r["cause"]), ({"thigh_back": "achy"}, "training"))

    def test_each_place_gets_its_own_feeling_and_warning_signs_are_found(self):
        self.assertEqual(assistant.rules("脖子僵，肩胛骨那里紧，腰酸")["tight"], {"neck": "stiff", "upper_back": "tight", "low_back": "achy"})
        r = assistant.rules("肩膀疼，手发麻")
        self.assertEqual((r["tight"], r["signs"]), ({"upper_back": "pain"}, ["numb"]))
        r = assistant.rules("my neck is tight and my lower back hurts after sitting all day")
        self.assertEqual((r["tight"], r["cause"]), ({"neck": "tight", "low_back": "pain"}, "sitting"))


class Assistant(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.cfg = Config(root=root, data_dir=root / "data", timezone="Australia/Melbourne")

    def tearDown(self):
        self.tmp.cleanup()
        sys.modules.pop("anthropic", None)

    def test_off_by_default_so_the_rules_answer_and_say_why(self):
        out = assistant.parse(self.cfg, "颈部紧张")
        self.assertEqual((out["parsed_by"], out["assistant"]), ("rules", "off"))

    def test_only_ids_from_the_fixed_lists_survive(self):
        answer = {"tight": [{"region": "neck", "feel": "tight"}, {"region": "spleen", "feel": "tight"}, {"region": "chest", "feel": "burning"}],
                  "cause": "sitting", "signs": ["numb", "aliens"], "also_ask": ["neck", "upper_back", "kidney"]}
        out = assistant.parse(self.cfg, "neck tight", ask_model=lambda cfg, said: answer)
        self.assertEqual(out, {"tight": {"neck": "tight"}, "cause": "sitting", "signs": ["numb"], "also_ask": ["upper_back"], "parsed_by": "assistant"})

    def test_any_failure_falls_back_to_the_rules(self):
        def broken(cfg, said):
            raise RuntimeError("declined")
        out = assistant.parse(self.cfg, "胸前紧", ask_model=broken)
        self.assertEqual((out["tight"], out["parsed_by"], out["assistant"]), ({"chest": "tight"}, "rules", "declined"))

    def test_the_request_it_sends(self):
        """With a stand-in for the anthropic package: the default model, a refusal fallback, a JSON schema, the
        sentence and nothing else; a refusal falls back to the rules."""
        sent = {}

        class Block:
            type = "text"
            text = json.dumps({"tight": [{"region": "neck", "feel": "stiff"}], "cause": "unknown", "signs": [], "also_ask": []})

        class Response:
            stop_reason = "end_turn"
            content = [Block()]

        class Messages:
            def create(self, **kw):
                sent.update(kw)
                return Response()

        class Client:
            def __init__(self, **kw):
                self.beta = types.SimpleNamespace(messages=Messages())

        fake = types.ModuleType("anthropic")
        fake.Anthropic = Client
        for name in ("AuthenticationError", "RateLimitError", "APIConnectionError", "APIStatusError"):
            setattr(fake, name, type(name, (Exception,), {}))
        sys.modules["anthropic"] = fake
        self.cfg.assistant_enabled = True
        out = assistant.parse(self.cfg, "脖子有点僵")
        self.assertEqual((out["tight"], out["parsed_by"]), ({"neck": "stiff"}, "assistant"))
        self.assertEqual(sent["model"], "claude-opus-5-5")
        self.assertEqual((sent["fallbacks"], sent["betas"]), ("default", ["server-side-fallback-2026-07-01"]))
        self.assertEqual(sent["output_config"]["format"]["type"], "json_schema")
        self.assertEqual(sent["output_config"]["effort"], "low")
        self.assertEqual(sent["messages"], [{"role": "user", "content": "脖子有点僵"}])
        self.assertNotIn("tool_choice", sent)
        Response.stop_reason = "refusal"
        out = assistant.parse(self.cfg, "胸前紧")
        self.assertEqual((out["parsed_by"], out["assistant"]), ("rules", "declined"))

    def test_the_page_endpoint_reads_but_writes_nothing(self):
        out = assistant.from_browser(self.cfg, {"said": "腰很僵"})
        self.assertEqual(out["tight"], {"low_back": "stiff"})
        self.assertFalse(care_log.path(self.cfg).exists())
        with self.assertRaises(ValueError):
            assistant.from_browser(self.cfg, {"said": "x" * 281})
        with self.assertRaises(ValueError):
            assistant.from_browser(self.cfg, {"said": "腰", "send_to": "elsewhere"})


class Report(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.cfg = Config(root=root, data_dir=root / "data", timezone="Australia/Melbourne")
        self.cfg.data_dir.mkdir()
        self.n = 0

    def tearDown(self):
        self.tmp.cleanup()

    def say(self, when, **kw):
        self.n += 1
        return care_log.from_browser(self.cfg, {"request_id": f"care-{self.n:07d}", **kw}, when)

    def test_moves_for_the_places_named(self):
        self.say(NOW, op="report", tight={"neck": "tight", "chest": "tight"}, cause="sitting")
        c = care.build(Context(self.cfg, now=NOW))
        self.assertEqual(c["report"]["tight"], {"neck": "tight", "chest": "tight"})
        self.assertFalse(c["moves"]["blocked"] or c["moves"]["stop_first"])
        regions = {r for i in c["moves"]["routines"] for r in routines.BY_ID[i]["regions"]}
        self.assertTrue({"neck", "chest"} <= regions)

    def test_a_warning_sign_means_no_moves(self):
        self.say(NOW, op="report", tight={"upper_back": "pain"}, signs=["numb"])
        m = care.build(Context(self.cfg, now=NOW))["moves"]
        self.assertEqual((m["routines"], m["blocked"]), ([], True))

    def test_pain_puts_the_warning_first_and_keeps_the_moves_short(self):
        self.say(NOW, op="report", tight={"neck": "pain"})
        m = care.build(Context(self.cfg, now=NOW))["moves"]
        self.assertTrue(m["stop_first"])
        self.assertTrue(m["routines"] and all(routines.BY_ID[i]["minutes"] <= 1 for i in m["routines"]))

    def test_may_be_sitting_only_with_a_long_stretch_that_day_or_the_day_before(self):
        self.say(NOW, op="report", tight={"neck": "tight"})
        self.assertIsNone(care.build(Context(self.cfg, now=NOW))["maybe_sitting"])
        start = datetime(2026, 10, 13, 9, 0)
        write_table(self.cfg.data_dir, "screen_sessions", [{"start": start, "end": start + timedelta(minutes=sitting.LONG_MIN + 10),
                                                             "device": "laptop", "app": "Code", "category": "work"}])
        ms = care.build(Context(self.cfg, now=NOW))["maybe_sitting"]
        self.assertEqual((ms["date"], ms["longest"]), ("2026-10-13", sitting.LONG_MIN + 10))

    def test_the_next_day_asks_until_answered(self):
        r = self.say(NOW, op="report", tight={"neck": "tight", "chest": "stiff"})
        tomorrow = Context(self.cfg, now=NOW + timedelta(days=1))
        self.assertEqual(care.build(Context(self.cfg, now=NOW))["ask"], [])  # not the same day
        self.assertEqual([a["region"] for a in care.build(tomorrow)["ask"]], ["neck", "chest"])
        self.say(NOW + timedelta(days=1), op="answer", ref=r["id"], region="neck", change="better")
        self.assertEqual([a["region"] for a in care.build(tomorrow)["ask"]], ["chest"])
        with self.assertRaises(ValueError):
            self.say(NOW + timedelta(days=1), op="answer", ref=r["id"], region="calf", change="better")

    def test_reports_are_checked(self):
        for bad in ({"tight": {}}, {"tight": {"spleen": "tight"}}, {"tight": {"neck": "burning"}}, {"tight": {"neck": "tight"}, "signs": ["aliens"]}):
            with self.assertRaises(ValueError):
                self.say(NOW, op="report", **bad)


class Demo(unittest.TestCase):
    def test_the_demo_asks_about_last_night(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = config.load(demo.generate(Path(tmp), date(2026, 10, 12)))
            c = care.build(Context(cfg, now=datetime(2026, 10, 12, 18, 40)))
            self.assertEqual([a["region"] for a in c["ask"]], ["neck", "chest"])
            self.assertIsNotNone(c["maybe_sitting"])


if __name__ == "__main__":
    unittest.main()
