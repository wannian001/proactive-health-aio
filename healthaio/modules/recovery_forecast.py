"""Personal, daily-resolution recovery estimates from observed trajectories.

No population recovery time, health score or physiological model. One anchor per
episode; missing follow-up is right-censored, never recovery. The empirical
Kaplan–Meier middle-half window is descriptive, not a calibrated probability.
All lookups stop at the selected date. See docs/RECOVERY_FORECAST.md.
"""
import statistics
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from ..context import Context, iso
from ..schema import SORE_REGIONS

HISTORY_DAYS = 365
HORIZON = 7
MIN_EPISODES = 5
MIN_EVENTS = 3
BASELINE_DAYS = 28
MIN_BASELINE = 10
RECENT_DAYS = 90
VERSION = "personal-trajectory-v1"


def _baseline(values: dict, day: date) -> Optional[float]:
    past = [v for d, v in values.items() if day - timedelta(days=BASELINE_DAYS) <= d < day]
    return float(statistics.median(past)) if len(past) >= MIN_BASELINE else None


def _context(body: dict, day: date) -> dict:
    # Only completed days BEFORE the anchor: no later-in-the-day activity leakage.
    rows = [body.get(day - timedelta(days=i)) for i in (1, 2, 3)]
    out = {}
    for field, name in (("sleep_min", "sleep"), ("workout_min", "training")):
        values = [r[field] for r in rows if r and r.get("complete") is not False and r.get(field) is not None]
        if len(values) == 3:
            out[name] = sum(values) / 3 if name == "sleep" else sum(values)
    for field, name, floor in (("hrv_ms", "hrv", 2.), ("resting_hr", "rhr", 1.)):
        recent = [r[field] for r in rows if r and r.get("complete") is not False and r.get(field) is not None]
        baseline = [r[field] for d, r in body.items() if day - timedelta(days=28) <= d < day
                    and r.get("complete") is not False and r.get(field) is not None]
        if len(recent) == 3 and len(baseline) >= 10:
            ordered = sorted(baseline)
            width = max(floor, ordered[int(.75 * (len(ordered) - 1))] - ordered[int(.25 * (len(ordered) - 1))])
            out[name] = (statistics.mean(recent) - statistics.median(baseline)) / width
    return out


def _phase(values: dict, day: date, target: float, kind: str) -> Optional[int]:
    """Observed days since last target reading; a gap makes phase unknown."""
    for age in range(1, HORIZON + 2):
        value = values.get(day - timedelta(days=age))
        if value is None:
            return None
        if (value >= target if kind == "energy" else value <= target):
            return age
    return HORIZON + 2  # a prolonged episode, never matched to a fresh onset


def _episodes(values: dict, end: date, current: float, kind: str, body: dict) -> List[dict]:
    """Match one start per episode; don't restart after a missing day or horizon.

    Soreness: same level, endpoint at least one level lower. Energy: deficit
    within 0.5 of the current deficit, endpoint the anchor's own prior-28d median.
    A new episode needs an observed endpoint of the previous one first.
    """
    target_now = _baseline(values, end) if kind == "energy" else current - 1
    if target_now is None:
        return []
    phase_now = _phase(values, end, target_now, kind)
    blocked_target = None
    anchors = []
    for d in sorted(values):
        if not end - timedelta(days=HISTORY_DAYS) <= d < end:
            continue
        v = values[d]
        if blocked_target is not None:
            recovered = v >= blocked_target if kind == "energy" else v <= blocked_target
            if not recovered:
                continue
            blocked_target = None
        target = _baseline(values, d) if kind == "energy" else current - 1
        match = (target is not None and v < target and abs((target - v) - (target_now - current)) <= .5
                 if kind == "energy" else v == current)
        if match and phase_now is not None and _phase(values, d, target, kind) != phase_now:
            match = False
        if not match:
            continue
        blocked_target = target
        duration, event = 0, False
        for step in range(1, HORIZON + 1):
            following = d + timedelta(days=step)
            if following > end or following not in values:
                break
            duration = step
            event = values[following] >= target if kind == "energy" else values[following] <= target
            if event:
                break
        anchors.append({"start": iso(d), "through": iso(d + timedelta(days=duration)),
                        "days": duration, "event": event, "value": v, "target": target,
                        "context": _context(body, d), "phase_days": _phase(values, d, target, kind)})
    return anchors


def _match_context(episodes: List[dict], context: dict) -> tuple:
    """Refine only when enough examples remain; otherwise label the broad match."""
    keys = [k for k in ("sleep", "training", "hrv", "rhr") if k in context]
    if not keys:
        return episodes, []
    matched = [e for e in episodes if all(k in e["context"] and
               abs(e["context"][k] - context[k]) <= (60 if k == "sleep" else max(30, context[k] * .5) if k == "training" else 1.5)
               for k in keys)]
    if sum(e["days"] > 0 for e in matched) >= MIN_EPISODES:
        return matched, keys
    return episodes, []


