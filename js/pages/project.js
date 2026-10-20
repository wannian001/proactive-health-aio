// Overview (#project): what Proactive Health AIO is, who it is for, the problem it answers and how, where the data
// comes from (which device collects what, how often, and what it costs your computer, measured), how far "proactive"
// goes today, then the comparison with what people use now, the trade-offs, where it stands, what comes next and who
// made it (each opening on a click), and at the end how to use it (guide.js, once a page of its own).
// The same facts as the README's "Why it exists", shorter. The server only names the page (modules/docs.py).
// History is not in this repository: it quotes the personal system it comes from, so it lives on the author's site.
import { esc } from "../charts.js?v=65d4646a27";
import { getLang, t } from "../i18n.js?v=65d4646a27";
import { guideSteps } from "./guide.js?v=65d4646a27";

const REPO = "https://github.com/wannian001/proactive-health-aio";

const PROJECT = {
  zh: {
    title: "项目说明", sub: "它是什么、为谁做、和现有的有什么不同",
    note: "在线演示里的人叫 Sam，是虚构的研究生，数字都是编的。代码开源（MIT），装到自己电脑上就能看自己的数据。",
    lede: "把睡眠、运动、饮食、体重、屏幕和日程放进同一天，每一项都和你自己最近 28 天比；每天早上说出今天该调整的最多三件事，每件都写明依据；第二天按数据核对做到没有，老做不到就换个做法。",
    facts: ["跑在你自己的电脑上", "和你自己比，不和人群比", "每条规则都写明", "中文 / English"],
    cards: [
      { h: "为谁做", items: ["戴手表、用好几个健康 App，数据多却散的人", "作息常被 deadline 和屏幕打乱的学生和知识工作者", "想自己定目标、看得到每条规则的人"] },
      { h: "要解决的问题", items: ["数据分在手表、饮食记录、屏幕使用时间、日历几个 App 里", "各打各的分：和人群比，或者给一个看不到公式的分数", "往往是不舒服了才去翻"] },
      { h: "它怎么做", items: ["Mac 和 iPhone 上的两个小 App 自动收数据，不用买新设备", "每一项和你自己的平常比", "每天最多三件该调整的，第二天核对做到没有"] },
    ],
    loopTitle: "每天怎么转",
    loop: [["量", "Mac 和 iPhone 自动收，也能手动导入", "data", "数据来源"], ["比", "和你的平常、你的目标比", "today", "今天"],
      ["调", "今天该调整的，最多三件", "today", "今天"], ["跟", "第二天核对做到没有，老做不到就换做法", "followup", "跟进"], ["验", "做了什么，第二天真的更好", "followup", "跟进 · 明天会更好"]],
    dataTitle: "数据从哪来",
    data: { head: ["从哪", "收什么", "多久一次", "你要做的"], rows: [
      ["iPhone App", "Apple 健康里的睡眠、HRV、静息心率、最大摄氧量、步数、活动和训练（带强度评分）、体重，以及记饮食的 App 写进健康的每一餐。Apple Watch 不直接连：手表先写进 Apple 健康，再由它带过来。", "每次打开 App，把最近 3 天发到你的电脑；不在后台跑", "用 Xcode 装一次，扫码配对。免费 Apple ID 签的 App 每 7 天要续签：手机提前提醒，点一下由电脑重签"],
      ["Mac App（菜单栏）", "屏幕使用时间：这台 Mac，以及打开了“跨设备共享”的 iPhone、iPad", "每 2 小时一次。macOS 只留大约 4 周，所以要一直开着", "给它“完全磁盘访问权限”，可以设成登录时打开"],
      ["手动记录", "恢复页上的早上打卡（感觉和酸痛）、练完弹出的“练了哪儿”；Apple 健康导出包（export.zip）、课表或日历（.ics）、任意 CSV", "你想记、想导的时候", "点几下保存；导入是一条命令，适合第一次带进几年的历史"]] },
    costTitle: "它在你电脑上的开销（在一台 M4 MacBook 上实测）",
    cost: [
      "<b>没有服务器要扛：</b>每个人的电脑就是自己的服务器，作者这边不收任何数据。唯一联网的是每天问一次 GitHub 有没有新版本。",
      "<b>手机发一次：</b>3 天约 1,600 条记录、约 350 KB（条数按作者真实的一天约 540 条算），电脑写进表里用 0.03 秒。",
      "<b>采一次屏幕时间：</b>4 周、3 台设备约 6,900 段，0.4 秒，内存峰值约 50 MB。",
      "<b>看板常开：</b>占约 105 MB 内存，空闲时 CPU 为 0；每一页 0.004–0.36 秒算完（14 个月的演示数据）。",
      "<b>占地方：</b>代码 25 MB；数据是普通 CSV，大头是屏幕记录，一天约 14 KB，一年约 5 MB。",
      "<b>装一次要花的：</b>下载代码约 6 秒，构建 Mac App 约 20 秒；装 iPhone App 要 Xcode（本体 3.7 GB）。钱：0（免费 Apple ID），或者每年 99 美元的开发者账号，换来一年才续签一次。"],
    ladderTitle: "“主动”到哪一步",
    ladder: { head: ["一步", "做什么", "这里有没有"], rows: [
      ["看见", "身体和生活的数据放进同一天", "yes", "today", "今天"],
      ["对比", "和你自己的平常、你的目标比", "yes", "sleep", "身体状态"],
      ["建议", "每天早上说出今天做什么，最多三件，写明依据", "yes", "today", "今天"],
      ["跟进", "第二天按数据核对做到没有，不用打勾", "new", "followup", "跟进"],
      ["换做法", "老做不到就换：改小一步、让手机替你记、写一句“如果……就……”", "new", "followup", "跟进"],
      ["追问", "练完问练了哪儿；之后两天早上先问这些部位酸不酸", "new", "recovery", "恢复"],
      ["找上门", "不打开页面也能收到提醒", "no", null, "现在要打开页面才看得到"],
      ["验证", "改了以后，第二天有没有更好", "part", "followup", "跟进页的“明天会更好”只说相关，不说因果"]] },
    status: { yes: "有", new: "这一版加的", no: "还没有", part: "一部分" },
    folds: [
      { h: "和现在常用的比", table: { head: ["现在用的", "管什么", "这里多做的"], rows: [
        ["手表 App（Oura、WHOOP、Garmin Connect）", "自己设备的恢复分", "把恢复和饮食、屏幕、日程放在同一天"],
        ["饮食记录（MyFitnessPal、Cronometer）", "吃了什么", "吃得晚不晚，和第二天的恢复对照"],
        ["屏幕使用时间", "用了多久", "和睡眠、专注、第二天放在一起"],
        ["Apple 健康", "几乎什么都存", "说出今天该改什么、为什么"],
        ["跨 App 找关联（Exist.io、Bearable）", "找相关", "只在本机，规则写明，落到今天的事"]] },
        after: "现在的代价：好几个 App，常常好几份订阅，历史散在几处云上，分数的公式看不到，最后还得自己把它们拼起来。" },
      { h: "有意的取舍", items: [
        "<b>不上云、不在后台同步：</b>iPhone App 打开时才把数据发到你自己的电脑；没装就导入 Apple 健康的导出包。换来的是数据只在你的电脑上。",
        "<b>规则，不是模型：</b>建议来自几条写明的固定规则，能解释、能检查，但不会自己“学”。可选的助手只负责读懂你说的“哪里紧”那句话，默认关着。",
        "<b>和自己比：</b>刚开始的 28 天还没有“平常”，回答会少。",
        "<b>不是医疗建议：</b>只看行为和身体信号，不诊断，不算连胜。",
        "<b>只有一个总分：</b>练后第二天的恢复分。四项先各自和你的平常比、换成同一把 0–10 的尺子再取平均，每一项都摊开写；别处单位不同的东西从不加成一个数，比如身体和精神的负担各看各的。"] },
      { h: "现在到哪一步", items: [
        "<b>电脑这边</b>（看板、导入、跟进）：在作者的 Mac 上用真实的屏幕使用时间跑过采集；每条规则都有测试。",
        "<b>iPhone App：</b>在模拟器上测过配对、读健康、发包的全流程，还没在真手机上读过真数据。",
        "<b>还没有作者以外的人装过。</b>装一次要 Mac、Xcode 和一点命令行，这是现在最大的门槛。"] },
      { h: "接下来", items: [
        "<b>早上找上门：</b>把“今天该调整的”推成手机通知，不用打开页面。",
        "<b>找人试：</b>2–3 个戴 Apple Watch 的朋友各用 14 天，记装机用了多久、打开了几天、建议做到了几成。",
        "<b>TestFlight：</b>不会用 Xcode 的人也能装，一年续签一次。",
        "<b>接 AI 助手：</b>助手读每一页的数据，提出调整目标的建议；你在目标页点了采纳才生效。接口已经留好：<code>healthaio goal propose</code>。"] },
      { h: "谁做的、怎么做的", items: [
        "分工：需求、取舍和验收是我；代码由 AI 编程工具（Claude Code、Codex）写。",
        "它来自我自己用了一年的个人系统，四代迭代见“迭代记录”（在我的网站上）。",
        "Python 标准库，不用装别的包；颜色、组件和图表是一套带版本号的设计套件；每条规则都有测试。"] },
    ],
    links: [[REPO, "GitHub 仓库"], ["#project/guide", "使用说明"], ["history", "迭代记录"], ["#kit", "设计套件"]],
  },
  en: {
    title: "Overview", sub: "What it is, who it is for, and how it differs from what people use now",
    note: "The person in the online demo, Sam, is a made-up graduate student, and every number is invented. The code is open source (MIT): install it on your computer to see your own data.",
    lede: "Sleep, exercise, food, weight, screens and your calendar on one day, each compared with your own last 28 days; every morning, at most three things to adjust today, each with the numbers behind it; the next day, a check against the data on whether they happened, and another way for the ones that keep not happening.",
    facts: ["Runs on your own computer", "You against you, not a population", "Every rule written down", "English / 中文"],
    cards: [
      { h: "Who it is for", items: ["People with a watch and several health apps: plenty of data, all in pieces", "Students and knowledge workers whose sleep gets pushed around by deadlines and screens", "People who want to set their own goals and see every rule"] },
      { h: "The problem", items: ["The data sits in separate apps: the watch, a food log, Screen Time, the calendar", "Each scores on its own: against a population, or with a formula you cannot see", "Most people only look after they already feel bad"] },
      { h: "What it does", items: ["Two small apps on your Mac and iPhone collect the data; no new device", "Compares every signal with your own normal", "At most three things to adjust each day, checked the next day"] },
    ],
    loopTitle: "The daily loop",
    loop: [["Measure", "The Mac and iPhone apps collect; you can also import", "data", "Data sources"], ["Compare", "Against your normal and your goals", "today", "Today"],
      ["Adjust", "At most three things today", "today", "Today"], ["Follow up", "Checked the next day; another way when it keeps failing", "followup", "Follow-up"], ["Check", "What has made the next day better", "followup", "Follow-up · Tomorrow will be better"]],
    dataTitle: "Where the data comes from",
    data: { head: ["From", "What", "How often", "What you do"], rows: [
      ["iPhone app", "From Apple Health: sleep, HRV, resting heart rate, VO2 max, steps, activity and workouts (with their effort score), weight, and the meals a food-logging app writes into Health. The Apple Watch is not connected directly: it writes into Apple Health, and the app brings it over.", "Each time you open the app, the last 3 days go to your computer; nothing is sent while it is closed", "Install it once with Xcode and scan a QR code to pair. An app signed with a free Apple ID needs renewing every 7 days: the phone reminds you, and one tap has your computer re-sign it"],
      ["Mac app (menu bar)", "Screen Time: this Mac, plus the iPhone and iPad when “Share across devices” is on", "Every 2 hours. macOS keeps only about four weeks, so it stays running", "Give it Full Disk Access; it can open at login"],
      ["By hand", "The morning check-in on the Recovery page (how you feel, where you are sore) and the note after a workout (what it trained); an Apple Health export (export.zip), a timetable or calendar (.ics), any CSV", "Whenever you like", "A few taps and Save; an import is one command, good for bringing in years of history the first time"]] },
    costTitle: "What it costs your computer (measured on an M4 MacBook)",
    cost: [
      "<b>No server to carry:</b> each person's computer is their own server, and the author receives no data. The only request to the internet is asking GitHub once a day whether there is a newer version.",
      "<b>One send from the phone:</b> 3 days are about 1,600 records and about 350 KB (counts from a real day of the author's, about 540 records); writing them into the tables takes 0.03 s.",
      "<b>One Screen Time collection:</b> four weeks from 3 devices, about 6,900 stretches, in 0.4 s with a peak of about 50 MB of memory.",
      "<b>The dashboard, always on:</b> about 105 MB of memory and no CPU when idle; each page is computed in 0.004–0.36 s (14 months of demo data).",
      "<b>Disk:</b> the code is 25 MB; the data is plain CSV, mostly screen records, about 14 KB a day or 5 MB a year.",
      "<b>Setting it up:</b> about 6 s to download the code and 20 s to build the Mac app; the iPhone app needs Xcode (3.7 GB). Money: nothing with a free Apple ID, or US$99 a year for a developer account, which makes renewing a once-a-year job."],
    ladderTitle: "How proactive it is",
    ladder: { head: ["Step", "What it means", "Here"], rows: [
      ["See", "Body and daily life on the same day", "yes", "today", "Today"],
      ["Compare", "Against your own normal and your goals", "yes", "sleep", "Body signals"],
      ["Advise", "Each morning, at most three things to do today, with the reason", "yes", "today", "Today"],
      ["Follow up", "The next day, checked against the data, nothing to tick", "new", "followup", "Follow-up"],
      ["Change the approach", "When it keeps failing: a smaller step, a phone setting that remembers for you, an if-then plan", "new", "followup", "Follow-up"],
      ["Ask back", "After a workout, what it trained; the next two mornings, whether those parts are sore", "new", "recovery", "Recovery"],
      ["Reach you", "A reminder without opening the page", "no", null, "For now you open the page to see it"],
      ["Check it helped", "After a change, were the next days better", "part", "followup", "Tomorrow will be better (on Follow-up) shows associations, not causes"]] },
    status: { yes: "Yes", new: "New in this version", no: "Not yet", part: "In part" },
    folds: [
      { h: "Next to what people use now", table: { head: ["What people use", "What it covers", "What this adds"], rows: [
        ["Watch apps (Oura, WHOOP, Garmin Connect)", "A recovery score from their own device", "Recovery on the same day as food, screens and the calendar"],
        ["Food logs (MyFitnessPal, Cronometer)", "What you ate", "How late you ate, next to the next morning's recovery"],
        ["Screen Time", "How long", "Next to sleep, focus and the next day"],
        ["Apple Health", "Stores almost everything", "Says what to change today, and why"],
        ["Cross-app trackers (Exist.io, Bearable)", "Correlations", "On this computer only, rules written down, turned into today's to-dos"]] },
        after: "What that costs now: several apps, often several subscriptions, your history in several clouds, scores whose formula you cannot check, and you still do the joining-up yourself." },
      { h: "Trade-offs, on purpose", items: [
        "<b>No cloud, and no sending while the app is closed:</b> the iPhone app sends the data to your own computer while it is open; without it you import an Apple Health export. In return, the data never leaves your computer.",
        "<b>Rules, not a model:</b> the advice comes from a few fixed rules, written down, explainable and checkable, but it does not “learn”. An optional assistant, off by default, only reads the sentence you type about where it feels tight.",
        "<b>You against you:</b> in the first 28 days there is no normal yet, so there are fewer answers.",
        "<b>Not medical advice:</b> behaviour and body signals only; no diagnosis, no streaks.",
        "<b>One total score only:</b> the morning after training. Its four parts are each set against your normal on the same 0–10 scale and then averaged, every part shown; nothing else with different units is added into one number, so the load on the body and on the mind stay apart."] },
      { h: "Where it stands", items: [
        "<b>The computer side</b> (dashboard, importers, follow-up): collection has run on the author's Mac with real Screen Time; every rule has tests.",
        "<b>The iPhone app:</b> pairing, reading Health and sending have been tested end to end in the simulator, not yet on a real phone with real data.",
        "<b>Nobody but the author has installed it yet.</b> Installing takes a Mac, Xcode and a little command line, which is the biggest hurdle today."] },
      { h: "What comes next", items: [
        "<b>Reach you in the morning:</b> today's adjustments as a phone notification, without opening the page.",
        "<b>Have people try it:</b> 2–3 friends with an Apple Watch, 14 days each: how long installing took, on how many days they opened it, how much of the advice happened.",
        "<b>TestFlight:</b> people who don't use Xcode can install it, renewed once a year.",
        "<b>An AI assistant:</b> it reads every page's data and proposes changes to your goals; nothing changes until you accept on the Goals page. The way in is ready: <code>healthaio goal propose</code>."] },
      { h: "Who made it, and how", items: [
        "Who did what: the needs, the trade-offs and the acceptance checks are mine; the code was written by AI coding tools (Claude Code, Codex).",
        "It comes from the personal system I have used for a year; its four generations are in History (on my own site).",
        "Python's standard library, nothing else to install; colours, components and charts are one versioned design kit; every rule has tests."] },
    ],
    links: [[REPO, "GitHub repository"], ["#project/guide", "Guide"], ["history", "History"], ["#kit", "Design kit"]],
  },
};

