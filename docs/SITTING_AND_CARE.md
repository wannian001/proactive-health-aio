# Sitting and tight spots · 久坐和哪里紧

## English

### Sitting

- **History** comes from Screen Time on the computers (`[devices] computers`, laptop and desktop by default). Sessions
  on a computer less than 5 minutes apart are one stretch. It is a proxy: a screen says you were at the computer, not
  that you sat (a standing desk counts too), and time in the chair away from the screen is not seen.
- **Right now** comes from the Mac app. Screen Time reaches the dashboard only every few hours, so the app reads how
  long the keyboard and mouse have been idle (never what is typed): 5 minutes idle is a break. It tells the server when
  a stretch starts, every 2 minutes while it goes on, and when a break begins (`healthaio sitting --since …`,
  `healthaio sitting --off --since …`); the server trusts that word for 3 minutes. Without the Mac app there is history
  but no reminder.
- **The reminder** (`api/nudge`) comes at 50 minutes and again every 30 while you stay; in the corner of every page
  (asked every two minutes) and as a notification from the Mac app (Settings can switch it off). It stays quiet while
  Rest & rewards is quiet (you asked for two quiet hours, you are resting, or you said you are absorbed). It hands one
  desk move, for where you said it was tight today if you did, else the day's turn, and a walk.
- **Pages**: a Sitting card on Exercise (`#exercise/sitting`: 14 days of the longest stretch against the reminder
  line, today's long ones, the moves with "I did it") and a Sitting line on Today (today's longest against your usual,
  the median of the daily longest over the 28 days before).
