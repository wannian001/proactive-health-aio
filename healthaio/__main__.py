"""Health AIO command line.

    python -m healthaio demo                 # write a demo folder (made-up person) and print how to open it
    python -m healthaio serve --demo         # try it at once with demo data
    python -m healthaio serve                # your own data: reads ./healthaio.toml
    python -m healthaio build-static --demo  # the GitHub Pages site (demo data only)
    python -m healthaio check                # validate your data files
    python -m healthaio import ...           # bring data in (Apple Health, .ics, Screen Time, any CSV)
    python -m healthaio kit json|export|check|lock  # the design kit: its manifest, a copy for another app, is a copy current
    python -m healthaio goal list|set|propose|accept|decline  # goals beyond healthaio.toml (also set on the Goals page)
    python -m healthaio checkin --feel 5 torso=2 left_calf=1  # this morning's check-in (also on the Recovery page)
    python -m healthaio trained --start 2026-10-12T17:44 --note "bench, rows"  # what a workout trained (also the popup)
    python -m healthaio serve --lan          # let your paired iPhone in (home network or Tailscale)
    python -m healthaio pair                 # open a code for the iPhone app;  devices [revoke ID|--all]
    python -m healthaio collect              # run the automatic importers once (the Mac app does it every few hours)
    python -m healthaio update [--check]     # is there a newer version on GitHub; install it
    python -m healthaio iphone status|renew  # re-sign and reinstall the iPhone app (free Apple ID: every 7 days)
    python -m healthaio status --json        # everything the Mac app shows, in one answer
"""
import argparse
import json
import sys
import tempfile
from datetime import date, datetime
from pathlib import Path
from typing import List, Optional

from . import __version__
from . import config as config_mod
from . import demo as demo_mod
from .schema import TABLES, describe_markdown


def _config(args) -> config_mod.Config:
    if getattr(args, "demo", False):
        folder = Path(tempfile.mkdtemp(prefix="healthaio-demo-"))
        today = date.fromisoformat(args.today) if getattr(args, "today", None) else None
        path = demo_mod.generate(folder, today)
        return config_mod.load(path)
    path = Path(args.config) if args.config else config_mod.find_config(Path.cwd())
    if path is None:
        sys.exit("No healthaio.toml here. Copy examples/healthaio.example.toml, or try `python -m healthaio serve --demo`.")
    return config_mod.load(path)


