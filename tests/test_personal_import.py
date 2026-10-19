"""Synthetic source tree only; verify the bridge never mutates its source."""
import contextlib
import hashlib
import io
import json
import tempfile
import types
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from healthaio.personal_import import main, prepare
from healthaio.store import Store


class PersonalImport(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        self.source.mkdir()
        for file in ("AGENTS.md", "AI_README.md"):
            (self.source/file).write_text("synthetic fixture")
        for folder in ("AIOS", "Vault", "Runtime", "Data/staged/body"):
            (self.source/folder).mkdir(parents=True)
        self.data = self.source/"Data/staged/body"
        (self.data/"apple_health_daily.csv").write_text("date,sleep_duration_min,hrv,resting_hr,is_fixture\n2026-10-15,400,40,60,false\n2026-10-16,420,43,62,true\n")
        (self.data/"daily_state_preview.csv").write_text("date,sleep_duration_min,hrv,resting_hr,in_bed_min\n2026-10-15,450,42,61,9999\n2026-10-19,500,60,55,550\n")
        (self.data/"daily.csv").write_text("date,qi_energy,note\n2026-10-15,,private synthetic note\n")
        module = types.ModuleType("Runtime.storage_paths")
        module.__file__ = str(self.source/"Runtime/storage_paths.py")
        module.storage_paths_for = lambda root: types.SimpleNamespace(resolve_private=lambda rel: root/rel)
        self.patcher = patch.dict("sys.modules", {"Runtime":types.ModuleType("Runtime"), "Runtime.storage_paths":module})
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        self.temp.cleanup()

    def hashes(self):
        return {str(p.relative_to(self.source)):hashlib.sha256(p.read_bytes()).hexdigest() for p in self.source.rglob("*") if p.is_file()}

    def test_precedence_cutoff_fixture_filter_and_no_inferred_ratings(self):
        before = self.hashes()
        body, energy, summary = prepare(self.source, date(2026,10,18))
        self.assertEqual(len(body), 1)
        self.assertEqual(body[0]["sleep_min"], 450)
        self.assertIsNone(body[0]["in_bed_min"])
        self.assertEqual(summary["excluded_measurements"], {"in_bed_min":1})
        self.assertEqual(energy, [])
        self.assertEqual(before, self.hashes())
        self.assertNotIn("private synthetic note", json.dumps([body, energy, summary]))

    def test_dry_run_and_private_profile_schema_and_permissions(self):
        before = self.hashes()
        out = self.root/"private"
        args = ["--source",str(self.source),"--out",str(out),"--until","2026-10-18"]
        with contextlib.redirect_stdout(io.StringIO()):
            main(args)
            self.assertFalse(out.exists())
            main(args+["--apply"])
        self.assertEqual(Store(out/"data").problems(), [])
        self.assertEqual(out.stat().st_mode & 0o777, 0o700)
        self.assertTrue(all(p.stat().st_mode & 0o777 == 0o600 for p in out.rglob("*") if p.is_file()))
        self.assertEqual(before, self.hashes())
        with self.assertRaises(ValueError): main(args+["--apply"])

    def test_output_cannot_be_inside_source(self):
        with self.assertRaises(ValueError):
            main(["--source",str(self.source),"--out",str(self.source/"new-profile"),"--until","2026-10-18","--apply"])
        self.assertFalse((self.source/"new-profile").exists())
