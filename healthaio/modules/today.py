"""Today: what is on, how recovered the body is, what yesterday's screen time went to, and what
has tended to help the next day.

Every number is structured (value, unit, band, state); the browser writes the words,
so the same payload reads in English and Chinese.
"""
import statistics
from datetime import date, datetime, time, timedelta
from typing import Any, Dict, List, Optional

from .. import stats
from ..context import FOCUS, FUN, Context, iso
from . import food as food_page
from . import plans
from . import care, sitting

SPARK_DAYS = 14
STALE_SCREEN_DAYS = 2  # the screens card looks at yesterday; more than 2 days behind means tracking stopped
RECOVERY = (("sleep", "sleep_min", "min", "higher"), ("hrv", "hrv_ms", "ms", "higher"),
            ("resting_hr", "resting_hr", "bpm", "lower"))
ACTIVITY = (("steps", "steps", "steps"), ("exercise", "exercise_min", "min"))


def metric(key: str, unit: str, better: str, values: stats.Series, day: Optional[date],
           partial: bool = False, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    value = values.get(day) if day else None
    band = None if partial or day is None else stats.typical(values, day)
    state = stats.classify(value, band)
    return {"key": key, "unit": unit, "better": better, "date": iso(day), "value": value,
            "band": band, "state": state, "tone": stats.tone(state, better), "partial": partial,
            "series": stats.window(values, day, SPARK_DAYS) if day else [], **(extra or {})}


def verdict(metrics: List[Dict[str, Any]]) -> str:
    tones = [m["tone"] for m in metrics if m["state"]]
    if not tones:
        return "unknown"
    bad, good = tones.count("bad"), tones.count("good")
    if bad >= 2:
        return "low"
    if good >= 2 and bad == 0:
        return "good"
    return "normal"


def recovery(ctx: Context, day: date) -> Dict[str, Any]:
    rows = [r for r in ctx.store.rows("body_daily") if r["date"] <= day]
    seen = max((r["date"] for r in rows if r.get("hrv_ms") is not None or r.get("sleep_min") is not None), default=None)
    by_day = {r["date"]: r for r in rows}
    out = []
    for key, column, unit, better in RECOVERY:
        values = stats.series(rows, column)
        extra = {}
        if key == "sleep" and seen and seen in by_day:
            extra = {"start": iso(by_day[seen].get("sleep_start")), "end": iso(by_day[seen].get("sleep_end")),
                     "in_bed": by_day[seen].get("in_bed_min")}
        out.append(metric(key, unit, better, values, seen, extra=extra))
    return {"as_of": iso(seen), "days_behind": (day - seen).days if seen else None,
            "verdict": verdict(out), "metrics": out}


def activity(ctx: Context, day: date) -> List[Dict[str, Any]]:
    rows = [r for r in ctx.store.rows("body_daily") if r["date"] <= day]
    whole = [r for r in rows if r.get("complete") is not False]
    last = rows[-1] if rows else None
    partial = bool(last and last.get("complete") is False)
    out = []
    for key, column, unit in ACTIVITY:
        values = stats.series(whole, column)
        if partial and last.get(column) is not None:
            values = {**values, last["date"]: float(last[column])}
        out.append(metric(key, unit, "none", values, last["date"] if last else None, partial=partial))
    week = [day - timedelta(days=k) for k in range(7)]
    by_day = {r["date"]: r for r in whole}
    trained = [d for d in week if (by_day.get(d) or {}).get("workout_min")]
    known = [d for d in week if (by_day.get(d) or {}).get("workout_min") is not None]
    last_workout = next((r for r in reversed(whole) if r.get("workout_min")), None)
    out.append({"key": "training", "unit": "days", "value": len(trained), "known_days": len(known),
                "series": [{"date": iso(d), "value": (by_day.get(d) or {}).get("workout_min")} for d in reversed(week)],
                "last": {"date": iso(last_workout["date"]), "type": last_workout.get("workout_type"),
                         "min": last_workout.get("workout_min")} if last_workout else None,
                "planned_today": plans.training_for(ctx.cfg, day)})
    return out


def attention(ctx: Context, day: date) -> Dict[str, Any]:
    days = ctx.screen_days()
    last = max((d for d in days if d < day), default=None)
    if last is None:
        return {"day": None, "stale": True, "days_behind": None, "metrics": [], "targets": []}
    behind = (day - last).days
    stale = behind > STALE_SCREEN_DAYS
    upto = {d: sd for d, sd in days.items() if d <= last and d < day}
    series = {
        "focus": {d: sd.share(FOCUS) for d, sd in upto.items()},
        "longest_focus": {d: sd.longest_focus for d, sd in upto.items()},
        "fun": {d: sd.share(FUN) for d, sd in upto.items()},
    }
    before_bed = {}
    for d in upto:
        value = ctx.fun_before_sleep(d)
        if value is not None:
            before_bed[d] = value
    series["fun_before_sleep"] = before_bed
    better = {"focus": "higher", "longest_focus": "higher", "fun": "lower", "fun_before_sleep": "lower"}
    metrics = []
    for key, values in series.items():
        m = metric(key, "min", better[key], values, last if last in values else None)
        if stale:
            m.update(band=None, state=None, tone="neutral")
        metrics.append(m)
    sd = days[last]
    return {"day": iso(last), "stale": stale, "days_behind": behind, "metrics": metrics,
            "total": sd.total, "by_category": sd.by_category,
            "targets": plans.screen_targets(ctx.cfg, series, last)}


def week_load(ctx: Context, day: date) -> Dict[str, Any]:
    rows = [r for r in ctx.store.rows("body_daily") if r["date"] <= day]
    sleep = stats.series(rows, "sleep_min")
    hrv = stats.series(rows, "hrv_ms")
    trained = {r["date"]: bool(r["workout_min"]) for r in rows if r.get("workout_min") is not None}
    week = [day - timedelta(days=k) for k in range(7)]
    nights = [d for d in week if d in sleep]
    short = [d for d in nights if sleep[d] < 7 * 60]
    train = [d for d in week if trained.get(d)]
    change = None
    recent = [hrv[d] for d in week if d in hrv]
    before = [hrv[day - timedelta(days=k)] for k in range(7, 7 + stats.BASELINE_DAYS) if day - timedelta(days=k) in hrv]
    if len(recent) >= 4 and len(before) >= stats.MIN_BASELINE:
        change = statistics.median(recent) / statistics.median(before) - 1
    return {"nights": len(nights), "short_nights": len(short), "train_days": len(train),
            "hrv_change": change, "strain": len(short) >= 3 and len(train) >= 3,
            "rule": {"short_nights_min": 3, "train_days_min": 3, "short_hours": 7}}


def agenda(ctx: Context, day: date) -> Dict[str, Any]:
    events = [e for e in ctx.store.rows("events") if e["start"].date() == day]
    events.sort(key=lambda e: e["start"])
    soon = []
    for d in ctx.store.rows("deadlines"):
        left = (d["due"].date() - day).days
        if 0 <= left <= 3 and d.get("status") not in ("submitted", "done"):
            soon.append({"due": iso(d["due"]), "title": d["title"], "group": d.get("group"),
                         "weight_pct": d.get("weight_pct"), "days_left": left})
    soon.sort(key=lambda d: d["due"])
    return {"events": [{"start": iso(e["start"]), "end": iso(e["end"]), "title": e["title"], "kind": e["kind"],
                        "location": e.get("location")} for e in events],
            "deadlines": soon, "training": plans.training_for(ctx.cfg, day),
            "sleep": plans.tonight(ctx, day)}


def ring(ctx: Context, day: date, attention_day: Optional[str]) -> Dict[str, Any]:
    """The day ring: last night's sleep, the day's calendar and workouts, and screen use by hour
    (the same day once its screen time has synced, otherwise the last day that has it)."""
    body = ctx.store.by_date("body_daily")
    row = body.get(day) or {}
    # the same day when its screen time has synced, otherwise the last whole day
    screen_day = day if day in ctx.screen_days() else (date.fromisoformat(attention_day) if attention_day else None)
    sd = ctx.screen_days().get(screen_day) if screen_day else None
    hours = [dict(h) for h in sd.by_hour] if sd else []
    attention_day = iso(screen_day) if sd else None
    return {"sleep": {"start": iso(row.get("sleep_start")), "end": iso(row.get("sleep_end"))} if row.get("sleep_end") else None,
            "events": [{"start": iso(e["start"]), "end": iso(e["end"]), "kind": e["kind"], "title": e["title"]}
                       for e in ctx.store.rows("events") if e["start"].date() == day and e["kind"] != "training"],
            "workouts": [{"start": iso(w["start"]), "end": iso(w["end"]), "type": w["type"]}
                         for w in ctx.store.rows("workouts") if w["start"].date() == day],
            "screen_day": attention_day, "screen_hours": hours,
            "now": iso(ctx.now) if day == ctx.today else None}


def effects(ctx: Context, day: date) -> Dict[str, Any]:
    """Next-day HRV, resting heart rate and self-reported energy after doing vs not doing a few things."""
    rows = [r for r in ctx.store.rows("body_daily") if r["date"] <= day and r.get("complete") is not False]
    hrv, rhr = stats.series(rows, "hrv_ms"), stats.series(rows, "resting_hr")
    outcomes: Dict[str, stats.Series] = {"hrv": {}, "resting_hr": {}}
    for d in hrv:
        band = stats.typical(hrv, d)
        if band:
            outcomes["hrv"][d] = (hrv[d] / band["median"] - 1) * 100
    for d in rhr:
        band = stats.typical(rhr, d)
        if band:
            outcomes["resting_hr"][d] = rhr[d] - band["median"]
    energy = stats.series([r for r in ctx.store.rows("self_report") if r["date"] <= day], "energy")
    if len(energy) >= 2 * stats.MIN_GROUP_DAYS:
        outcomes["energy"] = energy
    by_day = {r["date"]: r for r in rows}
    one = timedelta(days=1)

    def flag(d: date, column: str, test) -> Optional[float]:
        value = (by_day.get(d) or {}).get(column)
        return None if value is None else float(test(value))

    candidates = [
        ("trained", {}, lambda d: flag(d, "workout_min", lambda v: v > 0)),
        ("steps", {"min": 10000}, lambda d: flag(d, "steps", lambda v: v >= 10000)),
        ("exercise", {"min": 30}, lambda d: flag(d, "exercise_min", lambda v: v >= 30)),
        ("slept", {"hours": 7}, lambda d: flag(d + one, "sleep_min", lambda v: v >= 420)),
        ("in_bed", {"hours": 8}, lambda d: flag(d + one, "in_bed_min", lambda v: v >= 480)),
    ]
    early = food_page.late_meal_flags(ctx, day)
    if early:  # only for people who log food: everyone else would get a row that can never be compared
        candidates.append(("ate_early", {"hours": ctx.cfg.food.last_meal_gap_h}, lambda d: early.get(d)))
    bedtime = ctx.cfg.sleep.bedtime
    if bedtime:
        limit = stats.minutes_since_noon(bedtime)
        candidates.append(("asleep_by", {"clock": bedtime.strftime("%H:%M")},
                           lambda d: flag(d + one, "sleep_start", lambda v: stats.minutes_since_noon(v) <= limit)))
    results = {}
    for name, outcome in outcomes.items():
        out = []
        for key, params, condition in candidates:
            yes, no = [], []
            for d in sorted(outcome):
                f = condition(d - one)
                if f is None:
                    continue
                (yes if f == 1.0 else no).append(outcome[d])
            out.append({"key": key, "params": params, "yes_days": len(yes), "no_days": len(no),
                        **stats.compare(yes, no)})
        tested = [r for r in out if r["status"] == "ok"]
        for r, adjusted in zip(tested, stats.benjamini_hochberg([r["p"] for r in tested])):
            r["p_adjusted"] = adjusted
            r["detected"] = adjusted < stats.FDR
        results[name] = out
    return {"outcomes": list(outcomes), "rows": results,
            "units": {"hrv": "%", "resting_hr": "bpm", "energy": "points"},
            "better": {"hrv": "higher", "resting_hr": "lower", "energy": "higher"},
            "method": {"min_group_days": stats.MIN_GROUP_DAYS, "fdr": stats.FDR, "baseline_days": stats.BASELINE_DAYS}}


def energy_now(ctx: Context, day: date) -> Optional[Dict[str, Any]]:
    """The latest energy rated that day on Recovery's "How you are right now" card (0–10, with its time), or None."""
    from .. import recovery_log
    try:
        rows = recovery_log.read(ctx.cfg)
    except ValueError:  # a damaged log is reported on Recovery; Today just leaves the rating out
        return None
    now = recovery_log.moment(ctx.cfg, ctx.now)
    seen = [(at, r) for r in rows if r["kind"] == "energy"
            for at in [datetime.fromisoformat(r["at"]).astimezone(now.tzinfo)] if at.date() == day and at <= now]
    if not seen:
        return None
    at, r = max(seen, key=lambda x: x[0])
    return {"value": r["value"], "at": at.isoformat(timespec="seconds")}


def self_report(ctx: Context, day: date) -> Optional[Dict[str, Any]]:
    rows = [r for r in ctx.store.rows("self_report") if day - timedelta(days=1) <= r["date"] <= day]
    rated = energy_now(ctx, day)
    if not rows and rated is None:
        return None
    row = rows[-1] if rows else {"date": day}
    # the feeling is that morning's answer on the Recovery check-in, so only today's counts; energy rated on the card
    # (0–10) is shown instead of a hand-typed 0–5 one
    return {"date": iso(row["date"]), "energy": row.get("energy"), "focus": row.get("focus"), "note": row.get("note"),
            "feel": row.get("feel") if row["date"] == day else None, "energy_now": rated}


def _rhythm_line(ctx: Context) -> Dict[str, Any]:
    from .focus import rhythm
    r = rhythm(ctx)
    return {k: r[k] for k in ("over_run", "reward_ready", "light", "streak", "to_reward")}


def build(ctx: Context, day: Optional[str] = None) -> Dict[str, Any]:
    picked = date.fromisoformat(day) if day else ctx.today
    if picked > ctx.today:
        picked = ctx.today
    att = attention(ctx, picked)
    rec = recovery(ctx, picked)
    drain_card = drain_summary(ctx, picked)
    from . import actions, restore  # imported here: these modules also read this one
    return {
        "page": "today", "day": iso(picked), "today": iso(ctx.today), "now": iso(ctx.now),
        "looking_back": picked != ctx.today,
        "restore": restore.build(ctx) if picked == ctx.today else None,
        "agenda": agenda(ctx, picked),
        "recovery": rec,
        # what to adjust today, read off the other pages; only for today itself (a past day's advice is no use)
        "actions": None if picked != ctx.today else actions.build(ctx, picked, rec, drain_card),
        "self": self_report(ctx, picked),
        "sitting": sitting.light(ctx, picked),
        "care_ask": care.build(ctx, picked)["ask"] if picked == ctx.today else [],
        "rhythm": _rhythm_line(ctx) if picked == ctx.today else None,  # over budget days in a row, or a rhythm to celebrate  # yesterday's tight spots: how now?
        "activity": activity(ctx, picked),
        "attention": att,
        "week": week_load(ctx, picked),
        "drain": drain_card,
        "ring": ring(ctx, picked, att["day"]),
        "summary": summary(ctx, picked),
        "effects": effects(ctx, picked),
    }


def summary(ctx: Context, day: date) -> Dict[str, Any]:
    """One line each for the parts of the day the other pages own: the week's exercise, the last 7 days of food, the
    weight trend and cardio fitness (recovery, screens and wear and tear are in the payload already)."""
    from . import body as body_page
    from . import exercise as exercise_page
    week = exercise_page.week_status(ctx, day)
    goal = exercise_page.goal(ctx.cfg)
    weight = body_page.build(ctx, iso(day))
    plan = weight["plan"]
    return {
        "exercise": {"minutes": week["minutes"], "goal_min": goal["weekly_min"], "source": goal["source"],
                     "strength_days": week["strength_days"], "strength_goal": goal["strength_days"],
                     "remaining_min": week["remaining_min"], "days_left": week["days_left"], "status": week["status"],
                     "is_current": week["is_current"], "tracked": bool(exercise_page.active_minutes(ctx, day))},
        "food": food_page.summary(ctx, day),
        "weight": {**weight["latest"], "plan": plan} if weight["points"] else None,
        "cardio": weight["cardio"]["latest"],
    }


def drain_summary(ctx: Context, day: date) -> Dict[str, Any]:
    """The Drain page's two lines for the same 7 days (imported here to avoid a circular import)."""
    from . import drain
    page = drain.build(ctx, (day - timedelta(days=1)).isoformat())
    return {"window": page["window"], "worse": page["worse"], "strain": page["strain"]["strain"],
            # how many signals could be set against your normal: 0 says so, never "nothing got worse"
            "compared": page["compared"], "signals": len(page["rows"]),
            "plan_off": [{"key": r["key"], "over": r.get("plan_over")} for r in page["rows"] if r.get("plan_tone") == "bad"]}
