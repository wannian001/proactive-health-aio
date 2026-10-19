"""Actual rest choices and optional reflections, separate from measured health data.

restore.jsonl lives beside healthaio.toml. Events are appended under the existing
writer lock. Server timestamps and request IDs make retries safe; finishing a
session never implies that it helped, and planning a reward never completes it.
"""
import json
import os
import re
import secrets
from datetime import datetime, timedelta
from pathlib import Path

from . import state

FILENAME = "restore.jsonl"
ACTIVITIES = ("sit", "music", "walk", "friend", "photo", "play")
# written by the app itself, not chosen from the library: a break away from the computer after a long stretch, as
# the Mac app saw it (auto_break); "remove" takes back one that wasn't a rest
AUTO_ACTIVITIES = ("break",)
OPS = {"checkin", "quiet", "resume", "start", "finish", "cancel", "feedback",
       "reward_plan", "reward_done", "reward_cancel", "auto", "remove"}
CHOICES = {"body": ("comfortable", "tired", "sore"),
           "mind": ("clear", "tired", "tense", "bored", "engaged"),
           "task": ("easy", "fit", "hard")}
REQUEST_ID = re.compile(r"^[A-Za-z0-9_-]{8,80}$")


def path(cfg):
    return Path(cfg.root) / FILENAME


def moment(cfg, now=None):
    value = now or datetime.now(cfg.tz)
    return value.replace(tzinfo=cfg.tz) if value.tzinfo is None else value.astimezone(cfg.tz)


def read(cfg):
    """A damaged log is an error, never silently an empty or successful history."""
    file = path(cfg)
    if not file.exists():
        return []
    entries = []
    for i, line in enumerate(file.read_text(encoding="utf-8").splitlines(), 1):
        try:
            e = json.loads(line)
            if not isinstance(e, dict) or e.get("op") not in OPS or not e.get("id"):
                raise ValueError()
            if state.parse_iso(e.get("at")) is None or not isinstance(e.get("request"), dict):
                raise ValueError()
        except (ValueError, TypeError):
            raise ValueError(f"restore log line {i} could not be read; preserve and repair the file") from None
        entries.append(e)
    return entries


def replay(entries):
    out = {"checkin": None, "quiet_until": None, "sessions": {}, "rewards": {}}
    for e in entries:
        op = e["op"]
        if op == "checkin":
            out["checkin"] = {"id": e["id"], "at": e["at"], **e["values"]}
        elif op in ("quiet", "resume"):
            out["quiet_until"] = e.get("until")
        elif op == "start":
            out["sessions"][e["id"]] = {"id": e["id"], "activity": e["activity"],
                "started_at": e["at"], "status": "active", "ended_at": None,
                "feedback": None, "context": e["context"]}
        elif op == "auto":
            out["sessions"][e["id"]] = {"id": e["id"], "activity": e["activity"], "started_at": e["start"],
                "status": "finished", "ended_at": e["end"], "feedback": None, "context": None, "auto": True,
                "after": e.get("after")}
        elif op == "remove":
            s = out["sessions"].get(e["ref"])
            if s:
                s["status"] = "removed"
        elif op in ("finish", "cancel", "feedback"):
            s = out["sessions"].get(e["ref"])
            if not s:
                raise ValueError("restore log refers to a missing session")
            if op == "feedback":
                s["feedback"] = {"at": e["at"], "change": e.get("change"), "enjoyment": e.get("enjoyment")}
            else:
                s.update(status="finished" if op == "finish" else "cancelled", ended_at=e["at"])
        elif op == "reward_plan":
            out["rewards"][e["id"]] = {"id": e["id"], "title": e["title"], "note": e["note"],
                                         "at": e["at"], "status": "planned", "ended_at": None}
        elif op in ("reward_done", "reward_cancel"):
            r = out["rewards"].get(e["ref"])
            if not r:
                raise ValueError("restore log refers to a missing reward")
            r.update(status="done" if op == "reward_done" else "cancelled", ended_at=e["at"])
    out["sessions"] = list(reversed(list(out["sessions"].values())))
    out["rewards"] = list(reversed(list(out["rewards"].values())))
    out["active"] = next((s for s in out["sessions"] if s["status"] == "active"), None)
    return out


def _text(value, name, required=False):
    if not isinstance(value, str) or len(value.strip()) > 120 or (required and not value.strip()):
        raise ValueError(f"{name}: use {'1–120' if required else 'at most 120'} characters")
    return value.strip()


