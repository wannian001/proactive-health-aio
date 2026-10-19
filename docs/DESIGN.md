# Design notes

The look itself (tokens, components, charts, icons) is the design kit: [DESIGN_KIT.md](DESIGN_KIT.md), shown on the
gallery page `#kit`. This file is about what Health AIO's pages say and why.

## Who it is for

One person managing their own health from their own data, usually in the morning and before bed. Proactive means
the app reads the pages for you: the Today page has to answer, in this order, how am I today, **what should I adjust
today and why**, what is on, where did yesterday go, what has tended to help. Everything else is detail behind a
"How this is worked out" fold.

## A first look takes seconds

The pages are read by someone who opens them for half a minute in the morning, often in their first week. So every
page has the same shape: one sentence or one number that answers its question, the main chart, the rest of the
detail in tabs inside one card, and one "How this is worked out" fold at the end. A line on Today carries a name, a
number and a state, never a sentence; the sentence is on the page the line opens. Nothing is dropped to get there:
what a page no longer shows sits in a tab, a fold, or on the one page that owns it (the next-day patterns moved from
Today to Follow-up, the night-by-night sleep checks to Goals, the workout list from Time to Exercise). The calendar is
context, not a subject: one line on Today and a faint arc on the day ring; the list is on Schedule.

## What to adjust today

At most three items, at most one each for training, sleep, food and daytime screens (when all four have one, screens
wait: the hour before sleep is already the sleep item), each with the reason in numbers and a link to the page that
shows them. Fixed rules (listed in `healthaio/modules/actions.py` and in the card's fold), checked in order
within each kind: recovery below normal with training planned → take it easy; a load spike → rest; a part clearly
sore this morning → train but spare it; otherwise what the week's activity goal needs today, or a strength session
when the days left barely fit. The first three are about today's session, so once it is done (the minutes the plan
names, "Easy run 30 min", mostly in; 10 minutes when it names none) they are dropped: "take it easy today" after a
hard lunchtime run is advice that comes too late. A past day is still rebuilt as its morning saw it. Sleep: recovery low or a
short night → tonight's time to be asleep by; screens before sleep above normal → when to put the phone away. Food,
over the last 7 logged days: late last meals → when to finish dinner; then protein under 90% of the target; then
energy above the plan. Screens in the day, over the last 7 whole days: entertainment & social above the plan, or
above your normal when there is no plan → a cap for today (the plan, or your usual day to half an hour). Nothing off
is said as "a steady day", never as invented advice. Items need the data behind
them: no activity records, no "move more". No model, no score, and the card says it is not medical advice.

## Follow-up

Advice that is never checked turns into a list people learn to skip, and a reminder that keeps failing will not
start working by being repeated. So the Follow-up page closes the loop from the data alone, with nothing to tick: yesterday's advice
rebuilt with the same rules from the data as it stood that morning, each piece marked done, not done or no record
with the fact behind it (asleep at 02:47, 2 h 17 min after the time given); the last 14 days of each piece as a row
of dots; and for advice not done on 3 of its last 5 times, other ways with the person's own numbers in place of the
reminder: a smaller step (halfway from the median of what they did to the target, three days in a row before
moving on), a phone setting that does the remembering (Downtime, App Limits; the app cannot change Screen Time
itself, so it names the setting and the value), a change to the room, and an if-then plan (implementation
intentions). Training advice is listed but not checked: rebuilding it uses the day's own workouts. Counts, never
streaks or scores. What it does not do yet is reach you: the page has to be opened.

**Tomorrow will be better** sits at the bottom of Follow-up: what has gone with a better next day (HRV, resting
heart rate and self-rated energy the morning after doing something, against the mornings after not), with 95%
intervals and Benjamini–Hochberg, as before. It moved here from the Weekly review page on 2026-10-14: whether the
advice was kept and whether keeping it helped are one question asked twice, so they share a page.

