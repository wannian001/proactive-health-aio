"""Where it feels tight: the latest report, the moves for it, what you did, and the next day's question.

The report is said on Recovery's "How you are right now" card (care_log.py): regions, how each feels, optionally in
your own words. From it:
- moves: routines.for_regions, at most three, unless a warning sign was ticked (then none, and the line on seeing
  someone) or a region was called painful (then the line comes first and the moves are the gentlest only);
- maybe sitting: when the regions are the ones long sitting tends to tighten and a long stretch at the computer
  (sitting.LONG_MIN) came the day of the report or the day before. Said as "may be", never as a cause;
- the next day: one question per reported region, "how is it now?" (better / same / worse), until answered.
"""
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from .. import care_log, routines
from ..context import Context, iso

SITTING_REGIONS = ("neck", "chest", "upper_back", "low_back", "hip_front")
ASK_DAYS = 2  # a report is asked about the next day, and the day after if still unanswered


def _events(ctx: Context) -> List[Dict[str, Any]]:
    try:
        return care_log.read(ctx.cfg)
    except ValueError:
        return []


def _local_day(ctx: Context, at: str) -> date:
    from .. import state
    t = state.parse_iso(at)
    return (t.astimezone(ctx.cfg.tz) if ctx.cfg.tz and t.tzinfo else t).date()


def latest_report(ctx: Context, day: date) -> Optional[Dict[str, Any]]:
    reports = [e for e in _events(ctx) if e["op"] == "report" and _local_day(ctx, e["at"]) <= day]
    return reports[-1] if reports else None


def tight_today(ctx: Context) -> List[str]:
    r = latest_report(ctx, ctx.today)
    return list(r["tight"]) if r and _local_day(ctx, r["at"]) == ctx.today else []


def moves(report: Dict[str, Any]) -> Dict[str, Any]:
    if report["signs"]:
        return {"routines": [], "stop_first": True, "blocked": True}
    painful = [r for r, f in report["tight"].items() if f == "pain"]
    picks = routines.for_regions(report["tight"], 3)
    if painful:  # only the one-minute moves, and the warning line above them
        picks = [i for i in picks if routines.BY_ID[i]["minutes"] <= 1] or picks[:1]
    return {"routines": picks, "stop_first": bool(painful), "blocked": False}


def maybe_sitting(ctx: Context, report: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    from . import sitting
    if not any(r in SITTING_REGIONS for r in report["tight"]):
        return None
    day = _local_day(ctx, report["at"])
    for d in (day, day - timedelta(days=1)):
        s = sitting.day_summary(ctx, d)
        if s and s["longest"] >= sitting.LONG_MIN:
            return {"date": iso(d), "longest": s["longest"], "long": s["long"]}
    return None


def build(ctx: Context, day: Optional[date] = None) -> Dict[str, Any]:
    end = day or ctx.today
    events = [e for e in _events(ctx) if _local_day(ctx, e["at"]) <= end]
    report = next((e for e in reversed(events) if e["op"] == "report"), None)
    answered = {(e["ref"], e["region"]) for e in events if e["op"] == "answer"}
    ask = []
    if report:
        age = (end - _local_day(ctx, report["at"])).days
        if 1 <= age <= ASK_DAYS:
            ask = [{"ref": report["id"], "region": r, "feel": f} for r, f in report["tight"].items() if (report["id"], r) not in answered]
    done_today = [{"routine": e["routine"], "why": e["why"], "at": e["at"]} for e in events
                  if e["op"] == "done" and _local_day(ctx, e["at"]) == end]
    fresh = report and (end - _local_day(ctx, report["at"])).days <= 1
    return {"report": {k: report[k] for k in ("id", "at", "tight", "said", "signs", "cause", "parsed_by")} if fresh else None,
            "moves": moves(report) if fresh else None, "maybe_sitting": maybe_sitting(ctx, report) if fresh else None,
            "ask": ask, "done_today": done_today,
            "answers": [{"region": e["region"], "change": e["change"], "at": e["at"]} for e in events if e["op"] == "answer"][-10:]}
