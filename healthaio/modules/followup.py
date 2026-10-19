"""Follow-up: did yesterday's advice happen, and when a piece of advice keeps not happening, another way to do it.

Saying what to do each morning is half of being proactive; the other half is noticing whether it happened and, when
the same reminder keeps failing, changing the approach instead of repeating it. This page does both, from the data
alone: there is nothing to tick.

Rules
- A past day's advice is rebuilt from the data as it stood that morning, with the same rules as the Today page
  (modules/actions.py). The sleep, food and screen rules read only last night and the days before, so a rebuild gives
  what the page said then. Training advice reads the day's own workouts (what is left of the week), so a rebuild
  would already know the answer: it is listed, not checked.
- Each piece of advice is checked against what the data shows afterwards. No record is "no record", never a miss.
  - asleep_by: asleep that night no more than 15 minutes after the time given.
  - phone_away: no more than 15 minutes of entertainment & social in the hour before falling asleep that night.
  - late_meal: the last meal that day at least plan.food.last_meal_gap_h before falling asleep (a logged day).
  - protein: that day's protein at least 90% of the target (a logged day).
  - kcal: that day's energy at or under the plan's maximum (a logged day).
  - fun_cap: that day's entertainment & social at or under the cap (a whole screen day).
- The last 14 days: how often each piece of advice was given and on how many of the days with a record it was kept.
  Counts, never streaks or scores.
- Another way: advice not kept on 3 or more of the last 5 times it was given (with a record) gets three concrete
  alternatives with your own numbers instead of the same reminder: a smaller step (halfway between what you have
  been doing and the target, then three days in a row before moving on), letting the phone or the room do the
  remembering, and an if-then plan ("if it is 00:30, I put the phone on the charger in the living room"). If-then
  plans are among the better-tested ways to close the gap between meaning to and doing (Gollwitzer & Sheeran 2006, a
  meta-analysis of 94 studies, d = 0.65). These are habits, not medical advice.
- Tomorrow will be better ("effects", modules/today.py effects()): what has gone with a better next day, the days
  after doing something against the days after not, with 95% intervals and Benjamini-Hochberg. It closes the loop:
  whether the advice was kept is above, whether keeping it helped is here. It used to be on a Weekly review page,
  whose week-of-facts table nobody needed.
"""
import statistics
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from ..context import FUN, Context, iso
from . import actions
from . import food as food_page
from . import plans
from . import today as today_page

DAYS = 14
TOLERANCE_MIN = 15  # asleep_by: minutes after the time given that still count
CALM_MIN = 15  # phone_away: entertainment & social minutes in the last hour that still count
STUCK_OF = 5  # the last this many times the advice was given, with a record ...
STUCK_MISSED = 3  # ... with at least this many misses: try another way
COOK_MIN = 45  # late_meal: the alarm to start cooking, this long before dinner should be over
CHECKED = ("asleep_by", "phone_away", "late_meal", "protein", "kcal", "fun_cap")


def advice_on(ctx: Context, day: date) -> Dict[str, Any]:
    """The Today page's advice for ``day``, as it read that morning."""
    return actions.build(ctx, day, today_page.recovery(ctx, day), today_page.drain_summary(ctx, day))


def _minutes_between(a: datetime, b: datetime) -> float:
    return (a - b).total_seconds() / 60


