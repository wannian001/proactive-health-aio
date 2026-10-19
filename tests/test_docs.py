"""The reading pages under the menu: Overview (#project) and Guide (#guide); History is a link to the author's site."""
import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

from healthaio.modules import PAGES, docs

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "healthaio" / "web"
APP = (WEB / "js" / "app.js").read_text(encoding="utf-8")
I18N = (WEB / "js" / "i18n.js").read_text(encoding="utf-8")
ICONS = (WEB / "js" / "icons.js").read_text(encoding="utf-8")


class Registry(unittest.TestCase):
    def test_the_pages_are_registered_and_only_name_themselves(self):
        for name in docs.DOC_PAGES:
            self.assertIn(name, PAGES)
            self.assertEqual(PAGES[name](None), {"page": name})
        with self.assertRaises(ValueError):
            docs.build(None, "today")


class Menu(unittest.TestCase):
    def test_they_sit_under_the_menu_not_in_it(self):
        listed = re.findall(r'"(\w+)"', re.search(r"const DOCS\s*=\s*\[([^\]]*)\]", APP).group(1))
        self.assertEqual(listed, ["data", "project", "history"])  # where the numbers come from, then the reading pages (the guide is the end of the overview)
        nav = re.search(r"const NAV\s*=\s*\[([^\]]*)\]", APP).group(1)
        for name in listed:
            self.assertNotIn(f'"{name}"', nav)  # the tab bar keeps the four items of the health loop
        glyphs = dict(re.findall(r'(\w+): "(\w+)"', re.search(r"const DOC_ICON\s*=\s*\{([^}]*)\}", APP).group(1)))
        self.assertEqual(sorted(glyphs), sorted(listed))
        for glyph in glyphs.values():
            self.assertRegex(ICONS, rf"\b{glyph}: '<", glyph)  # an icon the kit draws
        self.assertIn('class="side-docs"', APP)

    def test_history_is_a_link_to_the_authors_site_not_part_of_this_repository(self):
        # it quotes the personal system this project comes from, so it is not published with the code
        self.assertFalse((WEB / "js" / "history-content.js").exists())
        self.assertFalse((WEB / "js" / "pages" / "history.js").exists())
        self.assertNotIn("history", PAGES)
        self.assertNotIn("history", docs.DOC_PAGES)
        self.assertIn('const OUTSIDE = { history: "doc.history_url" };', APP)
        self.assertIn('target="_blank" rel="noopener"', APP)
        urls = re.findall(r'"doc\.history_url": "([^"]+)"', I18N)
        self.assertEqual(sorted(urls), ["https://tangjiakuo.top/demo/aio-history/", "https://tangjiakuo.top/demo/aio-history/en/"])

    def test_every_word_in_both_languages(self):
        for key in ("nav.about", "nav.project", "nav.guide", "nav.history", "doc.other_lang"):
            self.assertEqual(I18N.count(f'"{key}"'), 2, key)


RENDER = """
globalThis.document = { documentElement: { dataset: {} } };
const [web, lang, page] = process.argv.slice(1);
const i18n = await import(`${web}/js/i18n.js`);
i18n.setLang(lang);
const mod = (await import(`${web}/js/pages/${page}.js`)).default;
process.stdout.write(JSON.stringify({ html: mod.render({ page }) }));
"""


@unittest.skipUnless(shutil.which("node"), "needs node to render the pages")
class Words(unittest.TestCase):
    @staticmethod
    def render(lang, page):
        out = subprocess.run(["node", "--input-type=module", "-e", RENDER, "--", str(WEB), lang, page],
                             capture_output=True, text=True, check=True, timeout=60)
        return json.loads(out.stdout)

    def test_pages_render_in_both_languages(self):
        for lang, title in (("en", "Guide"), ("zh", "使用说明")):
            html = self.render(lang, "guide")["html"]
            self.assertIn(f"<h1>{title}</h1>", html)
            self.assertIn("https://tangjiakuo.top/demo/aio-history/", html)  # where the project came from: a link out

    def test_the_overview_says_the_same_things_in_both_languages(self):
        shapes = []
        for lang, title in (("en", "Overview"), ("zh", "项目说明")):
            html = self.render(lang, "project")["html"]
            self.assertIn(f"<h1>{title}</h1>", html)
            self.assertIn('id="guide"', html)  # #guide moved here: #project/guide opens the overview at it
            shapes.append([len(re.findall(pattern, html)) for pattern in
                           (r'class="card doc-card"', r"<li><b>[^<]*</b><span>", r"<li><details", r"<tr>", r'class="chip"')])
        self.assertEqual(shapes[0], shapes[1])
        self.assertEqual(shapes[0][:3], [3, 5, 13])  # three cards, the five steps of the loop, five folds, then the guide's eight steps

    def test_no_personal_data_on_the_pages(self):
        text = "".join((WEB / "js" / f).read_text(encoding="utf-8") for f in ("pages/guide.js", "pages/project.js"))
        for leak in ("/Users/", "Data/raw", "Vault/", "kg", "bpm", " ms", "MAE"):
            self.assertNotIn(leak, text, leak)


if __name__ == "__main__":
    unittest.main()
