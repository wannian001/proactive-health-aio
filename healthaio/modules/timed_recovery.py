"""Interval-aware estimates from explicit, timestamped 0–10 check-ins.

Dates-only legacy ratings remain in recovery_forecast.py. No conversion between
scales. Sparse timestamped observations produce day ranges, never an hourly ETA.
"""
import math
import statistics
from datetime import datetime, timedelta

from .. import recovery_log
from .recovery_forecast import _context, _match_context

MAX_HOURS = 168
MIN_EPISODES = 5


def _quantile(values, q):
    return sorted(values)[max(0, math.ceil(len(values) * q) - 1)]


def _baseline(points, at):
    # At most one comparable-time rating per date, so frequent logging adds no weight.
    days = {}
    for p in points:
        if at - timedelta(days=28) <= p["at"] < at and p["at"].date() < at.date():
            delta = abs((p["at"].hour + p["at"].minute / 60) - (at.hour + at.minute / 60))
            if min(delta, 24 - delta) <= 3:
                days[p["at"].date()] = p["value"]
    return float(statistics.median(days.values())) if len(days) >= 10 else None


def _cohort(points, kind, body):
    current = points[-1]
    now, value = current["at"], current["value"]
    target_now = _baseline(points[:-1], now) if kind == "energy" else max(0, min(2, value - 1))
    if target_now is None:
        return target_now, [], False, []
    gaps = [(b["at"] - a["at"]).total_seconds() / 3600 for a, b in zip(points, points[1:])
            if b["at"] > a["at"]]
    dense = len(gaps) >= 12 and statistics.median(gaps) <= 8
    max_gap = 8 if dense else 36
    episodes, blocked = [], None
    for i, p in enumerate(points[:-1]):
        reached = lambda v, target: v >= target if kind == "energy" else v <= target
        if blocked is not None:
            if not reached(p["value"], blocked):
                continue
            blocked = None
        target = _baseline(points[:i], p["at"]) if kind == "energy" else target_now
        if target is None or reached(p["value"], target):
            continue
        if abs((target - p["value"]) - (target_now - value)) > 1:
            continue
        blocked = target
        lower, upper, previous = 0., math.inf, p["at"]
        for later in points[i + 1:]:
            elapsed = (later["at"] - p["at"]).total_seconds() / 3600
            if elapsed > MAX_HOURS or (later["at"] - previous).total_seconds() / 3600 > max_gap:
                break
            if reached(later["value"], target):
                upper = elapsed
                break
            lower, previous = elapsed, later["at"]
        episodes.append({"start": p["at"].isoformat(), "lower": lower,
                         "upper": upper if math.isfinite(upper) else None,
                         "event": math.isfinite(upper), "days": max(lower, upper if math.isfinite(upper) else 0) / 24,
                         "context": _context(body, p["at"].date()), "target": target})
    selected, matched = _match_context(episodes, _context(body, now.date()))
    # The common matcher counts distinct episodes with any positive follow-up.
    return target_now, selected, dense, matched


def _estimate(episodes, dense):
    n = len(episodes)
    events = sum(e["event"] for e in episodes)
    result = {"status": "insufficient", "n": n, "events": events, "censored": n - events,
              "range_hours": None, "range_days": None, "median_hours": None}
    if n < MIN_EPISODES:
        return result
    if events < 3:
        return dict(result, status="few_outcomes")
    # Interval bounds include unfinished episodes with an infinite upper bound.
    lo = _quantile([e["lower"] for e in episodes], .25)
    hi = _quantile([e["upper"] if e["upper"] is not None else math.inf for e in episodes], .75)
    if not math.isfinite(hi):
        return dict(result, status="incomplete")
    mid_lo = _quantile([e["lower"] for e in episodes], .5)
    mid_hi = _quantile([e["upper"] if e["upper"] is not None else math.inf for e in episodes], .5)
    unit = 1 if dense else 24
    # Never imply a precise instant within a diary interval; lower may legitimately be zero.
    window = [math.floor(lo / unit) * unit, math.ceil(hi / unit) * unit]
    result.update(status="estimated", range_hours=window, median_hours=round((mid_lo + mid_hi) / 2, 1),
                  resolution="hour" if dense else "day", interval_method="empirical_quantile_bounds")
    if not dense:
        result["range_days"] = [int(x / 24) for x in window]
    return result


