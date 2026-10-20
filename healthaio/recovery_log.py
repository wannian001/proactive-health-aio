"""Explicit current-time, original 0–10 ratings; separate from legacy morning CSVs."""
import json
import math
import os
import re
import secrets
from datetime import datetime, timezone
from pathlib import Path

from . import state
from .schema import ALL_SORE_REGIONS, SORE_REGIONS

FILENAME = "recovery_observations.jsonl"
REQUEST_ID = re.compile(r"[A-Za-z0-9_-]{8,80}\Z")


def moment(cfg, now=None):
    now = now or datetime.now(cfg.tz or timezone.utc)
    return now.replace(tzinfo=cfg.tz or timezone.utc) if now.tzinfo is None else now


def read(cfg):
    path = Path(cfg.root) / FILENAME
    if not path.exists():
        return []
    rows = []
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            try:
                r = json.loads(line)
                at = datetime.fromisoformat(r["at"])
                valid = (r["v"] == 1 and at.tzinfo is not None and r["scale"] == 10
                         and r["kind"] in ("energy", "soreness")
                         and (r["region"] in ALL_SORE_REGIONS if r["kind"] == "soreness" else r["region"] is None)
                         and not isinstance(r["value"], bool) and isinstance(r["value"], (int, float))
                         and math.isfinite(r["value"]) and 0 <= r["value"] <= 10
                         and isinstance(r["id"], str) and bool(REQUEST_ID.fullmatch(r["request_id"])))
                if "reported_range" in r:
                    bounds = r["reported_range"]
                    valid = valid and isinstance(bounds, list) and len(bounds) == 2 and all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) and 0 <= v <= 10 for v in bounds) and bounds[0] <= bounds[1] and r["value"] == sum(bounds)/2
                if "note" in r:
                    valid = valid and isinstance(r["note"], str) and len(r["note"]) <= 160
                if not valid:
                    raise ValueError()
            except (ValueError, TypeError, KeyError):
                raise ValueError("Invalid recovery observation log; retain the file and repair it before saving.") from None
            if rows and at < datetime.fromisoformat(rows[-1]["at"]):
                raise ValueError("Recovery observations are out of time order.")
            rows.append(r)
    return rows


def from_browser(cfg, request, now=None):
    if not isinstance(request, dict) or not {"request_id", "kind", "region", "value"} <= set(request) or set(request) - {"request_id", "kind", "region", "value", "note"}:
        raise ValueError("Use request_id, kind, region and value.")
    if not isinstance(request["request_id"], str) or not REQUEST_ID.fullmatch(request["request_id"]):
        raise ValueError("Invalid request_id.")
    kind, region, value = request["kind"], request["region"], request["value"]
    reported_range = None
    note = request.get("note", "")
    if not isinstance(note, str) or len(note) > 160:
        raise ValueError("Note must be at most 160 characters.")
    if isinstance(value, list):
        if len(value) != 2 or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or not 0 <= v <= 10 for v in value) or value[0] > value[1]:
            raise ValueError("Use an ordered rating range within 0–10.")
        reported_range = list(value)
        value = sum(value) / 2  # drawing coordinate only; original range is always retained
    if kind not in ("energy", "soreness") or (region not in SORE_REGIONS if kind == "soreness" else region is not None):
        raise ValueError("Choose a supported metric and region.")
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 10:
        raise ValueError("Rating must be between 0 and 10.")
    at = moment(cfg, now)
    with state.write_lock(cfg):
        rows = read(cfg)
        for r in rows:
            if r["request_id"] == request["request_id"]:
                if r["kind"] != kind or r["region"] != region or r["value"] != value or r.get("reported_range") != reported_range or r.get("note", "") != note:
                    raise ValueError("request_id already used for a different rating.")
                return {"ok": True, "id": r["id"], "at": r["at"], "replayed": True}
        if rows and at < datetime.fromisoformat(rows[-1]["at"]):
            raise ValueError("Server clock precedes the latest saved observation.")
        row = dict(request, value=value, v=1, id=secrets.token_hex(12), at=at.isoformat(timespec="seconds"), scale=10)
        if reported_range is not None: row["reported_range"] = reported_range
        if note: row["note"] = note
        path = Path(cfg.root) / FILENAME
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
    return {"ok": True, "id": row["id"], "at": row["at"], "replayed": False}