def check(ctx: Context, item: Dict[str, Any], day: date, meals: Dict[date, Dict[str, Any]]) -> Dict[str, Any]:
    """Whether the data shows ``item`` (advice given on ``day``) happened: met True / False / None, and the fact."""
    key, q = item["key"], item.get("params") or {}
    if key not in CHECKED:
        return {"checked": False, "met": None, "fact": None}
    met: Optional[bool] = None
    fact: Optional[Dict[str, Any]] = None
    if key == "asleep_by":
        start = (ctx.store.by_date("body_daily").get(day + timedelta(days=1)) or {}).get("sleep_start")
        if start and q.get("clock"):
            late = _minutes_between(start, datetime.fromisoformat(q["clock"]))
            met, fact = late <= TOLERANCE_MIN, {"asleep": iso(start), "late_min": late}
    elif key == "phone_away":
        fun = ctx.fun_before_sleep(day)
        if fun is not None:
            met, fact = fun <= CALM_MIN, {"minutes": fun}
    elif key in ("late_meal", "protein", "kcal"):
        d = meals.get(day)
        if d and d["full"]:
            if key == "late_meal" and d["late"] is not None:
                met, fact = not d["late"], {"last": iso(d["last"]), "gap_h": d["gap_h"]}
            elif key == "protein" and d.get("protein_g") is not None and q.get("target_g"):
                met, fact = d["protein_g"] >= actions.PROTEIN_SHORT * q["target_g"], {"grams": d["protein_g"]}
            elif key == "kcal" and d.get("kcal") is not None and q.get("max") is not None:
                met, fact = d["kcal"] <= q["max"], {"kcal": d["kcal"]}
    elif key == "fun_cap":
        sd = ctx.screen_known_days().get(day)
        if sd is not None and q.get("hours") is not None:
            fun = sd.share(FUN)
            met, fact = fun <= q["hours"] * 60, {"minutes": fun}
    return {"checked": True, "met": met, "fact": fact}


def _half_step(now: float, target: float, step: float) -> float:
    """Halfway from what you have been doing to the target, rounded to ``step``."""
    return round((now + target) / 2 / step) * step


def _since_noon(t: Any) -> float:
    """Minutes after noon of a time of day ("HH:MM" or an ISO time), so 23:00 < 01:00 the night after."""
    if isinstance(t, str):
        t = datetime.fromisoformat(t) if "T" in t else datetime.strptime(t, "%H:%M")
    return (t.hour * 60 + t.minute - 12 * 60) % (24 * 60)


def _clock(minutes_since_noon: float, round_to: int = 15) -> str:
    m = int(round(minutes_since_noon / round_to) * round_to + 12 * 60) % (24 * 60)
    return f"{m // 60:02d}:{m % 60:02d}"


def _halfway_clock(times: List[Any], target: Any) -> Optional[str]:
    """Halfway from the median of ``times`` to ``target``, to 15 minutes; None when that is the target already."""
    if not times:
        return None
    goal = _since_noon(target)
    step = _clock((statistics.median(_since_noon(t) for t in times) + goal) / 2)
    return None if step == _clock(goal) else step