def from_browser(cfg, request, now=None):
    if not isinstance(request, dict) or not isinstance(request.get("op"), str) or request["op"] not in OPS:
        raise ValueError("unknown recovery action")
    request_id = request.get("request_id")
    if not isinstance(request_id, str) or not REQUEST_ID.fullmatch(request_id):
        raise ValueError("a request_id of 8–80 letters, digits, hyphens or underscores is required")
    op = request["op"]
    allowed = {"op", "request_id"} | {
        "checkin": set(CHOICES), "start": {"activity"}, "finish": {"ref"}, "cancel": {"ref"},
        "feedback": {"ref", "change", "enjoyment"}, "reward_plan": {"title", "note"},
        "reward_done": {"ref"}, "reward_cancel": {"ref"}, "remove": {"ref"},
    }.get(op, set())
    if request.keys() - allowed:
        raise ValueError("unexpected fields in recovery action")
    when = moment(cfg, now)
    with state.write_lock(cfg):
        entries = read(cfg)
        for e in entries:
            if e.get("request_id") == request_id:
                if e["request"] != request:
                    raise ValueError("request_id already used for a different action")
                return {"ok": True, "id": e["id"], "replayed": True}
        current = replay(entries)
        if entries and when < state.parse_iso(entries[-1]["at"]):
            raise ValueError("server time is earlier than the last recovery record")
        event = {"v": 1, "id": secrets.token_hex(12), "at": when.isoformat(timespec="seconds"),
                 "op": op, "request_id": request_id, "request": request}
        if op == "checkin":
            values = {k: request.get(k) for k in CHOICES}
            if not any(v is not None for v in values.values()):
                raise ValueError("choose at least one feeling")
            if any(v is not None and v not in CHOICES[k] for k, v in values.items()):
                raise ValueError("unknown feeling")
            event["values"] = values
        elif op == "quiet":
            event["until"] = (when + timedelta(hours=2)).isoformat(timespec="seconds")
        elif op == "start":
            if request.get("activity") not in ACTIVITIES:
                raise ValueError("unknown recovery activity")
            if current["active"]:
                raise ValueError("finish or cancel the active activity first")
            from .context import Context
            from .modules.restore import situation
            event.update(activity=request["activity"],
                         context=situation(Context(cfg, now=when.replace(tzinfo=None)), current))
        elif op in ("finish", "cancel", "feedback"):
            s = next((s for s in current["sessions"] if s["id"] == request.get("ref")), None)
            if not s or s["status"] != ("finished" if op == "feedback" else "active"):
                raise ValueError("this activity is not in the required state; refresh the page")
            event["ref"] = s["id"]
            if op == "feedback":
                change, enjoyment = request.get("change"), request.get("enjoyment")
                if change not in (None, "better", "same", "worse") or enjoyment not in (None, "yes", "neutral", "no"):
                    raise ValueError("unknown feedback choice")
                if change is None and enjoyment is None:
                    raise ValueError("choose at least one reflection, or skip it")
                event.update(change=change, enjoyment=enjoyment)
        elif op == "auto":
            raise ValueError("breaks are written by the app, not the page")
        elif op == "remove":
            s = next((s for s in current["sessions"] if s["id"] == request.get("ref")), None)
            if not s or not s.get("auto") or s["status"] != "finished":
                raise ValueError("only a break the app wrote down can be taken back; refresh the page")
            event["ref"] = s["id"]
        elif op == "reward_plan":
            event.update(title=_text(request.get("title"), "title", True),
                         note=_text(request.get("note", ""), "note"))
        elif op in ("reward_done", "reward_cancel"):
            reward = next((r for r in current["rewards"] if r["id"] == request.get("ref")), None)
            if not reward or reward["status"] != "planned":
                raise ValueError("this celebration is not pending; refresh the page")
            event["ref"] = reward["id"]
        file = path(cfg)
        file.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(file, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        with os.fdopen(fd, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
    return {"ok": True, "id": event["id"]}


def auto_break(cfg, start, end, after: int) -> bool:
    """A break away from the computer after a long stretch (`after` minutes), as the Mac app saw it: written down as a
    finished rest by itself, so there is nothing to start or stop. Once per break (by its start); False when it was
    already there or would land before the last record."""
    request = {"op": "auto", "request_id": f"auto-break-{start.strftime('%Y%m%d%H%M%S')}"}
    with state.write_lock(cfg):
        entries = read(cfg)
        if any(e.get("request_id") == request["request_id"] for e in entries):
            return False
        when = moment(cfg, end)
        if entries and when < state.parse_iso(entries[-1]["at"]):
            return False
        event = {"v": 1, "id": secrets.token_hex(12), "at": when.isoformat(timespec="seconds"), "op": "auto",
                 "request_id": request["request_id"], "request": request, "activity": "break", "source": "mac",
                 "start": moment(cfg, start).isoformat(timespec="seconds"), "end": when.isoformat(timespec="seconds"), "after": int(after)}
        file = path(cfg)
        file.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(file, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        with os.fdopen(fd, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
    return True