## Weight & fitness

Weight against the plan's corridor, and cardio fitness: the VO2 max Apple Watch estimates on some outdoor walks, runs
and hikes. One estimate scatters by about 1 mL/kg/min and real change takes weeks, so the page shows a level (the
median of the last 30 days' estimates) against the level of about three months before, and calls a change under 1
"about the same". Apple's cardio fitness levels by age and sex are a population table and are not used. The words
say what it is, the body's engine built over weeks, and point to Recovery for how tired you are today, because the
two are easy to confuse.

## Exercise, Food and Goals

- **Exercise** opens on the week against the weekly goal (your `[plan.exercise]`, or the WHO guideline of 150
  active minutes and 2 strength days, named as such), as seven day cells whose bars split active minutes by kind of
  training and whose future days show the training planned. Then the last 7 days against your normal (totals for
  minutes and workouts, daily averages for steps and energy), load against recovery (7-day workout minutes over the
  4 weeks before; above 1.3 with recovery not better than usual = ease off), 12 weeks by kind with the goal dashed,
  and how HRV and resting heart rate answer each kind the next morning (medians, a description, not a test).
- **Food** counts a day once two main meals are logged; fewer is shown, not averaged, and a day not logged is
  unknown, never zero. Rows like the Wear and tear page's (value, normal band, plan tick, 8 weekly averages) for energy,
  protein, the hours from the last meal to sleep and fibre; the plan wins the colour, because the plan is the
  point of the page. The last meal is judged night by night (two or more late nights = off the plan), not by its
  average. Meals by time of day draw each day from waking to sleep with the hours before sleep striped. The energy
  balance sets the weekly change the log implies against the scale and says both ways what a gap usually means.
- **Goals** list every plan with 28 days of kept / not kept / no record and the count "n of the days with a
  record". Weekly goals show the last four weeks as bars against the target. Unset plans are listed with their
  `healthaio.toml` section. No streaks (they punish one missed day more than four kept ones reward), no total.

## Layout

- **Summary before detail.** Each page opens with one sentence-sized verdict or one number, then the parts that
  produced it. On Today that is the day ring plus "Recovered as usual / below your normal".
- **The day ring** is the one distinctive element: a 24-hour clock with midnight at the top. Outer track = the
  sleep that ended today, middle track = today's calendar, inner bars = screen minutes per hour (stacked from the
  centre: focus, entertainment & social, communication, other; full length = 60 minutes). An accent hand marks now.
  Today's workouts are drawn on the calendar track in the exercise colour, slightly wider than a calendar block.
  Planned training blocks are left off the ring, so it shows the workout you did, not the one you planned.
- **Two columns on desktop, one on phones.** HTML order is the phone priority order; the desktop grid only places
  it. Cards in a column stack so no card stretches over empty space.
- Every chart is drawn at its real pixel width (redrawn on resize), so text never scales with the chart. The charts
  live in the design kit (`healthaio/web/js/charts.js`); pages only map their data onto them.

## The Recovery page (`#recovery`)

The first page under Body signals, because recovery is the body signal the day's decisions hang on.

- **How recovered** is the Today page's verdict, the same numbers, so the two pages never disagree. Under it, this
  week's training load (a link to Body & mind load) and this morning's soreness, one line each.
