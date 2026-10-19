"""Focus budget (专注额度) and the sustainable rhythm built on it.

Deep focus is time on work or learning apps (Screen Time categories) in stretches of DEEP_MIN minutes or more, a quick
message inside a stretch not ending it (the same gap rule as the Time page's longest stretch). Creativity or "brain
power" cannot be measured by any device; deep focus is the nearest thing that can.

The budget for a day is what you yourself managed on the days most like it, not a target: among the last HISTORY days
with Screen Time, the K whose night's sleep and morning HRV (against its own 28-day normal) were closest to the day's,
weekdays matched with weekdays and weekends with weekends when there are enough of them. Its middle is the median of
those days' deep focus, its range their middle half. With fewer than MIN_DAYS such days there is no budget. On Recovery
the budget is the third gauge, today's deep focus filling it (Screen Time arrives every few hours, so "so far" says
until when).

The rhythm (Rest & rewards) looks back DAYS days, each day's budget worked out with only the days before it:
- over budget: deep focus above the range's top (more than on most days like it) and at least OVER_MIN minutes;
- took breaks: no stretch at the computer longer than BREAKS_MIN (modules/sitting.py), or a rest written down that day;
- a sustainable day: not over budget and took breaks; a sustainable week: at least SUSTAINED_DAYS of them among at least
  KNOWN_DAYS known days.
Three days over in a row bring a suggestion to keep the emptiest half-day of the next three light (from the calendar).
SUSTAINED_WEEKS sustainable weeks in a row bring a celebration to plan, once per run: it rewards keeping the rhythm, not
doing more. Rest is never earned this way.
"""
import statistics
from datetime import date, datetime, time, timedelta
from typing import Any, Dict, List, Optional

from ..context import FOCUS, STRETCH_GAP_MIN, Context, iso

DEEP_MIN = 25
HISTORY = 90
K = 10
MIN_DAYS = 7
DAYS = 56
OVER_MIN = 30
BREAKS_MIN = 90
KNOWN_DAYS = 5
SUSTAINED_DAYS = 5
SUSTAINED_WEEKS = 3
SLEEP_UNIT = 60.0  # an hour's difference in sleep counts as much as
HRV_UNIT = 0.15    # 15% of your normal HRV


def deep_minutes(minutes: Dict[int, str]) -> int:
    """Minutes in focus stretches of DEEP_MIN or more (a gap shorter than STRETCH_GAP_MIN does not end one)."""
    total = run = gap = 0
    for minute in range(1441):
        if minutes.get(minute) in FOCUS:
            run += 1 + gap
            gap = 0
        elif run and gap < STRETCH_GAP_MIN and minute < 1440:
            gap += 1
        else:
            if run >= DEEP_MIN:
                total += run
            run = gap = 0
    return total


def _features(ctx: Context) -> Dict[date, Dict[str, Any]]:
    """Per day: last night's sleep, this morning's HRV against its 28-day normal, weekend or not (once per request)."""
    cached = getattr(ctx, "_focus_features", None)
    if cached is not None:
        return cached
    body = {r["date"]: r for r in ctx.store.rows("body_daily")}
    hrv = sorted((d, r["hrv_ms"]) for d, r in body.items() if r.get("hrv_ms") is not None)
    out: Dict[date, Dict[str, Any]] = {}
    for d, r in body.items():
        normal = [v for x, v in hrv if d - timedelta(days=28) <= x < d]
        out[d] = {"sleep": r.get("sleep_min"),
                  "hrv": r["hrv_ms"] / statistics.median(normal) if r.get("hrv_ms") is not None and len(normal) >= 10 else None}
    ctx._focus_features = out
    return out


def _deep_days(ctx: Context) -> Dict[date, int]:
    cached = getattr(ctx, "_focus_deep", None)
    if cached is None:
        cached = {d: deep_minutes(sd.minutes) for d, sd in ctx.screen_days().items()}
        ctx._focus_deep = cached
    return cached


def budget(ctx: Context, day: date) -> Optional[Dict[str, Any]]:
    """The deep focus of the K past days most like `day` (only days before it), or None with too little history."""
    feats, deep = _features(ctx), _deep_days(ctx)
    me = feats.get(day, {})
    keys = [k for k in ("sleep", "hrv") if me.get(k) is not None]
    pool = [d for d in deep if day - timedelta(days=HISTORY) <= d < day and all(feats.get(d, {}).get(k) is not None for k in keys)]
    same = [d for d in pool if (d.weekday() >= 5) == (day.weekday() >= 5)]
    if len(same) >= MIN_DAYS:
        pool = same
    if len(pool) < MIN_DAYS:
        return None

    def distance(d):
        f = feats.get(d, {})
        return sum(abs(f[k] - me[k]) / (SLEEP_UNIT if k == "sleep" else HRV_UNIT) for k in keys)

    near = sorted(pool, key=lambda d: (distance(d), -d.toordinal()))[:K]
    values = sorted(deep[d] for d in near)
    q = statistics.quantiles(values, n=4, method="inclusive") if len(values) > 1 else [values[0]] * 3
    return {"middle": round(statistics.median(values)), "low": round(q[0]), "high": round(q[2]), "days": len(near),
            "matched": keys, "weekend": day.weekday() >= 5, "sleep": me.get("sleep"), "hrv": me.get("hrv")}