def ways(key: str, given: List[Dict[str, Any]], tonight: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Other ways to do ``key``, with numbers from the times it was given (with a record, newest last). When there is
    a smaller step, the phone setting and the if-then plan use it too, so the three say the same thing."""
    q = given[-1].get("params") or {}
    facts = [g["fact"] for g in given if g.get("fact")]
    out: List[Dict[str, Any]] = []
    if key in ("asleep_by", "phone_away"):
        phone = q.get("clock") if key == "phone_away" else (tonight or {}).get("phone_away")
        phone = _clock(_since_noon(phone), 1) if phone else None
        if key == "asleep_by":
            step = _halfway_clock([f["asleep"] for f in facts], q["clock"])
            if step:
                out.append({"kind": "smaller", "params": {"clock": step}})
                phone = _clock(_since_noon(step) - plans.PHONE_AWAY_MIN, 1)
        out.append({"kind": "setting", "params": {"clock": phone}})
        if key == "phone_away":
            out.append({"kind": "place", "params": {}})
        out.append({"kind": "if_then", "params": {"clock": phone}})
    elif key == "late_meal":
        clock = _clock(_since_noon(q["clock"]), 1) if q.get("clock") else None
        if clock:
            step = _halfway_clock([f["last"] for f in facts], clock)
            if step:
                out.append({"kind": "smaller", "params": {"clock": step}})
                clock = step
            out.append({"kind": "setting", "params": {"clock": _clock(_since_noon(clock) - COOK_MIN, 1)}})
        out.append({"kind": "if_then", "params": {"clock": clock, "hours": q.get("hours")}})
    elif key == "protein":
        if q.get("more_g") and q["more_g"] >= 10:
            out.append({"kind": "smaller", "params": {"g": round(q["more_g"] / 2 / 5) * 5}})
        out.append({"kind": "place", "params": {}})
        out.append({"kind": "if_then", "params": {}})
    elif key == "kcal":
        eaten = [f["kcal"] for f in facts]
        if eaten and q.get("max") is not None:
            step = _half_step(statistics.median(eaten), q["max"], 50)
            if step > q["max"]:
                out.append({"kind": "smaller", "params": {"kcal": step}})
        out.append({"kind": "place", "params": {}})
        out.append({"kind": "if_then", "params": {}})
    elif key == "fun_cap":
        hours = q.get("hours")
        spent = [f["minutes"] / 60 for f in facts]
        if spent and hours is not None:
            step = _half_step(statistics.median(spent), hours, 0.5)
            if step > hours:
                out.append({"kind": "smaller", "params": {"hours": step}})
                hours = step
        out.append({"kind": "setting", "params": {"hours": hours}})
        out.append({"kind": "place", "params": {}})
        out.append({"kind": "if_then", "params": {}})
    return out


def responses(ctx: Context, end: date) -> Dict[str, Any]:
    """The two other "how the body answered" analyses that "Tomorrow will be better" holds: the morning after hard
    training days (recovery.response) and the night and morning after stimulating screen days (time.response)."""
    from . import recovery, time as screen
    days = recovery.daily_load(ctx, end)
    recovery.annotate(days, recovery.workout_notes(ctx))
    seen = [d for d in screen.data_days(ctx) if d < end]
    return {"training_response": recovery.response(ctx, end, days, recovery.soreness_log(ctx)),
            "training_days": recovery.RESPONSE_DAYS,
            "screen_response": screen.response(ctx, seen[-1], screen.stim_series(ctx)) if seen else None}


def build(ctx: Context, day: Optional[str] = None) -> Dict[str, Any]:
    from . import restore
    end = min(date.fromisoformat(day) if day else ctx.today, ctx.today)
    window = [end - timedelta(days=k) for k in range(DAYS, 0, -1)]  # oldest first; yesterday last
    meals = food_page.food_days(ctx, end)
    days: List[Dict[str, Any]] = []
    for d in window:
        advice = advice_on(ctx, d)
        items = [{**x, **check(ctx, x, d, meals)} for x in advice["items"]]
        days.append({"date": iso(d), "items": items, "steady": advice["steady"]})

    rows = []
    for key in [k for k in actions.KEYS if any(x["key"] == k for day_ in days for x in day_["items"])]:
        given = [{**x, "date": day_["date"]} for day_ in days for x in day_["items"] if x["key"] == key]
        known = [g for g in given if g["met"] is not None]
        recent = known[-STUCK_OF:]
        stuck = len(recent) >= STUCK_MISSED and sum(1 for g in recent if g["met"] is False) >= STUCK_MISSED
        rows.append({"key": key, "domain": given[-1]["domain"], "checked": given[-1]["checked"], "given": len(given),
                     "known": len(known), "kept": sum(1 for g in known if g["met"]),
                     "dots": [{"date": g["date"], "met": g["met"]} for g in given],
                     "last": {k: given[-1].get(k) for k in ("date", "params", "met", "fact")},
                     "stuck": stuck, "ways": ways(key, known, plans.tonight(ctx, end)) if stuck else []})

    yesterday = days[-1]
    shown = [x for x in yesterday["items"] if x["checked"]]
    return {"page": "followup", "day": iso(end), "today": iso(ctx.today), "now": iso(ctx.now),
            "restore": restore.build(ctx) if end == ctx.today else None,
            "yesterday": yesterday,
            "yesterday_kept": sum(1 for x in shown if x["met"]), "yesterday_known": sum(1 for x in shown if x["met"] is not None),
            "dates": [iso(d) for d in window], "rows": rows, "stuck": [r["key"] for r in rows if r["stuck"]],
            "given_days": sum(1 for d in days if d["items"]),
            "effects": today_page.effects(ctx, end), **responses(ctx, end),
            "rule": {"days": DAYS, "tolerance_min": TOLERANCE_MIN, "calm_min": CALM_MIN,
                     "stuck_of": STUCK_OF, "stuck_missed": STUCK_MISSED}}
