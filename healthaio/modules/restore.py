"""Rest & rewards: measured signals, optional feelings, one explainable next step.

No stress score, diagnosis, hormone estimate or automatic task assignment. The
same payload powers Today, Recovery, the activity library and Follow-up.
"""
from datetime import timedelta

from .. import restore_log, state
from ..context import iso

POLICY = "restore-v1"


def situation(ctx, current=None):
    from .today import recovery
    current = current if current is not None else restore_log.replay(restore_log.read(ctx.cfg))
    now = restore_log.moment(ctx.cfg, ctx.now)
    rec = recovery(ctx, ctx.today)
    fresh = rec["days_behind"] == 0
    checkin = current["checkin"]
    recent = checkin if checkin and timedelta(0) <= now - state.parse_iso(checkin["at"]) < timedelta(hours=4) else None
    # Current calendar entries are plans, never a measurement of mental strain.
    start, end = ctx.now, ctx.now + timedelta(days=3)
    events = [e for e in ctx.store.rows("events") if e["kind"] in ("class", "work") and e["end"] > start and e["start"] < end]
    intervals = sorted((max(e["start"], start), min(e["end"], end)) for e in events)
    merged = []
    for a, b in intervals:
        if merged and a <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(b, merged[-1][1]))
        else:
            merged.append((a, b))
    deadlines = [d for d in ctx.store.rows("deadlines") if start <= d["due"] < end and d.get("status") not in ("submitted", "done")]
    schedule = {"from": iso(start), "to": iso(end),
                "hours": round(sum((b-a).total_seconds() for a, b in merged) / 3600, 1) if ctx.store.load("events").present else None,
                "deadlines": len(deadlines) if ctx.store.load("deadlines").present else None}
    # The latest three recorded days, each against its own previous 28 days.
    adverse = []
    for n in range(3):
        d = ctx.today - timedelta(days=n)
        r = rec if n == 0 else recovery(ctx, d)
        if r["as_of"] == iso(d) and r["verdict"] == "low":
            adverse.append(iso(d))
    quiet = current["quiet_until"] and now < state.parse_iso(current["quiet_until"])
    body, mind, task = ((recent or {}).get(k) for k in ("body", "mind", "task"))
    last = next((s for s in current["sessions"] if s["status"] == "finished"), None)
    recent_worse = bool(last and last["feedback"] and last["feedback"].get("change") == "worse"
                        and timedelta(0) <= now - state.parse_iso(last["feedback"]["at"]) < timedelta(hours=4))
    if current["active"]:
        key = "active"
    elif quiet:
        key = "quiet"
    elif body in ("tired", "sore") or mind in ("tired", "tense"):
        key = "reported"
    elif recent_worse:
        key = "gentler"
    elif fresh and rec["verdict"] == "low":
        key = "trend" if len(adverse) >= 2 else "signals"
    elif mind == "engaged":
        key = "engaged"
    elif task == "hard":
        key = "smaller"
    elif mind == "bored" and body == "comfortable":
        key = "challenge"
    elif (schedule["deadlines"] or 0) > 0:
        key = "ahead"
    elif not fresh or sum(m["state"] is not None for m in rec["metrics"]) < 2:
        key = "unknown"
    else:
        key = "steady"
    # Nutrition is context only. Missing carbohydrate entries are not zero intake,
    # and a meal this afternoon cannot explain a measurement earlier this morning.
    meals = [m for m in ctx.store.rows("meals") if m["time"].date() == ctx.today and m["time"] <= ctx.now]
    carbs = [m["carbs_g"] for m in meals if m.get("carbs_g") is not None]
    return {"policy": POLICY, "at": now.isoformat(timespec="seconds"), "key": key,
            "recovery": {"as_of": rec["as_of"], "fresh": fresh, "verdict": rec["verdict"],
                         "metrics": [{k: m[k] for k in ("key", "value", "unit", "band", "state", "date")} for m in rec["metrics"]]},
            "adverse_days": adverse, "checkin": recent, "last_checkin": checkin,
            "schedule": schedule, "quiet_until": current["quiet_until"] if quiet else None,
            "food": {"logged_meals": len(meals), "carb_entries": len(carbs),
                     "logged_carbs_g": round(sum(carbs), 1) if carbs else None}}


def build(ctx, day=None):
    current = restore_log.replay(restore_log.read(ctx.cfg))
    return {"page": "restore", "today": iso(ctx.today), "demo": ctx.cfg.demo,
            "situation": situation(ctx, current), "active": current["active"],
            "sessions": current["sessions"][:30],
            "rewards": [r for r in current["rewards"] if r["status"] == "planned"] +
                       [r for r in current["rewards"] if r["status"] != "planned"][:30],
            "activities": list(restore_log.ACTIVITIES)}
