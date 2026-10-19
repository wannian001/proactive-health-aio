"""Sitting: long stretches at the computer, and the reminder to get up.

Two sources, because one of them is late:
- History comes from Screen Time on the computers ([devices] computers, laptop and desktop by default): sessions on a
  computer with less than BREAK_MIN minutes between them are one stretch at the desk. It is a proxy: a screen says you
  were at the computer, not that you sat (a standing desk counts too), and a stretch away from the screen but still in
  the chair is not seen.
- Right now comes from the Mac app, which watches the keyboard and mouse: BREAK_MIN minutes without either is a break.
  It writes when the current stretch started to .healthaio/sitting.json (`healthaio sitting --since ...`). Screen Time
  only arrives every few hours, so it cannot say what is happening now; without the Mac app there is no reminder,
  only the history.

The reminder (nudge) comes once a stretch reaches LONG_MIN minutes and again every REPEAT_MIN while it goes on. It
hands one desk move and a walk (routines.py), for where you said it was tight today if you did. It stays quiet while
Rest & rewards is quiet (you asked for two quiet hours, you are resting, or you said you are absorbed).
"""
import statistics
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from .. import routines, state
from ..context import Context, iso

BREAK_MIN = 5       # this long away from the computer ends a stretch
LONG_MIN = 50       # a stretch this long gets the reminder (and counts as a long one on the pages)
REPEAT_MIN = 30     # and again this often while it goes on
FRESH_MIN = 3       # the Mac app's word on right now is trusted this long
AUTO_BREAK_MIN = 3  # getting up this long after a long stretch is written down as a rest by itself
DAYS = 14           # the days drawn
BASE_DAYS = 28      # "your usual" longest stretch: the median over this many days before
MIN_BASE = 7        # with at least this many days that had computer time


def live_path(cfg):
    return state.folder(cfg) / "sitting.json"


def _computer_days(ctx: Context) -> Dict[date, List[Dict[str, Any]]]:
    """Screen Time sessions on the computers, by the day they started (worked out once per request)."""
    cached = getattr(ctx, "_sitting_days", None)
    if cached is None:
        computers, cached = set(ctx.cfg.computers), {}
        for r in ctx.store.rows("screen_sessions"):
            if r["device"] in computers:
                cached.setdefault(r["start"].date(), []).append(r)
        for rows in cached.values():
            rows.sort(key=lambda r: r["start"])
        ctx._sitting_days = cached
    return cached


def stretches(ctx: Context, day: date) -> List[Dict[str, Any]]:
    """The stretches at a computer that started on `day`, oldest first, from Screen Time."""
    rows = _computer_days(ctx).get(day, [])
    out: List[List[datetime]] = []
    for r in rows:
        if out and r["start"] - out[-1][1] < timedelta(minutes=BREAK_MIN):
            out[-1][1] = max(out[-1][1], r["end"])
        else:
            out.append([r["start"], r["end"]])
    return [{"start": iso(a), "end": iso(b), "minutes": round((b - a).total_seconds() / 60)} for a, b in out]


def day_summary(ctx: Context, day: date) -> Optional[Dict[str, Any]]:
    s = stretches(ctx, day)
    if not s:
        return None
    return {"date": iso(day), "longest": max(x["minutes"] for x in s), "long": sum(1 for x in s if x["minutes"] >= LONG_MIN),
            "total": sum(x["minutes"] for x in s), "stretches": s}


def usual(ctx: Context, end: date) -> Optional[float]:
    longest = [d["longest"] for d in (day_summary(ctx, end - timedelta(days=k)) for k in range(1, BASE_DAYS + 1)) if d]
    return statistics.median(longest) if len(longest) >= MIN_BASE else None


def live(ctx: Context) -> Optional[Dict[str, Any]]:
    """The stretch going on now, as the Mac app last saw it, or None (no app, a break, or not heard from lately)."""
    raw = state.read_json(live_path(ctx.cfg))
    if not isinstance(raw, dict) or not raw.get("since") or not raw.get("seen"):
        return None
    try:
        since, seen = datetime.fromisoformat(raw["since"]), datetime.fromisoformat(raw["seen"])
    except (TypeError, ValueError):
        return None
    now = ctx.now
    local = lambda t: t.astimezone(ctx.cfg.tz).replace(tzinfo=None) if t.tzinfo else t  # local wall time, like the rest of the app
    since, seen = local(since), local(seen)
    if not timedelta(0) <= now - seen <= timedelta(minutes=FRESH_MIN) or since > now:
        return None
    return {"since": iso(since), "seen": iso(seen), "minutes": round((now - since).total_seconds() / 60)}


