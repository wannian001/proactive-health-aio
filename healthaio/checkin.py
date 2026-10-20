"""The check-ins: on the Recovery page, how you feel this morning (2, 5 or 8) and where it is sore; after a strength
or hard workout, from the prompt on any page, what it trained (see schema.py).

Soreness is said when it is felt: report() updates only the regions you name, for today, with the time and what you
said, and keeps today's other regions; the next days' answers ("fine now" is level 0) go the same way. The morning
feeling goes into that morning's row of self_report.csv (`feel` and optional 0–5 `energy`; focus and the note on that
row stay as they were). Rows of other days are never touched, and rows that do not parse (a hand-edited file) are kept
as written. `healthaio checkin` replaces a whole day's soreness from the command line (for a script or an assistant).

What a workout trained replaces that workout's row in workout_notes.csv: the regions tapped on the figure and a note
in your own words. Words in the note suggest regions (REGION_WORDS; the page shows them as you type and you can
untick any), and `healthaio trained` fills the regions from the note when none are given.
"""
import csv
import math
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from . import state
from .schema import FEELINGS, SORE_REGIONS, TABLES
from .store import write_table

LEVELS = (1, 2, 3)  # a little, clearly sore, very sore
NOTE_MAX = 500

# Words in a workout note -> the regions it trained, Chinese and English. Longer words are tried first and a matched
# word is used up, so 小腿 is not also 腿 and "leg press" is not also "leg"; English words match whole, with a plural
# s or es. A lift names the places it works: a bench press the chest, the fronts of the shoulders and the upper arms.
both = lambda *names: tuple(f"{side}_{n}" for side in ("left", "right") for n in names)
UPPER_ARMS = both("upper_arm")
REGION_WORDS: Tuple[Tuple[Tuple[str, ...], Tuple[str, ...]], ...] = (
    (("颈", "脖子", "耸肩", "neck", "shrug"), ("neck_back_left", "neck_back_right")),
    (("卧推", "俯卧撑", "bench", "push-up", "pushup"), ("chest",) + both("shoulder_front", "upper_arm")),
    (("胸", "飞鸟", "chest", "fly", "flye"), ("chest",)),
    (("肩", "推举", "侧平举", "shoulder", "overhead press", "lateral raise"), both("shoulder_front")),
    (("划船", "引体", "高位下拉", "row", "pull-up", "pullup", "pulldown"), ("upper_back",) + UPPER_ARMS),
    (("背", "back", "lat"), ("upper_back",)),
    (("腹", "核心", "卷腹", "平板支撑", "abs", "core", "crunch", "plank"), ("abs",)),
    (("硬拉", "deadlift"), ("low_back",) + both("glute", "thigh_back")),
    (("腰", "下背", "lower back"), ("low_back",)),
    (("臀", "髋", "臀推", "glute", "hip", "hip thrust"), both("glute")),
    (("深蹲", "箭步蹲", "腿举", "squat", "lunge", "leg press"), both("thigh_front", "glute")),
    (("腘绳", "腿弯举", "hamstring", "leg curl"), both("thigh_back")),
    (("手臂", "胳膊", "二头", "三头", "肱", "弯举", "臂屈伸", "arm", "bicep", "tricep", "curl", "dip"), UPPER_ARMS),
    (("小腿", "提踵", "calf", "calves", "calf raise"), both("calf_back")),
    (("跑", "run", "running", "jog"), both("calf_back", "thigh_front")),
    (("腿", "下肢", "leg", "lower body"), both("thigh_front", "thigh_back", "calf_back")),
    (("上肢", "upper body"), ("chest", "upper_back") + both("shoulder_front", "shoulder_back", "upper_arm")),
    (("全身", "full body"), ("chest", "upper_back", "abs") + both("shoulder_front", "upper_arm", "glute", "thigh_front", "calf_back")),
)


def regions_in(note: str) -> List[str]:
    """The regions a note's words suggest, in the figure's order."""
    text = f" {note.lower()} "
    found = set()
    for word, regions in sorted(((w, r) for words, r in REGION_WORDS for w in words), key=lambda x: -len(x[0])):
        pattern = rf"\b{re.escape(word)}(?:s|es)?\b" if word.isascii() else re.escape(word)
        if re.search(pattern, text, re.ASCII):  # \b as in the page's JavaScript: a Chinese character is not a letter
            text = re.sub(pattern, " ", text, flags=re.ASCII)
            found.update(regions)
    return [r for r in SORE_REGIONS if r in found]


class CheckinError(ValueError):
    """A check-in that cannot be written: an unknown region, a level or feeling out of range, a day not yet come."""


