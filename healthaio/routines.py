"""Short movement routines, one to three minutes each, for long sitting and for spots that feel tight or stiff: what
the sitting reminder and the "where it's tight" check-in hand you.

The list is fixed and reviewed by hand. Nothing here is generated: when an assistant is set up (healthaio.assistant)
it only reads what you said and picks ids from this list, and without one the same picks come from fixed rules. The
moves are gentle, common ones (a light stretch, not pain), chosen for people who sit at a computer; they are not a
treatment plan. Every routine carries the same line on when to stop and see a doctor or physiotherapist.

Why short and often rather than a posture programme: there is no single correct posture, and changing position
matters more than holding a "good" one (Slater et al., JOSPT 2019, "Sit up straight: time to re-evaluate"); breaking
up sitting every 30 to 60 minutes with a few minutes of light movement helps (Dunstan et al., Diabetes Care 2012);
and in office workers, regular neck and shoulder exercise reduces neck pain a little (Chen et al., Physical Therapy
2018, a systematic review of workplace interventions).

The words are here, in both languages, like the Guide and Overview content, because the Mac app shows them in its
notifications too (it reads /api/routines).
"""
from typing import Any, Dict, Iterable, List

# where it can feel tight after sitting: the check-in's choices (their names are in i18n.js, care.region.*)
REGIONS = ("neck", "chest", "upper_back", "low_back", "hip_front", "thigh_back", "calf", "wrist")
# what the feeling is (care.feel.*): tight and stiff fit these moves; pain is asked about before any move is shown
FEELINGS = ("tight", "stiff", "achy", "pain")

ROUTINES: List[Dict[str, Any]] = [
    {"id": "walk_break", "regions": [], "minutes": 2, "sitting": True,
     "zh": {"name": "起来走两分钟", "how": "站起来，去倒杯水、走一圈楼道或者在屋里走走，顺便看看远处。", "dose": "2–3 分钟"},
     "en": {"name": "Get up and walk for two minutes", "how": "Stand up, fetch a glass of water or walk a lap of the corridor or the room, and look at something far away.", "dose": "2–3 minutes"}},
    {"id": "chin_tuck", "regions": ["neck"], "minutes": 1, "sitting": True,
     "zh": {"name": "收下巴", "how": "坐直，眼睛平视。下巴水平往后收，像要做出双下巴，后颈被拉长；不要低头。停 3 秒再放松。", "dose": "10 次"},
     "en": {"name": "Chin tucks", "how": "Sit tall and look straight ahead. Slide your chin straight back, as if making a double chin, so the back of your neck lengthens; don't nod down. Hold 3 seconds, then relax.", "dose": "10 times"}},
    {"id": "neck_side", "regions": ["neck"], "minutes": 2,
     "zh": {"name": "颈侧拉伸", "how": "坐直，右手轻扶椅子边。头慢慢向左侧倾，耳朵靠近左肩，感到右侧脖子轻轻被拉开就停住。换边。", "dose": "每边 20–30 秒，2 轮"},
     "en": {"name": "Side neck stretch", "how": "Sit tall and hold the edge of the chair with your right hand. Tilt your head slowly to the left, ear towards shoulder, until the right side of your neck feels a light stretch. Swap sides.", "dose": "20–30 seconds a side, twice"}},
    {"id": "doorway_chest", "regions": ["chest"], "minutes": 2, "sitting": True,
     "zh": {"name": "门框拉伸胸前", "how": "站在门框里，前臂贴住门框两侧，手肘和肩差不多高。一只脚向前迈小半步，身体前倾，直到胸前轻轻被拉开。", "dose": "30 秒，2 次"},
     "en": {"name": "Doorway chest stretch", "how": "Stand in a doorway with your forearms on the frame, elbows about shoulder height. Step one foot forward a little and lean in until the front of your chest feels a light stretch.", "dose": "30 seconds, twice"}},
    {"id": "thoracic_extension", "regions": ["upper_back", "chest"], "minutes": 1, "sitting": True,
     "zh": {"name": "坐姿胸椎伸展", "how": "坐在有靠背的椅子上，双手抱在脑后。以椅背上沿为支点，上背慢慢向后仰，眼睛看向天花板，再回来。腰不用力。", "dose": "8–10 次"},
     "en": {"name": "Seated upper-back extension", "how": "Sit on a chair with a backrest, hands behind your head. Using the top of the backrest as a hinge, lean your upper back slowly back, eyes to the ceiling, then come back up. Keep your lower back relaxed.", "dose": "8–10 times"}},
    {"id": "shoulder_blades", "regions": ["upper_back", "neck"], "minutes": 1, "sitting": True,
     "zh": {"name": "肩胛后收", "how": "坐直，肩膀放松下沉。两侧肩胛骨向后、向下夹紧，像要把它们放进后裤兜。停 5 秒再放松。", "dose": "10 次"},
     "en": {"name": "Shoulder-blade squeezes", "how": "Sit tall with your shoulders relaxed and low. Draw both shoulder blades back and down, as if tucking them into your back pockets. Hold 5 seconds, then relax.", "dose": "10 times"}},
    {"id": "wall_angel", "regions": ["upper_back", "chest"], "minutes": 2,
     "zh": {"name": "靠墙天使", "how": "背靠墙站，脚离墙一小步。手臂举成「W」形，手背和手肘尽量贴墙，慢慢向上滑成「Y」，再滑回来。贴不住就只做到舒服的位置。", "dose": "8–10 次，慢"},
     "en": {"name": "Wall angels", "how": "Stand with your back to a wall, feet a small step out. Raise your arms into a W, backs of the hands and elbows towards the wall, and slide them slowly up into a Y and back down. Go only as far as stays comfortable.", "dose": "8–10 slow times"}},
    {"id": "hip_flexor", "regions": ["hip_front"], "minutes": 2, "sitting": True,
     "zh": {"name": "髋前侧拉伸", "how": "单膝跪地（膝下垫个软垫），另一只脚在前踩地。收紧臀部，身体保持直立，骨盆慢慢往前送，直到后腿大腿前侧、髋部前面轻轻被拉开。换边。", "dose": "每边 30 秒，2 轮"},
     "en": {"name": "Kneeling hip-flexor stretch", "how": "Kneel on one knee (a cushion under it), the other foot flat in front. Squeeze your bum, stay upright, and ease your hips forward until the front of the back hip and thigh feel a light stretch. Swap sides.", "dose": "30 seconds a side, twice"}},
    {"id": "hamstring", "regions": ["thigh_back"], "minutes": 2,
     "zh": {"name": "大腿后侧拉伸", "how": "一只脚跟放在矮台阶或椅子横档上，膝盖微弯不锁死。背挺直，从髋部向前俯身，直到大腿后侧轻轻被拉开。换边。", "dose": "每边 30 秒，2 轮"},
     "en": {"name": "Hamstring stretch", "how": "Rest one heel on a low step or a chair rung, knee soft. Keep your back straight and hinge forward from the hips until the back of the thigh feels a light stretch. Swap sides.", "dose": "30 seconds a side, twice"}},
    {"id": "calf_wall", "regions": ["calf"], "minutes": 2,
     "zh": {"name": "小腿靠墙拉伸", "how": "双手扶墙，一只脚向后迈一步，脚跟踩实，后腿伸直，身体前倾，感到小腿后侧被拉开。再把后腿膝盖微弯，拉小腿更深的一层。换边。", "dose": "每边伸直和微弯各 30 秒"},
     "en": {"name": "Calf stretch at the wall", "how": "Hands on a wall, step one foot back, heel down and back leg straight, and lean in until the calf stretches. Then bend the back knee a little to reach the deeper calf muscle. Swap sides.", "dose": "30 seconds straight and 30 bent, each side"}},
    {"id": "pelvic_tilt", "regions": ["low_back"], "minutes": 1, "sitting": True,
     "zh": {"name": "坐姿骨盆前后倾", "how": "坐在椅子前半部分，双脚踩地。慢慢把腰向前挺、骨盆前倾，再慢慢弓背、骨盆后倾，来回动，只在不疼的范围里。", "dose": "10 个来回"},
     "en": {"name": "Seated pelvic tilts", "how": "Sit on the front half of the chair, feet flat. Slowly arch your lower back and tip the pelvis forward, then round it and tip the pelvis back, to and fro, only as far as stays pain-free.", "dose": "10 times each way"}},
    {"id": "wrist_forearm", "regions": ["wrist"], "minutes": 1,
     "zh": {"name": "前臂拉伸", "how": "手臂向前伸直，掌心向外，另一只手轻轻把手指往回扳，感到前臂内侧被拉开；再掌心向内往下扳。换手。", "dose": "每个方向 20 秒"},
     "en": {"name": "Forearm stretch", "how": "Hold one arm straight out, palm away, and with the other hand ease the fingers back until the inside of the forearm stretches; then palm in, ease them down. Swap hands.", "dose": "20 seconds each way"}},
]
BY_ID = {r["id"]: r for r in ROUTINES}

