"""The design kit: the manifest matches the files on disk, every CSS variable is defined for both modes, export and
check agree, the static site carries the manifest, and the gallery page (#kit) is wired in and shows everything."""
import contextlib
import hashlib
import io
import json
import re
import shutil
import subprocess
import tempfile
import threading
import unittest
import urllib.request
from datetime import date, datetime
from http.server import ThreadingHTTPServer
from pathlib import Path

from healthaio import config, demo, kit
from healthaio.__main__ import main
from healthaio.server import make_handler

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "healthaio" / "web"
TODAY = date(2026, 10, 12)
NOW = datetime(2026, 10, 12, 18, 40)
KIT_PATHS = [path for path, _ in kit.FILES]
# colour tokens that dark mode keeps on purpose (status fills read the same on both backgrounds)
SAME_IN_BOTH = {"--good", "--watch", "--off", "--c-sore-1", "--c-sore-2", "--c-sore-3"}
COLOUR_ROLES = {"neutral", "accent", "data", "status"}


def read(path: str) -> str:
    return (WEB / path).read_text(encoding="utf-8")


def used_vars(text: str):
    return set(re.findall(r"var\((--[\w-]+)", text))


class Manifest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = kit.manifest()

    def test_lists_only_existing_files_with_their_hashes(self):
        self.assertEqual(self.m["name"], "healthaio-kit")
        self.assertRegex(self.m["version"], r"^\d+\.\d+\.\d+$")
        self.assertEqual(self.m["version"], kit.KIT_VERSION)
        self.assertEqual([f["path"] for f in self.m["files"]], KIT_PATHS)
        for f in self.m["files"]:
            data = (WEB / f["path"]).read_bytes()
            self.assertEqual(f["sha256"], hashlib.sha256(data).hexdigest(), f["path"])
            self.assertEqual(f["bytes"], len(data), f["path"])
        self.assertEqual({f["role"] for f in self.m["files"]}, {"tokens", "components", "charts", "icons"})

    def test_manifest_is_plain_json_and_stable(self):
        text = kit.to_json(self.m)
        self.assertEqual(json.loads(text), self.m)
        self.assertEqual(kit.manifest(), self.m)

    def test_tokens_carry_both_modes_and_a_role(self):
        tokens = {t["name"]: t for t in self.m["tokens"]}
        self.assertGreaterEqual(len(tokens), 50)
        for t in tokens.values():
            self.assertEqual(set(t), {"name", "light", "dark", "role"})
            self.assertIn(t["role"], {"type", "space", "radius", "motion", "neutral", "accent", "effect", "data", "status"}, t["name"])
        self.assertEqual((tokens["--accent"]["light"], tokens["--accent"]["dark"]), ("#1f5fbf", "#aea2f7"))
        self.assertEqual((tokens["--c-sleep"]["light"], tokens["--c-sleep"]["dark"]), ("#4a3aa7", "#9085e9"))
        self.assertEqual(tokens["--good"]["light"], tokens["--good"]["dark"])  # the same on purpose
        self.assertEqual(tokens["--t-xs"]["role"], "type")

    def test_components_and_charts_have_a_doc(self):
        self.assertGreaterEqual(len(self.m["components"]), 30)
        for c in self.m["components"]:
            self.assertTrue(c["class"] and c["doc"], c)
        names = {c["name"]: c for c in self.m["charts"]}
        for name in ("spark", "bullet", "dayRing", "timeChart", "lanes", "rangeStrip", "trendLine", "blockColumns", "legendKey", "icon", "setFormat"):
            self.assertIn(name, names)
        for c in self.m["charts"]:
            self.assertTrue(c["doc"], f"{c['name']} needs a one-line comment above it")
            self.assertTrue(c["signature"].startswith(c["name"]), c)
        self.assertEqual(names["rangeStrip"]["signature"], "rangeStrip(row, { width, height = 30, pad = 10 })")
        self.assertEqual(names["icon"]["file"], "js/icons.js")
        self.assertEqual(names["COLOR"]["kind"], "constant")

    def test_signatures_name_only_what_the_kit_exports(self):
        # a default such as `cats = RING_CATS` is printed in kit.json and the docs: an app must be able to import it
        names = {c["name"] for c in self.m["charts"]}
        for c in self.m["charts"]:
            for default in re.findall(r"=\s*([A-Za-z_$][\w$]*)\b(?!\s*\()", c["signature"]):
                if default not in {"null", "true", "false", "undefined"}:
                    self.assertIn(default, names, f"{c['name']} defaults to {default}, which the kit does not export")


