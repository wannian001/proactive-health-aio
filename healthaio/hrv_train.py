"""Train on a private AIO profile, with calendar splits and portable JSON output.

Requires numpy/scikit-learn ONLY during explicit training. The web app remains
standard-library-only. Never writes the personal-system sources or diary.
"""
import argparse
import json
import math
import os
import random
import statistics
import tempfile
from datetime import date, timedelta
from pathlib import Path

from . import config, hrv_model as core, state
from .store import Store

BASELINES = ("median28", "mean7", "last")
CANDIDATES = [{"name":f"ridge_{group}_a{alpha}_h{half}", "kind":"ridge", "feature_set":group,
               "alpha":alpha,"half_life_days":half}
              for group in ("hrv", "context") for alpha in (1.,10.,100.) for half in (365,730)]


def fit(rows, spec):
    import numpy as np
    from sklearn.linear_model import Ridge
    from sklearn.preprocessing import StandardScaler
    if spec["kind"] in BASELINES: return {"kind":spec["kind"]}, 0.
    keys = core.HRV_FEATURES + (core.CONTEXT_FEATURES if spec["feature_set"] == "context" else ())
    raw = np.array([[r["features"][k] if r["features"][k] is not None else np.nan for k in keys] for r in rows])
    # Everything learned about preprocessing belongs to this training fold.
    med = np.array([float(np.median(col[~np.isnan(col)])) if (~np.isnan(col)).any() else 0. for col in raw.T])
    x = np.column_stack([np.where(np.isnan(raw),med,raw),np.isnan(raw).astype(float)])
    scaler = StandardScaler().fit(x)
    x = scaler.transform(x)
    y = np.array([math.log(r["actual"]/r["base"]) for r in rows])
    last = date.fromisoformat(rows[-1]["target_date"])
    weight = np.array([r["base"]*2**(-(last-date.fromisoformat(r["target_date"])).days/spec["half_life_days"]) for r in rows])
    weight /= weight.mean()
    estimator = Ridge(alpha=spec["alpha"]).fit(x,y,sample_weight=weight)
    packed = dict(spec,features=list(keys),medians=med.tolist(),means=scaler.mean_.tolist(),scales=scaler.scale_.tolist(),
                  coef=estimator.coef_.tolist(),intercept=float(estimator.intercept_))
    expected = np.array([r["base"] for r in rows])*np.exp(np.clip(estimator.predict(x),-1.,1.))
    difference = max(abs(core.predict(r,packed)-v) for r,v in zip(rows,expected))
    if difference > 1e-7: raise ValueError("Inference parity failed")
    return packed, float(difference)


def score(rows, fitted):
    return statistics.mean(abs(core.predict(r,fitted)-r["actual"]) for r in rows)


def difference_interval(cases):
    """Exploratory paired bootstrap, preserving non-overlapping calendar weeks."""
    start=date.fromisoformat(cases[0]["date"]);blocks={}
    for r in cases:
        blocks.setdefault((date.fromisoformat(r["date"])-start).days//7,[]).append(
            abs(r["prediction"]-r["actual"])-abs(r["baseline"]-r["actual"]))
    groups=list(blocks.values());rng=random.Random(20261019)
    samples=sorted(statistics.mean(v for group in rng.choices(groups,k=len(groups)) for v in group) for _ in range(2000))
    return [samples[49],samples[1949]]


def partition(data):
    latest = date.fromisoformat(data[-1]["target_date"])
    test_start = latest-timedelta(days=179)
    calibration_start = test_start-timedelta(days=90)
    folds = []
    for offset in (270,180,90):
        start = calibration_start-timedelta(days=offset)
        stop = start+timedelta(days=90)
        train = [r for r in data if date.fromisoformat(r["target_date"]) < start]
        valid = [r for r in data if start <= date.fromisoformat(r["target_date"]) < stop]
        if len(train) < 180 or len(valid) < 25: raise ValueError("Not enough data in chronological folds")
        folds.append((train,valid))
    before_cal = [r for r in data if r["target_date"] < calibration_start.isoformat()]
    cal = [r for r in data if calibration_start.isoformat() <= r["target_date"] < test_start.isoformat()]
    development = [r for r in data if r["target_date"] < test_start.isoformat()]
    test = [r for r in data if r["target_date"] >= test_start.isoformat()]
    if len(cal)<30 or len(test)<60: raise ValueError("Not enough calibration or test outcomes")
    return folds,before_cal,cal,development,test