def check(levels: Any, keep_zero: bool = False) -> Dict[str, int]:
    """The soreness as {region: level} after validating everything: only sore regions, or with keep_zero also the ones
    said to be fine again (0)."""
    if not isinstance(levels, dict):
        raise CheckinError("levels must be an object of region: level")
    out: Dict[str, int] = {}
    for region, level in levels.items():
        if region not in SORE_REGIONS:
            raise CheckinError(f"unknown region {region!r}; one of {', '.join(SORE_REGIONS)}")
        if level in (0, None):
            if keep_zero and level == 0:
                out[region] = 0
            continue
        if isinstance(level, bool) or level not in LEVELS:
            raise CheckinError(f"{region}: level must be 0 to 3")
        out[region] = int(level)
    return out


def check_feel(feel: Any) -> Optional[int]:
    if feel is None:
        return None
    if isinstance(feel, bool) or feel not in FEELINGS:
        raise CheckinError(f"feel must be one of {', '.join(map(str, FEELINGS))}")
    return int(feel)


def check_energy(energy: Any) -> Optional[float]:
    if energy is None:
        return None
    if isinstance(energy, bool) or not isinstance(energy, (int, float)) or not math.isfinite(energy) or not 0 <= energy <= 5:
        raise CheckinError("energy must be a number from 0 to 5")
    return float(energy)


def parse_day(text: Any, today: date) -> date:
    try:
        day = date.fromisoformat(str(text))
    except ValueError:
        raise CheckinError("date must be YYYY-MM-DD") from None
    if day > today:
        raise CheckinError("a check-in cannot be for a day that has not come")
    return day