def _now(args) -> Optional[datetime]:
    if getattr(args, "now", None):
        return datetime.fromisoformat(args.now)
    if getattr(args, "demo", False) and args.command != "serve" or getattr(args, "today", None):
        # the demo person's day was generated up to 18:40; pages must agree on what "now" is
        day = date.fromisoformat(args.today) if getattr(args, "today", None) else date.today()
        return datetime.combine(day, datetime.min.time()).replace(hour=18, minute=40)
    return None


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="healthaio", description="A local-first dashboard for your day.")
    parser.add_argument("--config", help="path to healthaio.toml (default: ./healthaio.toml)")
    parser.add_argument("--version", action="version", version=f"healthaio {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("serve", help="run the dashboard on this computer")
    p.add_argument("--demo", action="store_true", help="use a made-up person instead of your data")
    p.add_argument("--today", help="demo only: pretend today is YYYY-MM-DD")
    p.add_argument("--now", help="pretend the current time is YYYY-MM-DDTHH:MM")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8790)
    p.add_argument("--lan", action="store_true",
                   help="also answer your home network and Tailscale (paired phones only; see docs/CAPTURE.md)")

    p = sub.add_parser("demo", help="write a demo folder you can open and edit")
    p.add_argument("--out", default="healthaio-demo")
    p.add_argument("--today", help="pretend today is YYYY-MM-DD")

    p = sub.add_parser("build-static", help="render a static site (for GitHub Pages)")
    p.add_argument("--demo", action="store_true")
    p.add_argument("--today")
    p.add_argument("--now")
    p.add_argument("--out", default="site")
    p.add_argument("--i-understand-this-publishes-my-data", dest="publish_own", action="store_true",
                   help="required to build from your own data instead of the demo")

    sub.add_parser("check", help="validate the CSV files in the data folder")
    p = sub.add_parser("schema", help="print the data format")
    p.add_argument("--markdown", action="store_true")
    p = sub.add_parser("kit", help="the design kit: print its manifest, copy it into another app, check a copy")
    kit_sub = p.add_subparsers(dest="kit_command", required=True)
    kit_sub.add_parser("json", help="print the manifest: files with hashes, tokens, components, charts")
    k = kit_sub.add_parser("export", help="copy the kit files into DIR (css/..., js/...) plus DIR/kit.json")
    k.add_argument("dir")
    k.add_argument("--force", action="store_true", help="overwrite files changed locally since the last export")
    k = kit_sub.add_parser("check", help="compare DIR with its kit.json and with this kit; exit 0 only when up to date")
    k.add_argument("dir")
    kit_sub.add_parser("lock", help="record this KIT_VERSION's file hashes in healthaio/kit.lock.json (after a version bump)")
    p = sub.add_parser("goal", help="goals set beyond healthaio.toml: list them, set one, or (for an assistant) propose one")
    goal_sub = p.add_subparsers(dest="goal_command", required=True)
    g = goal_sub.add_parser("list", help="every goal field: its value now, where it comes from, and open proposals")
    g.add_argument("--json", action="store_true")
    g = goal_sub.add_parser("set", help="FIELD VALUE [FIELD VALUE ...], e.g. food.kcal_max 2200; null = back to healthaio.toml")
    g.add_argument("pairs", nargs="+")
    g = goal_sub.add_parser("propose", help="for an assistant: suggest FIELD VALUE pairs; nothing changes until accepted")
    g.add_argument("pairs", nargs="+")
    g.add_argument("--note", help="why, in a sentence (shown with the proposal)")
    g.add_argument("--by", default="assistant", help="who proposes (shown with the proposal)")
    for name in ("accept", "decline"):
        g = goal_sub.add_parser(name, help=f"{name} an open proposal by its id (see `goal list`)")
        g.add_argument("id")
    p = sub.add_parser("checkin", help="the morning check-in: how you feel and where you are sore (also on the Recovery page)")
    p.add_argument("levels", nargs="*", metavar="REGION=LEVEL", help="1 a little, 2 clearly, 3 very; none given = nothing sore")
    p.add_argument("--feel", type=int, choices=[2, 5, 8], help="2 not recovered, 5 so-so, 8 recovered")
    p.add_argument("--energy", type=float, help="optional body energy, 0 drained to 5 full; separate from --feel")
    p.add_argument("--date", help="the morning, YYYY-MM-DD (default today)")
    p = sub.add_parser("trained", help="what a workout trained: regions of the body figure and a note (also the popup after a workout)")
    p.add_argument("regions", nargs="*", metavar="REGION", help="head, torso, pelvis, left_upper_arm, ...; none given = from the note's words")
    p.add_argument("--start", required=True, help="the workout's start, YYYY-MM-DDTHH:MM, as in workouts.csv")
    p.add_argument("--note", help="what you trained, in your own words")
    p = sub.add_parser("sitting", help="for the Mac app: the stretch at the computer going on now, or a break; prints the reminder as JSON")
    p.add_argument("--since", help="when the current stretch started (keyboard or mouse in use since), YYYY-MM-DDTHH:MM[:SS][+zone]")
    p.add_argument("--off", action="store_true", help="a break: nothing going on at the computer (with --since: when it began)")
    p.add_argument("--now")
    p = sub.add_parser("pair", help="open an 8-digit code (10 minutes) for the iPhone app")
    p.add_argument("--port", type=int, default=8790, help="the port `serve --lan` listens on")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("devices", help="paired phones; `devices revoke ID` or `devices revoke --all` cuts one off")
    p.add_argument("action", nargs="?", choices=["revoke"])
    p.add_argument("id", nargs="?")
    p.add_argument("--all", action="store_true")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("collect", help="run the importers that work by themselves ([collect] sources)")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("status", help="last collection, paired phones, newest data, iPhone app signature, updates")
    p.add_argument("--port", type=int, default=8790)
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("update", help="check GitHub for a newer version and install it")
    p.add_argument("--check", action="store_true", help="only say whether there is one")
    p.add_argument("--force", action="store_true", help="ask GitHub now, not the answer from the last 20 hours")
    p.add_argument("--yes", action="store_true", help="install without asking")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("iphone", help="the iPhone app: when its signature runs out, and renewing it")
    p.add_argument("action", choices=["status", "renew"])
    p.add_argument("--device", help="devicectl identifier of the iPhone (default: the paired one)")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("page", help="print one page's JSON (for scripts and assistants)")
    p.add_argument("name")
    p.add_argument("param", nargs="?")
    p.add_argument("--demo", action="store_true")
    p.add_argument("--today")
    p.add_argument("--now")

    try:
        from .importers import cli as importers_cli
        importers_cli.add_parsers(sub)
    except Exception:  # importers are optional; a broken one must not block serve
        importers_cli = None

    args = parser.parse_args(argv)
    if args.command == "schema":
        if args.markdown:
            print(describe_markdown())
        else:
            print(json.dumps({n: [c.name for c in t.columns] for n, t in TABLES.items()}, indent=2))
        return 0
    if args.command == "demo":
        today = date.fromisoformat(args.today) if args.today else None
        path = demo_mod.generate(Path(args.out), today)
        print(f"Demo written to {path.parent}. Open it with:\n  python -m healthaio --config {path} serve")
        return 0
    if args.command == "kit":
        from . import kit
        return kit.run(args)
    if args.command == "import":
        if importers_cli is None:
            sys.exit("importers are not installed")
        cfg = _config(args)
        from .state import write_lock
        with write_lock(cfg):
            return importers_cli.run(args, cfg)
    if args.command == "update":
        return _update(args)

    cfg = _config(args)
    if args.command == "goal":
        from . import goal_log
        return goal_log.run(args, cfg)
    if args.command == "checkin":
        from . import checkin
        return checkin.run(args, cfg)
    if args.command == "trained":
        from . import checkin
        return checkin.run_trained(args, cfg)
    if args.command == "sitting":
        from .context import Context
        from .modules import sitting
        if args.off:  # --since with --off: when the break began (the keyboard and mouse went quiet)
            sitting.note(cfg, None, _now(args), datetime.fromisoformat(args.since) if args.since else None)
        elif args.since:
            since = datetime.fromisoformat(args.since)
            sitting.note(cfg, since, _now(args) or datetime.now(since.tzinfo))
        print(json.dumps(sitting.nudge(Context(cfg, now=_now(args))), ensure_ascii=False))
        return 0
    done = _phone_commands(args, cfg)
    if done is not None:
        return done
    if args.command == "serve":
        from .server import serve
        fixed = _now(args)
        serve(cfg, host=args.host, port=args.port, now=lambda: fixed, lan=args.lan)
        return 0
    if args.command == "build-static":
        if not (cfg.demo or args.publish_own):
            sys.exit("build-static writes every number into public files. Use --demo, or add "
                     "--i-understand-this-publishes-my-data if you really mean to publish your own.")
        from .build_static import build
        build(cfg, Path(args.out), now=_now(args))
        return 0
    if args.command == "page":
        from .server import payload
        print(json.dumps(payload(cfg, args.name, args.param, _now(args)), ensure_ascii=False, indent=2, default=str))
        return 0
    if args.command == "check":
        from .store import Store
        store = Store(cfg.data_dir)
        bad = 0
        for name, table in TABLES.items():
            loaded = store.load(name)
            state = f"{len(loaded.rows)} rows" if loaded.present else "missing (optional)"
            print(f"{table.filename:22} {state}")
            for problem in loaded.problems[:20]:
                bad += 1
                print(f"  line {problem.line}, {problem.column}: {problem.message}")
        return 1 if bad else 0
    return 0


