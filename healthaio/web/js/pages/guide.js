// Guide: how to use Proactive Health AIO, from the demo to your own data to a normal day with it. It is drawn as the
// last section of the Overview (#project); #guide still renders it alone, for old links and the tests.
// Numbered steps in the order you meet them, in one card, each opening on a click; commands are the ones in the README's Quick start
// and companion-app sections. The server only
// names the page (modules/docs.py).
import { esc } from "../charts.js";
import { getLang, t } from "../i18n.js";

const CODE = {
  install: ["git clone https://github.com/wannian001/proactive-health-aio.git", "cd proactive-health-aio", "python3 -m healthaio serve --demo"],
  import: ["cp examples/healthaio.example.toml healthaio.toml", "python3 -m healthaio import apple-health ~/Downloads/export.zip"],
  more: ["python3 -m healthaio import ics ~/Downloads/timetable.ics --kind class", "python3 -m healthaio import macos-screentime",
    "python3 -m healthaio check"],
  serve: ["python3 -m healthaio serve"],
  apps: ["mac/build.sh", "open \"mac/build/Health AIO.app\"", "python3 -m healthaio pair"],
};

const GUIDE = {
  zh: {
    title: "使用说明", sub: "从看演示，到用上你自己的数据，再到每天怎么看",
    note: "在线演示里的人叫 Sam，是虚构的研究生，数字都是编的。想看你自己的，按下面第 2 到 4 步装到你自己的电脑上；数据只留在那台电脑里。",
    steps: [
      { h: "先看看演示", body: [
        "左边的菜单（手机上在底部）按管理健康的顺序排：<b>今天 → 身体状态 → 生活习惯 → 计划与跟进</b>。点有子页的一项，子页才展开，一次只展开一项。数据来源和说明在菜单下面。",
        "<b>身体状态</b>是结果，你没法直接改（恢复、睡眠、慢性磨损、体重和心肺）；<b>生活习惯</b>是你每天做的事，能直接改（运动、饮食、刺激水平）；<b>计划与跟进</b>是你计划了什么、做到没有（一周日程、身心负荷、目标、跟进）。",
        "从“今天”开始：恢复得怎样、今天该调整什么、今天有什么安排、今晚几点该睡着。",
        "菜单旁边的两个按钮可以切换中英文和深浅色。"] },
      { h: "装到你的电脑上", body: ["需要 Python 3.9 以上，不用装别的包。先用演示数据确认能跑，然后打开 <b>http://localhost:8790</b>："], code: "install" },
      { h: "先带进历史数据", body: [
        "在 iPhone 的“健康” App 里点右上角的头像，选“导出所有健康数据”，把得到的 <b>export.zip</b> 传到电脑上。",
        "一个导出包就能带进来大部分：睡眠、HRV、静息心率、步数、体重、每次训练，以及记饮食的 App 写进健康里的每一餐。历史长的话包会很大（几年的手表数据可以有几个 GB），导一次就行；之后交给第 5 步的 iPhone App。"], code: "import",
        after: "下面这些是可选的：课表或日历（.ics）、Mac 的屏幕使用时间（试验性）；最后一行检查哪些行读不出：", code2: "more" },
      { h: "打开，设你的目标", body: [
        "在 <b>healthaio.toml</b> 里改一下时区，然后运行下面这行。",
        "目标在“目标”页直接设、随时改：几点睡着、每周练几次、饮食和屏幕的上限。每一项都可以不设，没设的页面照样显示事实，只是没有目标可比。"], code: "serve" },
      { h: "让它自己跑：Mac App 和 iPhone App", body: [
        "<b>Mac App</b> 在菜单栏里（构建一次约 20 秒）：给它“完全磁盘访问权限”后，每 2 小时自己采一次屏幕使用时间，看板一直开着；GitHub 上有新版本时会弹窗问你要不要更新。",
        "<b>iPhone App</b> 用 Xcode（本体约 3.7 GB）装到手机上（见 ios/README.md），在 Mac App 里点“配对 iPhone”扫二维码。之后每次打开，它把最近 3 天的 Apple 健康发到电脑，看板就在它的一个标签页里。它不在后台跑：不打开，就不发。",
        "免费 Apple ID 签的 App 管 7 天：手机每天第一次打开时会检查，快到期就提醒你，点“现在续签”由电脑重新签好装上。"], code: "apps" },
      { h: "每天怎么用", body: [
        "<b>早上</b>打开“今天”：先看恢复（和你自己最近 28 天比），再看“今天该调整的”：训练、睡眠、饮食、白天的屏幕各最多一件，一共最多三件，每件都写明依据的数字。",
        "<b>第二天</b>看“计划与跟进 › 跟进”：昨天的建议按数据核对做到没有，不用你打勾。同一条老做不到，那里会换几种做法给你：改小一步、让手机替你记、写一句“如果……就……”。",
        "<b>练完力量训练或强度高的训练</b>（强度分 7 以上），打开任何一页，角落会弹出“刚练完”的提示：点“记一下”，在人体图上点练了哪儿，或者说一句练了什么（手机上按键盘的麦克风口述），写到的部位会自动点亮。不想记就点“这次不记”。",
        "<b>每天早上</b>打开“身体状态 › 恢复”打个卡：感觉怎么样点一下（没缓过来、一般、恢复得好）；前两天练过、记了部位的，那几个部位直接用按钮选酸不酸；其他部位在人体图上点；然后保存。练完的第二天早上，同一页会算出“练后第二天”的分：你的感觉、HRV、静息心率、练后那一晚的睡眠，各自和平常比再取平均，每一项都摊开写。训练完在手表或健身 App 里给这次训练打个强度分（1–10），训练负荷才算得出来。",
        "<b>排下几周的计划前</b>看“计划与跟进 › 身心负荷”：过去 8 周和接下来 4 周，训练、课和工作、截止各自和你平常的周比；课多、截止多的那周训练还照常排，它会提醒你提前减量。",
        "想细看某一项，去“身体状态”（恢复、睡眠、慢性磨损、体重和心肺）或“生活习惯”（运动、饮食、刺激水平）。“刺激水平”看你给大脑的刺激（娱乐和社交、睡前刷手机、切换应用、几台同时用）和身体接下来的反应；激素本身手机和手表测不了。",
        "<b>过一阵子</b>看“跟进”最下面的“明天会更好”：做了和没做的日子，第二天早上有什么不同。建议有没有用，看这里。",
        "某项很久没更新，去“数据来源”页看是哪一路断了。装了 iPhone App，打开它就会把新数据发过来；没装的话，再导出一次 Apple 健康、重新导入。"] },
      { h: "怎么读这些数", body: [
        "<b>和你自己比，</b>不和人群比：“平常”是你自己前 28 天的中间一半。",
        "<b>缺的就是缺：</b>没记的一天不算成 0，记得少，回答就少，不会编。",
        "<b>关联不是因果：</b>“做什么第二天会更好”只说哪些事常和更好的第二天一起出现。",
        "<b>不是医疗建议：</b>建议都是日常习惯（早点睡、早点吃、练轻一点）；健康问题请找专业人士。"] },
      { h: "你的数据", body: [
        "数据是你电脑上一个文件夹里的普通 CSV 文件，导入工具写它们。",
        "服务默认只在本机（127.0.0.1）运行。让手机连进来时，只认你配对过的设备，手机能发的只有 Apple 健康的样本。",
        "页面会写的只有三样：你在目标页设的目标（每次一行，记在 healthaio.toml 旁边的 goals.jsonl 里）；你在恢复页保存的早上打卡（只改那天早上 self_report.csv 里的 feel，并替换那天早上 soreness.csv 里的几行）；练完记下的练了哪儿（只替换那次训练在 workout_notes.csv 里的一行）。",
        "唯一联网的是每天问一次 GitHub 有没有新版本，只带版本号；在 healthaio.toml 里写 [updates] check = false 就关掉。"] },
    ],
    history: "这个项目是怎么来的？看迭代记录（在作者的网站上）",
  },
  en: {
    title: "Guide", sub: "From the demo, to your own data, to a normal day with it",
    note: "The person in the online demo, Sam, is a made-up graduate student, and every number is invented. To see your own, install it on your computer with steps 2 to 4 below; your data stays on that computer.",
    steps: [
      { h: "Look around the demo", body: [
        "The menu on the left (at the bottom on a phone) follows the loop of managing your health: <b>Today → Body signals → Daily life → Plans & follow-up</b>. An item with pages opens them with a click, one at a time. Data sources and the reading pages sit under the menu.",
        "<b>Body signals</b> are outcomes you cannot change directly (recovery, sleep, wear and tear, weight & fitness); <b>Daily life</b> is what you do every day and can change (exercise, food, stimulation); <b>Plans & follow-up</b> is what you have planned and whether it held (the week, body & mind load, goals, follow-up).",
        "Start with Today: how you recovered, what to adjust today, what is on, and when to be asleep tonight.",
        "The two buttons by the menu switch the language and light / dark."] },
      { h: "Install it on your computer", body: ["Needs Python 3.9 or newer, no other packages. Check it runs with the demo data first, then open <b>http://localhost:8790</b>:"], code: "install" },
      { h: "Bring in your history", body: [
        "On your iPhone, open the Health app, tap your picture at the top right and choose Export All Health Data; copy the <b>export.zip</b> to your computer.",
        "One export brings in most of it: sleep, HRV, resting heart rate, steps, weight, every workout, and the meals that food-logging apps write into Health. With a long history the file is large (years of watch data can run to several GB); you do this once, and the iPhone app in step 5 takes over."], code: "import",
        after: "These are optional: a timetable or calendar (.ics), Screen Time on a Mac (experimental); the last line checks which rows could not be read:", code2: "more" },
      { h: "Open it, set your goals", body: [
        "Set your timezone in <b>healthaio.toml</b>, then run the line below.",
        "Set goals right on the Goals page and change them any time: when to be asleep, how often to train, limits for food and screens. Each is optional; a page without its goal still shows the facts, just without a goal to compare with."], code: "serve" },
      { h: "Let it run by itself: the Mac app and the iPhone app", body: [
        "The <b>Mac app</b> lives in the menu bar (about 20 seconds to build). Once you give it Full Disk Access it collects Screen Time every 2 hours and keeps the dashboard running; when GitHub has a newer version it asks whether to update.",
        "Install the <b>iPhone app</b> with Xcode (3.7 GB on its own; see ios/README.md) and scan the QR code from Pair iPhone in the Mac app. From then on, each time you open it, it sends the last 3 days of Apple Health to your computer, and the dashboard is one of its tabs. It sends only while it is open: not opened, nothing sent.",
        "An app signed with a free Apple ID lasts 7 days: the first time it opens each day the phone checks, reminds you when the end is near, and Renew now has your computer sign and install it again."], code: "apps" },
      { h: "A normal day with it", body: [
        "<b>In the morning</b>, open Today: first recovery (against your own last 28 days), then what to adjust today: at most one thing each for training, sleep, food and daytime screens, three at most, each with the numbers behind it.",
        "<b>The next day</b>, open Plans & follow-up › Follow-up: yesterday's advice, checked against the data, with nothing to tick. When the same advice keeps not happening, it offers other ways: a smaller step, a phone setting that remembers for you, an if-then plan.",
        "<b>After a strength session or a hard one</b> (effort 7 or more), any page shows a note in the corner: Note it, then tap the parts it trained on the body figure or say what you did in a sentence (on a phone, the keyboard's microphone takes dictation); parts the sentence names light up by themselves. Not this time, if you would rather not.",
        "<b>Each morning</b>, check in on Body signals › Recovery: one tap for how you feel (not recovered, so-so, recovered); the parts a workout of the last two days trained come with a button per level; tap anywhere else on the body figure; then save. The morning after training, the same page works out the score for the morning after: how you felt, HRV, resting heart rate and the night's sleep, each against your normal, averaged, with every part shown. Rate each workout's effort (1–10) on the watch or in the Fitness app afterwards, so the training load can be worked out.",
        "<b>Before you plan the next weeks</b>, open Plans & follow-up › Body & mind load: the 8 weeks behind and the 4 ahead, training, classes and work, and deadlines, each against your usual weeks; when a week with more classes or deadlines than usual still has your usual training planned, it tells you to plan lighter.",
        "For a closer look, go to Body signals (recovery, sleep, wear and tear, weight & fitness) or Daily life (exercise, food, stimulation). Stimulation is what your days feed your brain (entertainment & social, scrolling before sleep, app switching, screens at once) and what your body does next; hormones themselves can't be measured by a phone or a watch.",
        "<b>Every so often</b>, look at Tomorrow will be better at the bottom of Follow-up: the next morning after days you did something against days you did not. Whether the advice helps is there.",
        "If something has not updated for a while, Data sources shows which stream stopped. With the iPhone app, opening it sends the new data; without it, export from Apple Health again and import it."] },
      { h: "How to read the numbers", body: [
        "<b>You against you,</b> never a population: “normal” is the middle half of your own previous 28 days.",
        "<b>Missing stays missing:</b> a day you did not log is not a zero; a sparse log gives fewer answers, not made-up ones.",
        "<b>Associations, not causes:</b> “What has tended to help the next day” only says what has gone with a better next day.",
        "<b>Not medical advice:</b> the suggestions are everyday habits (sleep earlier, eat earlier, train lighter); for anything about your health, talk to a professional."] },
      { h: "Your data", body: [
        "Your data is plain CSV files in a folder on your computer. The importers write them.",
        "The server listens only on this computer (127.0.0.1) unless you let your phone in, and then only devices you paired; all a phone can send is Apple Health samples.",
        "A page writes three things only: a goal you set on the Goals page (one line each, in goals.jsonl next to healthaio.toml); the morning check-in you save on the Recovery page (it sets that morning's feel in self_report.csv and replaces that morning's rows in soreness.csv); and what a workout trained (it replaces that workout's row in workout_notes.csv).",
        "The one request to the internet is asking GitHub once a day whether there is a newer version, with nothing but the version number; [updates] check = false in healthaio.toml turns it off."] },
    ],
    history: "Where did this project come from? Read its history (on the author's site)",
  },
};

