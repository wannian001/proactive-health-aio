"""Reading what you say about where it is sore: "跑完步右边大腿后面有点酸，左肩前面也疼" → right thigh, back, a little;
left shoulder, front, level not said.

Soreness is not felt until it is there, so the Recovery page asks for it only when you have something to say: one
sentence (typed, or spoken with the phone's or the browser's dictation), read into places, then a button for whatever
the sentence left open (which side, which face of the thigh, how much), then saved with checkin.report().

Two readers give the same answer shape ({"items": [{area, side, face, level}], "signs", "parsed_by"}), and neither
writes anything:
- rules (always there): fixed word lists in Chinese and English, clause by clause; a clause that names no place takes
  the place of the one before ("左肩前面和后面都疼"), and one that names no side takes the side before
  ("右大腿后侧和小腿");
- the assistant (optional, assistant.py's [assistant] setting): a Claude model reads the sentence and answers only with
  ids from schema.SORE_AREAS, checked again here. If it is off, not installed, fails, declines or finds nothing the
  rules can see, the rules answer and say why.

An item's side is left, right, both or None (not said); face is front, back, outer, inner, all or None; level is 0 (fine
again), 1, 2, 3 or None. Area "leg" (a leg, thigh or calf not said) is asked about too. The warning signs (numbness,
pain spreading, getting worse, waking you at night, an injury) are assistant.SIGN_WORDS: the page then shows the line
on seeing someone (routines.STOP) beside the save.
"""
import re
from typing import Any, Dict, List, Optional, Tuple

from . import assistant, care_log
from .schema import SORE_AREAS

AREAS = tuple(a for a, _, _ in SORE_AREAS)
SIDED = {a for a, sides, _ in SORE_AREAS if sides} | {"leg", "neck"}  # the back of the neck has a left and a right
FACES = {a: faces for a, _, faces in SORE_AREAS}
FACES["leg"] = FACES["thigh"]

# place words: (word, area, face it implies)
PLACE_WORDS: Tuple[Tuple[str, str, Optional[str]], ...] = (
    ("后颈", "neck", "back"), ("颈后", "neck", "back"), ("后脖子", "neck", "back"), ("脖子后", "neck", "back"),
    ("前颈", "neck", "front"), ("颈前", "neck", "front"), ("喉咙", "neck", "front"), ("脖子前", "neck", "front"),
    ("脖子", "neck", None), ("颈椎", "neck", "back"), ("颈部", "neck", None), ("颈", "neck", None),
    ("back of my neck", "neck", "back"), ("back of the neck", "neck", "back"), ("neck", "neck", None),
    ("肩膀", "shoulder", None), ("三角肌", "shoulder", None), ("肩", "shoulder", None), ("shoulder", "shoulder", None),
    ("delt", "shoulder", None),
    ("胸口", "chest", None), ("胸部", "chest", None), ("前胸", "chest", None), ("胸肌", "chest", None), ("胸", "chest", None),
    ("chest", "chest", None), ("pec", "chest", None),
    ("下背", "low_back", None), ("后腰", "low_back", None), ("腰椎", "low_back", None), ("腰部", "low_back", None),
    ("腰", "low_back", None), ("lower back", "low_back", None), ("low back", "low_back", None),
    ("上背", "upper_back", None), ("后背", "upper_back", None), ("背部", "upper_back", None), ("肩胛", "upper_back", None),
    ("斜方", "upper_back", None), ("背阔", "upper_back", None), ("背", "upper_back", None), ("upper back", "upper_back", None),
    ("lats", "upper_back", None), ("traps", "upper_back", None), ("back", "upper_back", None),
    ("腹肌", "abs", None), ("肚子", "abs", None), ("腹部", "abs", None), ("核心", "abs", None), ("腹", "abs", None),
    ("abs", "abs", None), ("stomach", "abs", None), ("belly", "abs", None), ("core", "abs", None),
    ("屁股", "glute", None), ("臀部", "glute", None), ("臀", "glute", None), ("glute", "glute", None), ("butt", "glute", None),
    ("buttock", "glute", None),
    ("上臂", "upper_arm", None), ("胳膊", "upper_arm", None), ("手臂", "upper_arm", None), ("二头", "upper_arm", None),
    ("三头", "upper_arm", None), ("肱", "upper_arm", None), ("bicep", "upper_arm", None), ("tricep", "upper_arm", None),
    ("upper arm", "upper_arm", None), ("arm", "upper_arm", None),
    ("股四头", "thigh", "front"), ("腘绳", "thigh", "back"), ("内收", "thigh", "inner"), ("髂胫束", "thigh", "outer"),
    ("大腿", "thigh", None), ("quad", "thigh", "front"), ("hamstring", "thigh", "back"), ("adductor", "thigh", "inner"),
    ("it band", "thigh", "outer"), ("thigh", "thigh", None),
    ("腿肚子", "calf", "back"), ("腿肚", "calf", "back"), ("小腿肚", "calf", "back"), ("胫骨", "calf", "front"),
    ("迎面骨", "calf", "front"), ("小腿", "calf", None), ("shin", "calf", "front"), ("calf", "calf", "back"),
    ("calves", "calf", "back"),
    ("腿", "leg", None), ("leg", "leg", None),
)
FACE_WORDS = (("front", ("前面", "前侧", "正面", "前边", "前", "front")),
              ("back", ("后面", "后侧", "背面", "后边", "后", "back", "rear", "behind")),
              ("outer", ("外侧", "外面", "外边", "外", "outer", "outside")),
              ("inner", ("内侧", "里面", "里侧", "内", "inner", "inside")),
              ("all", ("一圈", "整条", "整个", "all over", "all around", "whole")))