def _rows(path: Path) -> List[Dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def save(cfg, day: date, levels: Optional[Dict[str, int]], feel: Optional[int] = None, energy: Optional[float] = None) -> Dict[str, Any]:
    """Write this check-in, holding the write lock the importers hold."""
    energy = check_energy(energy)
    stamp = day.isoformat()
    with state.write_lock(cfg):
        if levels is not None:  # energy-only / feeling-only saves do not imply no soreness
            sore = [r for r in _rows(Path(cfg.data_dir) / TABLES["soreness"].filename) if (r.get("date") or "").strip() != stamp]
            new = [{"date": stamp, "region": region, "level": str(level)} for region, level in sorted(levels.items())]
            sore += new or [{"date": stamp, "region": "none", "level": "0"}]
            write_table(cfg.data_dir, "soreness", sorted(sore, key=lambda r: (r.get("date") or "", r.get("region") or "")))
        if feel is not None or energy is not None:
            rows = _rows(Path(cfg.data_dir) / TABLES["self_report"].filename)
            mine = next((r for r in rows if (r.get("date") or "").strip() == stamp), None)
            if mine is None:
                mine = {"date": stamp}
                rows.append(mine)
            if feel is not None:
                mine["feel"] = str(feel)
            if energy is not None:
                mine["energy"] = str(energy)
            write_table(cfg.data_dir, "self_report", sorted(rows, key=lambda r: r.get("date") or ""))
    return {"ok": True, "date": stamp, "levels": levels, "feel": feel, "energy": energy}


SAID_MAX = 280


def report(cfg, now: datetime, levels: Dict[str, int], said: str = "") -> Dict[str, Any]:
    """Today's soreness for the regions named (0 is fine again), with the time and what was said; today's other
    regions and every other day stay as they were. The write lock is the importers'."""
    if not levels:
        raise CheckinError("name at least one region")
    if not isinstance(said, str) or len(said) > SAID_MAX:
        raise CheckinError(f"what you said: at most {SAID_MAX} characters")
    said = " ".join(said.split())
    stamp, at = now.date().isoformat(), now.replace(tzinfo=None).strftime("%Y-%m-%dT%H:%M")
    with state.write_lock(cfg):
        rows = [r for r in _rows(Path(cfg.data_dir) / TABLES["soreness"].filename)
                if not ((r.get("date") or "").strip() == stamp and (r.get("region") or "").strip() in levels | {"none": 0})]
        rows += [{"date": stamp, "region": region, "level": str(level), "at": at, "said": said} for region, level in levels.items()]
        write_table(cfg.data_dir, "soreness", sorted(rows, key=lambda r: (r.get("date") or "", r.get("region") or "")))
    return {"ok": True, "date": stamp, "at": at, "levels": levels, "said": said}


def report_from_browser(cfg, request: Any, now: Optional[datetime] = None) -> Dict[str, Any]:
    """POST /api/sore: {"levels": {"left_thigh_back": 2, ...}, "said": "..."} — the regions said, or answered."""
    if not isinstance(request, dict) or set(request) - {"levels", "said", "parsed_by"}:
        raise CheckinError("send levels, and optionally said and parsed_by")
    now = now or datetime.now(cfg.tz)
    return report(cfg, now, check(request.get("levels"), keep_zero=True), request.get("said") or "")


def check_trained(regions: Any, note: Any) -> Tuple[List[str], str]:
    if not isinstance(regions, (list, tuple)) or not all(isinstance(r, str) for r in regions):
        raise CheckinError("regions must be a list of region names")
    unknown = [r for r in regions if r not in SORE_REGIONS]
    if unknown:
        raise CheckinError(f"unknown region {unknown[0]!r}; one of {', '.join(SORE_REGIONS)}")
    if note is not None and not isinstance(note, str):
        raise CheckinError("note must be text")
    note = " ".join((note or "").split())
    if len(note) > NOTE_MAX:
        raise CheckinError(f"a note can be at most {NOTE_MAX} characters")
    return [r for r in SORE_REGIONS if r in regions], note


def parse_start(text: Any, now: datetime) -> datetime:
    try:
        start = datetime.fromisoformat(str(text)).replace(second=0, microsecond=0, tzinfo=None)
    except ValueError:
        raise CheckinError("start must be a date and time, YYYY-MM-DDTHH:MM") from None
    if start > now.replace(tzinfo=None):
        raise CheckinError("a workout cannot start after now")
    return start


def save_trained(cfg, start: datetime, regions: Sequence[str], note: str) -> Dict[str, Any]:
    """Write what one workout trained (replacing that workout's row), holding the write lock the importers hold."""
    stamp = start.strftime("%Y-%m-%dT%H:%M")
    with state.write_lock(cfg):
        rows = [r for r in _rows(Path(cfg.data_dir) / TABLES["workout_notes"].filename)
                if (r.get("start") or "").strip()[:16] != stamp]
        rows.append({"start": stamp, "regions": " ".join(regions), "note": note})
        write_table(cfg.data_dir, "workout_notes", sorted(rows, key=lambda r: r.get("start") or ""))
    return {"ok": True, "start": stamp, "regions": list(regions), "note": note}


def trained_from_browser(cfg, request: Any, now: Optional[datetime] = None) -> Dict[str, Any]:
    """What a workout trained, sent by the prompt: {"start": "2026-10-12T17:44", "regions": ["torso"], "note": "..."}."""
    if not isinstance(request, dict):
        raise CheckinError("expected a JSON object")
    start = parse_start(request.get("start"), now or datetime.now())
    regions, note = check_trained(request.get("regions", []), request.get("note"))
    return save_trained(cfg, start, regions, note)


def from_browser(cfg, request: Any, now: Optional[datetime] = None) -> Dict[str, Any]:
    """A check-in sent by the Recovery page: {"date": "YYYY-MM-DD", "levels": {"torso": 2, ...}, "feel": 5}."""
    if not isinstance(request, dict):
        raise CheckinError("expected a JSON object")
    today = (now or datetime.now()).date()
    day = parse_day(request.get("date"), today)
    levels = None if "levels" in request and request["levels"] is None else check(request.get("levels", {}))
    return save(cfg, day, levels, check_feel(request.get("feel")), check_energy(request.get("energy")))


def run(args: Any, cfg) -> int:
    """`healthaio checkin [--date D] [--feel 2|5|8] REGION=LEVEL ...` (no pairs: nothing sore)."""
    try:
        today = datetime.now(cfg.tz).date() if getattr(cfg, "tz", None) else date.today()
        day = parse_day(args.date or today.isoformat(), today)
        levels: Dict[str, Any] = {}
        for pair in args.levels:
            region, _, level = pair.partition("=")
            try:
                levels[region] = int(level)
            except ValueError:
                raise CheckinError(f"{pair!r}: expected REGION=LEVEL, e.g. left_calf=2") from None
        result = save(cfg, day, check(levels), check_feel(args.feel), check_energy(getattr(args, "energy", None)))
    except CheckinError as error:
        print(f"healthaio checkin: {error}")
        return 2
    sore = ", ".join(f"{r} {lv}" for r, lv in result["levels"].items()) or "nothing sore"
    feel = f", feeling {result['feel']}" if result["feel"] is not None else ""
    energy = f", energy {result['energy']}/5" if result["energy"] is not None else ""
    print(f"{result['date']}: {sore}{feel}{energy}")
    return 0


def run_trained(args: Any, cfg) -> int:
    """`healthaio trained --start S [--note TEXT] [REGION ...]` (no regions: the note's words choose them)."""
    try:
        now = datetime.now(cfg.tz).replace(tzinfo=None) if getattr(cfg, "tz", None) else datetime.now()
        start = parse_start(args.start, now)
        regions, note = check_trained(args.regions or regions_in(args.note or ""), args.note)
        result = save_trained(cfg, start, regions, note)
    except CheckinError as error:
        print(f"healthaio trained: {error}")
        return 2
    print(f"{result['start']}: {', '.join(result['regions']) or 'no regions'}{f' ({note})' if note else ''}")
    return 0
