"""Recovery (#recovery): how recovered you are, what your training has asked of you, where you are sore, and how
your body has answered training.

- How recovered: the Today page's own verdict (HRV, resting heart rate and last night's sleep against your normal;
  two of three worse = below your normal), so both pages always agree.
- Training load: each workout's effort on Apple's 1-10 scale (your rating in the Fitness or Workout app, else the
  watch's estimate; workouts.csv `effort`) times its minutes, summed per day. This is the session-RPE method from
  sport science (Foster et al. 2001), and the same idea as Apple Fitness's own Training Load. The last 7 days
  (today so far included) are set against the weekly average of the 28 days before them: above 1.3 times reads as
  more than you are used to, below 0.8 as less (the Exercise page's minutes-only load uses the same lines).
  Workout minutes without an effort score are left out and counted; with under half of the minutes rated the load
  says it is unsure. A day with no workout, inside the range the workout record covers, is a load of 0.
  No device measures how tired the nervous system is. The load is what the training asked of you, as you (or the
  watch) judged it; the next morning's HRV and resting heart rate are the autonomic nervous system's answer.
- How the body answered (response): over the last RESPONSE_DAYS days, the next morning after hard days (load above
  the median of your training days) against every other known day (easier days and rest days): HRV in percent and
  resting heart rate in beats against your normal that morning, and, where you checked in, the most sore region's
  level. Difference of means with a 95% interval, at least stats.MIN_GROUP_DAYS days a side, Benjamini-Hochberg
  across the three; only what survives is a difference. An association, not a cause.
- After training (after_training): for each training day, one score the next morning, 0-10, from four parts put
  side by side and averaged (the one total score this app shows, and every part is shown with it):
  - how you feel that morning, your own answer on the check-in: 2, 5 or 8;
  - HRV the morning after against the morning before the training;
  - resting heart rate the day after against your normal;
  - the night after: how long you slept against your normal, and how much of the time in bed you were asleep
    against your normal (the two averaged).
  Each body part is 5 plus 2.5 for every width of your normal it lies away (the width of the middle half of your
  previous 28 days, at least SPREAD_FLOOR), better direction up, kept between 0 and 10; so 5 is a usual morning
  and 7.5 is one band width better. For HRV the normal is that of its morning-to-morning changes, since HRV moves a
  lot from one morning to the next and a change is what the part measures. A morning needs at least two parts, one of them from the body, for a score.
  6.5 and above reads as recovered well, under 3.5 as not recovered.
- Soreness (soreness.csv: 1 a little, 2 clearly sore, 3 very sore, 0 fine again, per region): said when it is felt,
  in a sentence (sore_say.py), and asked about again on the following days (follow_up(): every region whose latest
  answer in the last FOLLOW_DAYS days was sore, until you say it is fine), so nobody ticks through every region each
  morning. The figure shows today's; the last SORE_DAYS days show the levels of every region said in them, with the
  days each was trained marked. A region not said on a day is unknown, never "not sore".
- What a workout trained (workout_notes.csv): after a strength session or a hard one (effort HARD_EFFORT or more),
  every page asks once, for PROMPT_HOURS hours after it ended (prompt()), which regions it trained, by taps or a note.
  Each training day shows what it trained and how sore those regions were said to be the next morning.
"""
import statistics
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from .. import stats
from ..checkin import REGION_WORDS
from ..context import Context, iso
from ..schema import ALL_SORE_REGIONS, LEGACY_REGIONS, SORE_AREAS, SORE_REGIONS
from . import today as today_page

ACUTE = 7
CHRONIC = 28
CHART_DAYS = 42
LOAD_HIGH, LOAD_LOW = 1.3, 0.8
MIN_RATED_SHARE = 0.5
SORE_DAYS = 14
RESPONSE_DAYS = 90
AFTER_DAYS = 60  # training days of the last this many days are scored
PARTS = ("feel", "hrv", "resting_hr", "sleep")
SPREAD_FLOOR = {"hrv": 2.0, "resting_hr": 1.5, "sleep": 20.0, "efficiency": 2.0}
GOOD, LOW = 6.5, 3.5
OUTCOMES = ("hrv", "resting_hr", "sore_max")
OUTCOME_BETTER = {"hrv": "higher", "resting_hr": "lower", "sore_max": "lower"}
OUTCOME_UNITS = {"hrv": "%", "resting_hr": "bpm", "sore_max": "level"}
HARD_EFFORT = 7    # Apple's scale: 7-8 hard, 9-10 all out
PROMPT_HOURS = 36  # how long after a workout the pages ask what it trained
FOLLOW_DAYS = 14   # a region said to be sore is asked about on the following days, for at most this long


