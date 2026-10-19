"""Settings and plans from ``healthaio.toml`` (or ``healthaio.json``).

Every key is optional. A page whose plan is missing still shows the facts and
says which plan would let it compare them against a goal.
"""
import json
from dataclasses import dataclass, field
from datetime import date, time
from pathlib import Path
from typing import Any, Dict, List, Optional

try:  # Python 3.11+
    import tomllib as _toml
except ModuleNotFoundError:  # pragma: no cover - Python 3.9/3.10
    try:
        import tomli as _toml  # type: ignore
    except ModuleNotFoundError:
        _toml = None

try:
    from zoneinfo import ZoneInfo
except ModuleNotFoundError:  # pragma: no cover
    ZoneInfo = None  # type: ignore

WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
DEFAULT_DEVICES = ["phone", "tablet", "laptop", "desktop"]
# A computer keeps its screen on while you are away; a phone or tablet locks itself. So when an AI agent app is in
# front on a computer while another device is in use, the agent is working and you are on the other device.
DEFAULT_COMPUTERS = ["laptop", "desktop"]
COLLECT_SOURCES = ("macos-screentime",)
RETIRED_SOURCES = ("ai-logs",)  # still accepted in an older healthaio.toml, and ignored: the app no longer reads AI logs
DEFAULT_COLLECT = ["macos-screentime"]
DEFAULT_AGENT_APPS = ["Claude", "ChatGPT", "Codex", "Cursor", "Windsurf", "Terminal", "iTerm2", "Warp", "Ghostty"]


class ConfigError(ValueError):
    pass


def _clock(value: Any, where: str) -> Optional[time]:
    if value in (None, ""):
        return None
    try:
        hour, minute = str(value).split(":")
        return time(int(hour), int(minute))
    except (ValueError, TypeError):
        raise ConfigError(f"{where}: expected HH:MM, got {value!r}") from None


def _day(value: Any, where: str) -> Optional[date]:
    if value in (None, ""):
        return None
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        raise ConfigError(f"{where}: expected YYYY-MM-DD, got {value!r}") from None


def _num(value: Any, where: str) -> Optional[float]:
    if value in (None, ""):
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigError(f"{where}: expected a number, got {value!r}")
    return float(value)


@dataclass
class SleepPlan:
    target_hours: Optional[float] = None
    bedtime: Optional[time] = None
    wake: Optional[time] = None


@dataclass
class WakeShift:
    """Move the alarm earlier one step after each on-time morning; never later."""
    start: date
    first_alarm: time
    final_alarm: time
    step_min: float = 15
    grace_min: float = 15


@dataclass
class WeightPlan:
    start_date: date
    start_kg: float
    target_kg: float
    weekly_loss_pct: List[float] = field(default_factory=lambda: [0.5, 1.0])


@dataclass
class FoodPlan:
    """Daily energy range, protein, and how long before sleep the last meal should end."""
    kcal_min: Optional[float] = None
    kcal_max: Optional[float] = None
    protein_g: Optional[float] = None          # a fixed daily amount, or
    protein_g_per_kg: Optional[float] = None   # grams per kg of your latest weight
    last_meal_gap_h: float = 3.0


# What a week of exercise should hold when no [plan.exercise] is set: the WHO guideline for adults
# (at least 150 minutes of moderate activity, and muscle-strengthening on 2 or more days).
GUIDELINE_WEEKLY_MIN = 150.0
GUIDELINE_STRENGTH_DAYS = 2


@dataclass
class ExercisePlan:
    weekly_min: Optional[float] = None
    strength_days: Optional[int] = None


@dataclass
class ScreenPlan:
    entertainment_max_hours: Optional[float] = None
    work_min_hours: Optional[float] = None


