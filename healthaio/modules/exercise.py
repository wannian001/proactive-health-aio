"""Exercise: this week against the weekly goal, the last 7 days against your normal, training load against
recovery, twelve weeks by kind, and how your body tends to answer each kind the next day.

Rules
- Active minutes of a day = the Activity ring's exercise minutes (body_daily.exercise_min), which count any brisk
  movement; on a day without them, the minutes of logged workouts. Missing stays missing.
- The weekly goal is [plan.exercise] when set, otherwise the WHO guideline for adults: 150 minutes of moderate
  activity a week and muscle-strengthening on 2 or more days. The page says which one it uses.
- A week runs Monday to Sunday. What is left is shared over the days left, today included.
- Kind of a workout, from its type: strength (strength, weights, core, functional), cardio (running, cycling,
  swimming, rowing, HIIT, ...), walking (walking, hiking), other (yoga, pilates, sports, anything else).
- Last 7 days (ending yesterday, today is not over) against your normal: active minutes and workouts as 7-day totals
  against the middle half of the 7-day totals ending on each of the 28 days before (a total needs at least 5 days
  with data); steps and active energy as daily averages, like the Drain page.
- Load: workout minutes of the last 7 days over the weekly average of the 28 days before. Above 1.3 = clearly more
  than you are used to, under 0.8 = clearly less. A rule of thumb from sport science, not a diagnosis. Read together
  with the Today page's recovery: more load on a recovery below normal says rest.
- The next day after each kind: HRV against the median of your previous 28 days (in percent) and resting heart rate
  against its median (in bpm), the median over the last 120 days of that kind. A description, not a test: the Today
  page's list is where differences are tested.
"""
import statistics
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from .. import config as config_mod
from .. import stats
from ..context import Context, iso
from . import sitting
from . import plans
from .week import monday

WINDOW = 7
BASELINE = 28
MIN_WINDOW = 4
MIN_TOTAL_DAYS = 5
MIN_BASELINE = 10
WEEKS = 12
RECENT = 6
RESPONSE_DAYS = 120
MIN_RESPONSE = 4
LOAD_HIGH, LOAD_LOW = 1.3, 0.8
KINDS = ("strength", "cardio", "walk", "other")
_WORDS = {
    "strength": ("strength", "weight", "core", "functional"),
    "walk": ("walk", "hik"),
    "cardio": ("run", "cycl", "bik", "swim", "row", "ellip", "hiit", "stair", "cardio", "jump", "box", "dance",
               "cross", "ski", "skat", "climb"),
}


def kind_of(workout_type: Optional[str]) -> str:
    text = (workout_type or "").lower()
    for kind in ("strength", "walk", "cardio"):
        if any(word in text for word in _WORDS[kind]):
            return kind
    return "other"


def goal(cfg: config_mod.Config) -> Dict[str, Any]:
    plan = cfg.exercise
    set_ = plan.weekly_min is not None or plan.strength_days is not None
    return {"weekly_min": plan.weekly_min if plan.weekly_min is not None else config_mod.GUIDELINE_WEEKLY_MIN,
            "strength_days": plan.strength_days if plan.strength_days is not None else config_mod.GUIDELINE_STRENGTH_DAYS,
            "source": "plan" if set_ else "guideline"}


def _workouts(ctx: Context) -> List[Dict[str, Any]]:
    out = []
    for w in sorted(ctx.store.rows("workouts"), key=lambda w: w["start"]):
        out.append({"start": w["start"], "end": w["end"], "type": w["type"], "kind": kind_of(w["type"]),
                    "minutes": (w["end"] - w["start"]).total_seconds() / 60, "kcal": w.get("kcal"), "avg_hr": w.get("avg_hr")})
    return out