def today(ctx: Context, day: Optional[date] = None) -> Dict[str, Any]:
    """The Recovery gauge: today's budget and the deep focus so far."""
    day = day or ctx.today
    b = budget(ctx, day)
    sd = ctx.screen_days().get(day)
    used = deep_minutes(sd.minutes) if sd else None
    ends = [r["end"] for r in ctx.store.rows("screen_sessions") if r["start"].date() == day and r["end"] <= ctx.now]
    state = None
    if b and used is not None:
        state = "over" if used > b["high"] and used >= OVER_MIN else "near" if used >= 0.8 * b["middle"] else "room"
    # time on work or learning apps at all, and the longest stretch: when there is plenty of the first and no deep
    # focus, something kept breaking it up (the phone, as a rule: a minute on the phone is a minute off the work)
    focus_min = sum(sd.by_category.get(c, 0) for c in FOCUS) if sd else None
    return {"budget": b, "used": used, "as_of": iso(max(ends)) if ends else None, "state": state,
            "focus_min": round(focus_min) if focus_min is not None else None, "longest": round(sd.longest_focus) if sd else None,
            "rule": {"deep_min": DEEP_MIN, "history": HISTORY, "k": K, "min_days": MIN_DAYS}}


def _rested(ctx: Context) -> set:
    from .. import restore_log
    try:
        sessions = restore_log.replay(restore_log.read(ctx.cfg))["sessions"]
    except ValueError:
        return set()
    out = set()
    for s in sessions:
        if s["status"] == "finished" and s.get("started_at"):
            t = datetime.fromisoformat(s["started_at"])
            out.add((t.astimezone(ctx.cfg.tz) if t.tzinfo else t).date())
    return out


def light_half_day(ctx: Context, start: date) -> Optional[Dict[str, Any]]:
    """The half-day with the fewest class and work minutes in the three days from `start` (mornings to 13:00)."""
    best = None
    events = [e for e in ctx.store.rows("events") if e["kind"] in ("class", "work")]
    for k in range(3):
        d = start + timedelta(days=k)
        for half, (a, b) in (("am", (time(8), time(13))), ("pm", (time(13), time(19)))):
            lo, hi = datetime.combine(d, a), datetime.combine(d, b)
            booked = sum(max(0, (min(e["end"], hi) - max(e["start"], lo)).total_seconds() / 60) for e in events)
            if best is None or booked < best["booked"]:
                best = {"date": iso(d), "half": half, "booked": round(booked)}
    return best


def rhythm(ctx: Context) -> Dict[str, Any]:
    """The long view: DAYS days of budget, deep focus and breaks; weeks; the over-budget run and the rewarded rhythm."""
    from . import sitting
    deep, rested = _deep_days(ctx), _rested(ctx)
    days = []
    for k in range(DAYS, 0, -1):
        d = ctx.today - timedelta(days=k)
        b = budget(ctx, d)
        used = deep.get(d)
        if used is None:
            days.append({"date": iso(d), "known": False})
            continue
        sit = sitting.day_summary(ctx, d)
        over = bool(b and used > b["high"] and used >= OVER_MIN)
        breaks = (sit is None or sit["longest"] <= BREAKS_MIN) or d in rested
        days.append({"date": iso(d), "known": True, "used": used, "budget": b and {k2: b[k2] for k2 in ("middle", "low", "high")},
                     "over": over, "breaks": breaks, "rested": d in rested, "longest_sit": sit and sit["longest"],
                     "sustainable": (not over) and breaks})
    now = today(ctx)
    run = 1 if now["state"] == "over" else 0
    for x in reversed(days):
        if not x["known"] or not x["over"]:
            break
        run += 1
    # weeks, Monday first; the current week is shown so far and not judged
    this_monday = ctx.today - timedelta(days=ctx.today.weekday())
    weeks = []
    for w in range(8, 0, -1):
        start = this_monday - timedelta(days=7 * w)
        span = [x for x in days if start <= date.fromisoformat(x["date"]) < start + timedelta(days=7) and x["known"]]
        good = sum(1 for x in span if x["sustainable"])
        weeks.append({"start": iso(start), "known": len(span), "sustainable_days": good,
                      "met": None if len(span) < KNOWN_DAYS else good >= SUSTAINED_DAYS})
    streak = 0
    for wk in reversed(weeks):
        if wk["met"] is not True:
            break
        streak += 1
    planned = _rhythm_rewards(ctx)
    since = date.fromisoformat(weeks[-streak]["start"]) if streak else None
    reward = streak >= SUSTAINED_WEEKS and not any(p >= since for p in planned)
    return {"days": days, "weeks": weeks, "over_run": run, "streak": streak, "reward_ready": reward,
            "to_reward": max(0, SUSTAINED_WEEKS - streak), "light": light_half_day(ctx, ctx.today + timedelta(days=1)) if run >= 3 else None,
            "today": now,
            "rule": {"deep_min": DEEP_MIN, "over_min": OVER_MIN, "breaks_min": BREAKS_MIN, "known_days": KNOWN_DAYS,
                     "sustained_days": SUSTAINED_DAYS, "sustained_weeks": SUSTAINED_WEEKS, "days": DAYS}}


def _rhythm_rewards(ctx: Context) -> List[date]:
    """When celebrations for the rhythm were planned (restore.jsonl reward_plan with for = rhythm)."""
    from .. import restore_log
    try:
        rewards = restore_log.replay(restore_log.read(ctx.cfg))["rewards"]
    except ValueError:
        return []
    out = []
    for r in rewards:
        if r.get("for") == "rhythm":
            t = datetime.fromisoformat(r["at"])
            out.append((t.astimezone(ctx.cfg.tz) if t.tzinfo else t).date())
    return out