const table = (head, rows) => `<div class="table-wrap"><table class="doc-table"><thead><tr>${head.map((h) => `<th>${h}</th>`).join("")}</tr></thead>
  <tbody>${rows.join("")}</tbody></table></div>`;

// which device collects what, how often and what you do; then what it costs the computer, as measured
function dataHtml(c) {
  const rows = c.data.rows.map((r) => `<tr>${r.map((cell, k) => (k === 0 ? `<th scope="row">${esc(cell)}</th>` : `<td>${esc(cell)}</td>`)).join("")}</tr>`);
  return `<h2 class="doc-section">${c.dataTitle}</h2>
    <section class="card">${table(c.data.head, rows)}
      <h3 class="doc-sub">${c.costTitle}</h3><ul class="doc-list">${c.cost.map((x) => `<li>${x}</li>`).join("")}</ul></section>`;
}

// the steps from showing data to changing what happens, and which of them this version takes
const STATUS_TONE = { yes: "good", new: "good", part: "watch", no: "" };
function ladderHtml(c) {
  const rows = c.ladder.rows.map(([step, what, status, page, where]) => `<tr><th scope="row">${esc(step)}</th><td>${esc(what)}</td>
    <td><span class="chip${STATUS_TONE[status] ? ` ${STATUS_TONE[status]}` : ""}">${esc(c.status[status])}</span> ${page ? `<a href="#${page}">${esc(where)} ›</a>` : `<span class="muted">${esc(where)}</span>`}</td></tr>`);
  return `<h2 class="doc-section">${c.ladderTitle}</h2><section class="card doc-ladder">${table(c.ladder.head, rows)}</section>`;
}