def daily_load(ctx: Context, until: date) -> Dict[date, Dict[str, Any]]:
    """Every day from the first workout on record to ``until`` that the workout record covers: its load (effort x
    minutes, rated minutes only), its workout minutes, how many of them had an effort, and the sessions."""
    rows = [w for w in ctx.store.rows("workouts") if w["end"] > w["start"] and w["start"].date() <= until]
    out: Dict[date, Dict[str, Any]] = {}
    if not rows:
        return out
    d = min(w["start"].date() for w in rows)
    while d <= until:
        if ctx.exercise_on(d) is not None or any(w["start"].date() == d for w in rows):
            out[d] = {"load": 0.0, "minutes": 0.0, "rated_min": 0.0, "sessions": []}
        d += timedelta(days=1)
    for w in sorted(rows, key=lambda r: r["start"]):
        day = out.get(w["start"].date())
        if day is None:
            continue
        minutes = (w["end"] - w["start"]).total_seconds() / 60
        day["minutes"] += minutes
        if w.get("effort") is not None:
            day["load"] += w["effort"] * minutes
            day["rated_min"] += minutes
        last = day["sessions"][-1] if day["sessions"] else None
        if last and last["type"] == w["type"] and last["effort"] == w.get("effort"):  # stretches of one paused workout
            last["minutes"] += minutes
        else:
            day["sessions"].append({"type": w["type"], "start": iso(w["start"]), "minutes": minutes,
                                    "effort": w.get("effort"), "effort_source": w.get("effort_source")})
    return out


def load_summary(days: Dict[date, Dict[str, Any]], end: date) -> Dict[str, Any]:
    acute_days = [end - timedelta(days=k) for k in range(ACUTE)]
    base_days = [end - timedelta(days=ACUTE + k) for k in range(CHRONIC)]
    acute = sum(days[d]["load"] for d in acute_days if d in days)
    known_base = [d for d in base_days if d in days]
    chronic = sum(days[d]["load"] for d in known_base) / (CHRONIC / ACUTE) if len(known_base) >= 21 else None
    minutes = sum(days[d]["minutes"] for d in acute_days + base_days if d in days)
    rated = sum(days[d]["rated_min"] for d in acute_days + base_days if d in days)
    share = rated / minutes if minutes else None
    ratio = acute / chronic if chronic else None
    if not minutes:
        state = "none"
    elif share is not None and share < MIN_RATED_SHARE:
        state = "few_ratings"
    elif ratio is None:
        state = "unknown"
    else:
        state = "high" if ratio > LOAD_HIGH else "low" if ratio < LOAD_LOW else "steady"
    unrated = sum(days[d]["minutes"] - days[d]["rated_min"] for d in acute_days if d in days)
    return {"acute": acute, "chronic": chronic, "ratio": ratio, "state": state, "rated_share": share,
            "unrated_min": unrated, "known_base": len(known_base), "high": LOAD_HIGH, "low": LOAD_LOW}


def soreness_log(ctx: Context) -> Dict[date, Dict[str, int]]:
    """Each day something was said as {region: level}, 0 for a region said to be fine again; an empty dict is an older
    morning check-in with nothing sore."""
    out: Dict[date, Dict[str, int]] = {}
    for row in ctx.store.rows("soreness"):
        day = out.setdefault(row["date"], {})
        if row["region"] != "none":
            day[row["region"]] = int(row["level"] or 0)
    return out


def _minute(stamp: Any) -> datetime:
    when = stamp if isinstance(stamp, datetime) else datetime.fromisoformat(stamp)
    return when.replace(second=0, microsecond=0, tzinfo=None)


def is_hard(session: Dict[str, Any]) -> bool:
    return "strength" in session["type"].lower() or (session.get("effort") or 0) >= HARD_EFFORT


def workout_notes(ctx: Context) -> Dict[datetime, Dict[str, Any]]:
    """What each noted workout trained, by its start to the minute."""
    out: Dict[datetime, Dict[str, Any]] = {}
    for row in ctx.store.rows("workout_notes"):
        words = (row.get("regions") or "").split()
        out[_minute(row["start"])] = {"regions": [r for r in ALL_SORE_REGIONS if r in words], "note": row.get("note") or ""}
    return out


