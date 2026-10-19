"""A made-up person, so the dashboard can be tried without anyone's real data.

Sam is a graduate student in Melbourne: four courses, a night-owl sleep that a
wake-time plan is slowly pulling earlier, a weight plan that started seven weeks
ago, a food log kept most days for four months (with a late snack on
deadline nights, and a little less written down than eaten), and the screen
habits of most students. Everything is generated from a
fixed seed relative to "today", so the same day always gives the same numbers.
Nothing here is a real measurement; every page shows a "demo data" badge.
"""
import json
import math
import random
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

from .store import write_table

SEED = 20261012
BODY_DAYS = 420
SCREEN_DAYS = 120
LATE_MEAL_HRV_MS = 4.5  # the morning after a meal less than 3 hours before sleep (what the Food page should find)

COURSES = [  # code, name, weekly slots: (weekday 0=Mon, start, minutes, kind word, room)
    ("HCI 610", "Interaction Design", [(0, "10:00", 120, "Lecture", "Arts West 153"),
                                       (2, "14:00", 90, "Studio", "Design Hub 2.12")]),
    ("STAT 520", "Applied Statistics", [(1, "09:00", 60, "Lecture", "Old Quad 101"),
                                        (3, "09:00", 60, "Lecture", "Old Quad 101"),
                                        (3, "15:00", 60, "Tutorial", "Peter Hall G03")]),
    ("INFO 540", "Data Visualisation", [(1, "13:00", 120, "Lecture", "Online"),
                                        (4, "11:00", 90, "Workshop", "Melbourne Connect 3.05")]),
    ("SWEN 530", "Software Process", [(0, "16:00", 60, "Lecture", "Elisabeth Murdoch B117"),
                                      (2, "10:00", 120, "Tutorial", "Doug McDonell 7.02")]),
]

DEADLINES = [  # days from today, hh:mm, course, title, weight %, note
    (-44, "23:59", "STAT 520", "Assignment 1: Regression report", 15, "PDF, 6 pages"),
    (-30, "17:00", "HCI 610", "Design brief", 10, "Individual"),
    (-23, "23:59", "INFO 540", "Assignment 1: Dashboard critique", 20, "1,500 words"),
    (-12, "23:59", "SWEN 530", "Sprint 1 review", 10, "Team of 5"),
    (-3, "23:59", "STAT 520", "Assignment 2: Mixed models", 15, "R Markdown + PDF"),
    (2, "15:00", "HCI 610", "Usability test plan", 15, "Group of 4"),
    (4, "23:59", "SWEN 530", "Sprint 2 demo video", 5, "8–10 minutes"),
    (6, "23:59", "INFO 540", "Assignment 2: Interactive prototype", 30, "Shiny or Tableau"),
    (11, "23:59", "SWEN 530", "Team reflection", 10, "2,000 words"),
    (11, "23:59", "HCI 610", "Peer review", None, "Not graded, required"),
    (17, "23:59", "STAT 520", "Assignment 3: Case study", 20, "Pairs"),
    (23, "09:00", "HCI 610", "Final portfolio", 40, "Individual"),
    (29, "13:15", "STAT 520", "Final exam", 50, "2 hours, closed book"),
    (33, "09:00", "SWEN 530", "Final exam", 50, "Multiple choice + short answer"),
    (36, "13:15", "INFO 540", "Final exam", 40, "Hurdle 40%"),
]

TRAINING = {"mon": "Strength · upper body 50 min", "wed": "Easy run 30 min",
            "fri": "Strength · lower body 50 min", "sat": "Long walk 60 min"}
WORKOUT_DAYS = {0: ("strength training", 50), 2: ("running", 32), 4: ("strength training", 50), 5: ("walking", 62)}
WORKOUT_AT = {"strength training": "17:30", "running": "18:40", "walking": "11:00", "cycling": "16:10"}  # usual start

APPS = {  # category: [(device, app, weight)]
    "work": [("laptop", "VS Code", 4), ("laptop", "Figma", 2), ("laptop", "Google Docs", 3),
             ("laptop", "RStudio", 3), ("laptop", "Terminal", 1), ("laptop", "Claude", 2)],
    "learning": [("laptop", "canvas.lms.edu", 3), ("laptop", "Lecture recordings", 2), ("tablet", "Notability", 2)],
    "communication": [("laptop", "Slack", 3), ("phone", "WhatsApp", 3), ("laptop", "Mail", 2), ("phone", "Messages", 1)],
    "entertainment": [("tablet", "YouTube", 4), ("laptop", "youtube.com", 2), ("tablet", "Netflix", 2),
                      ("laptop", "Steam", 1), ("phone", "Spotify", 1)],
    "social": [("phone", "Instagram", 4), ("phone", "Reddit", 3), ("phone", "X", 2), ("phone", "TikTok", 2)],
    "other": [("laptop", "Finder", 2), ("phone", "Maps", 1), ("phone", "Banking", 1), ("laptop", "Settings", 1)],
}
# a second device in use at the same time (Sam.overlaps): what the phone does while the laptop or tablet is on
PHONE_ON_THE_SIDE = [("social", "Instagram", 4), ("social", "Reddit", 3), ("social", "TikTok", 2),
                     ("communication", "WhatsApp", 3), ("communication", "Messages", 1)]