function fold(f, i) {
  const table = f.table ? `<div class="table-wrap"><table class="doc-table"><thead><tr>${f.table.head.map((h) => `<th>${h}</th>`).join("")}</tr></thead>
    <tbody>${f.table.rows.map((r) => `<tr>${r.map((c, k) => (k === 0 ? `<th scope="row">${esc(c)}</th>` : `<td>${esc(c)}</td>`)).join("")}</tr>`).join("")}</tbody></table></div>` : "";
  const items = f.items ? `<ul class="doc-list">${f.items.map((x) => `<li>${x}</li>`).join("")}</ul>` : "";
  return `<li><details${i === 0 ? " open" : ""}><summary><span class="doc-n">${i + 1}</span>${f.h}</summary>${table}${items}${f.after ? `<p>${f.after}</p>` : ""}</details></li>`;
}

export default {
  render() {
    const c = PROJECT[getLang()] || PROJECT.en;
    const cards = c.cards.map((card, i) => `<section class="card doc-card"><h3><span class="doc-n">${"ABC"[i]}</span>${card.h}</h3>
      <ul>${card.items.map((x) => `<li>${esc(x)}</li>`).join("")}</ul></section>`).join("");
    const loop = c.loop.map(([name, what, page, label]) => `<li><b>${name}</b><span>${what}</span><a href="#${page}">${label} ›</a></li>`).join("");
    // History is on the author's own site, one page per language
    const links = c.links.map(([to, label]) => {
      const href = to === "history" ? t("doc.history_url") : to;
      const out = href.startsWith("http");
      return `<a href="${esc(href)}"${out ? ' target="_blank" rel="noopener"' : ""}>${label} ${out ? "↗" : "›"}</a>`;
    }).join("");
    return `<div class="head"><div><h1>${c.title}</h1><div class="sub">${c.sub}</div></div></div>
      <div class="doc">
        <div class="doc-note"><p>${c.note}</p><button type="button" class="doc-link" id="doc-lang">${t("doc.other_lang")}</button></div>
        <section class="card"><p class="doc-lede">${c.lede}</p><div class="doc-facts">${c.facts.map((f) => `<span class="chip">${f}</span>`).join("")}</div></section>
        <div class="doc-brief">${cards}</div>
        <h2 class="doc-section">${c.loopTitle}</h2>
        <ol class="doc-loop">${loop}</ol>
        ${dataHtml(c)}
        ${ladderHtml(c)}
        <section class="card"><ol class="doc-folds">${c.folds.map(fold).join("")}</ol></section>
        ${guideSteps(false)}
        <p class="doc-try">${links}</p>
      </div>`;
  },
  mount(el) {
    const lang = el.querySelector("#doc-lang");
    if (lang) lang.onclick = () => document.querySelector("#lang")?.click();
  },
};