def active_minutes(ctx: Context, until: date) -> stats.Series:
    """Activity-ring minutes per day, or logged workout minutes where the ring has none (see the module doc)."""
    out: stats.Series = {}
    for r in ctx.store.rows("body_daily"):
        if r["date"] <= until and r.get("exercise_min") is not None:
            out[r["date"]] = float(r["exercise_min"])
    logged: Dict[date, float] = {}
    for w in ctx.store.rows("workouts"):
        d = w["start"].date()
        logged[d] = logged.get(d, 0.0) + (w["end"] - w["start"]).total_seconds() / 60
    for d, minutes in logged.items():
        if d <= until and d not in out:
            out[d] = minutes
    return out


def week_status(ctx: Context, day: date) -> Dict[str, Any]:
    """The calendar week holding ``day``: minutes and strength days so far, what is left and over how many days."""
    g = goal(ctx.cfg)
    start = monday(day)
    minutes = active_minutes(ctx, max(day, ctx.today))
    workouts = _workouts(ctx)
    days = []
    for k in range(7):
        d = start + timedelta(days=k)
        mine = [w for w in workouts if w["start"].date() == d]
        days.append({"date": iso(d), "minutes": minutes.get(d) if d <= ctx.today else None,
                     "is_today": d == ctx.today, "future": d > ctx.today,
                     "planned": plans.training_for(ctx.cfg, d),
                     "by_kind": {kind: sum(w["minutes"] for w in mine if w["kind"] == kind) for kind in KINDS},
                     "workouts": [{"start": iso(w["start"]), "end": iso(w["end"]), "type": w["type"], "kind": w["kind"],
                                   "minutes": w["minutes"], "kcal": w["kcal"], "avg_hr": w["avg_hr"]} for w in mine]})
    done = sum(x["minutes"] or 0 for x in days)
    strength = sum(1 for x in days if x["by_kind"]["strength"] > 0)
    remaining = max(0.0, g["weekly_min"] - done)
    left = sum(1 for x in days if x["future"] or x["is_today"]) if start <= ctx.today else 0
    today_done = next((x["minutes"] or 0 for x in days if x["is_today"]), 0)
    # what today needs: the rest of the week shared out, today's own minutes counted back in
    need_today = (remaining + today_done) / left if left and remaining > 0 else 0.0
    status = "met" if remaining == 0 else ("behind" if left and need_today > 45 else "on_track") if left else "missed"
    return {"start": iso(start), "end": iso(start + timedelta(days=6)), "days": days, "minutes": done,
            "strength_days": strength, "remaining_min": remaining, "days_left": left,
            "need_today_min": need_today, "today_min": today_done,
            "strength_left": max(0, g["strength_days"] - strength), "status": status,
            "is_current": start == monday(ctx.today)}


def _rolling_totals(values: stats.Series, ends: List[date]) -> stats.Series:
    out: stats.Series = {}
    for d in ends:
        block = [values[d - timedelta(days=k)] for k in range(WINDOW) if d - timedelta(days=k) in values]
        if len(block) >= MIN_TOTAL_DAYS:
            out[d] = sum(block) * WINDOW / len(block)  # a day or two without data counts at the block's own rate
    return out


def _band(values: List[float]) -> Optional[Dict[str, float]]:
    if len(values) < MIN_BASELINE:
        return None
    q1, median, q3 = statistics.quantiles(values, n=4, method="inclusive")
    return {"q1": q1, "median": median, "q3": q3, "days": len(values)}


