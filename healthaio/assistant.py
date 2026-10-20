"""Reading what you said about where it feels tight: "久坐导致颈部前倾、颈部紧张、胸部紧张" → neck tight, chest tight,
probably from sitting.

Two readers give the same answer shape ({"tight": {region: feeling}, "cause", "signs", "also_ask", "parsed_by"}):
- rules (always there): fixed word lists in Chinese and English, clause by clause, like the workout note's regions;
- an assistant (optional): a Claude model reads the sentence and answers only with ids from the fixed lists
  (routines.REGIONS / FEELINGS, care_log.SIGNS), checked again here. It never writes advice: the moves come from
  routines.py, and the line on when to stop is fixed.

The assistant is off unless healthaio.toml says

    [assistant]
    enabled = true
    # model = "claude-opus-5-5"   # the default
    # effort = "low"              # how hard it thinks; low is plenty for picking ids

and the `anthropic` package is installed (pip install anthropic; it needs Python 3.10 or newer). The key is whatever
the Anthropic SDK finds on its own (ANTHROPIC_API_KEY, or a profile from `ant auth login`); this app never reads,
stores or shows it. What is sent: the sentence you typed and the fixed lists, nothing else (no measurements, dates or
name). If the assistant is off, not installed, fails, or declines, the rules answer instead and say so.
"""
import json
import re
from typing import Any, Dict, List, Optional, Tuple

from . import care_log, routines

# ---- rules ----------------------------------------------------------------------------------------------------
REGION_WORDS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("neck", ("脖子", "颈椎", "颈部", "后颈", "颈", "头前倾", "探头", "neck")),
    ("chest", ("胸口", "胸部", "胸前", "含胸", "胸", "chest", "pec", "pecs")),
    ("upper_back", ("上背", "肩胛", "斜方肌", "肩膀", "肩", "背上", "upper back", "shoulder blade", "shoulder", "traps")),
    ("low_back", ("下背", "后腰", "腰部", "腰", "lower back", "low back")),
    ("hip_front", ("髋前", "大腿前侧", "大腿前", "腹股沟", "屈髋", "股四头", "髋", "hip flexor", "front of my thigh", "front of the thigh", "quad", "hip")),
    ("thigh_back", ("大腿后侧", "大腿后", "腘绳肌", "腘绳", "hamstring", "back of my thigh", "back of the thigh")),
    ("calf", ("小腿后侧", "小腿", "腿肚子", "腿肚", "calf", "calves")),
    ("wrist", ("手腕", "前臂", "腕", "wrist", "forearm")),
)
FEEL_WORDS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (  # 酸痛 before 痛: sore after training is achy, not pain
    ("achy", ("酸痛", "酸胀", "酸", "achy", "ache", "sore")),
    ("stiff", ("僵硬", "发僵", "僵", "stiff")),
    ("tight", ("紧张", "紧绷", "发紧", "紧", "绷", "前倾", "tight", "tense", "knotted")),
    ("pain", ("刺痛", "疼痛", "疼", "痛", "pain", "painful", "hurts", "hurt")),
)
CAUSE_WORDS = (("sitting", ("久坐", "坐太久", "坐久", "一直坐", "坐了一天", "坐着", "伏案", "电脑前", "sitting", "sat", "desk")),
               ("training", ("训练", "健身", "练完", "跑步", "撸铁", "workout", "training", "gym", "run", "lifting")))
SIGN_WORDS = (("numb", ("发麻", "麻木", "麻", "刺麻", "numb", "tingl", "pins and needles")),
              ("spreading", ("放射", "窜到", "传到", "一直到手", "到腿", "radiat", "spreads", "spreading", "shooting")),
              ("worse", ("越来越重", "越来越疼", "加重", "worse", "worsening")),
              ("night", ("夜里", "半夜", "疼醒", "痛醒", "at night", "wakes me")),
              ("injury", ("摔", "扭到", "扭伤", "撞", "受伤", "injur", "fell", "sprain", "twisted")))
# what tends to come with what, for "anywhere else?" (the check-in asks; you decide)
TOGETHER = {"neck": ("upper_back", "chest"), "chest": ("upper_back", "neck"), "upper_back": ("neck", "chest"),
            "low_back": ("hip_front", "thigh_back"), "hip_front": ("low_back", "thigh_back"),
            "thigh_back": ("calf", "low_back"), "calf": ("thigh_back",), "wrist": ("neck",)}


def _find(text: str, table) -> List[str]:
    """The keys whose words are in `text`, longest words first and each used up once matched (so 酸痛 is achy and
    not also 痛, pain), in the table's order."""
    hits = set()
    for word, key in sorted(((w, k) for k, words in table for w in words), key=lambda x: -len(x[0])):
        pattern = rf"\b{re.escape(word)}" if word.isascii() else re.escape(word)
        if re.search(pattern, text):
            hits.add(key)
            text = re.sub(pattern, " ", text)
    return [k for k, _ in table if k in hits]


def rules(said: str) -> Dict[str, Any]:
    text = said.lower()
    tight: Dict[str, str] = {}
    default = (_find(text, FEEL_WORDS) or ["tight"])[0]
    for clause in re.split(r"[，,、;；。.!！?？\n]|和|还有|and", text):
        regions = _find(clause, REGION_WORDS)
        feels = _find(clause, FEEL_WORDS)
        for r in regions:
            # a later, stronger word for the same place wins (pain over achy over stiff over tight)
            feel = feels[-1] if feels else tight.get(r, default)
            order = ("tight", "stiff", "achy", "pain")
            if r not in tight or order.index(feel) > order.index(tight[r]):
                tight[r] = feel
    cause = next(iter(_find(text, CAUSE_WORDS)), None)
    signs = [s for s in _find(text, SIGN_WORDS)]
    return {"tight": tight, "cause": cause, "signs": signs, "also_ask": also_ask(tight), "parsed_by": "rules"}