def note(cfg, since: Optional[datetime], seen: Optional[datetime] = None, off_since: Optional[datetime] = None) -> None:
    """What the Mac app tells the server: the current stretch started at `since`, or (since None) you are on a break
    that began at `off_since`. A break of at least AUTO_BREAK_MIN after a stretch of LONG_MIN or more is written
    down as a rest by itself (restore_log.auto_break) when the next stretch starts: nothing to start or stop."""
    path = live_path(cfg)
    before = state.read_json(path) or {}
    seen = seen or datetime.now((since or off_since or datetime.now()).tzinfo)
    if since is None:
        last = None
        try:
            if before.get("since"):
                start = datetime.fromisoformat(before["since"])
                last = round(((off_since or seen) - start).total_seconds() / 60)
        except (TypeError, ValueError):
            last = None
        state.write_json(path, {"off_since": (off_since or seen).isoformat(timespec="seconds"), "after": last, "source": "mac"})
        return
    try:
        off, after = before.get("off_since"), before.get("after")
        if off and after and after >= LONG_MIN:
            off = datetime.fromisoformat(off)
            if timedelta(minutes=AUTO_BREAK_MIN) <= since - off <= timedelta(hours=2):
                from .. import restore_log
                restore_log.auto_break(cfg, off, since, after)
    except (TypeError, ValueError):
        pass
    state.write_json(path, {"since": since.isoformat(timespec="seconds"), "seen": seen.isoformat(timespec="seconds"), "source": "mac"})


def nudge(ctx: Context) -> Dict[str, Any]:
    """Whether to remind you now: {"kind": "sitting", ...} or {"kind": None, "why": ...}."""
    from . import restore
    now = live(ctx)
    if not now or now["minutes"] < LONG_MIN:
        return {"page": "nudge", "kind": None, "why": "not_long" if now else "no_live", "live": now}
    situation = restore.situation(ctx)
    if situation["key"] in ("quiet", "active", "engaged"):
        return {"page": "nudge", "kind": None, "why": situation["key"], "live": now}
    # which reminder of this stretch it is: the first at LONG_MIN, then one every REPEAT_MIN; a page that was shown
    # this one already keeps it hidden (by `since` and `round`)
    rounds = 1 + (now["minutes"] - LONG_MIN) // REPEAT_MIN
    from .care import tight_today
    picks = routines.for_sitting(ctx.today.toordinal() + rounds, tight_today(ctx))
    return {"page": "nudge", "kind": "sitting", "minutes": now["minutes"], "since": now["since"], "round": rounds,
            "routines": picks, "info": routines.info(picks), "stop": routines.STOP,
            "rule": {"long_min": LONG_MIN, "repeat_min": REPEAT_MIN}}


def light(ctx: Context, day: date) -> Dict[str, Any]:
    """Today's line: the longest stretch that day, how many long ones, your usual longest, and right now."""
    s = day_summary(ctx, day)
    return {"longest": s["longest"] if s else None, "long": s["long"] if s else None, "usual": usual(ctx, day),
            "live": live(ctx) if day == ctx.today else None, "long_min": LONG_MIN}


def build(ctx: Context, day: Optional[date] = None) -> Dict[str, Any]:
    """The sitting card: today's stretches, the last DAYS days' longest stretch and long ones, and your usual."""
    from .care import tight_today
    end = day or ctx.today
    days = [day_summary(ctx, end - timedelta(days=k)) for k in range(DAYS - 1, -1, -1)]
    picks = routines.for_regions(tight_today(ctx), 3) if end == ctx.today else []
    picks = [i for i in picks if routines.BY_ID[i].get("sitting")] or list(routines.SITTING_TURN[:3])
    return {"today": days[-1], "days": [d or {"date": iso(end - timedelta(days=DAYS - 1 - i))} for i, d in enumerate(days)],
            "usual": usual(ctx, end), "live": live(ctx) if end == ctx.today else None,
            "routines": picks + ["walk_break"], "info": routines.info(picks + ["walk_break"]), "stop": routines.STOP,
            "rule": {"break_min": BREAK_MIN, "long_min": LONG_MIN, "repeat_min": REPEAT_MIN, "base_days": BASE_DAYS,
                     "computers": list(ctx.cfg.computers)}}