# the week before deadlines: group chats about the work, open beside it
CRUNCH_SIDE = [("communication", "WhatsApp", 5), ("communication", "Messages", 1), ("social", "Instagram", 1)]
# what Sam eats: (title, share of the day's energy, share of that meal's energy from protein)
MENU = {
    "breakfast": [("Oats with banana", 0.20, 0.13), ("Toast and eggs", 0.22, 0.22), ("Yoghurt and granola", 0.19, 0.18),
                  ("Flat white and croissant", 0.18, 0.08)],
    "lunch": [("Chicken rice bowl", 0.32, 0.26), ("Sushi rolls", 0.28, 0.16), ("Pho", 0.30, 0.22), ("Burrito", 0.36, 0.17),
              ("Leftover pasta", 0.33, 0.14)],
    "dinner": [("Tofu stir-fry and rice", 0.34, 0.17), ("Salmon and vegetables", 0.33, 0.30), ("Spaghetti bolognese", 0.38, 0.19),
               ("Dumplings", 0.35, 0.15), ("Chicken curry", 0.37, 0.24)],
    "snack": [("Apple", 0.04, 0.02), ("Protein bar", 0.09, 0.32), ("Chips", 0.10, 0.05), ("Banana", 0.05, 0.04)],
    "late": [("Instant noodles", 0.17, 0.08), ("Toast with peanut butter", 0.13, 0.14), ("Ice cream", 0.12, 0.07)],
}
WORKOUT_HR = {"strength training": (118, 8), "running": (152, 6), "walking": (101, 6), "cycling": (134, 8)}
AGENT_APPS = ("Claude", "Terminal")  # an agent can run on its own here while Sam is on another device
EDITOR_AGENT = {"VS Code": 0.7, "RStudio": 0.25}  # how often a session in the editor has an agent working in it


def _hm(text: str) -> time:
    hour, minute = text.split(":")
    return time(int(hour), int(minute))


def _since_noon(t: datetime) -> int:
    """Minutes after the previous noon, so 23:30 comes before 01:10."""
    return (t.hour * 60 + t.minute - 12 * 60) % (24 * 60)


def _at(day: date, minutes_from_midnight: float) -> datetime:
    return datetime.combine(day, time()) + timedelta(minutes=round(minutes_from_midnight))