def annotate(days: Dict[date, Dict[str, Any]], notes: Dict[datetime, Dict[str, Any]]) -> None:
    """Give every session whether it was hard and what was written about it (None: nothing yet)."""
    for v in days.values():
        for s in v["sessions"]:
            s["hard"] = is_hard(s)
            s["note"] = notes.get(_minute(s["start"]))


def trained_on(days: Dict[date, Dict[str, Any]]) -> Dict[date, List[str]]:
    out: Dict[date, List[str]] = {}
    for d, v in days.items():
        regions = {r for s in v["sessions"] if s.get("note") for r in s["note"]["regions"]}
        if regions:
            out[d] = [r for r in ALL_SORE_REGIONS if r in regions]
    return out


def follow_up(ctx: Context, end: date) -> List[Dict[str, Any]]:
    """The regions to ask about on `end`: each whose latest answer before that day, in the last FOLLOW_DAYS days, was
    sore (said that day, how much, and in what words), and not answered yet on `end`."""
    latest: Dict[str, Dict[str, Any]] = {}
    for row in sorted(ctx.store.rows("soreness"), key=lambda r: (r["date"], r.get("at") or datetime.min)):
        if row["region"] in SORE_REGIONS and end - timedelta(days=FOLLOW_DAYS) <= row["date"] <= end:
            latest[row["region"]] = row
    out = []
    for region in SORE_REGIONS:
        row = latest.get(region)
        if row and row["date"] < end and (row["level"] or 0) > 0:
            out.append({"region": region, "date": iso(row["date"]), "level": int(row["level"]), "said": row.get("said") or ""})
    return out


def pending(days: Dict[date, Dict[str, Any]], now: datetime) -> Optional[Dict[str, Any]]:
    """The workout to ask about: the latest strength or hard session that ended in the last PROMPT_HOURS hours with
    nothing written about it yet."""
    now = now.replace(tzinfo=None)
    for d in sorted(days, reverse=True)[:3]:
        for s in reversed(days[d]["sessions"]):
            start = _minute(s["start"])
            end = start + timedelta(minutes=s["minutes"])
            if s.get("hard") and s.get("note") is None and end <= now and now - end <= timedelta(hours=PROMPT_HOURS):
                return {"date": iso(d), "start": s["start"], "end": iso(end), "type": s["type"], "minutes": s["minutes"],
                        "effort": s.get("effort"), "effort_source": s.get("effort_source")}
    return None


def words() -> List[List[List[str]]]:
    return [[list(w), list(r)] for w, r in REGION_WORDS]


def prompt(ctx: Context) -> Dict[str, Any]:
    """For every page: the workout to ask about, and what the ask needs (the figure, the regions, the note words)."""
    days = daily_load(ctx, ctx.today)
    annotate(days, workout_notes(ctx))
    return {"page": "prompt", "today": iso(ctx.today), "now": iso(ctx.now), "session": pending(days, ctx.now),
            "regions": list(SORE_REGIONS), "areas": areas(), "words": words(),
            "rule": {"hard_effort": HARD_EFFORT, "hours": PROMPT_HOURS}}


def areas() -> List[Dict[str, Any]]:
    """The places as the page asks about them: each area with its sides and faces (schema.SORE_AREAS)."""
    return [{"area": a, "sides": list(sides), "faces": list(faces)} for a, sides, faces in SORE_AREAS]


def soreness(ctx: Context, end: date, log: Dict[date, Dict[str, int]],
             trained: Optional[Dict[date, List[str]]] = None) -> Dict[str, Any]:
    """Today's soreness (what was said today), and the last SORE_DAYS days of every region said in them."""
    trained = trained or {}
    days = [end - timedelta(days=k) for k in range(SORE_DAYS - 1, -1, -1)]
    said = {r for d in days for r in log.get(d, {})}
    regions = []
    for region in [r for r in ALL_SORE_REGIONS if r in said]:
        levels = [log[d][region] for d in days if region in log.get(d, {})]
        regions.append({"key": region, "legacy": region in LEGACY_REGIONS,
                        "days": [{"date": iso(d), "level": log.get(d, {}).get(region),
                                  "trained": region in trained.get(d, ())} for d in days],
                        "sore_days": sum(1 for v in levels if v), "said_days": len(levels), "max": max(levels, default=0),
                        "trained_days": sum(1 for d in days if region in trained.get(d, ()))})
    today = log.get(end, {})
    return {"today": bool(today), "levels": {r: lv for r, lv in today.items() if lv > 0},
            "fine_today": [r for r, lv in today.items() if lv == 0], "said_days": sum(1 for d in days if log.get(d)),
            "days": SORE_DAYS, "regions": regions, "follow_up": follow_up(ctx, end)}