def _print(data, as_json: bool, text: str) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=1, default=str) if as_json else text)


def _update(args) -> int:
    from . import update
    path = Path(args.config) if args.config else config_mod.find_config(Path.cwd())
    cfg = config_mod.load(path) if path else None
    info = update.check(cfg, force=args.force or not args.check)
    if args.check or not info["update_available"]:
        state = (f"{info['latest']} is available (you have {info['current']}): {info['url']}" if info["update_available"]
                 else f"{info['current']} is the newest version" + (f" ({info['reason']})" if info.get("reason") else ""))
        _print(info, args.json, state)
        return 0
    if not args.yes:
        if args.json or not sys.stdin.isatty():
            sys.exit("add --yes to install without asking")
        print(f"Health AIO {info['latest']} is available (you have {info['current']}).\n{info['notes'][:600]}")
        if input("Install it now? [y/N] ").strip().lower() not in ("y", "yes"):
            return 0
    result = update.apply(cfg)
    lines = [result["message"]]
    if result["changed"]["mac_app"]:
        lines.append("The Mac app changed too: run mac/build.sh, then turn Full Disk Access on again for Health AIO.")
    if result["changed"]["ios_app"]:
        lines.append("The iPhone app changed too: `healthaio iphone renew` installs the new version.")
    _print(result, args.json, "\n".join(lines))
    return 0 if result["ok"] else 2


