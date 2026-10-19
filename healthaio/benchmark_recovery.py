"""Read-only PMData benchmark: original readiness and global soreness endpoints.

This evaluates method transfer, not predictions for the app's owner. February
selects between baseline and contextual matching; March is untouched until then.
Participant histories are never pooled. No personal health data is read.
"""
import argparse
import csv
import hashlib
import json
import statistics
from datetime import date, timedelta
from pathlib import Path

from .modules.recovery_forecast import _baseline, _episodes, _context, _match_context, _window


def number(raw):
    try: return float(raw)
    except (ValueError, TypeError): return None


def evaluate(groups, key, first, last):
    results = {name: {"eligible": 0, "issued": 0, "observed": 0, "unresolved": 0, "hits": 0, "errors": [], "cases": {}}
               for name in ("history", "context")}
    for participant, person in groups.items():
        values = {d: r[key] for d, r in person.items() if r[key] is not None}
        body = {d: {"date": d, "sleep_min": r["sleep"], "workout_min": r["training"], "resting_hr": r["rhr"], "complete": True}
                for d, r in person.items()}
        kind = "energy" if key == "readiness" else "soreness"
        for day in sorted(d for d in values if first <= d <= last):
            known = {d: v for d, v in values.items() if d <= day}
            target = _baseline(known, day) if kind == "energy" else max(0, values[day] - 1)
            if target is None or (values[day] >= target if kind == "energy" else values[day] <= target):
                continue
            histories = _episodes(known, day, values[day], kind, body)
            matched, _ = _match_context(histories, _context(body, day))
            actual = None
            for n in range(1, 8):
                future = day + timedelta(days=n)
                if future > last or future not in values: break
                if values[future] >= target if kind == "energy" else values[future] <= target:
                    actual = n
                    break
            for name, cohort in (("history", histories), ("context", matched)):
                r = results[name]
                r["eligible"] += 1
                prediction = _window(cohort)
                if prediction["status"] != "estimated": continue
                r["issued"] += 1
                if actual is None:
                    r["unresolved"] += 1
                    continue
                r["observed"] += 1
                r["errors"].append(abs(actual - prediction["median_days"]))
                r["cases"][participant + ":" + day.isoformat()] = r["errors"][-1]
                r["hits"] += prediction["range_days"][0] <= actual <= prediction["range_days"][1]
    for r in results.values():
        r["mae_days"] = round(statistics.mean(r.pop("errors")), 3) if r["observed"] else None
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pmdata-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    source = args.pmdata_dir / "daily.csv"
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    groups = {}
    with source.open(newline="", encoding="utf-8-sig") as stream:
        for r in csv.DictReader(stream):
            day = date.fromisoformat(r["date"])
            sore = number(r.get("soreness"))
            groups.setdefault(r["participant"], {})[day] = {
                "readiness": number(r.get("readiness")),
                # PMData: 1 most sore, 5 least sore. Reverse direction only;
                # keep four ordinal steps, never fabricate regional severity.
                "global_soreness": 5 - sore if sore is not None and 1 <= sore <= 5 else None,
                "sleep": number(r.get("sleep_minutes")), "training": number(r.get("training_minutes")),
                "rhr": number(r.get("resting_hr"))}
    report = {"source": "PMData processed daily table", "source_sha256": before,
              "participants": len(groups), "validation": "2020-02", "test": "2020-03",
              "personal_data_used": False, "endpoints": {}}
    for key in ("readiness", "global_soreness"):
        validation = evaluate(groups, key, date(2020, 2, 1), date(2020, 2, 29))
        base, candidate = validation["history"], validation["context"]
        common = sorted(base["cases"].keys() & candidate["cases"].keys())
        gain = statistics.mean(base["cases"][k] - candidate["cases"][k] for k in common) if common else None
        selected = "context" if len(common) >= 8 and gain > 0 and candidate["issued"] >= base["issued"] else "history"
        for r in validation.values(): r.pop("cases")
        test = evaluate(groups, key, date(2020, 3, 1), date(2020, 3, 31))
        for r in test.values(): r.pop("cases")
        report["endpoints"][key] = {"selected_before_test": selected, "paired_validation_n": len(common), "paired_validation_gain_days": gain, "validation": validation, "test": test,
                                  "selected_test": test[selected]}
    assert before == hashlib.sha256(source.read_bytes()).hexdigest()
    report["limits"] = ["Global soreness is not regional soreness severity.",
                        "Readiness is not the owner's energy self-rating.",
                        "Coverage and unresolved endpoints are reported; errors use observed outcomes only.",
                        "Sparse daily sampling cannot validate hourly recovery times."]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