SIDE_WORDS = (("both", ("两边", "两侧", "双侧", "两条", "双", "both")),
              ("left", ("左边", "左侧", "左", "left")),
              ("right", ("右边", "右侧", "右", "right")))
LEVEL_WORDS = ((0, ("好了", "不疼了", "不酸了", "不痛了", "没事了", "没感觉了", "fine now", "gone", "no longer")),
               (1, ("有一点", "一点点", "有点", "轻微", "微微", "稍微", "略", "a bit", "a little", "slightly", "mild", "a touch")),
               (3, ("好痛", "好疼", "好酸", "超疼", "超酸", "超痛", "疼死", "特别", "非常", "超级", "剧烈", "严重", "很", "very", "really", "severe", "badly", "extremely")),
               (2, ("还挺", "比较", "明显", "挺", "pretty", "quite", "fairly", "moderate")))
SPLIT = r"[，,、;；。.!！?？\n]|和|跟|还有|以及|另外|\band\b|\balso\b|\bplus\b"


def _find(text: str, table) -> Tuple[List[Any], str]:
    """The keys of the words in `text`, longest words first, each used up once matched, in the order they appear;
    and the text with them taken out."""
    hits = []
    for word, key in sorted(((w, k) for k, words in table for w in words), key=lambda x: -len(x[0])):
        pattern = rf"\b{re.escape(word)}(?:s|es)?\b" if word.isascii() else re.escape(word)
        for m in re.finditer(pattern, text, re.ASCII):
            hits.append((m.start(), key))
        text = re.sub(pattern, " " * len(word), text, flags=re.ASCII)
    return [k for _, k in sorted(hits)], text


def _places(text: str) -> Tuple[List[Tuple[str, Optional[str]]], str]:
    hits = []
    for word, area, face in sorted(PLACE_WORDS, key=lambda x: -len(x[0])):
        pattern = rf"\b{re.escape(word)}(?:s|es)?\b" if word.isascii() else re.escape(word)
        for m in re.finditer(pattern, text, re.ASCII):
            hits.append((m.start(), area, face))
        text = re.sub(pattern, lambda m: " " * len(m.group(0)), text, flags=re.ASCII)
    return [(a, f) for _, a, f in sorted(hits)], text


# words that look like a face, a side or a place but are not one: time (前天, 跑完后), 背面 (the back face, not the
# upper back); and English "back of my thigh" said the way the rules read it
NOT_PLACES = (r"前天|后天|前几天|前两天|前阵子|后来|然后|之后|之前|以后|以前|最后|午后|饭后|睡前|睡后|练前|练后|跑前|跑后|"
              r"步后|完后|运动后|训练后|结束后")
ENGLISH_FACE = {"front": "前", "back": "后", "outside": "外侧", "inside": "内侧"}


def _normal(text: str) -> str:
    text = re.sub(NOT_PLACES, " ", text)
    text = text.replace("背面", "后面").replace("背侧", "后侧")
    text = re.sub(r"左右(两边|两侧|都)", "两边", text)
    text = text.replace("左右", " ")  # "三天左右": about, not a side
    return re.sub(r"\b(front|back|outside|inside) of (?:my|the|your) ((?:left|right) )?(thigh|calf|leg|shoulder|neck)s?\b",
                  lambda m: f"{m.group(2) or ''}{m.group(3)} {ENGLISH_FACE[m.group(1)]}", text)


def rules(said: str) -> Dict[str, Any]:
    text = _normal(said.lower())
    levels_all = {lv for lv in _find(text, LEVEL_WORDS)[0]}
    items: List[Dict[str, Any]] = []
    last: Optional[Dict[str, Any]] = None
    for clause in re.split(SPLIT, text):
        places, rest = _places(clause)
        faces, rest = _find(rest, FACE_WORDS)
        sides, rest = _find(rest, SIDE_WORDS)
        levels, _ = _find(rest, LEVEL_WORDS)
        side = sides[0] if len(set(sides)) == 1 else "both" if sides else None
        level = levels[0] if levels else None
        if not places and last is not None and (faces or sides or levels):
            places = [(last["area"], None)]  # "...和后面都疼": the same place
            side = side or last["side"]
        for area, implied in places:
            face = implied or (faces[0] if faces else None)
            if face == "all" and area in ("neck", "shoulder"):
                face = None
            item = {"area": area, "side": side, "face": face if FACES.get(area) or face == "all" else None, "level": level}
            if area not in SIDED:
                item["side"] = None
            elif item["side"] is None and last is not None and last["side"] and not sides:
                item["side"] = last["side"]  # "右大腿后侧和小腿": the same side
            if area == "neck" and item["side"] and not item["face"]:
                item["face"] = "back"  # a side of the neck is its back
            if area == "neck" and item["face"] == "front":
                item["side"] = None
            if not FACES.get(area) and area != "leg":
                item["face"] = None
            items.append(item)
            last = item
    if len(levels_all) == 1:
        for item in items:
            if item["level"] is None:
                item["level"] = next(iter(levels_all))
    signs = _find(said.lower(), assistant.SIGN_WORDS)[0]
    return {"items": _merge(items), "signs": sorted(set(signs)), "parsed_by": "rules"}