def _phone_commands(args, cfg) -> Optional[int]:
    """pair, devices, collect, status, iphone; None for any other command."""
    from . import phone
    if args.command == "pair":
        import urllib.request
        opened = phone.open_code(cfg)
        urls = [f"http://{a}:{args.port}" for a in phone.local_addresses()]
        hello = None
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{args.port}/capture/v1/hello", timeout=3) as answer:
                hello = json.loads(answer.read())
        except (OSError, ValueError):
            pass
        data = {**opened, "urls": urls, "link": phone.pair_link(urls[0], opened["code"]) if urls else None,
                "server_running": hello is not None, "server_lan": bool(hello and hello.get("lan"))}
        text = [f"Pairing code: {opened['code']}  (good for 10 minutes)",
                *(f"  address: {u}" for u in urls), f"  link:    {data['link']}"]
        if not data["server_lan"]:
            text.append("Start the dashboard with `healthaio serve --lan` (or turn on \"Let my phone connect\" in the "
                        "Mac app), so the phone can reach it.")
        _print(data, args.json, "\n".join(text))
        return 0
    if args.command == "devices":
        if args.action == "revoke":
            if not (args.id or args.all):
                sys.exit("say which device (its id from `healthaio devices`) or --all")
            count = phone.revoke(cfg, args.id, everything=args.all)
            _print({"ok": True, "revoked": count}, args.json, f"unpaired {count} device(s)")
            return 0
        found = phone.devices(cfg)
        _print({"devices": found}, args.json, "\n".join(f"{d['id']}  {d['name']}  paired {d['paired_at']}  last seen "
                                                       f"{d['last_seen'] or '-'}" for d in found) or "no paired devices")
        return 0
    if args.command == "collect":
        from .collect import collect
        result = collect(cfg)
        _print(result, args.json, "\n".join(f"{s['name']}: {'ok' if s['ok'] else 'failed'}\n  "
                                            + s["message"].replace("\n", "\n  ") for s in result["sources"]))
        return 0 if result["ok"] else 2
    if args.command == "status":
        from .collect import status
        data = status(cfg, args.port)
        _print(data, True, "")  # the summary is for programs; people have the dashboard
        return 0
    if args.command == "iphone":
        from . import iphone
        if args.action == "status":
            data = iphone.status(cfg)
            last = data.get("last") or {}
            _print(data, args.json, (f"can renew here" if data["can_renew"] else f"cannot renew here: {data['reason']}")
                   + (f"; signature good until {last.get('expires_at')}" if last.get("expires_at") else ""))
            return 0
        result = iphone.renew(cfg, args.device)
        _print(result, args.json, result["message"] + (f" (until {result['expires_at']})" if result.get("expires_at") else ""))
        return 0 if result["ok"] else 2
    return None


if __name__ == "__main__":
    sys.exit(main())