def response(ctx: Context, end: date, days: Dict[date, Dict[str, Any]], log: Dict[date, Dict[str, int]]) -> Dict[str, Any]:
    """The next morning after hard days against the other known days (see the module's docstring)."""
    first = end - timedelta(days=RESPONSE_DAYS - 1)
    window = {d: v for d, v in days.items() if first <= d <= end and v["minutes"] == v["rated_min"]}  # fully rated
    trained = [v["load"] for v in window.values() if v["load"] > 0]
    median = statistics.median(trained) if len(trained) >= stats.MIN_GROUP_DAYS else None
    rows_all = [r for r in ctx.store.rows("body_daily") if r.get("complete") is not False]
    hrv, rhr = stats.series(rows_all, "hrv_ms"), stats.series(rows_all, "resting_hr")

    def outcome(key: str, d: date) -> Optional[float]:
        morning = d + timedelta(days=1)
        if key == "sore_max":
            return float(max(log[morning].values(), default=0)) if morning in log else None
        values = hrv if key == "hrv" else rhr
        band = stats.typical(values, morning) if morning in values else None
        if band is None:
            return None
        return (values[morning] / band["median"] - 1) * 100 if key == "hrv" else values[morning] - band["median"]

    rows = []
    for key in OUTCOMES:
        yes: List[float] = []
        no: List[float] = []
        if median is not None:
            for d, v in window.items():
                value = outcome(key, d)
                if value is not None:
                    (yes if v["load"] > median else no).append(value)
        rows.append({"outcome": key, "yes_days": len(yes), "no_days": len(no), **stats.compare(yes, no)})
    tested = [r for r in rows if r["status"] == "ok"]
    for r, adjusted in zip(tested, stats.benjamini_hochberg([r["p"] for r in tested])):
        r["p_adjusted"] = adjusted
        r["detected"] = adjusted < stats.FDR
    return {"from": iso(first), "to": iso(end), "median_load": median, "training_days": len(trained), "rows": rows,
            "better": OUTCOME_BETTER, "units": OUTCOME_UNITS,
            "method": {"min_group_days": stats.MIN_GROUP_DAYS, "fdr": stats.FDR}}


def _part(value: float, centre: float, width: float, higher_better: bool = True) -> float:
    steps = (value - centre) / width
    return max(0.0, min(10.0, 5 + 2.5 * (steps if higher_better else -steps)))


def _normal(values: stats.Series, day: date, floor: float) -> Optional[Dict[str, float]]:
    band = stats.typical(values, day)
    return None if band is None else {"median": band["median"], "width": max(band["q3"] - band["q1"], floor)}