def also_ask(tight: Dict[str, str]) -> List[str]:
    out: List[str] = []
    for r in tight:
        for other in TOGETHER.get(r, ()):
            if other not in tight and other not in out:
                out.append(other)
    return out[:3]


# ---- the assistant ---------------------------------------------------------------------------------------------
SYSTEM = (
    "You read one sentence a person wrote about where their body feels tight, stiff, achy or painful, often after "
    "sitting at a computer. Answer only with the JSON the schema asks for, using only the ids it allows. "
    "Map each body place they mention to one region id and say how it feels with one feeling id "
    "(posture words such as 'head poking forward' or '颈部前倾' mean the neck feels tight). "
    "cause: 'sitting' if they connect it to sitting or desk work, 'training' if to exercise, 'other' if to something "
    "else, 'unknown' if they don't say. signs: only warning signs they actually mention (numbness or tingling, pain "
    "spreading into an arm or leg, getting worse, waking them at night, starting with an injury). "
    "also_ask: up to three other region ids that often go with what they named, to ask about; never ones they named. "
    "Do not diagnose and do not give advice."
)


def _schema() -> Dict[str, Any]:
    return {"type": "object", "additionalProperties": False, "required": ["tight", "cause", "signs", "also_ask"],
            "properties": {
                "tight": {"type": "array", "items": {"type": "object", "additionalProperties": False, "required": ["region", "feel"],
                                                      "properties": {"region": {"type": "string", "enum": list(routines.REGIONS)},
                                                                     "feel": {"type": "string", "enum": list(routines.FEELINGS)}}}},
                "cause": {"type": "string", "enum": ["sitting", "training", "other", "unknown"]},
                "signs": {"type": "array", "items": {"type": "string", "enum": list(care_log.SIGNS)}},
                "also_ask": {"type": "array", "items": {"type": "string", "enum": list(routines.REGIONS)}}}}


def _clean(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Keep only ids from the fixed lists, whatever came back."""
    tight = {}
    for item in raw.get("tight") or []:
        if isinstance(item, dict) and item.get("region") in routines.REGIONS and item.get("feel") in routines.FEELINGS:
            tight[item["region"]] = item["feel"]
    cause = raw.get("cause") if raw.get("cause") in ("sitting", "training", "other") else None
    signs = sorted({s for s in raw.get("signs") or [] if s in care_log.SIGNS})
    ask = [r for r in raw.get("also_ask") or [] if r in routines.REGIONS and r not in tight][:3]
    return {"tight": tight, "cause": cause, "signs": signs, "also_ask": ask or also_ask(tight), "parsed_by": "assistant"}


def available(cfg) -> Tuple[bool, Optional[str]]:
    """Whether the assistant can be asked, and if not, why (shown next to the box)."""
    if not cfg.assistant_enabled:
        return False, "off"
    try:
        import anthropic  # noqa: F401  (optional: pip install anthropic)
    except ImportError:
        return False, "not_installed"
    return True, None


def _ask_model(cfg, said: str) -> Dict[str, Any]:
    return ask(cfg, SYSTEM, _schema(), said)


def ask(cfg, system: str, schema: Dict[str, Any], said: str) -> Dict[str, Any]:
    """One sentence to the model, answered as JSON in the given schema (shared by the readers of what you say)."""
    import anthropic
    client = anthropic.Anthropic(timeout=30.0, max_retries=2)
    response = client.beta.messages.create(
        model=cfg.assistant_model,
        max_tokens=4000,
        # if the model declines (a safety classifier), Anthropic re-runs the request on its recommended fallback
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        system=system,
        output_config={"effort": cfg.assistant_effort, "format": {"type": "json_schema", "schema": schema}},
        messages=[{"role": "user", "content": said}],
    )
    if response.stop_reason == "refusal":
        raise RuntimeError("declined")
    if response.stop_reason == "max_tokens":
        raise RuntimeError("cut_off")
    text = next(b.text for b in response.content if b.type == "text")
    return json.loads(text)


def parse(cfg, said: str, ask_model=None) -> Dict[str, Any]:
    """What a sentence says, from the assistant when it is on and answers, else from the rules (with why)."""
    said = (said or "").strip()[:280]
    if not said:
        return {"tight": {}, "cause": None, "signs": [], "also_ask": [], "parsed_by": None}
    ok, why = available(cfg) if ask_model is None else (True, None)
    if ok:
        try:
            out = _clean((ask_model or _ask_model)(cfg, said))
            if out["tight"] or not rules(said)["tight"]:
                return out
            why = "empty"  # the assistant found no place the rules can see: show the rules' reading
        except Exception as error:  # any failure (network, key, refusal, bad JSON) falls back to the rules
            why = _why(error)
    return {**rules(said), "assistant": why}


def from_browser(cfg, request, now=None) -> Dict[str, Any]:
    """POST /api/care-parse: read a sentence (nothing is written; the check-in's Save writes the report)."""
    if not isinstance(request, dict) or set(request) - {"said"} or not isinstance(request.get("said"), str):
        raise ValueError("send {\"said\": \"...\"}")
    if len(request["said"]) > 280:
        raise ValueError("what you said: at most 280 characters")
    return parse(cfg, request["said"])


def _why(error: Exception) -> str:
    try:
        import anthropic
        if isinstance(error, anthropic.AuthenticationError):
            return "no_key"
        if isinstance(error, anthropic.RateLimitError):
            return "busy"
        if isinstance(error, anthropic.APIConnectionError):
            return "offline"
        if isinstance(error, anthropic.APIStatusError):
            return "error"
    except ImportError:
        pass
    return "declined" if str(error) == "declined" else "error"
