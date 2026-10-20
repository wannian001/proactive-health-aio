"""The data contract: every table Health AIO reads, defined in one place.

All tables are UTF-8 CSV files with a header row, kept in the data directory
named in ``healthaio.toml``. Importers write them; modules only read them.
``docs/DATA_FORMAT.md`` is generated from this file (``python -m healthaio schema --markdown``).

Conventions
- ``date``: local calendar day, ``YYYY-MM-DD``.
- ``datetime``: local wall-clock time without offset, ``YYYY-MM-DDTHH:MM`` (seconds optional).
  The timezone is the one in ``healthaio.toml``. One exception: ``sleep_start`` / ``sleep_end`` from
  Apple Health are in the zone you slept in, so a night abroad reads as you lived it.
- Minutes are real minutes: on the day clocks go forward the skipped hour is not counted, and a
  record that runs through the repeated hour when they go back counts it twice (23- and 25-hour days).
- Empty cell = unknown. Unknown is never read as zero.
- A sleep belongs to the day you woke up.
"""
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

Parser = Callable[[str], Any]


def _date(text: str) -> date:
    return date.fromisoformat(text)


def _datetime(text: str) -> datetime:
    value = datetime.fromisoformat(text)
    if value.tzinfo is not None:
        raise ValueError("datetime must be local wall-clock time without an offset")
    return value


def _float(text: str) -> float:
    value = float(text)
    if value != value or value in (float("inf"), float("-inf")):
        raise ValueError("not a finite number")
    return value


def _flag(text: str) -> bool:
    lowered = text.strip().lower()
    if lowered in ("1", "true", "yes"):
        return True
    if lowered in ("0", "false", "no"):
        return False
    raise ValueError("expected 1/0")


def _text(text: str) -> str:
    return text


TYPES: Dict[str, Parser] = {"date": _date, "datetime": _datetime, "number": _float,
                            "flag": _flag, "text": _text}


@dataclass(frozen=True)
class Column:
    name: str
    type: str
    doc: str
    required: bool = False
    choices: Tuple[str, ...] = ()
    low: Optional[float] = None
    high: Optional[float] = None

    def parse(self, raw: str) -> Any:
        if raw is None or raw.strip() == "":
            if self.required:
                raise ValueError(f"{self.name} is required")
            return None
        value = TYPES[self.type](raw.strip())
        if self.choices and value not in self.choices:
            raise ValueError(f"{self.name} must be one of {', '.join(self.choices)}")
        if self.low is not None and value < self.low:
            raise ValueError(f"{self.name} below {self.low}")
        if self.high is not None and value > self.high:
            raise ValueError(f"{self.name} above {self.high}")
        return value


@dataclass(frozen=True)
class Table:
    name: str
    doc: str
    key: Tuple[str, ...]
    columns: Tuple[Column, ...]
    sources: Tuple[str, ...] = field(default_factory=tuple)
    interval: Tuple[str, ...] = ()  # (start, end) columns of a time span; end must be after start

    def interval_problem(self, row: Dict[str, Any]) -> Optional[str]:
        if not self.interval:
            return None
        start, end = (row.get(c) for c in self.interval)
        if start is not None and end is not None and end <= start:
            return f"{self.interval[1]} must be after {self.interval[0]}"
        return None

    @property
    def filename(self) -> str:
        return f"{self.name}.csv"

    def column(self, name: str) -> Column:
        for col in self.columns:
            if col.name == name:
                return col
        raise KeyError(name)


SCREEN_CATEGORIES = ("work", "learning", "communication", "entertainment", "social", "other")
EVENT_KINDS = ("class", "work", "training", "personal", "other")
DEADLINE_STATUS = ("todo", "submitted", "done")
MEALS = ("breakfast", "lunch", "dinner", "snack", "drink")
EFFORT_SOURCES = ("rated", "estimated")
FEELINGS = (2, 5, 8)  # the Recovery page's three answers to "how do you feel this morning?"
# Where it can be sore: places you can feel and name, a little finer than a whole limb. Most have a left and a right;
# thighs and calves have four faces. Each is area[_side][_face] (sore_region builds them), in this order.
SORE_AREAS = (  # area, sides, faces
    ("neck", (), ("front", "back")),            # the back of the neck has a left and a right half: neck_back_left
    ("shoulder", ("left", "right"), ("front", "back")),
    ("chest", (), ()), ("upper_back", (), ()), ("abs", (), ()), ("low_back", (), ()),
    ("glute", ("left", "right"), ()),
    ("upper_arm", ("left", "right"), ()),
    ("thigh", ("left", "right"), ("front", "back", "outer", "inner")),
    ("calf", ("left", "right"), ("front", "back", "outer", "inner")),
)


