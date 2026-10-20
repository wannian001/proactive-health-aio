"""Nothing personal goes into the repository: no home-folder paths, e-mail addresses, Apple team or device ids,
Tailscale addresses or local signing settings. The patterns are generic on purpose, so this file names nobody."""
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BINARY = {".png", ".jpg", ".jpeg", ".gif", ".icns", ".ico", ".mp4", ".mov", ".zip", ".pdf", ".woff", ".woff2", ".bin"}
PATTERNS = {
    "a home folder": re.compile(r"/(?:Users|home)/(?!you\b|me\b|example\b|USER\b|<)[A-Za-z0-9._-]+/"),
    "an e-mail address": re.compile(r"\b[A-Za-z0-9._%+-]+@(?!example\.(?:com|org|test)\b)"
                                    r"(?!users\.noreply\.github\.com\b)[A-Za-z][A-Za-z0-9-]*\.[A-Za-z][A-Za-z.]+\b"),
    # ABCDE12345 is the placeholder the docs and ios/Local.example.xcconfig use
    "an Apple team id": re.compile(r"(?:DEVELOPMENT_TEAM|HEALTHAIO_TEAM)\s*=\s*(?!ABCDE12345\b)[A-Z0-9]{10}\b"),
    "a device UDID": re.compile(r"\b0000[0-9A-F]{4}-[0-9A-F]{16}\b|\b[0-9a-f]{40}\b(?=.*udid)", re.I),
    "a Tailscale address": re.compile(r"\b100\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7])\.\d{1,3}\.\d{1,3}\b"),
}
# where a pattern may appear because the text is about the pattern itself
ALLOWED = {("healthaio/phone.py", "a Tailscale address"), ("tests/test_phone.py", "a Tailscale address"),
           ("docs/CAPTURE.md", "a Tailscale address"), ("tests/test_privacy.py", "an Apple team id"),
           ("tests/test_collect.py", "an Apple team id")}
NEVER_TRACKED = ("ios/Local.xcconfig", ".healthaio/", "healthaio.toml", "data/")


def files():
    listed = subprocess.run(["git", "-C", str(ROOT), "ls-files", "--cached", "--others", "--exclude-standard"],
                            capture_output=True, text=True, check=True).stdout.split("\n")
    return [name for name in listed if name and (ROOT / name).is_file()]


class Privacy(unittest.TestCase):
    def test_no_personal_details_in_any_file(self):
        found = []
        for name in files():
            path = ROOT / name
            if path.suffix.lower() in BINARY or name.startswith("tests/fixtures/") and name.endswith(".ics"):
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for label, pattern in PATTERNS.items():
                if (name, label) in ALLOWED:
                    continue
                for match in pattern.finditer(text):
                    line = text.count("\n", 0, match.start()) + 1
                    found.append(f"{name}:{line}: {label}: {match.group(0)[:60]}")
        self.assertEqual(found, [], "\n".join(found))

    def test_local_settings_and_data_stay_out(self):
        listed = files()
        for prefix in NEVER_TRACKED:
            self.assertFalse([n for n in listed if n == prefix or n.startswith(prefix)], prefix)
        csvs = [n for n in listed if n.endswith(".csv") and not n.startswith("tests/fixtures/")]
        self.assertEqual(csvs, [])


if __name__ == "__main__":
    unittest.main()
