# Health AIO for Mac · Mac 版 Health AIO

A small menu bar app that keeps the dashboard running on your Mac, collects Screen Time before macOS forgets it, keeps
the iPhone app signed, and tells you when a new version is out.<br>
一个菜单栏小应用：让面板在你的 Mac 上一直运行，在 macOS 删掉屏幕使用时间记录之前把它采集下来，让 iPhone 应用保持签名有效，有新版本时提醒你。

[English](#english) · [中文](#中文)

<p>
  <img src="screenshots/popover-normal-en-light.png" width="32%" alt="The popover, light mode">
  <img src="screenshots/popover-attention-en-dark.png" width="32%" alt="The popover when something needs you, dark mode">
  <img src="screenshots/pair-zh-light.png" width="32%" alt="Pairing an iPhone, in Chinese">
</p>
<p>
  <img src="screenshots/update-alert-zh-light.png" width="48%" alt="The update reminder, in Chinese">
</p>

## English

### Why a Mac app

- **Screen Time needs Full Disk Access.** macOS keeps it in `~/Library/Biome/streams/restricted/App.InFocus/` (your
  iPhone and iPad sync into it too when "Share across devices" is on) and lets a program read it only with Full Disk
  Access. Giving that to Terminal or to Python would give it to everything you run there. Giving it to this one app
  is enough: macOS counts the file access of a process the app starts against the app, so `healthaio` run by the app
  can read Screen Time and nothing else gains the permission.
- **Biome keeps about four weeks.** The app runs the import every couple of hours, so no day is lost.
- **The iPhone app runs out after 7 days** when it is built with a free Apple ID. The app reminds you two days before
  and renews it with one click (Xcode builds and installs it again).
- **Updates come from GitHub.** When there is a newer version, the app asks; if you say yes, it updates.
- **Sitting is only seen as it happens from here.** Screen Time reaches the dashboard every few hours, so the app
  watches how long the keyboard and mouse have been idle (5 minutes is a break). After 50 minutes at the computer
  it shows a notification with one short move (and again every 30 minutes); a click opens the sitting card. Getting
  up after a long stretch is written down as a rest by itself. **Remind me after 50 minutes at the computer** in
  Settings turns the notifications off. It reads only the idle time, never what you type.

### Build

Needs macOS 13 or newer and the Command Line Tools (`xcode-select --install`); Xcode itself is not needed to build
the Mac app.

```bash
mac/build.sh            # builds mac/build/Health AIO.app
mac/build.sh --force    # rebuild even if nothing changed
```

The script compiles `mac/Sources/*.swift` with `swiftc` (Apple silicon, plus Intel when that compiles), draws the
icon, and signs the app ad hoc. It writes two local facts into the built app only: where this repository is (it
becomes `PYTHONPATH`) and which `python3` it found. **It rebuilds only when the sources changed**: every new build has
a new ad-hoc signature, and macOS forgets the Full Disk Access it gave the old one.

### First run

1. `open "mac/build/Health AIO.app"`. A ring appears in the menu bar; there is no Dock icon.
2. Settings opens by itself: choose your `healthaio.toml` (copy `examples/healthaio.example.toml` if you have none).
   Check the Python path (the one found at build time, else `/usr/bin/python3`).
3. Give it Full Disk Access: in the popover, **Open Privacy settings**, then in the list add "Health AIO" with **+**
   and switch it on. If the repository is inside Documents, Desktop or Downloads, macOS may also ask once whether
   Health AIO may open that folder.
4. Optional: **Open at login** in Settings.
5. Optional, for the phone: turn on **Let my phone connect (local network)**, then **Pair iPhone…** and scan the QR
   code with the iPhone camera (or type the 8-digit code in the app). The phone must be on the same Wi-Fi or on
   Tailscale. Renewing the iPhone app needs Xcode and `ios/Local.xcconfig` (see `docs/CAPTURE.md`).

After a rebuild, switch Full Disk Access on again: remove the old "Health AIO" from the list and add the new one.

### What it runs, and when

Every command is `<python> -m healthaio --config <your toml> …`, run from the config's folder with `PYTHONPATH` set
to this repository.

| when | command |
|---|---|
| always, restarted with a growing pause if it stops | `serve [--lan] --port 8790` |
| 30 s after launch, then every 2 hours (Settings), never two at once | `collect --json` |
| 60 s after launch, then every 24 hours (can be turned off) | `update --check --json` |
| when the popover opens, and every 5 minutes | `status --json` (reads local files only) |
| Pair iPhone… | `pair --json`, then `devices --json` every 3 s while the window is open |
| Renew iPhone app, or **Renew now** in the reminder | `iphone renew --json` |
| Update in the update reminder | `update --yes --json`, then the server restarts |

The server's output goes to `~/Library/Logs/HealthAIO/server.log` (moved to `server.log.1` at 5 MB); what the app
ran and when goes to `app.log` next to it. Quitting stops the server and anything still running.

The iPhone reminder comes once a day when the signature has two days or less left, and a dot appears on the menu bar
icon. The update reminder offers **Update**, **Later** and **Skip this version**; a skipped version is not offered
again automatically, but **Check for updates** still shows it.

### What it never does

- It sends nothing anywhere. The only network traffic is what the Python side does to check GitHub for a new version
  (and `git` or `pip` when you choose to update), and the app's own check that the server answers on `127.0.0.1`.
- It changes no system setting. Full Disk Access is yours to give in System Settings; the app only opens the page.
- It writes one file outside its own logs and preferences: with **Open at login** on,
  `~/Library/LaunchAgents/io.github.wannian001.healthaio.mac.plist`, removed again when you switch it off. It never
  touches any other launch agent.
- It reads no health data itself. `healthaio` reads and writes your data folder, as it does from the command line.

### The commands it relies on

The Python side implements these; each prints one JSON object on stdout. Fields the app does not find are shown as
unknown, never guessed.

```
serve [--lan] [--port 8790]                      long-running; prints a line, then serves
collect --json        → {"ok":true,"at":"…","sources":[{"name":"macos-screentime","ok":true,"message":"…"},…]}   exit 0, or 2 when a source failed
status --json         → {"version","config","data_dir","timezone","port","collect":{…}|null,
                         "devices":[{"id","name","paired_at","last_seen"}],"latest":{…},"full_disk_access":true|false|null,
                         "iphone":{"can_renew","reason":null|"no_xcode"|"no_project"|"no_team"|"not_macos","running",
                                   "last":{"at","ok","expires_at","version","message"}|null},
                         "update":{…as update --check, from the cache…}}
pair --json           → {"code":"48213907","expires_at":"…","urls":["http://192.168.1.20:8790"],"link":"healthaio://pair?url=…&code=…",
                         "server_running":true,"server_lan":true}
devices --json        → {"devices":[…]}
update --check --json [--force] → {"current","latest":"0.3.1"|null,"update_available","url","notes","checked_at",
                                   "install":"git"|"pip"|"unknown","can_update","reason"}
update --yes --json   → {"ok","from","to","method","changed":{"mac_app","ios_app"},"message"}   exit 0, or 2
iphone renew --json   → {"ok","at","expires_at","version","device","message"}   exit 0, or 2
```

When a command prints no JSON, the app shows the last lines of its stderr instead.

### For development

- `HEALTHAIO_CLI="python3 /absolute/path/mac/tools/fake_healthaio.py"` makes the app run the fake CLI instead of
  `<python> -m healthaio`. It answers with made-up data; its knobs are at the top of the file.
- Settings can be given as launch arguments without saving them:
  `"mac/build/Health AIO.app/Contents/MacOS/HealthAIO" -configPath /tmp/demo/healthaio.toml -port 18790`.
- `HEALTHAIO_LOG_DIR` moves the logs, `HEALTHAIO_LANG=en|zh` picks the language, `HEALTHAIO_MAC_QUICKSTART=1`
  collects after 3 s and checks for updates after 6 s.
- `"mac/build/Health AIO.app/Contents/MacOS/HealthAIO" --snapshot mac/screenshots` draws the pictures in
  `screenshots/` (made-up data, light and dark, English and Chinese) and exits.

## 中文

### 为什么要一个 Mac 应用

- **屏幕使用时间需要完全磁盘访问权限。** macOS 把它存在 `~/Library/Biome/streams/restricted/App.InFocus/`（打开“跨设备共享”后，
  iPhone 和 iPad 的记录也会同步进来），只有拿到完全磁盘访问权限的程序才能读。把这个权限给终端或 Python，等于给了你在里面运行的所有东西；
  只给这个小应用就够了：macOS 把应用启动的进程的文件访问算在应用头上，所以由它运行的 `healthaio` 能读屏幕使用时间，别的程序拿不到这个权限。
- **Biome 只保留大约四周。** 应用每隔几个小时导入一次，一天都不会丢。
- **用免费 Apple ID 构建的 iPhone 应用 7 天后就打不开了。** 应用提前两天提醒你，点一下就续签（用 Xcode 重新构建并安装）。
- **更新来自 GitHub。** 有新版本时应用会问你；你同意，它就更新。
- **“此刻坐了多久”只能在这里看到。** 屏幕使用时间要过几个小时才进面板，所以应用看键盘和鼠标闲了多久（闲 5 分钟算起身）。在电脑前
  连续 50 分钟，弹一个系统通知，附一个小动作（还在继续就每 30 分钟再提醒）；点通知打开久坐卡片。坐了很久之后起身，会自动记成一次休息。
  设置里的 **在电脑前连续坐满 50 分钟时提醒我** 可以关掉通知。它只读闲置时长，从不读你打了什么字。

### 构建

需要 macOS 13 或更新版本，以及命令行工具（`xcode-select --install`）；构建 Mac 应用不需要 Xcode。

```bash
mac/build.sh            # 生成 mac/build/Health AIO.app
mac/build.sh --force    # 没有改动也重新构建
```

脚本用 `swiftc` 编译 `mac/Sources/*.swift`（Apple 芯片，能编译时也带 Intel），画好图标，再做临时（ad hoc）签名。它只往构建出来的应用里
写两条本地信息：这个仓库在哪里（作为 `PYTHONPATH`），以及找到的是哪个 `python3`。**只有源码改动时才会重新构建**：每次构建都会产生新的临时签名，
macOS 会忘掉给旧签名的完全磁盘访问权限。

### 第一次运行

1. `open "mac/build/Health AIO.app"`。菜单栏会出现一个圆环；程序坞里没有图标。
2. 设置窗口会自动打开：选择你的 `healthaio.toml`（没有的话复制 `examples/healthaio.example.toml`），确认 Python 路径
   （构建时找到的那个，否则是 `/usr/bin/python3`）。
3. 打开完全磁盘访问权限：在弹出面板里点**打开隐私设置**，在列表里用 **+** 添加“Health AIO”并打开开关。如果仓库放在“文稿”“桌面”或
   “下载”里，macOS 可能还会问一次是否允许 Health AIO 打开这个文件夹。
4. 可选：在设置里打开**登录时打开**。
5. 可选，给手机用：打开**允许手机连接（本地网络）**，再点**配对 iPhone…**，用 iPhone 相机扫二维码（或在应用里输入 8 位配对码）。
   手机需要和 Mac 在同一个 Wi-Fi 下，或者都在 Tailscale 上。续签 iPhone 应用需要 Xcode 和 `ios/Local.xcconfig`（见 `docs/CAPTURE.md`）。

重新构建之后，要重新打开完全磁盘访问权限：从列表里删掉旧的“Health AIO”，再添加新的。

### 它运行什么、什么时候运行

每条命令都是 `<python> -m healthaio --config <你的 toml> …`，在配置文件所在的文件夹里运行，`PYTHONPATH` 指向这个仓库。

| 什么时候 | 命令 |
|---|---|
| 一直运行，意外停止后按逐渐变长的间隔重启 | `serve [--lan] --port 8790` |
| 启动 30 秒后，之后每 2 小时（可在设置里改），绝不同时跑两次 | `collect --json` |
| 启动 60 秒后，之后每 24 小时（可以关掉） | `update --check --json` |
| 打开弹出面板时，以及每 5 分钟 | `status --json`（只读本地文件） |
| 配对 iPhone… | `pair --json`，窗口开着时每 3 秒 `devices --json` |
| 续签 iPhone 应用，或提醒里的**立即续签** | `iphone renew --json` |
| 更新提醒里的**更新** | `update --yes --json`，然后重启服务 |

服务的输出写到 `~/Library/Logs/HealthAIO/server.log`（到 5 MB 时移到 `server.log.1`）；应用运行了什么、什么时候运行，写在同一目录的
`app.log`。退出应用会停掉服务和所有还在运行的命令。

签名只剩两天或更少时，iPhone 提醒每天出现一次，菜单栏图标上也会出现一个圆点。更新提醒有**更新**、**以后再说**和**跳过这个版本**三个按钮；
跳过的版本不会再自动提醒，但点**检查更新**仍会显示。

### 它从不做的事

- 不向任何地方发送任何东西。唯一的网络活动是 Python 端去 GitHub 检查新版本（以及你选择更新时的 `git` 或 `pip`），还有应用自己确认服务在
  `127.0.0.1` 上有响应。
- 不改任何系统设置。完全磁盘访问权限由你在系统设置里给；应用只负责打开那个页面。
- 除了自己的日志和偏好设置，只会写一个文件：打开**登录时打开**时写入
  `~/Library/LaunchAgents/io.github.wannian001.healthaio.mac.plist`，关掉时删除。它从不碰其他任何启动项。
- 它自己不读健康数据。读写数据文件夹的是 `healthaio`，和你在命令行里运行时一样。

### 它依赖的命令

Python 端实现的命令和输出格式见上面英文部分的 “The commands it relies on”。命令没有输出 JSON 时，应用会显示它 stderr 的最后几行。

### 开发用

- `HEALTHAIO_CLI="python3 /绝对路径/mac/tools/fake_healthaio.py"` 让应用运行假的 CLI，而不是 `<python> -m healthaio`。它用虚构数据回答，
  可调的开关写在文件开头。
- 设置可以作为启动参数传入，不会被保存：
  `"mac/build/Health AIO.app/Contents/MacOS/HealthAIO" -configPath /tmp/demo/healthaio.toml -port 18790`。
- `HEALTHAIO_LOG_DIR` 改日志位置，`HEALTHAIO_LANG=en|zh` 指定语言，`HEALTHAIO_MAC_QUICKSTART=1` 让应用 3 秒后采集、6 秒后检查更新。
- `"mac/build/Health AIO.app/Contents/MacOS/HealthAIO" --snapshot mac/screenshots` 生成 `screenshots/` 里的图片（虚构数据，浅色和深色，
  英文和中文），然后退出。
