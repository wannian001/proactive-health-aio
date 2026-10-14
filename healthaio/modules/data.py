"""Data sources: where the data comes from, how it gets to this computer, what it is stored as and which pages read
it; how much has built up; and, folded away, what arrived each day and which rows could not be read.

The page is written for someone looking at how the app works (SOURCES: four sources, each with what it records, the
way it travels, the files it lands in and the pages that read them), with the numbers of the data as it stands (days,
rows, size on disk, each file's span). The daily check, each stream under the device it comes from with 90 days of
arrivals, is still there for the person whose data it is, below. The watch, the phone and the Mac reach this computer
through the iPhone app and the Mac app; the page says when each last did, outside the demo."""
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from .. import capture, state
from ..context import Context, iso
from ..schema import TABLES
from .food import food_days

DAYS = 90
DEVICES = ("watch", "phone", "mac", "manual")
# where each kind of data comes from: what it records, the files it lands in and the pages that read them
SOURCES = (
    {"key": "watch", "signals": ("sleep", "hrv", "resting_hr", "vo2max", "workouts"), "files": ("body_daily", "workouts"),
     "pages": ("recovery", "sleep", "drain", "body", "exercise")},
    {"key": "phone", "signals": ("steps", "weight", "food"), "files": ("body_daily", "meals"), "pages": ("exercise", "food", "body")},
    {"key": "mac", "signals": ("screen",), "files": ("screen_sessions",), "pages": ("today", "time", "drain")},
    {"key": "manual", "signals": ("checkin", "trained", "calendar", "goals"),
     "files": ("self_report", "soreness", "workout_notes", "events", "deadlines"), "pages": ("recovery", "week", "load", "goals", "followup")},
)


def _day(value: Any) -> Optional[date]:
    if isinstance(value, datetime):
        return value.date()
    return value if isinstance(value, date) else None
STREAMS = [  # key, table, column (None = any row that day), stale after N days, the device it comes from
    ("sleep", "body_daily", "sleep_min", 2, "watch"),
    ("hrv", "body_daily", "hrv_ms", 2, "watch"),
    ("resting_hr", "body_daily", "resting_hr", 2, "watch"),
    ("exercise", "body_daily", "exercise_min", 2, "watch"),
    ("vo2max", "body_daily", "vo2max", 30, "watch"),  # only on outdoor walks, runs and hikes: weeks can pass without one
    ("steps", "body_daily", "steps", 2, "phone"),
    ("weight", "body_daily", "weight_kg", 7, "phone"),
    ("food", "meals", None, 3, "phone"),  # a full day = at least two main meals logged; one meal = partial
    ("screen", "screen_sessions", None, 2, "mac"),
    ("sore", "soreness", None, 7, "manual"),
    ("self", "self_report", None, 7, "manual"),
]


def build(ctx: Context, day: Optional[str] = None) -> Dict[str, Any]:
    today = ctx.today
    first = today - timedelta(days=DAYS - 1)
    body = ctx.store.by_date("body_daily")
    screen = ctx.screen_days()
    selfr = ctx.store.by_date("self_report")
    sore = {r["date"] for r in ctx.store.rows("soreness")}
    meals = food_days(ctx, today) if ctx.store.load("meals").present else {}
    streams = []
    for key, table, column, stale_after, device in STREAMS:
        if table in ("meals", "self_report", "soreness") and not ctx.store.load(table).present:
            continue  # optional: someone who does not log food, soreness or how the day felt gets no "never arrived" row
        marks: List[str] = []
        last: Optional[date] = None
        for k in range(DAYS):
            d = first + timedelta(days=k)
            if table == "body_daily":
                row = body.get(d)
                v = row.get(column) if row else None
                mark = "0" if v is None else ("p" if row.get("complete") is False and column == "steps" else "1")
            elif table == "screen_sessions":
                sd = screen.get(d)
                mark = "1" if sd and sd.total >= 60 else ("p" if sd else "0")
            elif table == "meals":
                x = meals.get(d)
                mark = "0" if x is None else ("1" if x["main"] >= 2 else "p")
            elif table == "soreness":
                mark = "1" if d in sore else "0"
            else:
                mark = "1" if d in selfr else "0"
            marks.append(mark)
        if table == "body_daily":
            have = [d for d, r in body.items() if r.get(column) is not None]
        elif table == "screen_sessions":
            have = list(screen)
        elif table == "meals":
            have = list(meals)
        elif table == "soreness":
            have = list(sore)
        else:
            have = list(selfr)
        last = max(have) if have else None
        behind = (today - last).days if last else None
        streams.append({"key": key, "table": table, "device": device, "marks": "".join(marks), "last": iso(last), "days_behind": behind,
                        "stale_after": stale_after,
                        "status": "missing" if last is None else ("stale" if behind > stale_after else "ok"),
                        "days_with_data": marks.count("1")})
    tables = []
    for name, table in TABLES.items():
        loaded = ctx.store.load(name)
        days = [d for d in (_day(r.get(table.key[0])) for r in loaded.rows) if d is not None]
        path = Path(ctx.cfg.data_dir) / table.filename
        tables.append({"name": name, "file": table.filename, "present": loaded.present, "rows": len(loaded.rows),
                       "first": iso(min(days)) if days else None, "last": iso(max(days)) if days else None,
                       "bytes": path.stat().st_size if loaded.present and path.is_file() else 0,
                       "modified": iso(loaded.modified) if loaded.modified else None,
                       "problems": [p.as_dict() for p in loaded.problems[:12]], "problem_count": len(loaded.problems),
                       "doc": table.doc})
    present = [tb for tb in tables if tb["present"]]
    firsts = [tb["first"] for tb in present if tb["first"]]
    totals = {"tables": len(present), "rows": sum(tb["rows"] for tb in present), "bytes": sum(tb["bytes"] for tb in present),
              "first": min(firsts) if firsts else None}
    # how the data reached this computer: the iPhone app's last package and the Mac app's last collection
    receipt = None if ctx.cfg.demo else capture.last_receipt(ctx.cfg)
    collected = None if ctx.cfg.demo else state.read_json(state.folder(ctx.cfg) / "collect.json")
    return {"page": "data", "today": iso(today), "now": iso(ctx.now), "first": iso(first), "days": DAYS,
            "devices": [d for d in DEVICES if any(s["device"] == d for s in streams)],
            "carriers": {"phone": receipt.get("landed_at") if receipt else None,
                         "mac": collected.get("at") if collected else None},
            "streams": streams, "tables": tables, "totals": totals, "demo": ctx.cfg.demo,
            "sources": [{**src, "signals": list(src["signals"]), "files": list(src["files"]), "pages": list(src["pages"])} for src in SOURCES],
            "ok": all(s["status"] == "ok" for s in streams if s["key"] in ("sleep", "hrv", "screen"))}
