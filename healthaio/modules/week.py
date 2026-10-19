"""Week: seven days of calendar, deadlines and training, plus how heavy the weeks around it are for body and mind
(the Body & mind load payload, modules/load.py, which used to be a page of its own)."""
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from ..context import Context, iso
from . import plans

AHEAD_WEEKS = 6
SOON_DAYS = 21


def monday(day: date) -> date:
    return day - timedelta(days=day.weekday())


def _deadline(d: Dict[str, Any], today: date) -> Dict[str, Any]:
    return {"due": iso(d["due"]), "title": d["title"], "group": d.get("group"), "weight_pct": d.get("weight_pct"),
            "status": d.get("status") or "todo", "note": d.get("note"), "days_left": (d["due"].date() - today).days}


def build(ctx: Context, day: Optional[str] = None) -> Dict[str, Any]:
    from . import load as load_page  # imported here: load takes monday() from this module
    picked = date.fromisoformat(day) if day else ctx.today
    start = monday(picked)
    today = ctx.today
    body = ctx.store.by_date("body_daily")
    events = ctx.store.rows("events")
    deadlines = ctx.store.rows("deadlines")
    workouts = ctx.store.rows("workouts")
    days: List[Dict[str, Any]] = []
    for k in range(7):
        d = start + timedelta(days=k)
        row = body.get(d) or {}
        actual = None
        if d <= today and row:
            actual = {"sleep_min": row.get("sleep_min"), "workout_min": row.get("workout_min"),
                      "workout_type": row.get("workout_type"), "complete": row.get("complete") is not False}
        days.append({
            "date": iso(d), "is_today": d == today, "past": d < today,
            "events": [{"start": iso(e["start"]), "end": iso(e["end"]), "title": e["title"], "kind": e["kind"],
                        "location": e.get("location")} for e in sorted(events, key=lambda e: e["start"]) if e["start"].date() == d],
            "deadlines": [_deadline(x, today) for x in deadlines if x["due"].date() == d],
            "training": plans.training_for(ctx.cfg, d), "actual": actual,
            "workouts": [{"start": iso(w["start"]), "end": iso(w["end"]), "type": w["type"],
                          "minutes": (w["end"] - w["start"]).total_seconds() / 60}
                         for w in sorted(workouts, key=lambda w: w["start"]) if w["start"].date() == d],
        })
    load = []
    first = monday(today)
    for w in range(AHEAD_WEEKS):
        ws = first + timedelta(days=7 * w)
        items = [_deadline(x, today) for x in deadlines if ws <= x["due"].date() < ws + timedelta(days=7)]
        items.sort(key=lambda x: x["due"])
        load.append({"week_start": iso(ws), "items": items,
                     "total_pct": sum(x["weight_pct"] or 0 for x in items)})
    open_items = [x for x in deadlines if (x.get("status") or "todo") == "todo"]
    upcoming = sorted((_deadline(x, today) for x in open_items if 0 <= (x["due"].date() - today).days <= SOON_DAYS),
                      key=lambda x: x["due"])
    later = sorted((_deadline(x, today) for x in open_items if (x["due"].date() - today).days > SOON_DAYS),
                   key=lambda x: x["due"])
    overdue = sorted((_deadline(x, today) for x in open_items if x["due"].date() < today), key=lambda x: x["due"])
    return {"page": "week", "week_start": iso(start), "week_end": iso(start + timedelta(days=6)), "today": iso(today),
            "now": iso(ctx.now), "is_current": start == monday(today), "days": days, "load": load,
            "upcoming": upcoming, "later": later, "overdue": overdue, "body_mind": load_page.build(ctx, day)}