def build(ctx: Context, day: Optional[str] = None) -> Dict[str, Any]:
    picked = min(date.fromisoformat(day) if day else ctx.today, ctx.today)
    end = min(picked, ctx.today - timedelta(days=1))  # the comparisons use whole days
    window = [end - timedelta(days=k) for k in range(WINDOW)]
    base = [end - timedelta(days=WINDOW + k) for k in range(BASELINE)]
    g = goal(ctx.cfg)
    body = ctx.store.by_date("body_daily")
    whole = {d: r for d, r in body.items() if r.get("complete") is not False and d <= end}
    minutes = active_minutes(ctx, end)
    workouts = [w for w in _workouts(ctx) if w["start"].date() <= picked]
    sessions: stats.Series = {}
    for w in workouts:
        sessions[w["start"].date()] = sessions.get(w["start"].date(), 0.0) + 1
    known_days = set(minutes)
    sessions_full = {d: sessions.get(d, 0.0) for d in known_days}  # a day with activity data and no workout = 0

    def total_row(key: str, unit: str, better: str, values: stats.Series) -> Dict[str, Any]:
        totals = _rolling_totals(values, [end] + base)
        value = totals.get(end)
        band = _band([totals[d] for d in base if d in totals])
        state = stats.classify(value, band)
        weeks = [{"to": iso(end - timedelta(days=7 * w)), "value": _rolling_totals(values, [end - timedelta(days=7 * w)]).get(end - timedelta(days=7 * w))}
                 for w in range(8 - 1, -1, -1)]
        return {"key": key, "unit": unit, "better": better, "how": "total", "value": value, "band": band,
                "state": state, "tone": stats.tone(state, better), "days": sum(1 for d in window if d in values),
                "weeks": weeks, "series": [{"date": iso(d), "value": values.get(d)} for d in sorted(window + base)]}

    def mean_row(key: str, unit: str, better: str, values: stats.Series) -> Dict[str, Any]:
        inside = [values[d] for d in window if d in values]
        value = statistics.fmean(inside) if len(inside) >= MIN_WINDOW else None
        band = _band([values[d] for d in base if d in values])
        state = stats.classify(value, band)
        weeks = []
        for w in range(8 - 1, -1, -1):
            block = [values[end - timedelta(days=7 * w + k)] for k in range(WINDOW) if end - timedelta(days=7 * w + k) in values]
            weeks.append({"to": iso(end - timedelta(days=7 * w)), "value": statistics.fmean(block) if len(block) >= MIN_WINDOW else None})
        return {"key": key, "unit": unit, "better": better, "how": "mean", "value": value, "band": band, "state": state,
                "tone": stats.tone(state, better), "days": len(inside), "weeks": weeks,
                "series": [{"date": iso(d), "value": values.get(d)} for d in sorted(window + base)]}

    rows = [
        total_row("active_min", "min", "higher", minutes),
        total_row("sessions", "count", "none", sessions_full),
        mean_row("steps", "steps", "higher", stats.series(whole.values(), "steps")),
        mean_row("active_kcal", "kcal", "none", stats.series(whole.values(), "active_kcal")),
    ]

    # twelve calendar weeks by kind (the current one up to now)
    so_far = active_minutes(ctx, picked)
    first = monday(picked) - timedelta(days=7 * (WEEKS - 1))
    weeks = []
    for w in range(WEEKS):
        ws = first + timedelta(days=7 * w)
        span = [ws + timedelta(days=k) for k in range(7) if ws + timedelta(days=k) <= picked]
        mine = [x for x in workouts if ws <= x["start"].date() < ws + timedelta(days=7)]
        by_kind = {kind: sum(x["minutes"] for x in mine if x["kind"] == kind) for kind in KINDS}
        known = [so_far[d] for d in span if d in so_far]
        total = sum(known) if len(known) >= min(len(span), MIN_TOTAL_DAYS) else None
        # active minutes outside any logged workout (brisk walks to class, the bike to work)
        loose = max(0.0, total - sum(by_kind.values())) if total is not None else None
        weeks.append({"week_start": iso(ws), "minutes": total, "by_kind": by_kind, "loose": loose,
                      "strength_days": len({x["start"].date() for x in mine if x["kind"] == "strength"}),
                      "partial": ws + timedelta(days=6) > picked, "known_days": len(known)})

    # load: the last 7 days of workouts against the 28 days before (weekly average)
    workout_minutes: stats.Series = {}
    for x in workouts:
        workout_minutes[x["start"].date()] = workout_minutes.get(x["start"].date(), 0.0) + x["minutes"]
    acute = sum(workout_minutes.get(d, 0.0) for d in window)
    chronic_days = [d for d in base if d in known_days]
    chronic = sum(workout_minutes.get(d, 0.0) for d in base) / 4 if len(chronic_days) >= 21 else None
    ratio = acute / chronic if chronic else None
    load_state = "unknown" if ratio is None else "high" if ratio > LOAD_HIGH else "low" if ratio < LOAD_LOW else "normal"
    from . import today as today_page
    recovery = today_page.recovery(ctx, picked)
    advice = "unknown"
    if recovery["verdict"] == "low" or (load_state == "high" and recovery["verdict"] != "good"):
        advice = "ease"
    elif load_state == "low" and recovery["verdict"] in ("normal", "good"):
        advice = "build"
    elif recovery["verdict"] != "unknown":
        advice = "keep"

    # how the body answers each kind the next day
    hrv = {d: r["hrv_ms"] for d, r in body.items() if r.get("hrv_ms") is not None}
    rhr = {d: r["resting_hr"] for d, r in body.items() if r.get("resting_hr") is not None}

    def next_day(d: date) -> Dict[str, Optional[float]]:
        nd = d + timedelta(days=1)
        out: Dict[str, Optional[float]] = {"hrv_pct": None, "rhr_bpm": None}
        if nd in hrv:
            band = stats.typical(hrv, nd)
            out["hrv_pct"] = (hrv[nd] / band["median"] - 1) * 100 if band else None
        if nd in rhr:
            band = stats.typical(rhr, nd)
            out["rhr_bpm"] = rhr[nd] - band["median"] if band else None
        return out

    response = []
    since = picked - timedelta(days=RESPONSE_DAYS)
    rest_days = [d for d in sorted(known_days) if since <= d < picked and not workout_minutes.get(d)]
    groups = {kind: sorted({x["start"].date() for x in workouts if x["kind"] == kind and since <= x["start"].date() < picked})
              for kind in KINDS}
    groups["rest"] = rest_days
    for kind in KINDS + ("rest",):
        answers = [next_day(d) for d in groups[kind]]
        h = [a["hrv_pct"] for a in answers if a["hrv_pct"] is not None]
        r = [a["rhr_bpm"] for a in answers if a["rhr_bpm"] is not None]
        if len(h) >= MIN_RESPONSE:
            response.append({"kind": kind, "days": len(h), "hrv_pct": statistics.median(h),
                             "rhr_bpm": statistics.median(r) if len(r) >= MIN_RESPONSE else None})
    recent = []
    for x in reversed(workouts[-RECENT:]):
        recent.append({"start": iso(x["start"]), "end": iso(x["end"]), "type": x["type"], "kind": x["kind"],
                       "minutes": x["minutes"], "kcal": x["kcal"], "avg_hr": x["avg_hr"],
                       **(next_day(x["start"].date()) if x["start"].date() < picked else {"hrv_pct": None, "rhr_bpm": None})})
    return {
        "page": "exercise", "day": iso(picked), "today": iso(ctx.today), "now": iso(ctx.now),
        "looking_back": picked != ctx.today, "goal": g, "week": week_status(ctx, picked),
        "window": {"from": iso(window[-1]), "to": iso(end)}, "rows": rows,
        "weeks": weeks, "load": {"acute_min": acute, "chronic_min": chronic, "ratio": ratio, "state": load_state,
                                 "high": LOAD_HIGH, "low": LOAD_LOW},
        "recovery": {"verdict": recovery["verdict"], "as_of": recovery["as_of"],
                     "worse": [m["key"] for m in recovery["metrics"] if m["tone"] == "bad"]},
        "advice": advice, "response": response, "recent": recent,
        "sitting": sitting.build(ctx, picked),  # long stretches at the computer, the other half of moving (modules/sitting.py)
        "has_data": bool(minutes) or bool(workouts),
        "rule": {"window": WINDOW, "baseline": BASELINE, "min_total_days": MIN_TOTAL_DAYS, "weeks": WEEKS,
                 "response_days": RESPONSE_DAYS, "min_response": MIN_RESPONSE},
    }
