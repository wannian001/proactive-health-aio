"""Shared, calendar-aware HRV features and dependency-free JSON inference.

Target: next complete calendar day's recorded HRV in ms, not an energy or pain
label. Training and inference share this code; no input after the anchor is used.
"""
import hashlib
import json
import math
import statistics
from datetime import date, timedelta
from pathlib import Path

VERSION = "personal-hrv-v1"
FILENAME = "hrv_model.json"
FIELDS = ("hrv_ms", "resting_hr", "sleep_min", "workout_min", "exercise_min", "steps", "complete")
HRV_FEATURES = ("hrv_now", "hrv_lag1", "hrv_mean3", "hrv_mean7", "hrv_median7",
                "hrv_median90", "hrv_cv28", "hrv_slope", "hrv_log_base", "hrv_coverage")
CONTEXT_FEATURES = ("rhr_deviation", "sleep_hours", "sleep_mean7", "training_3d", "steps_mean3", "exercise_mean3")


def finite(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def clean_rows(rows, until):
    out = {}
    for r in rows:
        d = r["date"] if isinstance(r["date"], date) else date.fromisoformat(r["date"])
        if d > until:
            continue
        if d in out:
            raise ValueError("Duplicate body date; resolve source ambiguity before training.")
        out[d] = {k: r.get(k) for k in FIELDS}
    return out


def fingerprint(rows, through):
    text = json.dumps([[d.isoformat(), rows[d]] for d in sorted(rows) if d <= through],
                      sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(text.encode()).hexdigest()


def value(rows, day, field):
    r = rows.get(day, {})
    v = r.get(field)
    if r.get("complete") is False or not finite(v) or v < 0:
        return None
    if field in ("hrv_ms", "resting_hr") and v <= 0:
        return None
    return float(v)


def window(rows, at, field, days):
    return [v for n in range(days) if (v := value(rows, at-timedelta(days=n), field)) is not None]


def features(rows, at):
    h = value(rows, at, "hrv_ms")
    past = window(rows, at, "hrv_ms", 28)
    if h is None or len(past) < 10:
        return None
    base = statistics.median(past)
    ratio = lambda v: math.log(v/base) if v is not None and v > 0 else None
    mean = lambda xs, minimum: statistics.mean(xs) if len(xs) >= minimum else None
    med = lambda xs, minimum: statistics.median(xs) if len(xs) >= minimum else None
    m3 = mean(window(rows, at, "hrv_ms", 3), 2)
    m7 = mean(window(rows, at, "hrv_ms", 7), 3)
    h7 = window(rows, at, "hrv_ms", 7)
    rhr = value(rows, at, "resting_hr")
    rb = med(window(rows, at, "resting_hr", 28), 10)
    sleep = value(rows, at, "sleep_min")
    sleep7 = mean(window(rows, at, "sleep_min", 7), 3)
    train = window(rows, at, "workout_min", 3)
    steps = mean(window(rows, at, "steps", 3), 2)
    exercise = mean(window(rows, at, "exercise_min", 3), 2)
    f = {"hrv_now": ratio(h), "hrv_lag1": ratio(value(rows, at-timedelta(days=1), "hrv_ms")),
         "hrv_mean3": ratio(m3), "hrv_mean7": ratio(m7), "hrv_median7": ratio(med(h7, 3)),
         "hrv_median90": ratio(med(window(rows, at, "hrv_ms", 90), 20)),
         "hrv_cv28": statistics.stdev(past)/base, "hrv_slope": ratio(m3)-ratio(m7) if m3 and m7 else None,
         "hrv_log_base": math.log(base), "hrv_coverage": len(past)/28,
         "rhr_deviation": (rhr-rb)/5 if rhr is not None and rb is not None else None,
         "sleep_hours": sleep/60 if sleep is not None else None, "sleep_mean7": sleep7/60 if sleep7 is not None else None,
         "training_3d": sum(train)/60 if len(train) == 3 else None,
         "steps_mean3": steps/1000 if steps is not None else None,
         "exercise_mean3": exercise/30 if exercise is not None else None}
    ordered = sorted(past)
    return {"anchor": at.isoformat(), "target_date": (at+timedelta(days=1)).isoformat(),
            "base": base, "current": h, "mean7": m7 or base, "features": f,
            "normal": [ordered[int(.25*(len(past)-1))], ordered[int(.75*(len(past)-1))]],
            "coverage": len(past)}


def pairs(rows):
    out = []
    for at in sorted(rows):
        actual = value(rows, at+timedelta(days=1), "hrv_ms")
        if actual is None:
            continue
        f = features(rows, at)
        if f:
            out.append(dict(f, actual=actual))
    return out


def predict(row, model):
    kind = model["kind"]
    if kind == "median28": return row["base"]
    if kind == "mean7": return row["mean7"]
    if kind == "last": return row["current"]
    raw = [row["features"][k] for k in model["features"]]
    x = [v if v is not None else model["medians"][i] for i, v in enumerate(raw)] + [float(v is None) for v in raw]
    z = model["intercept"] + sum(c*(v-m)/s for c,v,m,s in zip(model["coef"],x,model["means"],model["scales"]))
    return row["base"] * math.exp(max(-1., min(1., z)))


def validate(model):
    if not isinstance(model, dict) or model.get("version") != VERSION:
        raise ValueError("Unsupported HRV model.")
    for key in ("trained_through", "created_on"):
        date.fromisoformat(model[key])
    if model["trained_through"] >= model["created_on"] or not isinstance(model.get("selected"),str):
        raise ValueError("Invalid training dates or selection.")
    if not isinstance(model.get("source_sha256"), str) or len(model["source_sha256"]) != 64:
        raise ValueError("Missing source fingerprint.")
    for fit in (model["fit"], model["learned_fit"]):
        if fit["kind"] in ("median28", "mean7", "last"):
            continue
        if fit["kind"] != "ridge" or not fit["features"] or len(set(fit["features"])) != len(fit["features"]):
            raise ValueError("Unsupported fitted model.")
        if any(k not in HRV_FEATURES+CONTEXT_FEATURES for k in fit["features"]):
            raise ValueError("Unknown feature.")
        n = len(fit["features"])
        if len(fit["medians"]) != n or any(len(fit[k]) != 2*n for k in ("coef", "means", "scales")):
            raise ValueError("Invalid coefficient shape.")
        if not all(finite(v) for k in ("medians", "coef", "means", "scales") for v in fit[k]) or not finite(fit["intercept"]) or any(v <= 0 for v in fit["scales"]):
            raise ValueError("Invalid coefficients.")
    if not finite(model["interval_halfwidth_ms"]) or model["interval_halfwidth_ms"] < 0:
        raise ValueError("Invalid error interval.")
    if not isinstance(model["evaluation"]["cases"], list) or not isinstance(model["training"]["pairs"], int):
        raise ValueError("Missing evaluation.")
    e=model["evaluation"]
    if not all(finite(e[k]) and e[k]>=0 for k in ("mae_ms","baseline_mae_ms","interval_coverage")) or e["interval_coverage"]>1:
        raise ValueError("Invalid evaluation metrics.")
    if not e["cases"] or e["n"] != len(e["cases"]) or not e["train_through"] < e["start"] <= e["end"] <= model["trained_through"]:
        raise ValueError("Invalid evaluation chronology.")
    previous=""
    for c in model["evaluation"]["cases"]:
        date.fromisoformat(c["date"])
        if not e["start"] <= c["date"] <= e["end"] or c["date"] <= previous:
            raise ValueError("Unordered evaluation cases.")
        previous=c["date"]
        if not all(finite(c[k]) and c[k] > 0 for k in ("actual", "prediction", "baseline")):
            raise ValueError("Invalid held-out case.")
    json.dumps(model, allow_nan=False)
    return model


def build(ctx, end):
    path = Path(ctx.cfg.root)/FILENAME
    if not path.exists(): return {"status":"not_trained"}
    try:
        if path.stat().st_size > 2_000_000: raise ValueError("Model too large")
        model = validate(json.loads(path.read_text()))
        if date.fromisoformat(model["created_on"]) > ctx.today:
            raise ValueError("Model creation date is in the future")
        through = date.fromisoformat(model["trained_through"])
        # Fingerprint against the full current table. New rows are allowed;
        # revisions of training inputs require an explicit retrain.
        rows = clean_rows(ctx.store.rows("body_daily"), ctx.today-timedelta(days=1))
        if any(r.get("table") == "body_daily" for r in ctx.store.problems()):
            return {"status":"invalid_source"}
        if fingerprint(rows, through) != model["source_sha256"]:
            return {"status":"source_changed"}
        cases = [r for r in model["evaluation"]["cases"] if r["date"] <= end.isoformat()]
        out = {"status":"history_only", "version":VERSION, "model":model["selected"],
               "created_on":model["created_on"], "trained_through":through.isoformat(),
               "training":model["training"], "evaluation":{k:v for k,v in model["evaluation"].items() if k != "cases"},
               "history":cases[-60:], "demo":ctx.cfg.demo,
               "feature_groups":["hrv"] + (["sleep", "rhr", "activity"] if model["fit"].get("feature_set") == "context" else [])}
        if end < through: return out  # no future-trained backcast for a historical day
        anchor = max((d for d in rows if d <= end and value(rows,d,"hrv_ms") is not None), default=None)
        f = features(rows,anchor) if anchor else None
        if not f: return dict(out,status="insufficient_recent")
        estimate = predict(f,model["fit"])
        half = model["interval_halfwidth_ms"]
        target = date.fromisoformat(f["target_date"])
        return dict(out,status="stale_data" if target < ctx.today else "ready", anchor=f["anchor"],
                    target_date=f["target_date"], current=f["current"], prediction=estimate,
                    interval=[max(0.,estimate-half),estimate+half], normal=f["normal"],
                    latest_age_days=(ctx.today-anchor).days, coverage=f["coverage"],
                    model_age_days=(ctx.today-date.fromisoformat(model["created_on"])).days)
    except (ValueError,KeyError,TypeError,AttributeError,OSError,OverflowError):
        return {"status":"invalid_model"}