def sore_region(area: str, side: Optional[str] = None, face: Optional[str] = None) -> str:
    """The region id of an area, side and face: left_thigh_back, chest, neck_front, neck_back_left."""
    if area == "neck":
        return "neck_front" if face == "front" else f"neck_back_{side}"
    return "_".join(x for x in (side, area, face) if x)


SORE_REGIONS = tuple(
    ["neck_front", "neck_back_left", "neck_back_right"]
    + [sore_region(a, s, f) for a, sides, faces in SORE_AREAS if a != "neck"
       for s in (sides or (None,)) for f in (faces or (None,))])
# the seven of the first body figure (the PMData wellness check-in's areas): older rows keep them and are shown as
# they were; nothing new is written with them (left_upper_arm and right_upper_arm are still current)
LEGACY_REGIONS = ("head", "torso", "pelvis", "left_calf", "right_calf")
ALL_SORE_REGIONS = SORE_REGIONS + LEGACY_REGIONS
MAIN_MEALS = ("breakfast", "lunch", "dinner")

TABLES: Dict[str, Table] = {t.name: t for t in (
    Table(
        name="body_daily",
        doc="One row per day of body measurements, usually from a watch or phone.",
        key=("date",),
        sources=("Apple Health export (healthaio import apple-health)", "any CSV with these columns"),
        columns=(
            Column("date", "date", "The day. Sleep is filed under the day you woke up.", required=True),
            Column("sleep_min", "number", "Minutes asleep in the main sleep that ended this day.", low=0, high=1440),
            Column("in_bed_min", "number", "Minutes in bed for the same sleep.", low=0, high=1440),
            Column("sleep_start", "datetime", "When you fell asleep (local time)."),
            Column("sleep_end", "datetime", "When you woke up (local time)."),
            Column("hrv_ms", "number", "Heart-rate variability (SDNN or RMSSD, but keep one kind), ms.", low=1, high=400),
            Column("resting_hr", "number", "Resting heart rate, beats per minute.", low=20, high=200),
            Column("vo2max", "number", "Cardio fitness (VO2 max), mL per kg per minute, as Apple Watch estimates it on some "
                   "outdoor walks, runs and hikes; most days have none.", low=10, high=90),
            Column("steps", "number", "Steps that day.", low=0),
            Column("exercise_min", "number", "Minutes of exercise (Apple 'Exercise' ring or similar).", low=0, high=1440),
            Column("workout_min", "number", "Minutes of logged workouts. 0 means rest day; empty means unknown.", low=0, high=1440),
            Column("workout_type", "text", "Main workout that day, free text (e.g. strength, run)."),
            Column("active_kcal", "number", "Active energy burned that day, kcal (Apple's Move ring).", low=0, high=10000),
            Column("basal_kcal", "number", "Resting energy that day, kcal (what the body burns at rest).", low=0, high=10000),
            Column("weight_kg", "number", "Body weight, kg.", low=20, high=400),
            Column("waist_cm", "number", "Waist, cm.", low=30, high=250),
            Column("complete", "flag", "1 if the day was over when the data was exported; 0 if the export happened "
                                         "mid-day (then steps and minutes are not compared with your normal)."),
        ),
    ),
    Table(
        name="workouts",
        doc="Each workout with its start and end, e.g. from Apple Fitness or a watch. The day ring and Review use the "
            "times; body_daily.workout_min is the daily total. A workout paused along the way can be one row per "
            "stretch of moving (the Apple Health importer writes it so), so the minutes are the time spent moving. "
            "`end` must be after `start`.",
        key=("start", "type"),
        interval=("start", "end"),
        sources=("Apple Health export, which includes Apple Fitness and Workout app sessions (healthaio import apple-health)",
                 "Strava, Garmin or any CSV with these columns"),
        columns=(
            Column("start", "datetime", "Start (local time).", required=True),
            Column("end", "datetime", "End (local time).", required=True),
            Column("type", "text", "What kind of workout, e.g. strength training, running.", required=True),
            Column("source", "text", "Which app or device recorded it."),
            Column("kcal", "number", "Active energy for the workout, kcal.", low=0),
            Column("avg_hr", "number", "Average heart rate during the workout, beats per minute.", low=30, high=230),
            Column("effort", "number", "How hard it was, 1 (easy) to 10 (all out): your own rating in the Fitness or Workout "
                   "app, otherwise the watch's estimate. On every row of a paused workout.", low=1, high=10),
            Column("effort_source", "text", "Whose number the effort is: rated by you, or estimated by the watch.",
                   choices=EFFORT_SOURCES),
        ),
    ),
    Table(
        name="meals",
        doc="What you ate, one row per meal or snack, e.g. from a food-logging app that writes to Apple Health. "
            "A day with no rows was not logged: it is unknown, never zero calories. A day counts as logged once "
            "it has at least two main meals (breakfast, lunch, dinner); with fewer it is shown but not averaged. "
            "A meal before 4 am counts for the day before; a time of exactly 00:00 is read as a date without a time "
            "(what a date-only export gives) and counts for its own day.",
        key=("time", "meal"),
        sources=("Apple Health export, which holds what MyFitnessPal, Lose It!, Cronometer and similar apps "
                 "write there (healthaio import apple-health)", "a food app's CSV export (healthaio import csv meals)"),
        columns=(
            Column("time", "datetime", "When you started eating (local time).", required=True),
            Column("meal", "text", "Which meal it was.", required=True, choices=MEALS),
            Column("title", "text", "What it was, in your own words."),
            Column("kcal", "number", "Energy, kcal.", low=0, high=6000),
            Column("protein_g", "number", "Protein, grams.", low=0, high=500),
            Column("carbs_g", "number", "Carbohydrate, grams.", low=0, high=1000),
            Column("fat_g", "number", "Fat, grams.", low=0, high=500),
            Column("fiber_g", "number", "Fibre, grams.", low=0, high=200),
            Column("source", "text", "Which app it came from."),
        ),
    ),
    Table(
        name="self_report",
        doc="How you said you felt. Optional; pages show a prompt when it is empty. `feel` is the Recovery page's "
            "morning check-in; energy and focus are typed by hand or written by an assistant.",
        key=("date",),
        sources=("typed by hand", "an assistant that writes this file for you"),
        columns=(
            Column("date", "date", "The day.", required=True),
            Column("energy", "number", "Body energy, 0 (drained) to 5 (full).", low=0, high=5),
            Column("focus", "number", "Mental focus, 0 to 5.", low=0, high=5),
            Column("note", "text", "One line in your own words."),
            Column("feel", "number", "This morning, in one of three answers: 2 not recovered, 5 so-so, 8 recovered "
                   "(the Recovery page writes it).", low=0, high=10),
        ),
    ),
    Table(
        name="soreness",
        doc="Where it was sore on a day and how much, one row per region. You say it when you feel it (Recovery's "
            "\"Where does it hurt?\", in a sentence, typed or spoken), and the next days the page asks about it "
            "until you say it is fine (level 0). A region without a row that day was not said: unknown, never "
            "\"not sore\". Older files may hold a morning check-in's region `none` (nothing sore) and the first "
            "figure's seven regions (head, torso, pelvis, left_calf, right_calf, and the upper arms); they are read "
            "as they are. You can also write it by hand or import a CSV.",
        key=("date", "region"),
        sources=("the Recovery page's body figure", "typed by hand", "any CSV with these columns"),
        columns=(
            Column("date", "date", "The morning.", required=True),
            Column("region", "text", "Which region (an older file may also hold the first figure's "
                   + ", ".join(LEGACY_REGIONS) + ", or none).", required=True, choices=ALL_SORE_REGIONS + ("none",)),
            Column("level", "number", "1 a little, 2 clearly sore, 3 very sore; 0 fine again (or with region none).",
                   required=True, low=0, high=3),
            Column("at", "datetime", "When it was said (optional)."),
            Column("said", "text", "What you said, in your own words (optional)."),
        ),
    ),
    Table(
        name="workout_notes",
        doc="What a workout trained: the regions (the soreness regions) and a note in your own words (typed, or "
            "dictated with the phone keyboard's microphone). After a strength session or a hard one (effort 7 or more) "
            "the pages ask once. A row with no regions and no note means you chose not to say.",
        key=("start",),
        sources=("the after-workout prompt on any page", "healthaio trained", "typed by hand"),
        columns=(
            Column("start", "datetime", "The workout's start, as in workouts.csv.", required=True),
            Column("regions", "text", "The regions trained, separated by spaces (the soreness regions)."),
            Column("note", "text", "What you trained, in your own words, e.g. bench, rows, curls."),
        ),
    ),
    Table(
        name="screen_sessions",
        doc="Foreground app sessions across your devices. Overlaps between devices are allowed; "
            "Health AIO counts wall-clock time once, preferring the device order in healthaio.toml "
            "(the Stimulation page's devices-at-once tab counts each device on its own). "
            "`end` must be after `start`.",
        key=("start", "device", "app"),
        interval=("start", "end"),
        sources=("macOS Screen Time / Biome (healthaio import macos-screentime)", "RescueTime or ActivityWatch CSV",
                 "any CSV with these columns"),
        columns=(
            Column("start", "datetime", "Session start (local time).", required=True),
            Column("end", "datetime", "Session end (local time).", required=True),
            Column("device", "text", "Device name, e.g. laptop, phone, tablet.", required=True),
            Column("app", "text", "App name or website domain.", required=True),
            Column("category", "text", "What kind of use it was.", required=True, choices=SCREEN_CATEGORIES),
        ),
    ),
    Table(
        name="events",
        doc="Calendar blocks: classes, work shifts, planned training.",
        key=("start", "title"),
        sources=("any .ics calendar (healthaio import ics)", "any CSV with these columns"),
        columns=(
            Column("start", "datetime", "Start (local time).", required=True),
            Column("end", "datetime", "End (local time).", required=True),
            Column("title", "text", "What it is.", required=True),
            Column("kind", "text", "Type of block.", required=True, choices=EVENT_KINDS),
            Column("location", "text", "Where."),
        ),
    ),
    Table(
        name="deadlines",
        doc="Things due on a date: assignments, exams, milestones.",
        key=("due", "title"),
        sources=("typed by hand", "a course or project tracker export"),
        columns=(
            Column("due", "datetime", "When it is due (local time). Use 23:59 if only the day is known.", required=True),
            Column("title", "text", "What is due.", required=True),
            Column("group", "text", "Course or project it belongs to."),
            Column("weight_pct", "number", "Share of the course grade, percent. Empty if it is not graded.", low=0, high=100),
            Column("status", "text", "Where it stands.", choices=DEADLINE_STATUS),
            Column("note", "text", "Format, length, group size, anything you want to see next to it."),
        ),
    ),
)}


def describe_markdown() -> str:
    """The reference page in docs/DATA_FORMAT.md, generated so it never drifts from the code."""
    lines: List[str] = [
        "# Data format",
        "",
        "<!-- generated by `python -m healthaio schema --markdown`; edit healthaio/schema.py instead -->",
        "",
        __doc__.split("\n\n", 1)[1].strip(),
        "",
    ]
    for table in TABLES.values():
        lines += [f"## `{table.filename}`", "", table.doc, "",
                  f"Key: {', '.join('`%s`' % k for k in table.key)}. "
                  f"Typical sources: {'; '.join(table.sources) or 'any CSV'}.", "",
                  "| column | type | required | meaning |", "|---|---|---|---|"]
        for col in table.columns:
            extra = f" One of: {', '.join('`%s`' % c for c in col.choices)}." if col.choices else ""
            lines.append(f"| `{col.name}` | {col.type} | {'yes' if col.required else ''} | {col.doc}{extra} |")
        lines.append("")
    return "\n".join(lines)