def _merge(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """The same place said twice is one item; a later level wins."""
    out: Dict[Tuple, Dict[str, Any]] = {}
    for item in items:
        key = (item["area"], item["side"], item["face"])
        if key in out and item["level"] is None:
            continue
        out[key] = item
    return list(out.values())


# ---- the assistant ---------------------------------------------------------------------------------------------
SYSTEM = (
    "You read one sentence a person said about where their body is sore, aching or in pain, often after training or "
    "sitting. Answer only with the JSON the schema asks for, using only the ids it allows. One item per place: "
    "area (neck, shoulder, chest, upper_back, abs, low_back, glute, upper_arm, thigh, calf; 'leg' when they only say "
    "leg), side (left, right, both, or unsure if they don't say; neck sides are the back of the neck), face (front, back, "
    "outer, inner, all, or unsure; only neck, shoulder, thigh and calf have faces), and level (fine if they say it is "
    "better or gone, a_little, clearly, very, or unsure if they don't say how much). signs: only warning signs they "
    "actually mention (numbness or tingling, pain spreading into an arm or leg, getting worse, waking them at night, "
    "starting with an injury). Do not diagnose and do not give advice."
)
LEVEL_IDS = {"fine": 0, "a_little": 1, "clearly": 2, "very": 3, "unsure": None}


def _schema() -> Dict[str, Any]:
    item = {"type": "object", "additionalProperties": False, "required": ["area", "side", "face", "level"],
            "properties": {"area": {"type": "string", "enum": list(AREAS) + ["leg"]},
                           "side": {"type": "string", "enum": ["left", "right", "both", "unsure"]},
                           "face": {"type": "string", "enum": ["front", "back", "outer", "inner", "all", "unsure"]},
                           "level": {"type": "string", "enum": list(LEVEL_IDS)}}}
    return {"type": "object", "additionalProperties": False, "required": ["items", "signs"],
            "properties": {"items": {"type": "array", "items": item},
                           "signs": {"type": "array", "items": {"type": "string", "enum": list(care_log.SIGNS)}}}}


def _clean(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Keep only ids from the fixed lists, whatever came back."""
    items = []
    for x in raw.get("items") or []:
        if not isinstance(x, dict) or x.get("area") not in AREAS + ("leg",):
            continue
        area = x["area"]
        side = x.get("side") if x.get("side") in ("left", "right", "both") and area in SIDED else None
        face = x.get("face") if x.get("face") in tuple(FACES.get(area) or ()) + ("all",) and (FACES.get(area) or area == "leg") else None
        if area == "neck" and side and not face:
            face = "back"
        items.append({"area": area, "side": side, "face": face, "level": LEVEL_IDS.get(x.get("level"))})
    signs = sorted({s for s in raw.get("signs") or [] if s in care_log.SIGNS})
    return {"items": _merge(items), "signs": signs, "parsed_by": "assistant"}


def parse(cfg, said: str, ask_model=None) -> Dict[str, Any]:
    """What a sentence says, from the assistant when it is on and answers, else from the rules (with why)."""
    said = (said or "").strip()[:280]
    if not said:
        return {"items": [], "signs": [], "parsed_by": None}
    ok, why = assistant.available(cfg) if ask_model is None else (True, None)
    if ok:
        try:
            out = _clean((ask_model or (lambda c, s: assistant.ask(c, SYSTEM, _schema(), s)))(cfg, said))
            if out["items"] or not rules(said)["items"]:
                return out
            why = "empty"
        except Exception as error:  # any failure (network, key, refusal, bad JSON) falls back to the rules
            why = assistant._why(error)
    return {**rules(said), "assistant": why}


def from_browser(cfg, request, now=None) -> Dict[str, Any]:
    """POST /api/sore-parse: read a sentence (nothing is written; the page saves what you confirm)."""
    if not isinstance(request, dict) or set(request) - {"said"} or not isinstance(request.get("said"), str):
        raise ValueError("send {\"said\": \"...\"}")
    if len(request["said"]) > 280:
        raise ValueError("what you said: at most 280 characters")
    return parse(cfg, request["said"])