@dataclass
class Config:
    root: Path
    data_dir: Path
    timezone: str = "UTC"
    locale: str = "en"
    title: str = "Health AIO"
    demo: bool = False
    figure: str = "male"  # [healthaio] figure: which body figure the Recovery page draws (male or female)
    devices: List[str] = field(default_factory=lambda: list(DEFAULT_DEVICES))
    computers: List[str] = field(default_factory=lambda: list(DEFAULT_COMPUTERS))
    agent_apps: List[str] = field(default_factory=lambda: list(DEFAULT_AGENT_APPS))
    sleep: SleepPlan = field(default_factory=SleepPlan)
    wake_shift: Optional[WakeShift] = None
    weight: Optional[WeightPlan] = None
    training: Dict[str, str] = field(default_factory=dict)
    screen: ScreenPlan = field(default_factory=ScreenPlan)
    food: FoodPlan = field(default_factory=FoodPlan)
    exercise: ExercisePlan = field(default_factory=ExercisePlan)
    # filled by goal_log.apply(): the fields set on the Goals page (laid over the plans above) and the proposals
    # waiting for an answer
    goals_set: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    goals_proposed: List[Dict[str, Any]] = field(default_factory=list)
    # [collect] sources: what `healthaio collect` (the Mac app, every few hours) imports by itself
    collect_sources: List[str] = field(default_factory=lambda: list(DEFAULT_COLLECT))
    # [updates] check: whether to ask GitHub once a day for a newer version
    check_updates: bool = True
    # [assistant]: an optional assistant that reads the sentence you type about where it feels tight (assistant.py).
    # Off by default; when on, that sentence (and nothing else) is sent to the model below
    assistant_enabled: bool = False
    assistant_model: str = "claude-opus-5-5"
    assistant_effort: str = "low"

    @property
    def tz(self):
        if ZoneInfo is None:
            raise ConfigError("zoneinfo is unavailable; use Python 3.9 or newer")
        return ZoneInfo(self.timezone)

    def public(self) -> Dict[str, Any]:
        """What the browser is allowed to know about the settings."""
        return {"title": self.title, "locale": self.locale,
                "timezone": self.timezone, "demo": self.demo}


def _toml_value(text: str, number: int) -> Any:
    text = text.strip()
    if text.startswith('"'):
        close = text.find('"', 1)
        while close > 0 and text[close - 1] == "\\":
            close = text.find('"', close + 1)
        rest = text[close + 1:].strip() if close > 0 else "x"
        if close < 0 or (rest and not rest.startswith("#")):
            raise ConfigError(f"line {number}: unclosed or trailing text after a string")
        return json.loads(text[:close + 1])
    if text.startswith("["):
        close = text.find("]")
        if close < 0:
            raise ConfigError(f"line {number}: lists must fit on one line here; install tomli for more")
        return [_toml_value(item, number) for item in text[1:close].split(",") if item.strip()]
    token = text.split("#", 1)[0].strip()
    if token in ("true", "false"):
        return token == "true"
    try:
        return int(token) if token.lstrip("-").isdigit() else float(token)
    except ValueError:
        raise ConfigError(f"line {number}: cannot read {token!r}; install tomli or use healthaio.json") from None


def _mini_toml(text: str) -> Dict[str, Any]:
    """The part of TOML that healthaio.toml uses: [tables], key = "string" | number | true/false | [list].

    Only used on Python 3.9/3.10 without tomli; anything fancier raises a clear error.
    """
    out: Dict[str, Any] = {}
    table = out
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and not line.startswith("[["):
            name = line[1:line.index("]")].strip()
            table = out
            for part in name.split("."):
                table = table.setdefault(part.strip(), {})
            continue
        if "=" not in line:
            raise ConfigError(f"line {number}: expected key = value")
        key, value = line.split("=", 1)
        table[key.strip().strip('"')] = _toml_value(value, number)
    return out


def _read(path: Path) -> Dict[str, Any]:
    if path.suffix == ".json":
        return json.loads(path.read_text(encoding="utf-8"))
    if _toml is None:
        return _mini_toml(path.read_text(encoding="utf-8"))
    with path.open("rb") as handle:
        return _toml.load(handle)


def find_config(start: Path) -> Optional[Path]:
    # dayring.* is the name this project had before it became Health AIO; old folders keep working
    for name in ("healthaio.toml", "healthaio.json", "dayring.toml", "dayring.json"):
        candidate = start / name
        if candidate.is_file():
            return candidate
    return None


