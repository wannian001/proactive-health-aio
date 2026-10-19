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


MIN_ANSWERED = 2  # an activity is put forward by name once you have said how it went at least this often


def milestones(ctx):
    """Something done today worth a reward: a deadline handed in (due yesterday or today and marked submitted or
    done) or a workout of 20 minutes or more. Rest is never earned this way; this only adds a nicer suggestion."""
    out = []
    if any(d["due"].date() in (ctx.today, ctx.today - timedelta(days=1)) and d.get("status") in ("submitted", "done")
           for d in ctx.store.rows("deadlines")):
        out.append("deadline")
    if any(w["start"].date() == ctx.today and w["start"] <= ctx.now and (w["end"] - w["start"]) >= timedelta(minutes=20)
           for w in ctx.store.rows("workouts")):
        out.append("workout")
    return out


def screens_heavy(ctx):
    """Yesterday's entertainment & social over the plan's cap: rewards then lean away from screens."""
    from .time import stim_series
    limit = ctx.cfg.screen.entertainment_max_hours
    fun = stim_series(ctx)["fun"].get(ctx.today - timedelta(days=1))
    return limit is not None and fun is not None and fun > limit * 60


def suggest(ctx, key, tried_rows):
    """One activity by name, from your own answers: after a hard spell (the body below normal, or you said you're
    tired), the one that most often left you better; after something done (milestones), the one that most often left
    you better and glad, away from screens if yesterday's were heavy. None until an activity has MIN_ANSWERED answers."""
    known = [b for b in tried_rows if b["activity"] in restore_log.ACTIVITIES and b["answered"] >= MIN_ANSWERED]
    if key in ("signals", "trend", "reported", "gentler"):
        best = max(known, key=lambda b: (b["better"] / b["answered"], b["times"]), default=None)
        if best and best["better"] / best["answered"] >= 0.5:
            return {"why": "restore", "activity": best["activity"], "better": best["better"], "glad": best["glad"], "answered": best["answered"]}
        return None
    done = milestones(ctx)
    if not done or key in ("active", "quiet"):
        return None
    pool = [b for b in known if not (b["activity"] == "play" and screens_heavy(ctx))]
    best = max(pool, key=lambda b: ((b["better"] + b["glad"]) / (2 * b["answered"]), b["times"]), default=None)
    if best and (best["better"] + best["glad"]) / (2 * best["answered"]) >= 0.5:
        return {"why": "reward", "for": done, "activity": best["activity"], "better": best["better"], "glad": best["glad"], "answered": best["answered"]}
    return None


def tried(sessions):
    """What each activity has done for you, from your own reflections: finished sessions, how many you said how it went,
    how many left you better, how many you were glad of (and how many left you more tired). Ranked by the share that
    were better or glad among the ones you answered (share); fewer than MIN_ANSWERED answers come after. Unanswered is
    unknown, never "it didn't help"."""
    by = {}
    for s in sessions:
        if s["status"] != "finished":
            continue
        b = by.setdefault(s["activity"], {"activity": s["activity"], "times": 0, "answered": 0, "better": 0, "worse": 0, "glad": 0,
                                          "last": s["started_at"]})
        b["times"] += 1
        b["last"] = max(b["last"], s["started_at"])
        f = s.get("feedback") or {}
        if f.get("change") or f.get("enjoyment"):
            b["answered"] += 1
            b["better"] += f.get("change") == "better"
            b["worse"] += f.get("change") == "worse"
            b["glad"] += f.get("enjoyment") == "yes"
    return sorted(by.values(), key=lambda b: (share(b), b["times"]), reverse=True)


def share(b):
    """Better or glad, among the times you answered; -1 below MIN_ANSWERED answers (too few to put it ahead)."""
    return (b["better"] + b["glad"]) / (2 * b["answered"]) if b["answered"] >= MIN_ANSWERED else -1


def build(ctx, day=None):
    current = restore_log.replay(restore_log.read(ctx.cfg))
    rows = tried(current["sessions"])
    s = situation(ctx, current)
    s["suggest"] = suggest(ctx, s["key"], rows)
    # the library in the order your own answers put it (better after, then glad), untried ones after, as listed
    score = {b["activity"]: (share(b), b["times"]) for b in rows}
    order = sorted(restore_log.ACTIVITIES, key=lambda a: score.get(a, (-1, 0)), reverse=True)
    return {"page": "restore", "today": iso(ctx.today), "demo": ctx.cfg.demo,
            "situation": s, "active": current["active"],
            "sessions": [x for x in current["sessions"] if x["status"] != "removed"][:30], "tried": rows,
            "rewards": [r for r in current["rewards"] if r["status"] == "planned"] +
                       [r for r in current["rewards"] if r["status"] != "planned"][:30],
            "activities": order}
