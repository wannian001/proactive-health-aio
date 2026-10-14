"""Data sources, written for someone looking at how the app works.

Rules under test (healthaio/modules/data.py):
- every source names files that exist in the schema and pages that exist in the app, and every file is fed by a source
- the totals add up the files as they stand (rows, size, the earliest day)
- the daily check is still there for the person whose data it is (90 days of arrivals per stream)
"""
import re
import shutil
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

from healthaio import config, demo
from healthaio.modules import PAGES
from healthaio.schema import TABLES
from healthaio.server import payload

TODAY = date(2026, 10, 12)
NOW = datetime(2026, 10, 12, 18, 40)
WEB = Path(__file__).resolve().parents[1] / "healthaio" / "web"


class DataPage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="healthaio-data-page-"))
        try:
            cls.cfg = config.load(demo.generate(cls.tmp, TODAY, NOW))
        except config.ConfigError:
            raise unittest.SkipTest("needs Python 3.11+ or tomli")
        cls.page = payload(cls.cfg, "data", None, NOW)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_every_source_goes_somewhere_real(self):
        fed = set()
        for src in self.page["sources"]:
            self.assertIn(src["key"], ("watch", "phone", "mac", "manual"))
            for f in src["files"]:
                self.assertIn(f, TABLES)
            for p in src["pages"]:
                self.assertIn(p, PAGES)
            fed |= set(src["files"])
        self.assertEqual(fed, set(TABLES))  # no file without a source
        i18n = (WEB / "js" / "i18n.js").read_text(encoding="utf-8")
        page_js = (WEB / "js" / "pages" / "data.js").read_text(encoding="utf-8")
        named = set(re.findall(r"(\w+): \"nav\.", page_js.split("const PAGE_NAME")[1].split("};")[0]))
        for src in self.page["sources"]:
            self.assertLessEqual(set(src["pages"]), named)  # each page has a name to show
            self.assertEqual(i18n.count(f'"data.flow_how.{src["key"]}"'), 2)
            for k in src["signals"]:
                self.assertEqual(i18n.count(f'"data.s.{k}"'), 2, k)

    def test_the_totals_add_up(self):
        T, tables = self.page["totals"], [t for t in self.page["tables"] if t["present"]]
        self.assertEqual(T["rows"], sum(t["rows"] for t in tables))
        self.assertEqual(T["bytes"], sum(t["bytes"] for t in tables))
        self.assertEqual(T["first"], min(t["first"] for t in tables if t["first"]))
        self.assertGreater(T["bytes"], 0)

    def test_the_daily_check_is_still_there(self):
        self.assertTrue(self.page["streams"])
        for s in self.page["streams"]:
            self.assertEqual(len(s["marks"]), self.page["days"])
