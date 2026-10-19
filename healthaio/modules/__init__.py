"""Page registry: name -> build(ctx, param) returning a JSON-ready dict."""
from datetime import timedelta
from typing import Any, Callable, Dict, List, Optional

from ..context import Context
from . import body, data, docs, drain, exercise, followup, food, goals, load, recovery, restore, sleep, time, today, week

PAGES: Dict[str, Callable[..., Dict[str, Any]]] = {
    "today": lambda ctx, param=None: today.build(ctx, day=param),
    "week": lambda ctx, param=None: week.build(ctx, day=param),
    "body": lambda ctx, param=None: body.build(ctx, day=param),
    "sleep": lambda ctx, param=None: sleep.build(ctx, day=param),
    "recovery": lambda ctx, param=None: recovery.build(ctx, day=param),
    "restore": lambda ctx, param=None: restore.build(ctx),
    # not a page: what every page asks after a strength or hard workout (the popup; modules/recovery.py)
    "prompt": lambda ctx, param=None: recovery.prompt(ctx),
    "load": lambda ctx, param=None: load.build(ctx, day=param),
    "time": lambda ctx, param=None: time.build(ctx, day=param),
    "drain": lambda ctx, param=None: drain.build(ctx, day=param),
    "food": lambda ctx, param=None: food.build(ctx, day=param),
    "exercise": lambda ctx, param=None: exercise.build(ctx, day=param),
    "goals": lambda ctx, param=None: goals.build(ctx, day=param),
    "followup": lambda ctx, param=None: followup.build(ctx, day=param),
    "data": lambda ctx, param=None: data.build(ctx, day=param),
    # the reading pages under the menu: no numbers, only which page it is
    "project": lambda ctx, param=None: docs.build(ctx, "project"),
    "guide": lambda ctx, param=None: docs.build(ctx, "guide"),
}


def static_params(name: str, ctx: Context) -> List[Optional[str]]:
    """Which parameter values `healthaio build-static` pre-renders (a static site cannot compute)."""
    if name == "today":
        return [None] + [(ctx.today - timedelta(days=k)).isoformat() for k in range(1, 15)]
    if name == "week":
        start = ctx.today - timedelta(days=ctx.today.weekday())
        return [None] + [(start + timedelta(days=7 * k)).isoformat() for k in range(-4, 3)]
    if name in ("drain", "food"):
        # every end day of the last four weeks: the 7-day steps from the latest window, and the window each
        # pre-rendered Today links to (the 7 days before that day), from which Earlier / Later step on
        return [None] + [(ctx.today - timedelta(days=k)).isoformat() for k in range(1, 30)]
    if name == "time":
        return time.static_params(ctx)
    return [None]