def load(path: Optional[Path] = None, data_dir: Optional[Path] = None) -> Config:
    raw: Dict[str, Any] = {}
    root = Path.cwd()
    if path is not None:
        raw = _read(path)
        root = path.resolve().parent
    main = raw.get("healthaio", raw.get("dayring", {}))
    plan = raw.get("plan", {})
    folder = Path(data_dir) if data_dir else root / main.get("data_dir", "data")
    cfg = Config(root=root, data_dir=folder.resolve(),
                 timezone=str(main.get("timezone", "UTC")),
                 locale=str(main.get("locale", "en")),
                 title=str(main.get("title", "Health AIO")),
                 demo=bool(main.get("demo", False)))
    if cfg.locale not in ("en", "zh"):
        raise ConfigError("healthaio.locale must be en or zh")
    cfg.figure = str(main.get("figure", "male"))
    if cfg.figure not in ("male", "female"):
        raise ConfigError("healthaio.figure must be male or female")
    devices = raw.get("devices", {})
    if devices.get("priority"):
        cfg.devices = [str(d) for d in devices["priority"]]
    for key in ("computers", "agent_apps"):
        if devices.get(key) is not None:
            if not isinstance(devices[key], list):
                raise ConfigError(f"devices.{key} must be a list")
            setattr(cfg, key, [str(d) for d in devices[key]])

    collect = raw.get("collect", {})
    if collect.get("sources") is not None:
        sources = collect["sources"]
        if not isinstance(sources, list) or any(s not in COLLECT_SOURCES + RETIRED_SOURCES for s in sources):
            raise ConfigError(f"collect.sources must be a list of {', '.join(COLLECT_SOURCES)}")
        cfg.collect_sources = [str(s) for s in sources if s not in RETIRED_SOURCES]
    updates = raw.get("updates", {})
    if updates.get("check") is not None:
        if not isinstance(updates["check"], bool):
            raise ConfigError("updates.check must be true or false")
        cfg.check_updates = updates["check"]
    assistant = raw.get("assistant", {})
    if assistant.get("enabled") is not None:
        if not isinstance(assistant["enabled"], bool):
            raise ConfigError("assistant.enabled must be true or false")
        cfg.assistant_enabled = assistant["enabled"]
    if assistant.get("model") is not None:
        cfg.assistant_model = str(assistant["model"])
    if assistant.get("effort") is not None:
        if assistant["effort"] not in ("low", "medium", "high", "xhigh", "max"):
            raise ConfigError("assistant.effort must be low, medium, high, xhigh or max")
        cfg.assistant_effort = assistant["effort"]

    sleep = plan.get("sleep", {})
    cfg.sleep = SleepPlan(target_hours=_num(sleep.get("target_hours"), "plan.sleep.target_hours"),
                          bedtime=_clock(sleep.get("bedtime"), "plan.sleep.bedtime"),
                          wake=_clock(sleep.get("wake"), "plan.sleep.wake"))
    shift = plan.get("wake_shift")
    if shift:
        cfg.wake_shift = WakeShift(
            start=_day(shift.get("start"), "plan.wake_shift.start"),
            first_alarm=_clock(shift.get("first_alarm"), "plan.wake_shift.first_alarm"),
            final_alarm=_clock(shift.get("final_alarm"), "plan.wake_shift.final_alarm"),
            step_min=_num(shift.get("step_min", 15), "plan.wake_shift.step_min"),
            grace_min=_num(shift.get("grace_min", 15), "plan.wake_shift.grace_min"))
        if None in (cfg.wake_shift.start, cfg.wake_shift.first_alarm, cfg.wake_shift.final_alarm):
            raise ConfigError("plan.wake_shift needs start, first_alarm and final_alarm")
    weight = plan.get("weight")
    if weight:
        pct = weight.get("weekly_loss_pct", [0.5, 1.0])
        cfg.weight = WeightPlan(start_date=_day(weight.get("start_date"), "plan.weight.start_date"),
                                start_kg=_num(weight.get("start_kg"), "plan.weight.start_kg"),
                                target_kg=_num(weight.get("target_kg"), "plan.weight.target_kg"),
                                weekly_loss_pct=[float(p) for p in pct])
        if None in (cfg.weight.start_date, cfg.weight.start_kg, cfg.weight.target_kg):
            raise ConfigError("plan.weight needs start_date, start_kg and target_kg")
    training = plan.get("training", {})
    cfg.training = {k: str(v) for k, v in training.items() if k in WEEKDAYS and v}
    screen = plan.get("screen", {})
    cfg.screen = ScreenPlan(
        entertainment_max_hours=_num(screen.get("entertainment_max_hours"), "plan.screen.entertainment_max_hours"),
        work_min_hours=_num(screen.get("work_min_hours"), "plan.screen.work_min_hours"))
    food = plan.get("food", {})
    cfg.food = FoodPlan(kcal_min=_num(food.get("kcal_min"), "plan.food.kcal_min"),
                        kcal_max=_num(food.get("kcal_max"), "plan.food.kcal_max"),
                        protein_g=_num(food.get("protein_g"), "plan.food.protein_g"),
                        protein_g_per_kg=_num(food.get("protein_g_per_kg"), "plan.food.protein_g_per_kg"),
                        last_meal_gap_h=_num(food.get("last_meal_gap_h", 3), "plan.food.last_meal_gap_h"))
    if cfg.food.kcal_min is not None and cfg.food.kcal_max is not None and cfg.food.kcal_min > cfg.food.kcal_max:
        raise ConfigError("plan.food.kcal_min must not be above kcal_max")
    exercise = plan.get("exercise", {})
    days = _num(exercise.get("strength_days"), "plan.exercise.strength_days")
    cfg.exercise = ExercisePlan(weekly_min=_num(exercise.get("weekly_min"), "plan.exercise.weekly_min"),
                                strength_days=None if days is None else int(days))
    return cfg
