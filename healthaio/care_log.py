"""Where it feels tight, and the short moves you did: a private log beside healthaio.toml, apart from the data tables.

body_care.jsonl is append-only, one event a line, written under the app's writer lock with a server timestamp:
- report: the regions that feel tight, stiff, achy or painful (routines.REGIONS / FEELINGS), what you said in your own
  words if you said something, whether you think sitting brought it on, and the warning signs you ticked (any sign
  means no moves are offered, only the line on seeing someone);
- done: a routine you did, and why it was offered (the sitting reminder or the check-in);
- answer: the next day, how a reported region feels now (better, same, worse).
Request ids make a retry safe. Like restore.jsonl it never changes a measured sample, and a damaged line is an error,
never quietly an empty history.
"""
import json
import os
import re
import secrets
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from . import routines, state

FILENAME = "body_care.jsonl"
OPS = ("report", "done", "answer")
CAUSES = ("sitting", "training", "other", None)
SIGNS = ("numb", "spreading", "worse", "night", "injury")  # see routines.STOP
WHY = ("sitting", "care")
CHANGE = ("better", "same", "worse")
REQUEST_ID = re.compile(r"^[A-Za-z0-9_-]{8,80}$")


def path(cfg) -> Path:
    return Path(cfg.root) / FILENAME


def moment(cfg, now=None) -> datetime:
    value = now or datetime.now(cfg.tz)
    return value.replace(tzinfo=cfg.tz) if value.tzinfo is None else value.astimezone(cfg.tz)


def read(cfg) -> List[Dict[str, Any]]:
    file = path(cfg)
    if not file.exists():
        return []
    out = []
    for i, line in enumerate(file.read_text(encoding="utf-8").splitlines(), 1):
        try:
            e = json.loads(line)
            if not isinstance(e, dict) or e.get("op") not in OPS or not e.get("id") or state.parse_iso(e.get("at")) is None:
                raise ValueError()
        except (ValueError, TypeError):
            raise ValueError(f"body care log line {i} could not be read; keep the file and repair it") from None
        out.append(e)
    return out


def _report(request: Dict[str, Any]) -> Dict[str, Any]:
    tight = request.get("tight")
    if not isinstance(tight, dict) or not tight or len(tight) > len(routines.REGIONS):
        raise ValueError("name at least one region, each with how it feels")
    for region, feel in tight.items():
        if region not in routines.REGIONS or feel not in routines.FEELINGS:
            raise ValueError("unknown region or feeling")
    said = request.get("said") or ""
    if not isinstance(said, str) or len(said) > 280:
        raise ValueError("what you said: at most 280 characters")
    signs = request.get("signs") or []
    if not isinstance(signs, list) or any(s not in SIGNS for s in signs):
        raise ValueError("unknown warning sign")
    cause = request.get("cause")
    if cause not in CAUSES:
        raise ValueError("unknown cause")
    parsed = request.get("parsed_by")
    if parsed not in (None, "assistant", "rules"):
        raise ValueError("unknown parser")
    return {"tight": dict(tight), "said": said.strip(), "signs": sorted(set(signs)), "cause": cause, "parsed_by": parsed}


def from_browser(cfg, request, now=None) -> Dict[str, Any]:
    if not isinstance(request, dict) or request.get("op") not in OPS:
        raise ValueError("unknown body care action")
    request_id = request.get("request_id")
    if not isinstance(request_id, str) or not REQUEST_ID.fullmatch(request_id):
        raise ValueError("a request_id of 8–80 letters, digits, hyphens or underscores is required")
    op = request["op"]
    allowed = {"op", "request_id"} | {"report": {"tight", "said", "signs", "cause", "parsed_by"},
                                      "done": {"routine", "why"}, "answer": {"ref", "region", "change"}}[op]
    if request.keys() - allowed:
        raise ValueError("unexpected fields in body care action")
    when = moment(cfg, now)
    with state.write_lock(cfg):
        entries = read(cfg)
        for e in entries:
            if e.get("request_id") == request_id:
                if e["request"] != request:
                    raise ValueError("request_id already used for a different action")
                return {"ok": True, "id": e["id"], "replayed": True}
        if entries and when < state.parse_iso(entries[-1]["at"]):
            raise ValueError("server time is earlier than the last body care record")
        event = {"v": 1, "id": secrets.token_hex(12), "at": when.isoformat(timespec="seconds"), "op": op,
                 "request_id": request_id, "request": request}
        if op == "report":
            event.update(_report(request))
        elif op == "done":
            if request.get("routine") not in routines.BY_ID or request.get("why") not in WHY:
                raise ValueError("unknown routine or reason")
            event.update(routine=request["routine"], why=request["why"])
        else:
            report = next((e for e in entries if e["op"] == "report" and e["id"] == request.get("ref")), None)
            if not report or request.get("region") not in report["tight"] or request.get("change") not in CHANGE:
                raise ValueError("answer a region of a report that exists, with better, same or worse")
            event.update(ref=report["id"], region=request["region"], change=request["change"])
        file = path(cfg)
        file.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(file, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        with os.fdopen(fd, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
    return {"ok": True, "id": event["id"]}