class VersionLock(unittest.TestCase):
    """A kit file never changes under the same KIT_VERSION: healthaio/kit.lock.json holds the current version's hashes."""

    def test_the_lock_matches_the_kit_files_and_version(self):
        self.assertIsNone(kit.lock_problem())
        self.assertEqual(kit.read_lock()["version"], kit.KIT_VERSION)

    def test_a_changed_file_needs_a_new_version(self):
        tmp = Path(tempfile.mkdtemp(prefix="healthaio-kit-"))
        try:
            src, lock = tmp / "web", tmp / "kit.lock.json"
            for path in KIT_PATHS:
                (src / path).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(WEB / path, src / path)
            self.assertTrue(kit.write_lock(src, lock, "1.0.0"))
            self.assertFalse(kit.write_lock(src, lock, "1.0.0"))  # already current
            with open(src / "css" / "tokens.css", "a", encoding="utf-8") as f:
                f.write("\n/* a value changed */\n")
            problem = kit.lock_problem(src, lock, "1.0.0")
            self.assertIn("css/tokens.css", problem)
            self.assertIn("bump KIT_VERSION", problem)
            with self.assertRaises(kit.KitError):  # the lock never records changed files under the old version
                kit.write_lock(src, lock, "1.0.0")
            self.assertIn("not newer", kit.lock_problem(src, lock, "0.9.0"))
            self.assertIn("kit lock", kit.lock_problem(src, lock, "1.0.1"))
            self.assertTrue(kit.write_lock(src, lock, "1.0.1"))
            self.assertIsNone(kit.lock_problem(src, lock, "1.0.1"))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class Tokens(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.css = read("css/tokens.css")
        cls.tokens = kit.parse_tokens(cls.css)
        cls.light = {t["name"] for t in cls.tokens}
        cls.media, cls.dark = kit.dark_blocks(cls.css)

    def test_the_two_dark_blocks_are_the_same(self):
        self.assertTrue(self.dark)
        self.assertEqual(self.media, self.dark)
        self.assertLessEqual(set(self.dark), self.light)  # dark mode only redefines, never adds

    def test_every_colour_token_has_a_dark_step(self):
        for t in self.tokens:
            if t["role"] in COLOUR_ROLES and not t["light"].startswith("var(") and t["name"] not in SAME_IN_BOTH:
                self.assertIn(t["name"], self.dark, f"{t['name']} has no dark-mode value")

    def test_every_variable_the_kit_uses_is_defined_for_both_modes(self):
        for path in ("css/kit.css", "js/charts.js", "js/icons.js"):
            missing = used_vars(read(path)) - self.light
            self.assertFalse(missing, f"{path} uses undefined {sorted(missing)}")

    def test_every_variable_the_app_uses_is_defined(self):
        for path in [p for p in WEB.rglob("*") if p.suffix in (".css", ".js", ".html")]:
            text = path.read_text(encoding="utf-8")
            # Page-scoped CSS may declare its own properties without changing the exported kit.
            local = set(re.findall(r"(--[\w-]+)\s*:", text)) if path.suffix == ".css" else set()
            missing = used_vars(text) - self.light - local
            self.assertFalse(missing, f"{path.name} uses undefined {sorted(missing)}")

    def test_kit_css_spacing_and_corners_use_the_tokens(self):
        # a margin, padding or gap that equals a step of the space scale is written as that step, and a corner that
        # equals a radius token as that token, so an app that changes a token moves every place that uses it
        steps = {role: {t["light"]: t["name"] for t in self.tokens if t["role"] == role} for role in ("space", "radius")}
        css = re.sub(r"/\*.*?\*/", "", read("css/kit.css"), flags=re.S)
        found = re.findall(r"(?<![\w-])((?:margin|padding|gap|row-gap|column-gap|border-radius)(?:-[a-z]+)*)\s*:\s*([^;}]*)", css)
        self.assertGreater(len(found), 30)
        for prop, value in found:
            for literal in re.findall(r"(?<![\w.-])\d+px\b", value):
                name = steps["radius" if prop == "border-radius" else "space"].get(literal)
                self.assertIsNone(name, f"kit.css {prop}: {value} writes {literal}; use var({name})")

    def test_kit_code_has_no_raw_colours(self):
        for path in ("css/kit.css", "js/charts.js", "js/icons.js"):
            text = read(path)
            self.assertFalse(re.findall(r"#[0-9a-fA-F]{3,8}\b|\brgba?\(|\bhsla?\(", text), path)
        self.assertFalse(re.findall(r"#[0-9a-fA-F]{3,8}\b|\brgba?\(", read("css/app.css")))


class Isolation(unittest.TestCase):
    def test_kit_scripts_import_nothing(self):
        # an app copies charts.js and icons.js alone: they may not reach for Health AIO's i18n.js or pages
        for path in ("js/charts.js", "js/icons.js"):
            text = read(path)
            self.assertNotRegex(text, r"(?m)^\s*import\b", path)
            self.assertNotIn("import(", text, path)

    def test_kit_css_names_no_page(self):
        selectors = " ".join(re.findall(r"([^{}]+)\{", re.sub(r"/\*.*?\*/", "", read("css/kit.css"), flags=re.S)))
        self.assertNotIn("#", selectors)
        page = re.findall(r"\.(act-[\w-]+|drain-[\w-]+|time-[\w-]+|daycell[\w-]*|days-strip|days7|chg-[\w-]+|effects?|daycol|daylist|day-[\w-]+|"
                          r"apps|streams?|workout-icon|training-row|verdict|hero|kit-[\w-]+|review|checks|problem)(?![\w-])", selectors)
        self.assertFalse(page, page)

    def test_index_loads_tokens_then_kit_then_app(self):
        links = re.findall(r'<link rel="stylesheet" href="([^"]+)"', read("index.html"))
        self.assertEqual(links, ["css/tokens.css", "css/kit.css", "css/app.css", "css/recovery-overview.css"])

    def test_pages_use_the_kit_drawings(self):
        self.assertIn("rangeStrip(", read("js/pages/drain.js"))
        self.assertIn("trendLine(", read("js/pages/drain.js"))
        self.assertIn("legendKey(", read("js/pages/drain.js"))
        self.assertIn("blockColumns(", read("js/pages/week.js"))
        for page in ("drain.js", "week.js"):
            self.assertNotIn("<svg viewBox", read(f"js/pages/{page}"), page)  # the drawing lives in charts.js


class ExportCheck(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="healthaio-kit-"))
        self.src = self.tmp / "src"
        for path in KIT_PATHS:
            (self.src / path).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(WEB / path, self.src / path)
        self.dest = self.tmp / "app" / "static" / "kit"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def statuses(self):
        _, rows = kit.check(self.dest, self.src)
        return {r["path"]: r["status"] for r in rows}

    def test_export_then_check_is_up_to_date(self):
        written = kit.export(self.dest, self.src)
        self.assertEqual(sorted(written), sorted(KIT_PATHS + ["kit.json"]))
        for path in KIT_PATHS:
            self.assertEqual((self.dest / path).read_bytes(), (self.src / path).read_bytes(), path)
        self.assertEqual(json.loads((self.dest / "kit.json").read_text(encoding="utf-8")), kit.manifest(self.src))
        self.assertEqual(self.statuses(), {path: kit.UP_TO_DATE for path in KIT_PATHS})

    def test_a_file_edited_in_the_copy_is_modified_locally(self):
        kit.export(self.dest, self.src)
        with open(self.dest / "css" / "kit.css", "a", encoding="utf-8") as f:
            f.write("\n.card { padding: 2px; }\n")
        statuses = self.statuses()
        self.assertEqual(statuses.pop("css/kit.css"), kit.MODIFIED)
        self.assertEqual(set(statuses.values()), {kit.UP_TO_DATE})
        with self.assertRaises(kit.KitError):  # export would overwrite the local change
            kit.export(self.dest, self.src)
        kit.export(self.dest, self.src, force=True)
        self.assertEqual(set(self.statuses().values()), {kit.UP_TO_DATE})

    def test_a_changed_kit_file_makes_the_copy_outdated(self):
        kit.export(self.dest, self.src)
        with open(self.src / "js" / "charts.js", "a", encoding="utf-8") as f:
            f.write("\n// a change in Health AIO after the export\n")
        statuses = self.statuses()
        self.assertEqual(statuses.pop("js/charts.js"), kit.OUTDATED)
        self.assertEqual(set(statuses.values()), {kit.UP_TO_DATE})
        kit.export(self.dest, self.src)  # nothing was changed locally, so export just refreshes the copy
        self.assertEqual(set(self.statuses().values()), {kit.UP_TO_DATE})

    def test_a_changed_and_edited_file_counts_as_modified(self):
        kit.export(self.dest, self.src)
        for root in (self.src, self.dest):
            with open(root / "css" / "tokens.css", "a", encoding="utf-8") as f:
                f.write(f"\n/* {root.name} */\n")
        _, rows = kit.check(self.dest, self.src)
        row = next(r for r in rows if r["path"] == "css/tokens.css")
        self.assertEqual(row["status"], kit.MODIFIED)
        self.assertIn("also changed", row["note"])

    def test_a_missing_file_is_reported(self):
        kit.export(self.dest, self.src)
        (self.dest / "js" / "icons.js").unlink()
        self.assertEqual(self.statuses()["js/icons.js"], kit.MISSING)

    def test_a_copy_without_kit_json_is_an_error(self):
        self.dest.mkdir(parents=True)
        with self.assertRaises(kit.KitError):
            kit.check(self.dest, self.src)

    def test_a_first_export_never_overwrites_a_file_it_did_not_write(self):
        (self.dest / "css").mkdir(parents=True)
        own = "/* my hand-made kit.css, not from healthaio */\n"
        (self.dest / "css" / "kit.css").write_text(own, encoding="utf-8")
        with self.assertRaises(kit.KitError) as raised:
            kit.export(self.dest, self.src)
        self.assertIn("--force", str(raised.exception))
        self.assertEqual((self.dest / "css" / "kit.css").read_text(encoding="utf-8"), own)
        self.assertFalse((self.dest / "kit.json").exists())
        kit.export(self.dest, self.src, force=True)
        self.assertEqual(set(self.statuses().values()), {kit.UP_TO_DATE})

    def test_a_first_export_over_identical_files_goes_ahead(self):
        (self.dest / "js").mkdir(parents=True)
        shutil.copyfile(self.src / "js" / "icons.js", self.dest / "js" / "icons.js")
        kit.export(self.dest, self.src)
        self.assertEqual(set(self.statuses().values()), {kit.UP_TO_DATE})

    def record_extra(self, path, text, recorded_text=None):
        """Pretend an earlier kit had `path`: put it in the copy and in its kit.json."""
        (self.dest / path).write_text(text, encoding="utf-8")
        data = json.loads((self.dest / "kit.json").read_text(encoding="utf-8"))
        sha = hashlib.sha256((recorded_text if recorded_text is not None else text).encode("utf-8")).hexdigest()
        data["files"].append({"path": path, "role": "components", "sha256": sha, "bytes": len(text)})
        (self.dest / "kit.json").write_text(json.dumps(data), encoding="utf-8")

    def test_an_untouched_file_the_kit_dropped_is_removed_on_export(self):
        kit.export(self.dest, self.src)
        self.record_extra("css/old.css", ".old { }\n")
        self.assertEqual(self.statuses()["css/old.css"], kit.OUTDATED)
        notes = []
        kit.export(self.dest, self.src, notes=notes)
        self.assertFalse((self.dest / "css" / "old.css").exists())
        self.assertTrue(any("removed" in n for n in notes), notes)
        self.assertEqual(self.statuses(), {path: kit.UP_TO_DATE for path in KIT_PATHS})

    def test_a_changed_file_the_kit_dropped_is_left_and_still_reported(self):
        kit.export(self.dest, self.src)
        self.record_extra("css/old.css", ".old { color: red }\n", recorded_text=".old { }\n")
        self.assertEqual(self.statuses()["css/old.css"], kit.MODIFIED)
        with self.assertRaises(kit.KitError):
            kit.export(self.dest, self.src)
        notes = []
        kit.export(self.dest, self.src, force=True, notes=notes)
        self.assertTrue((self.dest / "css" / "old.css").exists())  # never deleted when it holds a local change
        self.assertTrue(any("left" in n for n in notes), notes)
        _, rows = kit.check(self.dest, self.src)
        row = next(r for r in rows if r["path"] == "css/old.css")
        self.assertEqual((row["status"], row["hint"]), (kit.OUTDATED, ""))
        self.assertIn("no longer part of the kit", row["note"])
        kit.export(self.dest, self.src)  # stays on record across exports
        self.assertEqual(self.statuses()["css/old.css"], kit.OUTDATED)
        (self.dest / "css" / "old.css").unlink()
        self.assertEqual(self.statuses(), {path: kit.UP_TO_DATE for path in KIT_PATHS})

    def test_a_malformed_kit_json_is_a_clear_error_with_the_way_out(self):
        kit.export(self.dest, self.src)
        for text in ("[]", '{"version": "1.0.0", "files": [{"path": "css/kit.css"}]}', '{"files": "x"}', "{"):
            (self.dest / "kit.json").write_text(text, encoding="utf-8")
            for action in (lambda: kit.check(self.dest, self.src), lambda: kit.export(self.dest, self.src)):
                with self.assertRaises(kit.KitError, msg=text) as raised:
                    action()
                self.assertIn("--force", str(raised.exception), text)
        kit.export(self.dest, self.src, force=True)
        self.assertEqual(set(self.statuses().values()), {kit.UP_TO_DATE})

    def test_a_change_without_a_version_bump_says_so(self):
        kit.export(self.dest, self.src)
        with open(self.src / "js" / "charts.js", "a", encoding="utf-8") as f:
            f.write("\n// changed, same KIT_VERSION\n")
        _, rows = kit.check(self.dest, self.src)
        note = next(r for r in rows if r["path"] == "js/charts.js")["note"]
        self.assertIn("without a version bump", note)
        self.assertNotIn(f"{kit.KIT_VERSION} → {kit.KIT_VERSION}", note)
        recorded = json.loads((self.dest / "kit.json").read_text(encoding="utf-8"))
        recorded["version"] = "0.9.0"
        (self.dest / "kit.json").write_text(json.dumps(recorded), encoding="utf-8")
        _, rows = kit.check(self.dest, self.src)
        self.assertIn(f"0.9.0 → {kit.KIT_VERSION}", next(r for r in rows if r["path"] == "js/charts.js")["note"])

    def test_command_line(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(main(["kit", "json"]), 0)
        self.assertEqual(json.loads(out.getvalue()), kit.manifest())
        target = str(self.tmp / "cli")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(["kit", "export", target]), 0)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(main(["kit", "check", target]), 0)
        self.assertEqual(out.getvalue().count(kit.UP_TO_DATE), len(KIT_PATHS))
        with open(Path(target) / "js" / "icons.js", "a", encoding="utf-8") as f:
            f.write("\n")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(main(["kit", "check", target]), 1)
        self.assertIn("modified locally  js/icons.js", out.getvalue())
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(["kit", "export", target]), 1)  # refuses to overwrite the local change
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(main(["kit", "check", str(self.tmp / "nowhere")]), 1)
        # the commands it tells the user to run work with the documented setup (no pip install)
        self.assertIn("`python3 -m healthaio kit export ", out.getvalue())
        self.assertNotIn("`healthaio kit", out.getvalue())
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(main(["kit", "lock"]), 0)  # the lock is current: nothing to write
        self.assertIn("already records", out.getvalue())


