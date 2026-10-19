"""Rest & rewards from your own answers: the order of the library, one activity by name, and rewards after a milestone."""
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from healthaio.config import Config
from healthaio.context import Context
from healthaio.modules import restore
from healthaio.store import write_table

NOW = datetime(2026, 10, 14, 18, 0)


def row(activity, times, answered, better, glad):
    return {"activity": activity, "times": times, "answered": answered, "better": better, "worse": 0, "glad": glad, "last": "2026-10-13T18:00"}


def finished(activity, change=None, enjoyment=None):
    return {"activity": activity, "status": "finished", "started_at": "2026-10-13T18:00",
            "feedback": {"change": change, "enjoyment": enjoyment} if change or enjoyment else None}


class Ranking(unittest.TestCase):
    def test_too_few_answers_never_go_ahead(self):
        rows = restore.tried([finished("play", "better", "yes"), finished("walk", "better", "yes"), finished("walk", "better", "no"),
                              finished("sit"), finished("sit")])
        self.assertEqual([b["activity"] for b in rows], ["walk", "sit", "play"])  # play's one answer doesn't count yet
        self.assertEqual(restore.share(rows[0]), 0.75)
        self.assertEqual(restore.share(rows[-1]), -1)

    def test_after_a_hard_spell_the_one_that_most_often_left_you_better(self):
        rows = [row("music", 6, 4, 1, 4), row("friend", 2, 2, 2, 2), row("walk", 7, 6, 3, 2), row("play", 1, 1, 1, 1)]
        s = restore.suggest(None, "signals", rows)
        self.assertEqual((s["why"], s["activity"]), ("restore", "friend"))
        self.assertIsNone(restore.suggest(None, "signals", [row("sit", 3, 3, 1, 0)]))  # nothing helped often enough: no name


class Rewards(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.cfg = Config(root=root, data_dir=root / "data", timezone="Australia/Melbourne")
        self.cfg.data_dir.mkdir()
        self.rows = [row("play", 4, 4, 2, 4), row("walk", 6, 6, 3, 3)]

    def tearDown(self):
        self.tmp.cleanup()

    def ctx(self):
        return Context(self.cfg, now=NOW)

    def test_no_milestone_no_reward(self):
        self.assertIsNone(restore.suggest(self.ctx(), "steady", self.rows))

    def test_a_deadline_handed_in_brings_the_one_that_left_you_better_and_glad(self):
        write_table(self.cfg.data_dir, "deadlines", [{"due": NOW - timedelta(hours=3), "title": "A2", "status": "submitted"}])
        s = restore.suggest(self.ctx(), "steady", self.rows)
        self.assertEqual((s["why"], s["for"], s["activity"]), ("reward", ["deadline"], "play"))

    def test_after_heavy_screens_the_reward_leaves_screens(self):
        write_table(self.cfg.data_dir, "deadlines", [{"due": NOW - timedelta(hours=3), "title": "A2", "status": "done"}])
        self.cfg.screen.entertainment_max_hours = 2
        y = NOW - timedelta(days=1)
        write_table(self.cfg.data_dir, "screen_sessions", [{"start": y.replace(hour=20), "end": y.replace(hour=23), "device": "phone",
                                                             "app": "YouTube", "category": "entertainment"}])
        self.assertEqual(restore.suggest(self.ctx(), "steady", self.rows)["activity"], "walk")


if __name__ == "__main__":
    unittest.main()