def after_training(ctx: Context, end: date, days: Dict[date, Dict[str, Any]],
                   trained: Optional[Dict[date, List[str]]] = None,
                   log: Optional[Dict[date, Dict[str, int]]] = None) -> Dict[str, Any]:
    """The score the morning after each training day (see the module's docstring), newest first, with the regions it
    trained (when noted) and their soreness that morning (when checked in)."""
    rows = [r for r in ctx.store.rows("body_daily") if r.get("complete") is not False or r["date"] == end]
    hrv, rhr, sleep = stats.series(rows, "hrv_ms"), stats.series(rows, "resting_hr"), stats.series(rows, "sleep_min")
    eff = {r["date"]: r["sleep_min"] / r["in_bed_min"] * 100 for r in rows
           if r.get("sleep_min") and r.get("in_bed_min") and r["in_bed_min"] >= r["sleep_min"]}
    feel = {r["date"]: r["feel"] for r in ctx.store.rows("self_report") if r.get("feel") is not None}
    change = {d: v - hrv[d - timedelta(days=1)] for d, v in hrv.items() if d - timedelta(days=1) in hrv}  # morning to morning
    out = []
    # today's training is listed too (its morning has not come: no score yet)
    for d in sorted((d for d, v in days.items() if v["minutes"] > 0 and end - timedelta(days=AFTER_DAYS) < d <= end), reverse=True):
        m = d + timedelta(days=1)
        parts: Dict[str, Dict[str, Any]] = {}
        if m in feel:
            parts["feel"] = {"value": feel[m], "score": float(feel[m])}
        n = _normal(change, m, SPREAD_FLOOR["hrv"])
        if m in change and n:
            parts["hrv"] = {"before": hrv[d], "after": hrv[m], "usual_change": n["median"], "width": n["width"],
                            "score": _part(change[m], n["median"], n["width"])}
        n = _normal(rhr, m, SPREAD_FLOOR["resting_hr"])
        if m in rhr and n:
            parts["resting_hr"] = {"value": rhr[m], "median": n["median"], "width": n["width"],
                                   "score": _part(rhr[m], n["median"], n["width"], higher_better=False)}
        n = _normal(sleep, m, SPREAD_FLOOR["sleep"])
        if m in sleep and n:
            scores = [_part(sleep[m], n["median"], n["width"])]
            e = _normal(eff, m, SPREAD_FLOOR["efficiency"])
            part = {"value": sleep[m], "median": n["median"]}
            if m in eff and e:
                scores.append(_part(eff[m], e["median"], e["width"]))
                part.update(efficiency=eff[m], efficiency_median=e["median"])
            part["score"] = sum(scores) / len(scores)
            parts["sleep"] = part
        body = [k for k in ("hrv", "resting_hr", "sleep") if k in parts]
        score = sum(p["score"] for p in parts.values()) / len(parts) if len(parts) >= 2 and body else None
        out.append({"date": iso(d), "morning": iso(m), "load": days[d]["load"], "minutes": days[d]["minutes"],
                    "sessions": days[d]["sessions"], "parts": parts, "missing": [k for k in PARTS if k not in parts],
                    "trained": (trained or {}).get(d, []),
                    "sore_next": None if log is None or m not in log else {r: log[m].get(r) for r in (trained or {}).get(d, [])},
                    "score": score, "band": None if score is None else "good" if score >= GOOD else "low" if score < LOW else "ok"})
    return {"days": out, "latest": next((x for x in out if x["score"] is not None), None),
            "rule": {"good": GOOD, "low": LOW, "floor": SPREAD_FLOOR, "after_days": AFTER_DAYS}}


def build(ctx: Context, day: Optional[str] = None) -> Dict[str, Any]:
    from .. import hrv_model
    from .. import assistant, care_log, routines
    from . import body, care, drain, focus, restore, recovery_forecast, timed_recovery
    end = min(date.fromisoformat(day) if day else ctx.today, ctx.today)
    days = daily_load(ctx, end)
    annotate(days, workout_notes(ctx))
    trained = trained_on(days)
    log = soreness_log(ctx)
    forecast = recovery_forecast.build(ctx, end, log)
    care_payload = care.build(ctx, end)
    shown = (care_payload["moves"] or {}).get("routines", [])
    care_payload["info"], care_payload["stop"] = routines.info(shown), routines.STOP
    ratings = timed_recovery.build(ctx, end, forecast)
    return {"page": "recovery", "day": iso(end), "today": iso(ctx.today), "now": iso(ctx.now),
            "restore": restore.build(ctx) if end == ctx.today else None,
            "recovery": today_page.recovery(ctx, end),
            "self": today_page.self_report(ctx, end),
            "cardio": body.cardio(ctx, end),
            "hrv_prediction": hrv_model.build(ctx, end),
            "drain": drain.build(ctx, day),  # the long view at the end of the page (Wear and tear)
            "focus": focus.today(ctx, end),  # the third gauge: the focus budget and today's deep focus (modules/focus.py)
            "care": care_payload,  # where it feels tight: the report, its moves, tomorrow's question (modules/care.py)
            "care_choices": {"regions": list(routines.REGIONS), "feelings": list(routines.FEELINGS), "signs": list(care_log.SIGNS),
                             "assistant": dict(zip(("on", "why"), assistant.available(ctx.cfg)))},
            "forecast": forecast, "current_ratings": ratings,
            "load": load_summary(days, end),
            "soreness": soreness(ctx, end, log, trained),
            "after": after_training(ctx, end, days, trained, log),
            "words": words(),
            "feel_today": next((r["feel"] for r in ctx.store.rows("self_report") if r["date"] == end and r.get("feel") is not None), None),
            "response": response(ctx, end, days, log),
            "regions": list(SORE_REGIONS), "areas": areas(), "sore_assistant": dict(zip(("on", "why"), assistant.available(ctx.cfg))),
            "rule": {"follow_days": FOLLOW_DAYS, "acute": ACUTE, "chronic": CHRONIC, "min_rated": MIN_RATED_SHARE, "sore_days": SORE_DAYS,
                     "response_days": RESPONSE_DAYS}}