class Sam:
    def __init__(self, today: date, now: Optional[datetime] = None):
        self.today = today
        self.now = now or datetime.combine(today, time(18, 40))
        self.rng = random.Random(SEED + today.toordinal())
        self.shift_start = today - timedelta(days=12)
        self.weight_start = today - timedelta(days=49)
        self.weight_start_kg = 81.2  # set by body(): the weight the plan starts from, as generated
        self.semester_start = today - timedelta(days=70)
        self.semester_end = today + timedelta(days=40)
        self.workouts: List[Dict] = []
        # nights with a late snack: more of them in the days before a deadline (their own random stream, so
        # nothing else about Sam changes); the HRV of the next morning pays a little for it
        late_rng = random.Random(SEED + 21)
        crunch = {today + timedelta(days=d[0] - k) for d in DEADLINES for k in range(3)}
        self.food_start = today - timedelta(days=SCREEN_DAYS - 1)
        self.late = {self.food_start + timedelta(days=k): late_rng.random() < (0.6 if self.food_start + timedelta(days=k) in crunch else 0.25)
                     for k in range((today - self.food_start).days)}

    # ---- sleep -------------------------------------------------------------------------------
    def alarm_for(self, day: date, on_time: Dict[date, bool]) -> Optional[float]:
        """The wake-shift rule: one 15-minute step earlier after each on-time morning, never later."""
        if day < self.shift_start:
            return None
        alarm = 10 * 60 + 30
        d = self.shift_start
        while d < day:
            if on_time.get(d):
                alarm = max(7 * 60 + 30, alarm - 15)
            d += timedelta(days=1)
        return alarm

    def nights(self) -> Dict[date, Tuple[datetime, datetime, float]]:
        rng = self.rng
        out: Dict[date, Tuple[datetime, datetime, float]] = {}
        on_time: Dict[date, bool] = {}
        start = self.today - timedelta(days=BODY_DAYS - 1)
        for k in range(BODY_DAYS):
            day = start + timedelta(days=k)
            if rng.random() < 0.035:  # watch left on the charger
                continue
            weekend = day.weekday() >= 5
            alarm = self.alarm_for(day, on_time)
            if alarm is None:
                wake = 10 * 60 + 20 + (55 if weekend else 0) + rng.gauss(0, 50)
            else:
                late = rng.random() < 0.3
                wake = alarm + (rng.uniform(20, 95) if late else rng.uniform(-10, 12))
                on_time[day] = not late and wake <= alarm + 15
            duration = max(4.2, min(10.5, rng.gauss(7.45 if not weekend else 8.1, 0.85)))
            if alarm is not None:  # an earlier alarm cuts sleep until bedtime catches up
                duration -= max(0.0, (10 * 60 + 30 - alarm) / 60) * 0.35
            end = _at(day, wake)
            begin = end - timedelta(hours=duration)
            out[day] = (begin, end, duration)
        return out

    # ---- body --------------------------------------------------------------------------------
    def body(self) -> List[Dict]:
        rng = self.rng
        nights = self.nights()
        rows: List[Dict] = []
        start = self.today - timedelta(days=BODY_DAYS - 1)
        hrv_noise = 0.0
        weight = 81.6
        trained_yesterday = False
        energy = random.Random(SEED + 22)  # energy burned and workout heart rate: their own stream
        for k in range(BODY_DAYS):
            day = start + timedelta(days=k)
            night = nights.get(day)
            sleep_h = night[2] if night else None
            hrv_noise = 0.62 * hrv_noise + rng.gauss(0, 3.6)
            seasonal = 2.2 * math.sin(k / 41.0)
            hrv = 44 + seasonal + hrv_noise + (1.1 * (sleep_h - 7.4) if sleep_h else 0) - (1.6 if trained_yesterday else 0)
            late = self.late.get(day - timedelta(days=1), False)
            hrv -= LATE_MEAL_HRV_MS if late else 0
            if rng.random() < 0.05:
                hrv -= rng.uniform(5, 11)  # a late night out
            rhr = 61.5 - 0.09 * (hrv - 44) - (0.45 * (sleep_h - 7.4) if sleep_h else 0) + rng.gauss(0, 1.2) + (0.6 if late else 0)
            plan = WORKOUT_DAYS.get(day.weekday())
            did = plan is not None and rng.random() < 0.74
            if not did and plan is None and rng.random() < 0.06:
                plan, did = ("cycling", 40), True
            campus = day.weekday() <= 4 and self.semester_start <= day <= self.semester_end
            steps = max(800.0, rng.gauss(8600 if campus else 5600, 2300) + (3500 if did and plan[0] in ("running", "walking") else 0))
            exercise = max(0.0, rng.gauss(14, 7) + (plan[1] * rng.uniform(0.7, 1.0) if did else 0))
            complete = day != self.today
            row = {"date": day, "complete": complete}
            if night:
                begin, end, duration = night
                row.update(sleep_min=round(duration * 60), in_bed_min=round(duration * 60 + rng.uniform(12, 42)),
                           sleep_start=begin, sleep_end=end)
            if rng.random() > 0.03:
                row["hrv_ms"] = round(max(18.0, hrv), 1)
                row["resting_hr"] = round(rhr, 1)
            basal = 1690 + 11 * (weight - 75) + energy.gauss(0, 22)
            if complete:
                minutes = round(plan[1] * rng.uniform(0.85, 1.15)) if did else 0
                row.update(steps=round(steps), exercise_min=max(round(exercise), minutes),
                           workout_min=minutes, workout_type=plan[0] if did else None)
                burned = 0.0
                if did:  # the same workout with its clock time, as Apple Fitness records it
                    hh, mm = map(int, WORKOUT_AT[plan[0]].split(":"))
                    begin = datetime.combine(day, time(hh, mm)) + timedelta(minutes=rng.randint(-25, 35))
                    burned = round(minutes * rng.uniform(5.5, 8.5))
                    mean, sd = WORKOUT_HR[plan[0]]
                    self.workouts.append({"start": begin, "end": begin + timedelta(minutes=minutes), "type": plan[0],
                                          "source": "Apple Watch", "kcal": burned, "avg_hr": round(energy.gauss(mean, sd))})
                row.update(active_kcal=round(250 + 0.035 * steps + 0.9 * burned + energy.gauss(0, 45)), basal_kcal=round(basal))
            else:
                share = (self.now.hour * 60 + self.now.minute - 600) / 840
                row.update(steps=round(steps * max(0.05, share)), exercise_min=round(exercise * max(0.0, share)),
                           active_kcal=round((250 + 0.035 * steps) * max(0.05, share)), basal_kcal=round(basal * self.now.hour / 24))
            # weight: drifting before the plan, ~0.6% a week down after it. The plan starts from the weight as it is
            # that day, so its corridor begins where the line does (the walk moves whenever the stream draws differ)
            if day == self.weight_start:
                self.weight_start_kg = round(weight, 1)
            if day < self.weight_start:
                weight += rng.gauss(0.004, 0.09)
                weighed = rng.random() < 0.3
            else:
                weight -= weight * 0.0062 / 7 * rng.uniform(0.2, 1.8)
                weighed = rng.random() < 0.8
            if weighed:
                row["weight_kg"] = round(weight + rng.gauss(0, 0.32), 1)
            if day >= self.weight_start and day.weekday() == 6:
                row["waist_cm"] = round(92.5 - (day - self.weight_start).days * 0.045 + rng.gauss(0, 0.4), 1)
            trained_yesterday = did and plan[0] == "strength training"
            rows.append(row)
        return rows

    # ---- food --------------------------------------------------------------------------------
    def meals(self, body: List[Dict]) -> List[Dict]:
        """A food log kept for the last four months: most days in full, some days only a meal or two, some not at
        all (weekends more often). Sam eats less once the weight plan starts, writes down a little less than was
        eaten (as most people do), skips breakfast after a late wake, and has a late snack on the nights in
        self.late; protein stays under the plan's 1.6 g per kg."""
        rng = random.Random(SEED + 23)
        by_day = {row["date"]: row for row in body}
        out: List[Dict] = []
        day = self.food_start
        while day <= self.today:
            weekend = day.weekday() >= 5
            state = rng.choices(["full", "partial", "none"], [0.62, 0.18, 0.2] if weekend else [0.84, 0.08, 0.08])[0]
            eaten = rng.gauss(2560 if day < self.weight_start else 2080, 210)
            written = eaten * rng.uniform(0.84, 0.96)  # what makes it into the log
            row, tomorrow = by_day.get(day, {}), by_day.get(day + timedelta(days=1), {})
            wake = row.get("sleep_end") or datetime.combine(day, time(9, 30))
            plan = []
            if wake.hour < 10 or rng.random() < 0.35:
                plan.append(("breakfast", wake + timedelta(minutes=rng.uniform(20, 70))))
            plan.append(("lunch", datetime.combine(day, time(12, 15)) + timedelta(minutes=rng.uniform(0, 90))))
            if rng.random() < 0.4:
                plan.append(("snack", datetime.combine(day, time(15, 30)) + timedelta(minutes=rng.uniform(0, 60))))
            plan.append(("dinner", datetime.combine(day, time(18, 30)) + timedelta(minutes=rng.uniform(0, 105))))
            asleep = tomorrow.get("sleep_start")
            if self.late.get(day) and asleep:
                plan.append(("late", asleep - timedelta(minutes=rng.uniform(45, 150))))
            if state == "partial":
                keep = rng.choice([m for m, _ in plan if m in ("lunch", "dinner")])
                plan = [(m, t) for m, t in plan if m == keep]
            if state == "none":
                plan = []
            picks = [(meal, at, rng.choice(MENU[meal])) for meal, at in plan]
            # the day's food is shared out over the meals eaten; a late snack comes on top of it
            shares = sum(share for meal, _, (_, share, _) in picks if meal != "late") or 1.0
            for meal, at, (title, share, protein) in picks:
                if at > self.now:
                    continue
                kcal = written * share / (1.0 if meal == "late" else shares) * rng.uniform(0.88, 1.12)
                carbs_share = rng.uniform(0.42, 0.55)
                out.append({"time": at.replace(second=0, microsecond=0), "meal": "snack" if meal == "late" else meal,
                            "title": title, "kcal": round(kcal), "protein_g": round(kcal * protein / 4, 1),
                            "carbs_g": round(kcal * carbs_share / 4, 1),
                            "fat_g": round(kcal * max(0.12, 1 - protein - carbs_share) / 9, 1),
                            "fiber_g": round(kcal / 1000 * rng.uniform(7, 14), 1), "source": "Food log app"})
            day += timedelta(days=1)
        return out

    def self_report(self, body: List[Dict]) -> List[Dict]:
        rng = random.Random(SEED + 7)
        notes = ["Slept through", "Heavy legs after the gym", "Groggy, alarm too early", "Good focus in the morning",
                 "Too much coffee", "Calm day", "Stayed up for the deadline", "Felt fresh after the run"]
        out = []
        for row in body[-150:]:
            if rng.random() > 0.55:
                continue
            sleep = (row.get("sleep_min") or 420) / 60
            energy = max(0, min(5, round(2.4 + 0.5 * (sleep - 7.2) + rng.gauss(0, 0.8))))
            focus = max(0, min(5, round(2.6 + 0.3 * (sleep - 7.2) + rng.gauss(0, 0.9))))
            out.append({"date": row["date"], "energy": energy, "focus": focus,
                        "note": rng.choice(notes) if rng.random() < 0.35 else None})
        return out

    # ---- calendar ----------------------------------------------------------------------------
    def events(self) -> List[Dict]:
        out = []
        day = self.semester_start
        midterm = self.semester_start + timedelta(days=42)  # one teaching-free week
        while day <= self.semester_end - timedelta(days=12):
            if not (midterm <= day < midterm + timedelta(days=7)):
                for code, name, slots in COURSES:
                    for weekday, start, minutes, word, room in slots:
                        if day.weekday() == weekday:
                            begin = datetime.combine(day, _hm(start))
                            out.append({"start": begin, "end": begin + timedelta(minutes=minutes),
                                        "title": f"{code} {word}", "kind": "class", "location": room})
            day += timedelta(days=1)
        for offset, start, minutes, title in [(1, "18:30", 120, "Dinner with flatmates"), (5, "10:00", 90, "Farmers market"),
                                              (8, "12:00", 60, "Career fair")]:
            begin = datetime.combine(self.today + timedelta(days=offset), _hm(start))
            out.append({"start": begin, "end": begin + timedelta(minutes=minutes), "title": title,
                        "kind": "personal", "location": None})
        return out

    def deadlines(self) -> List[Dict]:
        out = []
        for offset, hhmm, group, title, weight, note in DEADLINES:
            due = datetime.combine(self.today + timedelta(days=offset), _hm(hhmm))
            status = "submitted" if offset < 0 else ("todo" if offset > 0 else "todo")
            out.append({"due": due, "title": title, "group": group, "weight_pct": weight,
                        "status": status, "note": note})
        return out

    # ---- effort and soreness ---------------------------------------------------------------------
    def rate_workouts(self) -> None:
        """Effort on Apple's 1-10 scale for each workout (its own random stream, so nothing else moves): Sam rates
        most sessions himself in the Fitness app; the rest keep the watch's estimate, and a few have neither.
        Strength days are hard, runs moderate, walks easy; the week before a deadline runs a little harder."""
        rng = random.Random(SEED + 29)
        base = {"strength training": 7.0, "running": 5.5, "walking": 2.5, "cycling": 4.5}
        for w in self.workouts:
            crunch = any(0 <= (self.today + timedelta(days=d[0]) - w["start"].date()).days <= 7 for d in DEADLINES)
            effort = base.get(w["type"], 4.0) + rng.gauss(0, 0.9) + (0.6 if crunch else 0)
            roll = rng.random()
            if roll < 0.08:
                continue  # no rating, no estimate
            w["effort"] = float(min(10, max(1, round(effort))))
            w["effort_source"] = "rated" if roll < 0.82 else "estimated"

    def cardio(self, body: List[Dict]) -> None:
        """VO2 max as Apple Watch estimates it: after most outdoor runs and walks, so a value every few days.
        Flat until Sam started running regularly about seven months ago, then climbing about 1.5 mL/kg/min every three
        months, with the watch's own scatter."""
        rng = random.Random(SEED + 43)
        by_day = {r["date"]: r for r in body}
        first = self.today - timedelta(days=BODY_DAYS - 1)
        for w in sorted(self.workouts, key=lambda x: x["start"]):
            day = w["start"].date()
            chance = {"running": 0.9, "walking": 0.6}.get(w["type"], 0)
            if day >= self.today or day not in by_day or rng.random() > chance:
                continue
            level = 40.6 + 0.016 * max(0, (day - (self.today - timedelta(days=210))).days) + rng.gauss(0, 0.55)
            by_day[day]["vo2max"] = round(level, 1)

    def lunch_run(self) -> None:
        """Today Sam fitted in a run at lunch, harder than usual (an 8 he rated himself). Nothing is written yet about
        what it trained, so every page asks (the after-workout prompt)."""
        if self.now.time() < time(13, 30):
            return
        begin = datetime.combine(self.today, time(12, 20))
        self.workouts.append({"start": begin, "end": begin + timedelta(minutes=34), "type": "running", "source": "Apple Watch",
                              "kcal": 342, "avg_hr": 161, "effort": 8.0, "effort_source": "rated"})

    def workout_notes(self) -> List[Dict]:
        """What Sam wrote about his strength sessions and hard runs: most of them, those of the last four days always
        (so this week's check-ins ask about them), never today's run. Monday is upper body, Friday lower, as in
        soreness(); the notes use the words the page turns into regions."""
        rng = random.Random(SEED + 41)
        upper = ("Bench, rows, curls", "Pull-ups, bench press, dips", "Chest and back, then arms")
        lower = ("Squats, deadlifts, calf raises", "Leg day: squats and lunges", "Deadlifts, hip thrusts, calf raises")
        runs = ("Tempo run", "Intervals, calves heavy at the end")
        rows = []
        for w in sorted(self.workouts, key=lambda x: x["start"]):
            day = w["start"].date()
            if day >= self.today or not (w["type"] == "strength training" or (w.get("effort") or 0) >= 7):
                continue
            if (self.today - day).days > 4 and rng.random() < 0.2:
                continue  # not written that time
            if w["type"] == "strength training" and day.weekday() == 0:
                regions, note = ("torso", "left_upper_arm", "right_upper_arm"), rng.choice(upper)
            elif w["type"] == "strength training":
                regions, note = ("pelvis", "left_calf", "right_calf"), rng.choice(lower)
            else:
                regions, note = ("left_calf", "right_calf"), rng.choice(runs)
            rows.append({"start": w["start"], "regions": " ".join(regions), "note": note})
        return rows

    def soreness(self) -> List[Dict]:
        """Morning check-ins on nine mornings in ten after a workout and one in two otherwise (the morning after is
        when Sam wants to know how he came back): the regions a workout loads are sore the next morning
        and fading the one after (upper-body strength on Mondays: torso and upper arms; lower body on Fridays: hips
        and calves; runs: calves), now and then a stiff neck, and a check-in with nothing sore otherwise."""
        rng = random.Random(SEED + 31)
        hits: Dict[date, Dict[str, int]] = {}
        for w in self.workouts:
            day = w["start"].date()
            if w["type"] == "strength training":
                regions = ["torso", "left_upper_arm", "right_upper_arm"] if day.weekday() == 0 else ["pelvis", "left_calf", "right_calf"]
                first = 2 if (w.get("effort") or 6) < 8 else 3
            elif w["type"] == "running":
                regions, first = ["left_calf", "right_calf"], 1
            else:
                continue
            for lag, level in ((1, first), (2, first - 1)):
                if level <= 0:
                    continue
                spot = hits.setdefault(day + timedelta(days=lag), {})
                for region in regions:
                    if rng.random() < 0.85:
                        spot[region] = max(spot.get(region, 0), max(1, level - (1 if rng.random() < 0.25 else 0)))
        after = {w["start"].date() + timedelta(days=1) for w in self.workouts}
        rows: List[Dict] = []
        start = self.today - timedelta(days=BODY_DAYS - 1)
        for k in range(BODY_DAYS):
            day = start + timedelta(days=k)
            if rng.random() > (0.9 if day in after else 0.5):
                continue  # no check-in that morning
            sore = dict(hits.get(day, {}))
            if rng.random() < 0.05:
                sore["head"] = 1
            if not sore:
                rows.append({"date": day, "region": "none", "level": 0})
            for region, level in sorted(sore.items()):
                rows.append({"date": day, "region": region, "level": level})
        return rows

    def energy_ratings(self, report: List[Dict]) -> List[Dict]:
        """Sam rates his energy on the 0–10 "How you are right now" card on the mornings he rated it: about twice his
        0–5 answer, give or take one, a little after eight; and this morning too, so the demo has a current rating."""
        rng = random.Random(SEED + 43)
        tz = ZoneInfo("Australia/Melbourne")
        by_day = {(r["date"] if isinstance(r["date"], date) else date.fromisoformat(r["date"])): r["energy"]
                  for r in report if r.get("energy") is not None}
        by_day.setdefault(self.today, 3)
        out = []
        for i, (day, energy) in enumerate(sorted(by_day.items())):
            at = datetime.combine(day, datetime.min.time(), tzinfo=tz).replace(hour=7 if day == self.today else 8, minute=rng.randint(5, 50))
            out.append({"request_id": f"demo-energy-{day.isoformat()}", "kind": "energy", "region": None,
                        "value": max(0, min(10, energy * 2 + rng.choice((-1, 0, 0, 1)))), "v": 1,
                        "id": f"demo{i:08d}", "at": at.isoformat(timespec="seconds"), "scale": 10})
        return out

    def with_feelings(self, report: List[Dict], body: List[Dict], mornings) -> List[Dict]:
        """On the mornings Sam checks in he also answers how he feels: 8 after a good night with HRV above his usual,
        2 after a short night or a low HRV, 5 otherwise, now and then off by one answer (his own random stream)."""
        rng = random.Random(SEED + 37)
        by_day = {r["date"]: r for r in body}
        hrvs = [r["hrv_ms"] for r in body if r.get("hrv_ms") is not None]
        usual = sorted(hrvs)[len(hrvs) // 2] if hrvs else None
        rows = {r["date"]: dict(r) for r in report}
        for day in sorted(mornings):
            r = by_day.get(day) or {}
            short = (r.get("sleep_min") or 450) < 6.5 * 60
            low = usual is not None and r.get("hrv_ms") is not None and r["hrv_ms"] < usual * 0.93
            high = usual is not None and r.get("hrv_ms") is not None and r["hrv_ms"] > usual * 1.04
            feel = 2 if (short or low) else 8 if (high and not short) else 5
            if rng.random() < 0.2:
                feel = rng.choice([x for x in (2, 5, 8) if x != feel])
            rows.setdefault(day, {"date": day})["feel"] = feel
        return [rows[d] for d in sorted(rows)]

    # ---- screen ------------------------------------------------------------------------------
    def screen(self, body: List[Dict], events: List[Dict]) -> List[Dict]:
        """Sam's screens. Two habits make the Stimulation page's "how the body answers" card show something: on
        nights Sam falls asleep later than usual the last hour is mostly scrolling (on earlier nights mostly
        winding down), and the evening before a morning with HRV under Sam's normal (a stressful day) holds more
        entertainment."""
        rng = random.Random(SEED + 11)
        by_day = {row["date"]: row for row in body}
        onsets = sorted(_since_noon(row["sleep_start"]) for row in body if row.get("sleep_start"))
        usual_onset = onsets[len(onsets) // 2] if onsets else None
        hrv = {row["date"]: row["hrv_ms"] for row in body if row.get("hrv_ms") is not None}

        def stressed(morning: date) -> bool:
            past = sorted(hrv[morning - timedelta(days=j)] for j in range(1, 29) if morning - timedelta(days=j) in hrv)
            return morning in hrv and len(past) >= 10 and hrv[morning] < past[len(past) // 2]
        classes: Dict[date, List[Tuple[datetime, datetime]]] = {}
        for e in list(events) + list(self.workouts):
            classes.setdefault(e["start"].date(), []).append((e["start"], e["end"]))
        out: List[Dict] = []
        for k in range(SCREEN_DAYS - 1, -1, -1):
            day = self.today - timedelta(days=k)
            wake_row, next_row = by_day.get(day, {}), by_day.get(day + timedelta(days=1), {})
            wake = wake_row.get("sleep_end") or datetime.combine(day, time(10, 30))
            bed = next_row.get("sleep_start") or datetime.combine(day + timedelta(days=1), time(1, 45))
            stop = min(bed, self.now) if day == self.today else bed
            busy = classes.get(day, [])
            deadline_crunch = any(0 <= (self.today + timedelta(days=d[0]) - day).days <= 2 for d in DEADLINES)
            late_night = usual_onset is not None and next_row.get("sleep_start") is not None and _since_noon(bed) > usual_onset
            tense = stressed(day + timedelta(days=1))
            t = wake + timedelta(minutes=rng.uniform(1, 6))
            while t < stop:
                if any(a <= t < b for a, b in busy):
                    t = max(b for a, b in busy if a <= t < b) + timedelta(minutes=rng.uniform(3, 12))
                    continue
                minutes_left = (stop - t).total_seconds() / 60
                hour = t.hour + t.minute / 60
                before_bed = minutes_left < 60
                if before_bed:
                    weights = ({"social": 6, "entertainment": 5, "communication": 1, "other": 0.3} if late_night
                               else {"social": 0.6, "entertainment": 0.2, "communication": 2, "other": 3})
                elif hour < 12:
                    weights = {"social": 2.5, "communication": 2, "work": 2, "learning": 1.5, "other": 1}
                elif hour < 18:
                    weights = {"work": 5 + (3 if deadline_crunch else 0), "learning": 2.5, "communication": 2,
                               "social": 1.5 * (3 if tense else 1), "entertainment": 1 * (4 if tense else 1), "other": 0.8}
                else:
                    weights = {"work": 2 + (4 if deadline_crunch else 0), "entertainment": 4.5 * (3 if tense else 1),
                               "social": 2.5 * (2.5 if tense else 1), "communication": 1.5, "learning": 0.8, "other": 0.5}
                category = rng.choices(list(weights), list(weights.values()))[0]
                device, app, _ = rng.choices(APPS[category], [w for _, _, w in APPS[category]])[0]
                length = {"work": rng.expovariate(1 / 32), "learning": rng.expovariate(1 / 26),
                          "entertainment": rng.expovariate(1 / 34), "social": rng.expovariate(1 / 11),
                          "communication": rng.expovariate(1 / 5), "other": rng.expovariate(1 / 4)}[category]
                length = max(1.0, min(length, 150.0, minutes_left))
                end = t + timedelta(minutes=length)
                out.append({"start": t, "end": end, "device": device, "app": app, "category": category})
                gap = rng.expovariate(1 / 7) if rng.random() < 0.8 else rng.uniform(20, 75)  # meals, walks, away
                t = end + timedelta(minutes=gap)
        return out + self.overlaps(out)

    def overlaps(self, sessions: List[Dict]) -> List[Dict]:
        """A second device at the same time, on top of the one-at-a-time sessions above (its own random
        stream, so those stay the same): the phone while a video plays on the tablet, the phone while an
        agent runs on the laptop, quick checks during work (more of them in the week before deadlines),
        and now and then the same video left open on the laptop too (one thing on two devices)."""
        rng = random.Random(SEED + 12)
        out: List[Dict] = []

        def side(start: datetime, end: datetime, device: str = "phone", pick=PHONE_ON_THE_SIDE) -> None:
            if end - start < timedelta(minutes=1):
                return
            category, app, _ = rng.choices(pick, [w for _, _, w in pick])[0]
            out.append({"start": start, "end": end, "device": device, "app": app, "category": category})

        for s in sessions:
            length = (s["end"] - s["start"]).total_seconds() / 60
            if length < 6 or s["device"] == "phone":
                continue
            crunch = (self.today - s["start"].date()).days < 7  # deadlines in the coming days: more phone checks
            if s["device"] == "laptop" and s["app"] in AGENT_APPS and rng.random() < 0.75:
                start = s["start"] + timedelta(minutes=length * rng.uniform(0.1, 0.3))  # set the agent going, then scroll
                end = start + timedelta(minutes=length * rng.uniform(0.45, 0.65))
                if rng.random() < 0.6:
                    side(start, end)
                else:
                    side(start, end, "tablet", [("entertainment", "YouTube", 3), ("entertainment", "Netflix", 1)])
            elif s["device"] == "tablet" and s["category"] == "entertainment" and rng.random() < 0.8:
                t = s["start"] + timedelta(minutes=rng.uniform(1, 6))
                while t < s["end"] - timedelta(minutes=3):  # scrolling the phone with a video on
                    end = min(s["end"], t + timedelta(minutes=rng.uniform(4, 14)))
                    side(t, end)
                    t = end + timedelta(minutes=rng.uniform(3, 12))
                if s["app"] == "YouTube" and rng.random() < 0.15:  # the same video open on the laptop too
                    out.append({"start": s["start"], "end": s["start"] + timedelta(minutes=min(length, rng.uniform(5, 15))),
                                "device": "laptop", "app": "YouTube", "category": "entertainment"})
            elif s["device"] == "laptop" and s["category"] in ("work", "learning", "entertainment"):
                busy = crunch and s["category"] != "entertainment"
                chance = 0.45 if s["category"] == "entertainment" else 0.9 if busy else 0.4
                t = s["start"] + timedelta(minutes=rng.uniform(2, 8))
                while t < s["end"] - timedelta(minutes=2):
                    if rng.random() < chance:
                        end = min(s["end"], t + timedelta(minutes=rng.uniform(3, 12) if busy else rng.uniform(2, 9)))
                        side(t, end, pick=CRUNCH_SIDE if busy else PHONE_ON_THE_SIDE)
                        t = end
                    t += timedelta(minutes=rng.uniform(3, 9) if busy else rng.uniform(5, 14))
        return out


def demo_config(today: date, start_kg: float = 81.2) -> str:
    shift = today - timedelta(days=12)
    weight = today - timedelta(days=49)
    training = "\n".join(f'{day} = "{text}"' for day, text in TRAINING.items())
    return f"""# Demo settings for a made-up person. Copy examples/healthaio.example.toml for your own.
[healthaio]
data_dir = "data"
timezone = "Australia/Melbourne"
locale = "en"
title = "Health AIO"
demo = true

[devices]
priority = ["phone", "tablet", "laptop"]

[plan.sleep]
target_hours = 8
bedtime = "23:30"
wake = "07:30"

[plan.wake_shift]
start = "{shift.isoformat()}"
first_alarm = "10:30"
final_alarm = "07:30"
step_min = 15
grace_min = 15

[plan.weight]
start_date = "{weight.isoformat()}"
start_kg = {start_kg}
target_kg = 75
weekly_loss_pct = [0.5, 1.0]

[plan.training]
{training}

[plan.exercise]
weekly_min = 150
strength_days = 2

[plan.food]
kcal_min = 1900
kcal_max = 2300
protein_g_per_kg = 1.6
last_meal_gap_h = 3

[plan.screen]
entertainment_max_hours = 3
work_min_hours = 4
"""


def generate(out: Path, today: Optional[date] = None, now: Optional[datetime] = None) -> Path:
    """Write a complete demo folder (healthaio.toml + data/*.csv) and return the config path."""
    today = today or date.today()
    out = Path(out)
    data = out / "data"
    sam = Sam(today, now)
    body = sam.body()
    sam.cardio(body)
    events = sam.events()
    write_table(data, "body_daily", body)
    sore = sam.soreness()
    report = sam.with_feelings(sam.self_report(body), body, {r["date"] for r in sore})
    write_table(data, "self_report", report)
    write_table(data, "events", events)
    write_table(data, "deadlines", sam.deadlines())
    sam.rate_workouts()
    sam.lunch_run()
    write_table(data, "workouts", sam.workouts)
    write_table(data, "workout_notes", sam.workout_notes())
    write_table(data, "soreness", sore)
    write_table(data, "meals", sam.meals(body))
    sessions = sam.screen(body, events)
    write_table(data, "screen_sessions", sessions)
    config = out / "healthaio.toml"
    config.write_text(demo_config(today, sam.weight_start_kg), encoding="utf-8")
    # one proposal from an assistant, waiting on the Goals page (see goal_log): it changes nothing until accepted
    proposal = {"id": "5a3e0c1d", "at": f"{today.isoformat()}T08:30:00", "op": "propose", "by": "assistant",
                "changes": {"screen.entertainment_max_hours": 2.5},
                "note": {"en": "A smaller step first: half an hour less a day, then look again in two weeks.",
                         "zh": "先小步收：每天少半小时，两周后再看。"}}
    (out / "goals.jsonl").write_text(json.dumps(proposal, ensure_ascii=False) + "\n", encoding="utf-8")
    # energy said on the "How you are right now" card, kept with its time (see recovery_log)
    (out / "recovery_observations.jsonl").write_text("".join(json.dumps(r) + "\n" for r in sam.energy_ratings(report)), encoding="utf-8")
    return config