class Served(unittest.TestCase):
    def test_api_kit_is_the_manifest(self):
        tmp = Path(tempfile.mkdtemp(prefix="healthaio-kit-"))
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(config.Config(root=tmp, data_dir=tmp), lambda: NOW))
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        try:
            base = f"http://127.0.0.1:{httpd.server_address[1]}"
            self.assertEqual(json.loads(urllib.request.urlopen(f"{base}/api/kit", timeout=10).read()), kit.manifest())
            for path in KIT_PATHS + ["js/pages/kit.js"]:
                self.assertEqual(urllib.request.urlopen(f"{base}/{path}", timeout=10).status, 200, path)
        finally:
            httpd.shutdown()
            httpd.server_close()
            shutil.rmtree(tmp, ignore_errors=True)

    def test_static_build_writes_api_kit_json(self):
        tmp = Path(tempfile.mkdtemp(prefix="healthaio-kit-"))
        try:
            try:
                cfg = config.load(demo.generate(tmp / "demo", TODAY, NOW))
            except config.ConfigError:
                self.skipTest("needs Python 3.11+ or tomli")
            from healthaio.build_static import build
            with contextlib.redirect_stdout(io.StringIO()):
                out = build(cfg, tmp / "site", now=NOW)
            self.assertEqual(json.loads((out / "api" / "kit.json").read_text(encoding="utf-8")), kit.manifest())
            index = (out / "index.html").read_text(encoding="utf-8")
            version = re.search(r'data-build="([0-9a-f]{10})"', index).group(1)
            self.assertIn(f'css/kit.css?v={version}"', index)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class Gallery(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = read("js/app.js")
        cls.page = read("js/pages/kit.js")
        cls.i18n = read("js/i18n.js")
        cls.m = kit.manifest()

    def block(self, start):
        return self.page[self.page.index(start):self.page.index("\n};", self.page.index(start))]

    def test_gallery_route_is_registered_but_not_in_the_menu(self):
        self.assertIn('import kit from "./pages/kit.js";', self.app)
        self.assertRegex(self.app, r"const PAGES = \{[^}]*\bkit\b[^}]*\}")
        self.assertNotIn('"kit"', re.search(r"const NAV\s*=\s*\[([^\]]*)\]", self.app).group(1))
        self.assertIn('href="#kit"', self.app)  # the footer of every page
        self.assertIn('href="#kit"', read("js/pages/data.js"))
        self.assertEqual(self.i18n.count('"nav.kit"'), 2)  # English and Chinese
        self.assertIn("setFormat(", self.app)  # the kit's charts get Health AIO's words

    def test_every_component_and_chart_has_a_sample(self):
        samples = set(re.findall(r'(?m)^  "?([^":\s]+)"?: \(\) =>', self.block("const SAMPLES = {")))
        charts = set(re.findall(r"(?m)^  (\w+): \{", self.block("const CHARTS = {")))
        helpers = set(re.findall(r'"(\w+)"', re.search(r"const HELPERS = \[([^\]]*)\]", self.page).group(1)))
        for c in self.m["components"]:
            self.assertIn(c["class"], samples, f"the gallery shows no sample of {c['class']}")
        for c in self.m["charts"]:
            self.assertIn(c["name"], charts | helpers, f"the gallery neither draws nor lists {c['name']}")
        self.assertFalse(charts & helpers)

    def test_every_doc_has_a_chinese_line(self):
        for name in [c["class"] for c in self.m["components"]] + [c["name"] for c in self.m["charts"]]:
            self.assertIn(f'"kitdoc.{name}"', self.i18n, name)

    def test_gallery_words_are_in_both_languages(self):
        used = set(re.findall(r't\("(kit\.[\w.-]+)"', self.page))
        self.assertGreater(len(used), 20)
        for key in used:
            self.assertEqual(self.i18n.count(f'"{key}"'), 2, key)


def table_rows(text):
    """`--token` rows of a Markdown table: {name: [cells after the name, backticks dropped]}."""
    rows = {}
    for line in text.splitlines():
        hit = re.match(r"^\s*\|(?:[^|`]*\|)?\s*`(--[\w-]+)`\s*\|(.*)\|\s*$", line)
        if hit:
            rows[hit.group(1)] = [cell.strip().strip("`") for cell in hit.group(2).split("|")]
    return rows


def chinese_docs():
    """The gallery's Chinese line for each component and chart (kitdoc.<name> in i18n.js)."""
    text = (WEB / "js" / "i18n.js").read_text(encoding="utf-8")
    return {name: json.loads(f'"{value}"') for name, value in re.findall(r'"kitdoc\.([^"]+)": "((?:[^"\\]|\\.)*)"', text)}


class Docs(unittest.TestCase):
    def test_design_kit_tables_match_the_code(self):
        # the tables are written by hand: every value and description must still be the code's
        doc = (ROOT / "docs" / "DESIGN_KIT.md").read_text(encoding="utf-8")
        m = kit.manifest()
        tokens = {t["name"]: t for t in m["tokens"]}
        zh = chinese_docs()
        for half, same, words in ((doc.split("\n## 中文\n")[0], "same", lambda c: c["doc"]),
                                  (doc.split("\n## 中文\n")[1], "同左", lambda c: zh[c["name"]])):
            rows = table_rows(half)
            for t in m["tokens"]:
                if t["role"] in COLOUR_ROLES:
                    light, dark = rows[t["name"]][:2]
                    self.assertEqual(light, t["light"], t["name"])
                    self.assertEqual(dark, same if t["light"] == t["dark"] else t["dark"], t["name"])
                elif t["name"] not in ("--font", "--mono", "--shadow", "--seg-on-edge"):
                    self.assertIn(f"`{t['name']}` {t['light']}", half, t["name"])  # the type, space, radius and motion values
            self.assertFalse(set(rows) - set(tokens), "the doc names tokens tokens.css does not have")
            listed = re.findall(r"`([^`]+)`", re.search(r"(?:Components \(kit\.css\)|组件（kit\.css）)：?:? ?(.*)", half).group(1))
            self.assertEqual(listed, [c["class"] for c in m["components"]])
            for c in m["charts"]:
                line = next(l for l in half.splitlines() if l.startswith(f"| `{c['signature']}`"))
                self.assertEqual(line.rstrip(" |").split(" | ")[-1], words(c), c["name"])
        rows = table_rows((ROOT / "docs" / "DESIGN.md").read_text(encoding="utf-8"))
        for name, cells in rows.items():
            self.assertEqual(cells[:2], [tokens[name]["light"], tokens[name]["dark"]], f"docs/DESIGN.md {name}")

    def test_design_kit_doc_is_bilingual_and_current(self):
        doc = (ROOT / "docs" / "DESIGN_KIT.md").read_text(encoding="utf-8")
        english, chinese = doc.split("\n## 中文\n")
        self.assertIn("\n## English\n", english)
        m = kit.manifest()
        for half in (english, chinese):
            self.assertIn(f"| {m['version']} |", half)  # the version table names the current version
            for path in KIT_PATHS:
                self.assertIn(f"`{path}`", half, path)
            for t in m["tokens"]:
                if t["role"] in COLOUR_ROLES:
                    self.assertIn(f"`{t['name']}`", half, t["name"])
            for c in m["components"]:
                self.assertIn(f"`{c['class']}`", half, c["class"])
            for c in m["charts"]:
                self.assertIn(f"`{c['signature']}`", half, c["name"])
        for readme_half in (ROOT / "README.md").read_text(encoding="utf-8").split("\n## 中文\n"):
            self.assertIn("docs/DESIGN_KIT.md", readme_half)
            self.assertIn("#kit", readme_half)


RENDER = r"""
import { readFileSync } from "node:fs";
globalThis.document = { documentElement: {} };
const [web, file] = process.argv.slice(1);
const i18n = await import(`${web}/js/i18n.js`);
const charts = await import(`${web}/js/charts.js`);
charts.setFormat({ t: i18n.t, dur: i18n.dur, clock: i18n.clock, shortDay: i18n.shortDay, measure: i18n.measure, toDate: i18n.toDate, wtype: i18n.wtype });
const kit = await import(`${web}/js/pages/kit.js`);
const manifest = JSON.parse(readFileSync(file, "utf8"));
const out = {};
for (const lang of ["en", "zh"]) {
  i18n.setLang(lang);
  const svgs = [];
  for (const c of Object.values(kit.CHARTS)) for (const fn of Object.values(c.draw || {})) for (const w of [320, 900]) svgs.push(fn(w));
  out[lang] = { html: kit.default.render(manifest), svgs, columns: kit.CHARTS.stackedColumns.draw.columns(900), load: kit.CHARTS.blockColumns.draw.load(254) };
}
console.log(JSON.stringify(out));
"""

# an app whose t() knows only a few words: the charts write the rest in CHART_WORDS' English, never the raw key
PARTIAL_T = r"""
const [web] = process.argv.slice(1);
const charts = await import(`${web}/js/charts.js`);
const known = { "cat.focus": "专注" };
charts.setFormat({ t: (key) => known[key] ?? key });
const nights = charts.sleepWindows([{ date: "2026-10-12" }], { width: 300 });
const ring = charts.dayRing({ screen_hours: [{ work: 30 }] }, { size: 300 });
const lanes = charts.lanes([{ label: "A", parts: [["x", "red"]], max: 60, values: [{ x: 10 }] }], [{ label: "0" }], { width: 300 });
console.log(JSON.stringify({ nights, ring, lanes, words: Object.keys(charts.CHART_WORDS) }));
"""


@unittest.skipUnless(shutil.which("node"), "needs node to render the gallery")
class GalleryRenders(unittest.TestCase):
    def test_renders_in_both_languages_with_every_chart_drawn(self):
        tmp = Path(tempfile.mkdtemp(prefix="healthaio-kit-"))
        try:
            file = tmp / "kit.json"
            file.write_text(json.dumps(kit.manifest()), encoding="utf-8")
            done = subprocess.run(["node", "--input-type=module", "-e", RENDER, "--", str(WEB), str(file)],
                                  capture_output=True, text=True, timeout=60)
            self.assertEqual(done.returncode, 0, done.stderr)
            out = json.loads(done.stdout)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        for lang, page in out.items():
            self.assertFalse(re.findall(r"\bkit(?:doc)?\.[a-z_-]+\.[\w.-]+", page["html"]), lang)  # no key left untranslated
            for c in kit.manifest()["components"] + kit.manifest()["charts"]:
                self.assertIn(c.get("class") or c["name"], page["html"], lang)
            for svg in page["svgs"]:
                self.assertTrue(svg.startswith("<svg"), svg[:60])
                self.assertNotRegex(svg, r"NaN|undefined")
        self.assertIn("设计套件", out["zh"]["html"])
        self.assertIn("Design kit", out["en"]["html"])
        for lang, page in out.items():
            for t in kit.manifest()["tokens"]:  # every token has a place in the gallery, effects and motion included
                self.assertIn(t["name"], page["html"], f"{lang}: the gallery does not show {t['name']}")
            # a duration axis steps on whole hours, and the limit's label is under the axis, not over the columns
            ticks = re.findall(r'class="num">([^<]+)</text>', page["columns"])
            self.assertEqual(ticks, ["0m", "2h", "4h", "6h"] if lang == "en" else ["0 分", "2 小时", "4 小时", "6 小时"])
            axis = float(re.search(r'<line x1="[\d.]+" x2="[\d.]+" y1="([\d.]+)" y2="\1" stroke="var\(--c-axis\)"', page["columns"]).group(1))
            label = re.search(r'<text x="[\d.]+" y="([\d.]+)" font-size="11" fill="var\(--ink-2\)">', page["columns"])
            self.assertGreater(float(label.group(1)), axis)
        # in a 254px box "This week" and "+1 wk" would run into each other: every other column label is left out
        labels = re.findall(r'font-weight="600">([^<]*)</text>', out["en"]["load"])
        self.assertEqual([x for x in labels if "wk" in x or "week" in x], ["This week", "+2 wk", "+4 wk"])

    def test_charts_fall_back_to_their_english_words(self):
        done = subprocess.run(["node", "--input-type=module", "-e", PARTIAL_T, "--", str(WEB)], capture_output=True, text=True, timeout=60)
        self.assertEqual(done.returncode, 0, done.stderr)
        out = json.loads(done.stdout)
        self.assertIn("no record", out["nights"])
        self.assertIn('aria-label="Last 21 nights"', out["nights"])
        self.assertIn("专注", out["ring"])  # the word the app does know is the app's
        for svg in (out["nights"], out["ring"], out["lanes"]):
            for key in out["words"]:
                if "." in key:
                    self.assertNotIn(key, svg)


if __name__ == "__main__":
    unittest.main()