def forecast(points, kind, now, body, validate=True):
    unique = {p["at"]: p for p in points if now - timedelta(days=365) <= p["at"] <= now}
    points = [unique[k] for k in sorted(unique)][-2000:]
    out = {"status": "missing_current", "scale": 10, "value": None, "target": None,
           "range_days": None, "range_hours": None, "n": 0, "events": 0, "censored": 0,
           "no_followup": 0, "matched_context": [], "evidence": [], "validation": None,
           "method": "timestamped_intervals_v1", "as_of": now.isoformat()}
    if not points or now - points[-1]["at"] > timedelta(hours=24):
        return out
    current = points[-1]
    out.update(value=current["value"], recorded_at=current["at"].isoformat())
    if current.get("reported_range") is not None:
        return dict(out, status="range_rating", value_range=current["reported_range"])
    points = [p for p in points if p.get("reported_range") is None]
    target, cohort, dense, matched = _cohort(points, kind, body)
    out["target"] = target
    out["matched_context"] = matched
    if target is None:
        return dict(out, status="baseline_needed")
    if (current["value"] >= target if kind == "energy" else current["value"] <= target):
        return dict(out, status="at_target")
    out.update(_estimate(cohort, dense))
    if out["status"] == "estimated":
        if not any(datetime.fromisoformat(e["start"]) >= now - timedelta(days=90) for e in cohort):
            out.update(status="old_history", range_hours=None, range_days=None)
        else:
            # Range is measured from the latest actual rating, not page-open time.
            dates = [current["at"] + timedelta(hours=x) for x in out["range_hours"]]
            if dates[-1] < now:
                out.update(status="refresh_needed", range_hours=None, range_days=None)
            else:
                out["range_timestamps"] = [d.isoformat() for d in dates]
                out["range_hours"] = [max(0, math.floor((dates[0] - now).total_seconds() / 3600)),
                                      max(1, math.ceil((dates[1] - now).total_seconds() / 3600))]
                if not dense:
                    out["range_days"] = [math.floor(out["range_hours"][0] / 24), math.ceil(out["range_hours"][1] / 24)]
    out["evidence"] = [{"start": e["start"], "event": e["event"], "lower_hours": e["lower"], "upper_hours": e["upper"]} for e in cohort]
    if validate:
        errors, count = [], 0
        for e in cohort[-24:]:
            cutoff = datetime.fromisoformat(e["start"])
            prior = [p for p in points if p["at"] <= cutoff]
            _, train, is_dense, _ = _cohort(prior, kind, body)
            prediction = _estimate(train, is_dense)
            if prediction["status"] != "estimated" or not e["event"]:
                continue
            count += 1
            # Interval outcome: zero error when point falls inside observed bounds.
            pred = prediction["median_hours"]
            errors.append(max(e["lower"] - pred, pred - e["upper"], 0))
        out["interval_validation"] = {"observed": count, "mean_interval_error_hours": statistics.mean(errors) if errors else None}
    return out


def build(ctx, end, daily_forecast):
    now = recovery_log.moment(ctx.cfg, ctx.now)
    if end < now.date():
        now = datetime.combine(end, datetime.max.time(), tzinfo=ctx.cfg.tz or now.tzinfo)
    body = {r["date"]: r for r in ctx.store.rows("body_daily") if r["date"] < end}
    rows = recovery_log.read(ctx.cfg)
    state = {"soreness": {}, "energy": None, "scale": 10}
    for kind, region in [("energy", None)] + [("soreness", r) for r in daily_forecast["soreness"]]:
        points = [{"at": datetime.fromisoformat(r["at"]).astimezone(now.tzinfo), "value": r["value"], "reported_range": r.get("reported_range")}
                  for r in rows if r["kind"] == kind and r["region"] == region]
        f = forecast(points, kind, now, body)
        if f["value"] is not None:
            if kind == "energy":
                state["energy"] = f
                daily_forecast["energy"] = f
            else:
                state["soreness"][region] = f
                daily_forecast["soreness"][region] = f
    return state