def train(rows, as_of):
    import sklearn
    cleaned = core.clean_rows(rows,as_of-timedelta(days=1))
    data = core.pairs(cleaned)
    if len(data)<600: raise ValueError("At least 600 complete next-day pairs are required")
    folds,precal,cal,dev,test = partition(data)
    specs = [{"name":x,"kind":x} for x in BASELINES] + CANDIDATES
    results = []
    for spec in specs:
        errors=[]; counts=[]
        for training,valid in folds:
            fitted,_=fit(training,spec)
            errors.append(score(valid,fitted));counts.append(len(valid))
        results.append({"name":spec["name"],"fold_mae_ms":errors,"validation_n":sum(counts),
                        "mae_ms":sum(e*n for e,n in zip(errors,counts))/sum(counts)})
    selected=min(results,key=lambda r:r["mae_ms"])["name"]
    learned=min((r for r in results if r["name"].startswith("ridge_")),key=lambda r:r["mae_ms"])["name"]
    spec=next(s for s in specs if s["name"]==selected)
    learned_spec=next(s for s in specs if s["name"]==learned)
    # Freeze selection before calibration/test. Never retune on holdout results.
    calibrator,_=fit(precal,spec)
    residuals=sorted(abs(core.predict(r,calibrator)-r["actual"]) for r in cal)
    half=residuals[min(len(residuals)-1,math.ceil(.8*(len(residuals)+1))-1)]
    evaluation_fit,_=fit(dev,spec)
    cases=[{"date":r["target_date"],"actual":r["actual"],"prediction":core.predict(r,evaluation_fit),
            "baseline":r["base"]} for r in test]
    mae=statistics.mean(abs(r["prediction"]-r["actual"]) for r in cases)
    base_mae=statistics.mean(abs(r["baseline"]-r["actual"]) for r in cases)
    monthly={}
    for r in cases:
        monthly.setdefault(r["date"][:7],[]).append(r)
    monthly=[{"month":k,"n":len(v),"mae_ms":statistics.mean(abs(r["prediction"]-r["actual"]) for r in v),
              "baseline_mae_ms":statistics.mean(abs(r["baseline"]-r["actual"]) for r in v)} for k,v in monthly.items()]
    # The final fit may use all observed labels only AFTER frozen holdout evaluation.
    deployed,parity=fit(data,spec)
    learned_fit,learned_parity=fit(data,learned_spec)
    through=max(cleaned)
    result={"version":core.VERSION,"created_on":as_of.isoformat(),"trained_through":through.isoformat(),
            "source_sha256":core.fingerprint(cleaned,through),"selected":selected,"learned_selected":learned,
            "fit":deployed,"learned_fit":learned_fit,"interval_halfwidth_ms":half,
            "training":{"pairs":len(data),"hrv_days":sum(core.value(cleaned,d,"hrv_ms") is not None for d in cleaned),
                        "first_target":data[0]["target_date"],"last_target":data[-1]["target_date"],
                        "sklearn_version":sklearn.__version__,"parity_max_abs_ms":max(parity,learned_parity)},
            "selection":{"candidates":results,"calibration_n":len(cal),"calibration_start":cal[0]["target_date"],
                         "calibration_end":cal[-1]["target_date"],"test_used_for_selection":False},
            "evaluation":{"n":len(test),"start":test[0]["target_date"],"end":test[-1]["target_date"],
                          "train_through":dev[-1]["target_date"],"mae_ms":mae,"baseline_mae_ms":base_mae,
                          "difference_ms":mae-base_mae,"relative_improvement":1-mae/base_mae if base_mae else None,
                          "difference_ci95_ms":difference_interval(cases),
                          "interval_nominal":.8,"interval_coverage":sum(abs(r["prediction"]-r["actual"])<=half for r in cases)/len(cases),
                          "monthly":monthly,"cases":cases},
            "limits":["Daily observed HRV only, not pain, subjective energy or a clinical recovery score.",
                      "Historical calendar holdout; no prospective accuracy claim.",
                      "Intervals use earlier calibration residuals; time dependence prevents a probability guarantee.",
                      "No future-night sleep or future-day measurements are features."]}
    return core.validate(result)


def save(cfg, model):
    root=Path(cfg.root)
    with state.write_lock(cfg):
        fd,tmp=tempfile.mkstemp(prefix=".hrv_model-",suffix=".json",dir=root)
        try:
            with os.fdopen(fd,"w") as stream:
                json.dump(model,stream,ensure_ascii=False,allow_nan=False,indent=2);stream.flush();os.fsync(stream.fileno())
            core.validate(json.loads(Path(tmp).read_text()))
            os.replace(tmp,root/core.FILENAME)
        finally:
            if Path(tmp).exists(): Path(tmp).unlink()


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config",type=Path,required=True)
    p.add_argument("--as-of",type=date.fromisoformat,required=True)
    p.add_argument("--apply",action="store_true")
    args=p.parse_args(argv);cfg=config.load(args.config);store=Store(cfg.data_dir)
    if any(r.get("table") == "body_daily" for r in store.problems()): raise ValueError("Resolve body table errors before training")
    rows=store.rows("body_daily")
    if not args.apply:
        data=core.pairs(core.clean_rows(rows,args.as_of-timedelta(days=1)))
        print(json.dumps({"mode":"dry_run","pairs":len(data),"out":str(cfg.root/core.FILENAME)}));return 0
    model=train(rows,args.as_of)
    fresh=core.clean_rows(Store(cfg.data_dir).rows("body_daily"),args.as_of-timedelta(days=1))
    if core.fingerprint(fresh,date.fromisoformat(model["trained_through"])) != model["source_sha256"]:
        raise ValueError("Training source changed; no model installed")
    save(cfg,model)
    print(json.dumps({"selected":model["selected"],"training":model["training"],
                      "evaluation":{k:v for k,v in model["evaluation"].items() if k not in ("cases","monthly")}},indent=2))
    return 0


if __name__ == "__main__": raise SystemExit(main())