- **The morning check-in** is two things in one save. How you feel is one tap of three: not recovered (2), so-so (5),
  recovered (8); three steps are as many as a sleepy person tells apart, and the numbers put them on the same 0–10
  scale as the score below. Where you are sore is the body figure from the author's GEOM90007 project Ready to Train
  (seven regions, a male and a female figure, `[healthaio] figure`): tapping a region cycles a little → clearly →
  very → not sore. Save sends `POST /api/checkin`, which sets that morning's `feel` in `self_report.csv` and replaces
  its rows in `soreness.csv` (same rule as goals: only this app's own page). An SVG mask does not change what a
  click hits, so the region under the pointer is read from the masks' own pixels. The figure is line art with a
  see-through background, made from Ready to Train's reference images and painted in `--plate-ink` on `--plate`, so
  it sits on a light plate in light mode and a dark one in dark mode; the soreness colours (`--c-sore-1..3`) are one
  yellow getting stronger, the same in both modes and on every body figure. A morning without a check-in is unknown.
- **What a workout trained.** Soreness the next morning means little without knowing what was trained, and the
  watch does not know (a strength session is just "strength training"). So after a strength session or a hard one
  (effort 7 or more on Apple's scale, where 7–8 is "hard"), every page shows a note in the corner for 36 hours after
  it ended: tap the parts it trained on the figure, or say it in a sentence. A sentence is quicker than taps right
  after training, and on a phone the keyboard's microphone takes dictation, so the page needs no speech service of
  its own (nothing leaves the computer). Words in the sentence light up the parts they name (Chinese and English,
  `checkin.REGION_WORDS`: 卧推 or bench → torso, 二头 or curls → both upper arms; longer words first, so 小腿 is not
  also 腿), always shown and always untickable, never a hidden guess. "Not this time" writes an empty row, so the
  note does not come back on the phone after it was dismissed on the computer. Saved into `workout_notes.csv`
  through `POST /api/trained`. The note appears only when a page is open: the iPhone app sends Health data while it
  is open, so "right after the workout" means the next time you look.
- **The next two mornings ask about those parts first**, a row per part with a button per level (not sore, a
  little, clearly, very), above the figure, which still takes the rest; buttons and figure are the same check-in.
  Delayed muscle soreness peaks a day or two after training, hence two mornings. The 14-day strips mark the days
  each part was trained, and each training day under the morning-after score says what it trained and how sore
  those parts were the next morning.
- **The morning after training** answers "did I come back from that session?" for the last training day, on day 2:
  four parts, each set against your own normal and put on 0–10 with 5 for a usual morning (2.5 points per spread
  of your normal, better direction up): how you said you felt; HRV the morning after against the morning before
  (scaled by how much your HRV usually moves from one morning to the next, so a jump is read against your own day to
  day noise); resting heart rate against your 28-day median; and the night after (sleep length against your normal,
  and how much of the time in bed you were asleep). They are added up and divided by how many there are, with at
  least two parts and one of them from the body. This is the only total score in the app, on purpose: the parts are
  already on one scale, each is "against your normal", and every part is shown beside the score with its own
  number, so nothing is hidden in the sum. Each part's bar has a tick at 5, so "against a usual morning" is seen,
  not read. The last 60 days of scores are a dot chart on the fixed 0–10 scale (one dot per training day, no line:
  the days between have no score), with the so-so band shaded; the session's details are in each dot's tooltip.
  Under it, only the training days still waiting for a note are listed, as links that open the note.
- **How the body answered training**: the next morning after hard days (load above the median of your fully rated
  training days) against every other known day, for HRV, resting heart rate and the worst sore region, with 95%
  intervals and Benjamini–Hochberg. An association; the card names the obvious confound. Each outcome is drawn as
  on Follow-up's Tomorrow will be better, a difference with its interval against zero (right = better), each row on its own scale, with
  the numbers in the tooltip: the picture answers "which way, and does it cross zero" before any number is read.
- A region clearly or very sore this morning, with training planned, gives "train, but spare the sore parts" on
  Today (after "take it easy" and "rest", which come first).

## The Body & mind load page (`#load`)

The page answers "how much is being asked of me, by the body and by the mind, and is a heavy stretch coming?". It
sits under Schedule, after the week itself: the schedule is the thing you look at, the load is what it adds up to,
and training is only half of it. It looks at the 8 weeks behind, this week and the 4 ahead, Monday to Sunday.

- **The body** is training load: each workout's effort on Apple's 1–10 scale times its minutes (session-RPE, Foster
  et al. 2001; the same idea as Apple Fitness's Training Load). The effort is your own rating in the Fitness or
  Workout app when there is one, else the watch's estimate (`workouts.csv` says which). Minutes without an effort
  are left out and counted, and with under half of the minutes rated the load says it is unsure instead of reading
  low. Weeks ahead hold the sessions planned in `[plan.training]`, each at the median load of your sessions in the
  last 28 days, drawn hatched as planned. People ask for "load on the nervous system"; no device measures that, so
  the page says so and points to the closest honest answer, the morning after on Recovery.
- **The mind** is hours of classes and work on the calendar (`events.csv`) and the share of grade due
  (`deadlines.csv`), with how many are due.
- **Against your usual weeks**: each measure against the middle half of the 8 full weeks before this one (from at
  least 4 weeks with the record). The three are never added into one number: effort × minutes and a share of grade
  are not the same kind of thing, and a sum would hide which side is heavy.
- **What it says**: this week (done plus still planned) as body and mind together ("stacked"), the mind's side, the
  body's side, or a usual week; the heaviest week ahead; and the weeks to plan lighter, both also marked under their
  week on the 13-week chart ("heaviest", "lighter"). A week ahead is not judged
  on training, since a plan is not a load (not every planned session happens); it is flagged instead when classes or
  deadlines are heavier than usual and the plan still holds your usual number of sessions or more.
- Below: the 13 weeks as three lanes (training done and planned, calendar hours, share of grade), 42 days of
  training load (the last 7 days against the weekly average of the 28 before, with the Exercise page's lines 1.3 and
  0.8), and the open deadlines with a link to Schedule.

## The Stimulation page (`#time`)

The page answers "how stimulating were my days, and what did my body do afterwards?". It replaced "Where your
time went" on 2026-10-14: where the hours went is already on Today's day ring, and the question people bring to
their screen data is not "A, B or C" but whether their days are getting more stimulating and whether it shows in
their body. It keeps the address `#time`, so old links (and `#attention`, `#ai`) still open it.

- **No hormone numbers.** Dopamine, cortisol and melatonin cannot be measured by a phone or a watch, so the page
  never shows a number for them; a card says so. It measures the two ends that can be measured: what goes in, and
  what the body does next.
- **What goes in: five signals from Screen Time,** each the daily average of the 7 days shown against your normal.
  Entertainment & social minutes (each minute once across devices) is the level the page leads with; the hour
  before sleep (entertainment & social in the hour before falling asleep that night), app switching (sessions per
  screen hour, as on Wear and tear), screens at once (device time over clock time) and the longest focus stretch (work and
  learning apps; longer is better) say how it was spread. *Normal* = the middle half of your 7-day averages ending
  on each of the 28 days before the first shown day (`time.typical_week`, at least 10 of them, each from at least
  4 days with the record); an average of 7 days moves much less than one day, so a band of single days would let
  a quiet or a heavy week read as usual. *A change* = at least one band width outside it (the width counts as at
  least 15 minutes for entertainment & social, 5 for the last hour and the focus stretch, 2 switches an hour and
  0.05 for the ratio, or a tenth of the usual value when larger); just past the edge reads "just above normal",
  uncoloured.
- **The top** is one sentence: more / less stimulation than your normal, or within it (from entertainment & social
  alone), the minutes against the band, your plan if you set one ("over it on 5 of 7 days"), and chips for the
  other signals clearly outside normal. Then the five tiles, each with a bullet against its band.
- **The long view** is the 90-day card (7-day averages of entertainment & social and of the longest focus stretch,
  the last 28 days next to the 28 before them): whether the baseline is drifting, which is what people mean by
  "dopamine tolerance", shown as behaviour.
- **How the body answered** compares, over the last 90 days, the night and next morning after days with
  entertainment & social above your own median against the rest, and after evenings with more than 15 minutes of
  it in the last hour against calm ones: when you fell asleep, how long you slept, the next morning's HRV (percent
  against your normal) and resting heart rate (beats against it). Difference of means with a 95% interval, at
  least 8 days on each side, Benjamini–Hochberg across all eight; only what survives is "a difference". The card
  says it is an association and gives the obvious other reading (a stressful day brings both).
- **In detail**, as tabs: entertainment & social by hour of the day (these days against your usual day), devices
  at once (each device counts its own minutes; an agent app on a computer while another device is in use, and one
  app on several devices at once, are taken out first), and where it came from (the entertainment and social apps
  and sites, per device).
- **A missing record is not zero.** Only days whose Screen Time is whole count (today is not over; when Screen
  Time has stopped arriving its last day counts as cut off), and a night whose last hour sits partly on a day
  without a whole record leaves the hour before sleep unknown. When Screen Time stops before the last day shown,
  the page says so.
- **Minutes are real minutes,** counted from the records minute by minute in the configured timezone (the same
  `Context.time_days` the day ring uses): on the day the clocks go forward the skipped hour is not counted.
- **Which days.** Whole days with a record of their own; the latest 7 are shown, and "Earlier" and "Later" step by
  7 such days, "Later" ending on the newest one, so a gap never strands the stepper.

## The Wear and tear page (`#drain`)

The page answers "what has been slowly wearing me down this week?" (慢性磨损: chronic wear, not the calories
"消耗" would suggest; it was called Drain, and its address stays `#drain`) with seven signals named the way physiology
and sleep research name them: resting heart rate (higher is worse), HRV (lower is worse), the time you fall
asleep (later is worse), sleep-timing spread (the standard deviation of each night's midpoint; larger is worse), screens in the
hour before sleep, entertainment & social, and app switches per screen hour. Each row has one line on why it
matters, and says when the evidence is softer (entertainment).

- **Three groups**, so seven rows read as three questions: what the body already shows (resting heart rate, HRV),
  sleep timing (falling asleep, spread) and screen habits (before sleep, entertainment & social, switching). The
  card at the bottom asks "short nights and hard training in the same week?" (it was "load over these 7 days",
  which read like the Body & mind load page).
- **Two judgements, never mixed.** Against your normal: the last 7 days' average against the middle half of the
  28 days before (sleep-timing spread against the range of the four 7-night blocks before, because a spread only
  exists over a run of nights). Against your plan, only where `healthaio.toml` sets one: falling asleep against
  `plan.sleep.bedtime`, entertainment & social against `plan.screen.entertainment_max_hours`. A habit that was
  already bad reads as "within normal" and still shows up against the plan.
- **No total score.** The signals have different units and different strength of evidence.
- **Missing is missing.** Each signal uses only days its own record covers in full; fewer than 4 of the 7 days and
  the row says so instead of guessing. A screen day counts only when it is whole: not today, and not the last day
  of a Screen Time import that has stopped arriving (the same rule the Stimulation page uses), since that day was most
  likely cut off part-way. Screens in the hour before sleep need a screen record for every day that hour touches.
  When no signal can be set against your normal, the page says so instead of "nothing got worse", and a plan that
  could not be checked is named as such, never counted as within plan.
- **App switches** count each session once, even when the same session was imported under two device names, so
  they agree with screen hours, which count each minute once across devices.
- **Row anatomy.** The design kit's `rangeStrip` and `trendLine`. Grey band = your normal, tick = its median, dot = these 7 days, dashed tick = the plan (the
  legend draws each key the way the row draws it); on the right the value, its normal, the state and the plan
  chips; the last column is eight weekly averages, for slow signals like HRV. All rows share one set of columns,
  so the strips line up down the card. At 900 px and narrower the strip and the weekly line get rows of their
  own and the weekly line carries its own label; on phones the value moves under the name.
- **Stepping.** Earlier / Later move 7 days at a time; Later from a window off the 7-day grid (opened from a past
  day on Today) ends on the latest window. Today's card links to the Wear and tear window it summarises.
- The week stack-up check (at least 3 nights under 7 hours and at least 3 training days) moved here from Today;
  Today keeps a two-line summary that links to this page.

## Menu

Today · Body signals (Recovery, Sleep, Wear and tear, Weight & fitness) · Daily life (Exercise, Food, Stimulation) ·
Plans & follow-up (Week, Body & mind load, Goals, Follow-up); under it, Data sources with the reading pages. The items are the loop of
managing your health, one question each: how am I today and what do I change; what is my body showing (outcomes you
cannot change directly); what do I do every day (the causes you can change); what have I planned (the week, how heavy
the weeks are for body and mind, my goals) and did it hold and help. Schedule and Actions & goals were two items
until 2026-10-14; they ask one question (a plan, and whether it held), so they are one. Where the numbers come from is not a step of
the loop, so Data sources sits under the menu. One item's pages are open at a time (arriving in an item, or opening
one, closes the other), so the sidebar stays about ten lines long. On a phone's tab bar each item takes a short
name: Today, Body, Life, Plans. Weekly review was folded into Follow-up on
2026-10-14: its week-of-facts table repeated the other pages, and its one useful part, what has helped the next
day, belongs next to whether the advice was kept ("Tomorrow will be better"). (Two earlier menus mixed axes: Today and Week (time) next to Time and Drain (topics) and
Review and Data (meta pages); then Body held exercise and food (things you do) next to weight (an outcome), while
Time & energy held drain (mostly body signals). Splitting outcomes from causes is what makes "what to change" a
question the menu itself asks.) The menu sits in a sidebar on the left from 900 px (the
browser already takes height at the top and bottom, so the menu takes width instead). The sidebar folds to a 64 px
column of icons with the button at its top; folded, the logo unfolds it, and the choice is remembered in this
browser. A menu item that holds more than one page opens and closes its list of pages with a click (a small arrow
at its end turns down while open) instead of jumping to a page; the item you are in opens by itself, the others
start closed. Folded or on a phone, the item opens its first page, its pages are a small switch above the page
title instead, and each page is titled by its own tab
(Weight, Sleep). On a phone the menu is a tab bar at the bottom, with the logo, language and light/dark in a row
above the page.

## Colour

- The colour rules are the design kit's ([DESIGN_KIT.md](DESIGN_KIT.md#colour-rules)); the values are in
  `healthaio/web/css/tokens.css` and on the gallery page (`#kit`).
- Two looks, no theme picker (`healthaio/web/css/tokens.css`): **light mode** uses graphite neutrals with a blue
  accent, **dark mode** uses dusk neutrals (blue-black) with a violet accent. The page follows the system setting;
  the moon button overrides it and remembers the choice (a shared `?mode=` link sets the starting look; a click
  wins over it and drops it from the address). The chosen part of a switch (Weight / Sleep, the outcome switch on
  Today) has its own raised step in each look (`--seg-on`), lighter than its track in dark mode.
- Data colours are the same in both modes (each mode has its own step of the same hue):

  | thing | token | light | dark |
  |---|---|---|---|
  | focus (work + learning) | `--c-focus` | `#2a78d6` | `#3987e5` |
  | entertainment & social | `--c-fun` | `#eb6834` | `#d95926` |
  | communication | `--c-comms` | `#1baf7a` | `#199e70` |
  | other | `--c-other` | `#a3a9b5` | `#5d6474` |
  | sleep (own ring track) | `--c-sleep` | `#4a3aa7` | `#9085e9` |
  | exercise (workouts) | `--c-exercise` | `#bf3fa6` | `#cb4db2` |
  | exercise as text | `--c-exercise-ink` | `#a8318f` | `#de78c8` |

  Focus / entertainment / communication pass the colour-vision checks in both modes for every pair
  (worst CVD ΔE 9.2). Sleep is too close to focus for protanopia, so it is never placed next to it: it has its
  own track on the ring, its own chart on the Sleep page.
  Exercise was checked against every colour above, sleep included, in both modes: worst CVD ΔE 8.7 in light and
  8.4 in dark (both against sleep), at least 9.3 against the screen colours, and at least 3:1 contrast on every
  mode's surface. So exercise may sit next to sleep: they are neighbouring tracks on the ring. Exercise minutes written as text use the darker (light mode) or lighter
  (dark mode) text step, at least 5.5:1 on every mode's surface. Calendar blocks are drawn in ink, not a
  data colour.
- Status colours (good / watch / off) are reserved for states and always come with a word or icon.
- Charts are otherwise ink and grey. The "normal" band is a faint fill; dashed lines mean a plan or a limit.

## Charts and what they encode

| chart | encodes |
|---|---|
| tile sparkline | 14 days, grey band = your normal on the last day, × = no record, end dot coloured only if out of normal |
| bullet | today's value against the band; tick = median |
| interval | difference after doing vs not doing, 95% interval, against zero |
| weight corridor | dots = weigh-ins, line = 7-day average, shaded corridor = the plan's two weekly rates, dashed = target |
| sleep windows | one bar per night from falling asleep to waking, on an 20:00–14:00 axis; ink tick with a surface halo, drawn over the bar = that morning's alarm |
| alarm ladder | the alarm as a step line (earlier = higher), dots = actual wake (green on time, red late) |
| lanes | one row per activity (sleep, exercise, calendar, screens; the daily-average tiles use the same order), one column per hour or per day; on the 30-day lanes each row has its own scale, written under its label (the hour lanes all run to 60 minutes); screens stack entertainment on the baseline so days compare against the dashed limit, whose label also sits under the row's name; × = no record that day, shaded = the 7 days above |
| activity icons | one stroke icon per lane (screen, exercise, calendar, sleep, a dashed clock for not recorded) and per thing "what changed" can name (entertainment & social = a feed with a play button, focused work = a laptop with a code bracket, communication = a speech bubble), drawn in its colour; a change carries an up / down badge in its tone, a usual day a check, a day with no normal yet a dashed clock |
| week load | `blockColumns`: one column per week, one block per deadline, height = share of grade, amber = due within 3 days (its label in `--on-watch`), faded = done |
| arrivals | one cell per day per stream: has data / partial / nothing |

## Words

- One word, one source. "Exercise / 运动" is logged workouts everywhere (the ring, Exercise); Apple's
  Exercise-ring minutes on Today are "Exercise ring / 锻炼圆环". Workout types and device names are
  translated; app names and anything you typed stay as written.

- The server returns numbers; the browser writes sentences from `i18n.js`. Add a language by adding a dictionary.
- Labels name what a person recognises ("Entertainment in the hour before sleep"), not how it is stored.
- Page names say what the page measures. The page about screens is **Stimulation** (刺激水平): it measures what
  goes in and what the body does next, and never calls either a hormone level.
- No scores out of 100, no streaks, no badges.
- A sentence that carries numbers is a chart waiting to be drawn. "2.1% lower (95% interval −7.4% to 3.2%)" is an
  interval against zero; ten rows of "date, session, score" are dots on a scale; "these weeks need a lighter plan"
  is a flag under those weeks. Words stay for what to do and why; the numbers move into the picture and its
  tooltip, and how-to text that the controls already show (a legend, a button's own label) is cut.

## Accessibility

- Every chart has `role="img"` and a label, and every mark with a tooltip is also reachable as text elsewhere on
  the page (the tile values, the sentence under each interval for screen readers).
- Activity icons are hidden from screen readers; the tile names and the sentence at the top of the Stimulation page
  say the same thing in words.
- Focus is visible; motion respects `prefers-reduced-motion`; nothing scrolls sideways at 320 px.