- **A break after a long stretch is a rest by itself**: when the Mac app says you got up after 50 minutes or more and
  came back 3 minutes to 2 hours later, the break is written to `restore.jsonl` as a finished rest ("Away from the
  computer"), once. Nothing to start or stop; "Not a rest, take it back" removes it.

### Where it feels tight

- Said on Recovery's "How you are right now" card, in a folded part apart from soreness after training: places
  (neck, chest, upper back, lower back, front of hip and thigh, back of thigh, calf, wrist and forearm), how each feels
  (tight, stiff, achy, painful), what it may be from (sitting, training, something else), and, once something is
  painful, warning signs (numbness or tingling, spreading into an arm or leg, getting worse, waking you at night,
  started with an injury). Saved with the rest of the card to `body_care.jsonl` (private, append-only).
- **Say it in a sentence** and press Read: fixed word lists in Chinese and English read it clause by clause (longest
  words first, each used once, so 酸痛 is achy and not also 痛). With the assistant switched on, a Claude model reads
  it instead and answers only with ids from the same lists (a JSON schema; ids are checked again); if it is off, not
  installed, fails or declines, the word lists answer and the page says why. Then "anywhere else?" suggests places that
  often go together; you decide.
- **The moves** come from `healthaio/routines.py`: twelve gentle moves of one to three minutes, each with how and how
  much, chosen for the places named (most specific first, at most three). Painful: the warning line first and only the
  one-minute moves. A warning sign: no moves, only the advice to see a doctor or physiotherapist.
- **Maybe from sitting**: when the places are ones long sitting tends to tighten and a stretch of 50 minutes or more
  came that day or the day before, the card says so, as two things that came together, not as a cause.
- **The next day** Today and Recovery ask, per place, how it is now (better, same, worse), until answered.

### The assistant

Off unless `healthaio.toml` has `[assistant] enabled = true` and the `anthropic` package is installed. It sends the
sentence you typed and the fixed lists, nothing else (no measurements, dates or name), to Anthropic's API with the
model `claude-opus-5-5` at effort `low` (both settable) and the server-side refusal fallback. The key is whatever the
Anthropic SDK finds itself (`ANTHROPIC_API_KEY` or an `ant auth login` profile); the app never reads or stores it. It
never writes advice: the moves and the warning line are fixed.

### Why no posture page

No phone, watch or computer measures posture. There is no single correct posture, and changing position matters more
than holding a "good" one (Slater et al., JOSPT 2019, "Sit up straight: time to re-evaluate"). Breaking up sitting
every 30 to 60 minutes with a few minutes of light movement helps (Dunstan et al., Diabetes Care 2012), and regular
neck and shoulder exercise reduces neck pain a little in office workers (Chen et al., Physical Therapy 2018). So the
app reminds you to move and hands short moves for where it feels tight, instead of grading a posture it cannot see.

Not medical advice: the moves are general, gentle ones, not a treatment plan.

## 中文

### 久坐

- **历史**来自电脑上的屏幕使用时间（`[devices] computers`，默认笔记本和台式机）。电脑上的使用中间间隔不到 5 分钟，就算同一段。
  这只是近似：屏幕只说明你在电脑前，不说明你坐着（站立办公也算进去），坐在椅子上但没看屏幕的时间看不到。
- **此刻**来自 Mac 应用。屏幕使用时间要过几个小时才进面板，所以应用看键盘和鼠标闲了多久（从不读你打了什么）：闲 5 分钟算起身。
  一段开始、继续中每 2 分钟、开始休息时，它都告诉服务端（`healthaio sitting --since …`、`healthaio sitting --off --since …`），
  服务端认这个说法 3 分钟。没有 Mac 应用就只有历史，没有提醒。
- **提醒**（`api/nudge`）在连续 50 分钟时出现，还在继续就每 30 分钟再来一次；出现在每一页的角落（每两分钟问一次）和 Mac 应用的
  系统通知里（设置里可以关）。“休息与奖励”少打扰的时候（你要了两小时少打扰、正在休息、或者说自己正投入）不提醒。提醒附一个坐着
  就能做的动作（今天说过哪里紧就针对那里，没说就按天轮换）和起来走走。
- **页面**：运动页的久坐卡片（`#exercise/sitting`：最近 14 天每天最长连续多久、对着提醒线；今天过长的几段；小动作和“做完了”），
  今天页的久坐一行（今天最长连续多久，和你的平常比：之前 28 天里每天最长一段的中位数）。
- **坐久了起身会自动记成休息**：Mac 应用说你连续坐了 50 分钟以上后起身、3 分钟到 2 小时后回来，这次离开就作为一次做完的休息
  写进 `restore.jsonl`（“离开电脑一会儿”），只记一次。不用点开始结束；不算休息就点“删掉”。

### 哪里紧或不舒服

- 在恢复页「此刻怎么样」卡片里一块折叠的地方说，和训练后的酸痛分开：部位（颈部、胸前、上背、下背、髋前和大腿前侧、大腿后侧、
  小腿后侧、手腕和前臂），每个部位的感觉（紧、僵、酸、疼），可能和什么有关（久坐、训练、别的），有部位选了“疼”时再问警示情况
  （麻木或刺痛、往手臂或腿放射、越来越重、夜里痛醒、受伤之后开始）。和卡片其他内容一起保存到 `body_care.jsonl`（私有，只追加）。
- **说一句**再点“识别”：固定的中英文词表逐句读（先匹配长词、每个词只用一次，所以“酸痛”算酸，不会又算成疼）。打开助手的话，
  改由 Claude 模型来读，只能回答同一份清单里的编号（用 JSON 格式约束，回来后再核对一遍）；没开、没装、出错或拒答时，用词表读，
  页面写明原因。之后“还有哪里不舒服？”会提示常常一起出现的部位，由你决定。
- **动作**来自 `healthaio/routines.py`：12 个温和的小动作，每个 1–3 分钟，写清做法和做多少，按你说的部位挑（越对口的越靠前，
  最多三个）。有“疼”：停止提示放在最前面，只给一分钟的动作。有警示情况：不给动作，只建议去看医生或物理治疗师。
- **可能和久坐有关**：说的部位是久坐常让人发紧的那些，并且当天或前一天有连续 50 分钟以上的一段，卡片会写出来，只说两件事一起
  出现，不说是它引起的。
- **第二天**今天页和恢复页会按部位问现在怎么样（好一点、差不多、更重），答了就不再问。

### 助手

默认关着；`healthaio.toml` 里写 `[assistant] enabled = true` 并装了 `anthropic` 包才会用。它把你打的那句话和固定清单发给
Anthropic 的 API，别的都不发（没有测量数据、日期和名字），模型是 `claude-opus-5-5`、思考力度 `low`（都可以改），并开着服务端的
拒答兜底。API key 由 Anthropic SDK 自己找（`ANTHROPIC_API_KEY` 或 `ant auth login` 的登录信息），应用不读也不存。它从不写建议：
动作和停止提示都是固定的。

### 为什么没有体态页

手机、手表、电脑都测不了体态。不存在唯一正确的姿势，常换姿势比保持某个“好姿势”更重要（Slater 等，JOSPT 2019，《“坐直”：
是时候重新评估了》）；每 30–60 分钟起来轻轻动几分钟有好处（Dunstan 等，Diabetes Care 2012）；办公室人群规律做颈肩练习，
颈痛会轻一点（Chen 等，Physical Therapy 2018）。所以应用提醒你起来动、针对哪里紧给小动作，而不是给一个它看不见的姿势打分。

不是医疗建议：这些是一般性的温和动作，不是治疗方案。