def _window(episodes: List[dict]) -> dict:
    usable = [e for e in episodes if e["days"] > 0]
    n = len(usable)
    events = sum(e["event"] for e in usable)
    out = {"status": "insufficient", "n": n, "events": events, "censored": n - events,
           "no_followup": len(episodes) - n, "range_days": None, "median_days": None}
    if n < MIN_EPISODES:
        return out
    if events < MIN_EVENTS:
        return dict(out, status="few_outcomes")
    # Heavy missingness is not safely summarized by the observed quick recoveries.
    if (len(episodes) - events) / len(episodes) > .4:
        return dict(out, status="incomplete")
    survival, quantiles = 1., {}
    for step in range(1, HORIZON + 1):
        risk = sum(e["days"] >= step for e in usable)
        hits = sum(e["event"] and e["days"] == step for e in usable)
        if risk:
            survival *= 1 - hits / risk
        for q in (.25, .5, .75):
            if q not in quantiles and 1 - survival >= q - 1e-9:
                quantiles[q] = step
    if .75 not in quantiles:
        return dict(out, status="beyond_horizon")
    return dict(out, status="estimated", range_days=[quantiles[.25], quantiles[.75]],
                median_days=quantiles[.5])


def _backtest(episodes: List[dict], values: dict, kind: str, body: dict) -> dict:
    """Rebuild every historical prediction using only that anchor's prefix."""
    errors, hits, issued = [], 0, 0
    for test in episodes:
        cutoff = date.fromisoformat(test["start"])
        known = {d: v for d, v in values.items() if d <= cutoff}
        past = _episodes(known, cutoff, known[cutoff], kind, body)
        selected, _ = _match_context(past, test["context"])
        prediction = _window(selected)
        if prediction["status"] != "estimated":
            continue
        issued += 1
        if test["event"]:
            errors.append(abs(prediction["median_days"] - test["days"]))
            hits += prediction["range_days"][0] <= test["days"] <= prediction["range_days"][1]
    return {"predictions": issued, "observed": len(errors), "inside_range": hits,
            "mean_absolute_days": round(statistics.mean(errors), 2) if errors else None,
            "scope": "retrospective_complete_endpoints_only"}


def _forecast(values: dict, end: date, kind: str, body: dict) -> Dict[str, Any]:
    value = values.get(end)
    out = {"as_of": iso(end), "value": value, "scale": 5 if kind == "energy" else 3, "status": "missing_current", "range_days": None,
           "median_days": None, "target": None, "n": 0, "events": 0, "censored": 0,
           "no_followup": 0, "matched_context": [], "evidence": [], "validation": None}
    if value is None:
        return out
    target = _baseline(values, end) if kind == "energy" else max(0, value - 1)
    out["target"] = target
    if target is None:
        return dict(out, status="baseline_needed")
    if (kind == "energy" and value >= target) or (kind == "soreness" and value == 0):
        return dict(out, status="at_target")
    all_episodes = _episodes(values, end, value, kind, body)
    episodes, matched = _match_context(all_episodes, _context(body, end))
    result = _window(episodes)
    # Require a recent matched observation, not only last year's recoveries.
    recent = [e for e in episodes if e["days"] > 0 and
              date.fromisoformat(e["start"]) >= end - timedelta(days=RECENT_DAYS)]
    if result["status"] == "estimated" and not recent:
        result.update(status="old_history", range_days=None, median_days=None)
    out.update(result, matched_context=matched, evidence=episodes,
               validation=_backtest(all_episodes, values, kind, body),
               phase_days=_phase(values, end, target, kind))
    if out["range_days"]:
        out["range_dates"] = [iso(end + timedelta(days=n)) for n in out["range_days"]]
    return out


def build(ctx: Context, end: date, soreness_log: dict) -> dict:
    body = {r["date"]: r for r in ctx.store.rows("body_daily") if r["date"] < end}
    energy = {r["date"]: r["energy"] for r in ctx.store.rows("self_report")
              if r["date"] <= end and r.get("energy") is not None}
    log = {d: r for d, r in soreness_log.items() if d <= end}
    # an older morning check-in covered every region (one not listed was not sore); since soreness is said when felt,
    # a region not said that day is unknown
    whole = {r["date"] for r in ctx.store.rows("soreness") if r.get("at") is None}
    regions = {region: _forecast({d: levels.get(region, 0) for d, levels in log.items() if d in whole or region in levels},
                                 end, "soreness", body)
               for region in SORE_REGIONS}
    result = {"version": VERSION, "as_of": iso(end), "demo": ctx.cfg.demo,
              "energy": _forecast(energy, end, "energy", body), "soreness": regions,
              "rule": {"history_days": HISTORY_DAYS, "horizon_days": HORIZON, "min_episodes": MIN_EPISODES,
                       "min_events": MIN_EVENTS, "baseline_days": BASELINE_DAYS, "min_baseline": MIN_BASELINE,
                       "window": "empirical_middle_half", "resolution": "day", "experimental": True}}
    # Invalid rows must not disappear into an apparently complete personal forecast.
    for kind, table in (("energy", "self_report"), ("soreness", "soreness")):
        if ctx.store.load(table).problems:
            items = [result["energy"]] if kind == "energy" else list(regions.values())
            for item in items:
                item.update(status="invalid_records", range_days=None, median_days=None)
                item.pop("range_dates", None)
    return result