const code = (key) => `<pre class="doc-code"><code>${CODE[key].map(esc).join("\n")}</code></pre>`;

// the steps in one card: every step's title in view, its text one click away; the first step opens with `first`
export function guideSteps(first = true) {
  const c = GUIDE[getLang()] || GUIDE.en;
  const steps = c.steps.map((s, i) => `<li><details${first && i === 0 ? " open" : ""}><summary><span class="doc-n">${i + 1}</span>${s.h}</summary>
      ${s.body.map((p) => `<p>${p}</p>`).join("")}${s.code ? code(s.code) : ""}${s.after ? `<p>${s.after}</p>${code(s.code2)}` : ""}</details></li>`).join("");
  return `<section class="card" id="guide"><h2>${c.title}</h2><ol class="doc-folds doc-guide-steps">${steps}</ol></section>`;
}

export default {
  render() {
    const c = GUIDE[getLang()] || GUIDE.en;
    return `<div class="head"><div><h1>${c.title}</h1><div class="sub">${c.sub}</div></div></div>
      <div class="doc">
        <div class="doc-note"><p>${c.note}</p><button type="button" class="doc-link" id="doc-lang">${t("doc.other_lang")}</button></div>
        ${guideSteps()}
        <p class="doc-try"><a href="${esc(t("doc.history_url"))}" target="_blank" rel="noopener">${c.history} ↗</a></p>
      </div>`;
  },
  mount(el) {
    const lang = el.querySelector("#doc-lang");
    if (lang) lang.onclick = () => document.querySelector("#lang")?.click();
  },
};
