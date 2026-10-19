"""Explicit read-only bridge from a personal-system tree to a private AIO profile.

Only named numeric/date health columns are imported. Notes, IDs, raw samples,
credentials and coursework participants never enter the profile. No Git calls.
"""
import argparse
import csv
import hashlib
import json
import math
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from .store import write_table, Store
from .schema import TABLES

SOURCES = ["Data/staged/body/apple_health_daily.csv", "Data/staged/body/daily_state_preview.csv",
           "Data/staged/body/sleep_times.csv", "Data/staged/body/daily.csv"]


def _number(value):
    try:
        x = float(value)
        return x if math.isfinite(x) else None
    except (ValueError, TypeError):
        return None


def prepare(source, until):
    source = Path(source).resolve()
    for marker in ("AI_README.md", "AGENTS.md", "AIOS", "Vault"):
        if not (source / marker).exists():
            raise ValueError("Source is not a confirmed personal-system working tree.")
    sys.path.insert(0, str(source))
    try:
        from Runtime.storage_paths import storage_paths_for
        if not Path(sys.modules["Runtime.storage_paths"].__file__).resolve().is_relative_to(source):
            raise ValueError("Storage resolver belongs to a different source tree.")
        resolver = storage_paths_for(source)
    finally:
        sys.path.pop(0)
    tables, provenance = [], []
    for rel in SOURCES:
        path = resolver.resolve_private(rel)
        if not path.is_file():
            tables.append([])
            provenance.append({"source": rel, "available": False})
            continue
        raw = path.read_bytes()
        with path.open(encoding="utf-8-sig", newline="") as stream:
            rows = list(csv.DictReader(stream))
        accepted = []
        for row in rows:
            if str(row.get("is_fixture", "")).lower() in ("true", "1") or row.get("record_status") in ("test", "excluded") or row.get("health_maturity") == "test":
                continue
            try:
                day = date.fromisoformat(row["date"])
            except (KeyError, ValueError):
                continue
            if day <= until:
                accepted.append(row)
        if raw != path.read_bytes():
            raise ValueError("Source changed during import; retry after synchronization settles.")
        tables.append(accepted)
        provenance.append({"source": rel, "available": True, "sha256": hashlib.sha256(raw).hexdigest(), "rows": len(accepted)})
    merged = {}
    for rows in tables[:2]:  # live daily projection has precedence for an overlapping date
        for row in rows:
            d = row["date"]
            mapped = {"date": d}
            for src, dst in (("sleep_duration_min", "sleep_min"), ("in_bed_min", "in_bed_min"),
                             ("hrv", "hrv_ms"), ("resting_hr", "resting_hr"), ("steps", "steps"),
                             ("exercise_min", "exercise_min"), ("active_kcal", "active_kcal"),
                             ("body_weight_kg", "weight_kg")):
                mapped[dst] = _number(row.get(src))
            minutes = _number(row.get("training_min"))
            mapped["workout_min"] = minutes if minutes is not None else 0 if str(row.get("workout_done")).lower() == "false" else None
            mapped["complete"] = date.fromisoformat(d) < until
            received = row.get("health_sync_received_at")
            if received:
                try:
                    from zoneinfo import ZoneInfo
                    when = datetime.fromisoformat(received.replace("Z", "+00:00"))
                    if when.tzinfo and when.astimezone(ZoneInfo("Australia/Melbourne")).date() <= date.fromisoformat(d):
                        mapped["complete"] = False
                except ValueError:
                    mapped["complete"] = False
            merged[d] = mapped
    for row in tables[2]:
        if row["date"] in merged:
            for key in ("sleep_start", "sleep_end"):
                raw = row.get(key)
                if raw:
                    try:
                        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                        # Preserve the clock/zone convention of the original sleep projection.
                        merged[row["date"]][key] = parsed.replace(tzinfo=None).isoformat(timespec="minutes")
                    except ValueError:
                        pass
    energy = []
    for row in tables[3]:
        value = _number(row.get("qi_energy"))
        if value is not None and 0 <= value <= 5:
            energy.append({"date": row["date"], "energy": value})
    rows = [merged[d] for d in sorted(merged)]
    rejected = {}
    for row in rows:
        for col in TABLES["body_daily"].columns:
            value = row.get(col.name)
            try:
                col.parse("" if value is None else str(int(value)) if isinstance(value, bool) else str(value))
            except ValueError:
                rejected[col.name] = rejected.get(col.name, 0) + 1
                row[col.name] = None  # explicitly unknown; original file stays unchanged
    summary = {"excluded_measurements": rejected, "body_days": len(rows), "first_date": rows[0]["date"] if rows else None,
               "last_date": rows[-1]["date"] if rows else None, "legacy_energy_days": len(energy),
               "regional_soreness_days": 0, "source_kind": "personal_system_private_snapshot",
               "as_of": until.isoformat(), "sources": provenance,
               "limitations": ["No self-report is inferred from device measurements.",
                               "No region-level history imported; unsupported or absent regions remain unknown.",
                               "No workout timestamps are fabricated from daily totals."]}
    return rows, energy, summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--until", type=date.fromisoformat, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    body, energy, summary = prepare(args.source, args.until)
    if args.apply:
        out = args.out.expanduser().resolve()
        if out.exists():
            raise ValueError("Output exists; use a new private profile directory to preserve earlier records.")
        if out.is_relative_to(Path(__file__).resolve().parents[1]) or out.is_relative_to(args.source.resolve()):
            raise ValueError("Use a private directory outside the source/code worktrees.")
        out.mkdir(parents=True, mode=0o700)
        try:
            write_table(out / "data", "body_daily", body)
            if energy:
                write_table(out / "data", "self_report", energy)
            problems = Store(out / "data").problems()
            if problems:
                raise ValueError("Imported rows failed AIO schema validation; profile not activated.")
            cfg = {"healthaio": {"data_dir": "data", "timezone": "Australia/Melbourne", "locale": "zh", "demo": False},
                   "updates": {"check": False}}
            (out / "healthaio.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=2))
            (out / "personal-source.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
            for p in out.rglob("*"):
                if p.is_file(): os.chmod(p, 0o600)
                elif p.is_dir(): os.chmod(p, 0o700)
        except Exception:
            # Keep the partial profile for diagnosis; no usable config is promised on failure.
            (out / "IMPORT_INCOMPLETE").write_text("Import failed. Retained for diagnosis; do not use as a completed profile.")
            raise
    print(json.dumps({k: v for k, v in summary.items() if k != "sources"}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