# when to stop and see someone; shown with every routine, and instead of any routine when "pain" is chosen together
# with one of these signs
STOP = {
    "zh": "应该只是轻微的拉伸感，不疼。出现麻木、刺痛、往手臂或腿放射的痛、头晕，或者疼痛越来越重、夜里痛醒、是受伤之后开始的，先停下，去看医生或物理治疗师。",
    "en": "It should feel like a light stretch, never pain. If you get numbness, pins and needles, pain spreading into an arm or leg, dizziness, or pain that keeps getting worse, wakes you at night or started with an injury, stop and see a doctor or physiotherapist.",
}

# a sitting reminder hands one move for the desk and a walk; the desk move turns over day by day, or follows where
# you said it was tight
SITTING_TURN = ("doorway_chest", "chin_tuck", "thoracic_extension", "hip_flexor", "shoulder_blades", "pelvic_tilt")


def for_regions(regions: Iterable[str], limit: int = 3) -> List[str]:
    """Routines for the regions you named, most specific first (a move for one region before one for several), at
    most `limit`, without repeats; nothing for regions not on the list."""
    wanted = [r for r in regions if r in REGIONS]
    out: List[str] = []
    for region in wanted:
        hits = sorted((r for r in ROUTINES if region in r["regions"]), key=lambda r: len(r["regions"]))
        for r in hits:
            if r["id"] not in out:
                out.append(r["id"])
                break
    for region in wanted:  # then a second move where there is one
        for r in (r for r in ROUTINES if region in r["regions"]):
            if r["id"] not in out:
                out.append(r["id"])
                break
    return out[:limit]


def for_sitting(day_number: int, regions: Iterable[str] = ()) -> List[str]:
    """A desk move (for where it was tight today, else the day's turn) and the walk."""
    named = [i for i in for_regions(regions, 3) if BY_ID[i].get("sitting")]
    desk = named[0] if named else SITTING_TURN[day_number % len(SITTING_TURN)]
    return [desk, "walk_break"]


def info(ids: Iterable[str]) -> Dict[str, Dict[str, Any]]:
    """What a page needs to show these routines (both languages, minutes, regions), keyed by id."""
    return {i: {k: BY_ID[i][k] for k in ("minutes", "regions", "zh", "en")} for i in ids if i in BY_ID}


def payload() -> Dict[str, Any]:
    return {"page": "routines", "routines": ROUTINES, "regions": list(REGIONS), "feelings": list(FEELINGS), "stop": STOP}
