"""A small web server: the page files, one JSON endpoint per page, and the routes the iPhone app uses.

GET/POST /api/restore serves the separate append-only restore.jsonl: feelings,
actual activities, reflections and celebrations. POST /api/care appends to
body_care.jsonl: where it feels tight and the short moves done. The same
origin/device write boundary as check-ins applies; neither changes measured health samples.

Binds to 127.0.0.1 by default. The pages only read the data; it changes by editing or importing the CSV files, or by
a package from the paired iPhone app. The browser can write three things, and only from a page this server served
itself, plus the rest log above: a goal (POST /api/goals: set one, or answer an assistant's proposal), added as a line to goals.jsonl next to
healthaio.toml; the morning check-in (POST /api/checkin: how you feel and where you are sore), which replaces
that morning's soreness rows and sets that morning's feeling; and what a workout trained (POST /api/trained), which
replaces that workout's row in workout_notes.csv. ``--lan`` lets phones on your home network or Tailscale in: they need a token from pairing,
and nobody else is answered (docs/CAPTURE.md).
"""
import json
import mimetypes
import os
import re
import sys
import threading
from datetime import datetime, timedelta
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, Dict, Optional
from urllib.parse import parse_qs, urlsplit

from . import __version__, capture, goal_log, iphone, kit, phone, update
from . import care_log, checkin, restore_log, recovery_log
from .config import Config
from .context import Context
from .modules import PAGES

WEB = Path(__file__).resolve().parent / "web"
PARAM = re.compile(r"^\d{4}-\d{2}-\d{2}$")
PACKAGE_ROUTE = re.compile(r"^/capture/v1/packages/([^/]+)$")
SMALL_BODY = 64 * 1024
mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("image/svg+xml", ".svg")


def payload(cfg: Config, name: str, param: Optional[str] = None, now: Optional[datetime] = None) -> Any:
    if name == "settings":
        return cfg.public()
    if name == "kit":  # the design kit's manifest, for the gallery page (#kit)
        return kit.manifest()
    ctx = Context(goal_log.apply(cfg), now=now)  # the goals set on the Goals page, laid over healthaio.toml
    return PAGES[name](ctx, param)


def to_json(data: Any) -> bytes:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"), default=str).encode("utf-8")


class Updater:
    """``POST /api/update``: install the newest version in the background, then start this server again."""

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.running = False
        self.last: Optional[Dict[str, Any]] = None
        self.lock = threading.Lock()

    def start(self) -> bool:
        with self.lock:
            if self.running:
                return False
            self.running = True
        threading.Thread(target=self._run, daemon=True).start()
        return True

    def _run(self) -> None:
        try:
            self.last = update.apply(self.cfg)
        finally:
            self.running = False
        if self.last.get("ok") and self.last.get("to") != __version__:
            threading.Timer(1.0, restart).start()  # let the page read the result first


def restart() -> None:
    """Replace this process with a fresh one running the new code: same arguments, same port, same pid (so the Mac
    app that started it keeps watching the same process)."""
    sys.stdout.flush()
    os.execv(sys.executable, [sys.executable, "-m", "healthaio", *sys.argv[1:]])


def make_handler(cfg: Config, now: Callable[[], Optional[datetime]] = lambda: None, lan: bool = False):
    updater = Updater(cfg)

    class Handler(BaseHTTPRequestHandler):
        server_version = "healthaio"

        def log_message(self, fmt: str, *args: Any) -> None:  # quiet by default
            if cfg.demo is False and "--verbose" in sys.argv:
                super().log_message(fmt, *args)

        def _send(self, status: int, body: bytes, kind: str, cache: str = "no-store") -> None:
            self.send_response(status)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", cache)
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy",
                             "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; "
                             "img-src 'self' data:; frame-ancestors 'none'")
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def _json(self, status: int, data: Any) -> None:
            self._send(status, to_json(data), "application/json; charset=utf-8")

        # ------------------------------------------------ who is asking

        def _local(self) -> bool:
            return phone.is_loopback(self.client_address[0])

        def _bearer(self) -> Optional[str]:
            value = self.headers.get("Authorization", "")
            return value[7:].strip() if value[:7].lower() == "bearer " else None

        def _cookie(self) -> Optional[str]:
            try:
                jar = SimpleCookie(self.headers.get("Cookie", ""))
            except Exception:
                return None
            morsel = jar.get("healthaio_read")
            return morsel.value if morsel else None

        def _gate(self) -> bool:
            """Refuse anyone outside this computer, the home network and Tailscale, and any request whose Host is
            not this computer's address (a rebound DNS name). Answers 403 itself and returns False."""
            if not phone.allowed_source(self.client_address[0]) or not phone.host_ok(self.headers.get("Host")):
                self._json(403, {"error": "this server only answers this computer and your own network"})
                return False
            return True

        def _reader(self) -> bool:
            if self._local():
                return True
            token = self._cookie() or self._bearer()
            if phone.authenticate(cfg, token, "read"):
                return True
            self._json(401, {"error": "pair this device first (healthaio pair on the computer)"})
            return False

        def _device(self) -> Any:
            """The paired device behind a capture token; {} for this computer itself; None (after answering 401)."""
            device = phone.authenticate(cfg, self._bearer(), "capture")
            if device:
                return device
            if self._local() and not self._bearer():
                return {}
            self._json(401, {"error": "this device is not paired, or was unpaired; pair it again"})
            return None

        def _body(self, limit: int) -> Optional[bytes]:
            if self.headers.get("Content-Type", "").split(";")[0].strip() != "application/json":
                self._json(415, {"error": "send JSON"})
                return None
            try:
                length = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                length = -1
            if not 0 < length <= limit:
                self._json(413, {"error": f"expected a JSON body of at most {limit // 1024} KB"})
                return None
            return self.rfile.read(length)

        # ------------------------------------------------ routes

        def do_HEAD(self) -> None:
            self.do_GET()

        def do_GET(self) -> None:
            if not self._gate():
                return
            url = urlsplit(self.path)
            path = url.path
            if path.startswith("/capture/"):
                return self._capture_get(path)
            if not self._reader():
                return
            if path == "/api/version":
                return self._json(200, update.cached(cfg))
            if path == "/api/update":
                return self._json(200, {"running": updater.running, "last": updater.last})
            if path.startswith("/api/"):
                name = path[len("/api/"):]
                if name not in ("settings", "kit") and name not in PAGES:
                    return self._send(404, to_json({"error": "unknown page"}), "application/json")
                query = parse_qs(url.query)
                param = (query.get("day") or query.get("week") or [None])[0]
                if param is not None and not PARAM.match(param):
                    return self._send(400, to_json({"error": "expected YYYY-MM-DD"}), "application/json")
                try:
                    body = to_json(payload(cfg, name, param, now()))
                except Exception as error:  # show the page an error, keep the server up
                    print(f"[healthaio] {name} failed: {error!r}", file=sys.stderr)
                    return self._send(500, to_json({"error": "this page could not be computed; see the server log"}),
                                      "application/json")
                return self._send(200, body, "application/json; charset=utf-8")
            target = (WEB / ("index.html" if path in ("", "/") else path.lstrip("/"))).resolve()
            if WEB not in target.parents or not target.is_file():
                return self._send(404, b"not found", "text/plain; charset=utf-8")
            kind = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
            if kind.startswith("text/") or kind.endswith(("javascript", "json", "svg+xml")):
                kind += "; charset=utf-8"
            self._send(200, target.read_bytes(), kind, cache="no-cache")

        def do_POST(self) -> None:
            if not self._gate():
                return
            path = urlsplit(self.path).path
            if path.startswith("/capture/"):
                if self.headers.get("Origin"):  # the phone app sends none; a web page always does
                    return self._json(403, {"error": "web pages cannot write here"})
                return self._capture_post(path)
            if path == "/api/update":
                if not (self._local() and self._same_site()):
                    return self._json(403, {"error": "updates can only be started from this computer's own page"})
                if updater.start():
                    return self._json(202, {"started": True})
                return self._json(409, {"started": False, "error": "an update is already running"})
            if path == "/api/goals":
                return self._goals()
            if path == "/api/recovery-checkin":
                return self._checkin(recovery_log.from_browser)
            if path == "/api/checkin":
                return self._checkin(checkin.from_browser)
            if path == "/api/trained":
                return self._checkin(checkin.trained_from_browser)
            if path == "/api/restore":
                return self._checkin(restore_log.from_browser)
            if path == "/api/care":
                return self._checkin(care_log.from_browser)
            return self._json(404, {"error": "nothing to write here"})

        def _same_site(self) -> bool:
            # only this app's own page may write: a page on any other site sends another Origin (and a DNS name pointed
            # at this computer was already refused by _gate), and JSON forces the browser to ask first, which this
            # server never answers
            host = self.headers.get("Host", "")
            return (self.headers.get("Origin") == f"http://{host}"
                    and self.headers.get("Content-Type", "").split(";")[0].strip() == "application/json")

        def _goals(self) -> None:
            # this computer's page, or the panel in a paired phone (it holds the read token for this dashboard)
            if not self._same_site() or not (self._local() or phone.authenticate(cfg, self._cookie(), "read")):
                return self._send(403, to_json({"error": "goals can only be changed from this app's own page"}), "application/json")
            length = int(self.headers.get("Content-Length") or 0)
            if not 0 < length <= 8192:
                return self._send(413, to_json({"error": "expected a small JSON body"}), "application/json")
            try:
                entry = goal_log.from_browser(cfg, json.loads(self.rfile.read(length)), now())
            except ValueError as error:  # GoalError, ConfigError and bad JSON are all ValueErrors
                return self._send(400, to_json({"error": str(error)}), "application/json")
            return self._send(200, to_json({"ok": True, "id": entry["id"]}), "application/json; charset=utf-8")

        def _checkin(self, write) -> None:
            # the morning check-in, or what a workout trained: the same rule as goals (this app's own page, here or in
            # the paired phone's panel), and it only ever writes that morning's rows or that workout's row
            if not self._same_site() or not (self._local() or phone.authenticate(cfg, self._cookie(), "read")):
                return self._send(403, to_json({"error": "a check-in can only be saved from this app's own page"}), "application/json")
            body = self._body(4096)
            if body is None:
                return
            try:
                result = write(cfg, json.loads(body), now())
            except ValueError as error:  # CheckinError and bad JSON
                return self._send(400, to_json({"error": str(error)}), "application/json")
            return self._send(200, to_json(result), "application/json; charset=utf-8")

        def _capture_get(self, path: str) -> None:
            if path == "/capture/v1/hello":
                return self._json(200, {"app": "healthaio", "protocol": 1, "version": __version__,
                                        "timezone": cfg.timezone, "kinds": list(capture.KINDS),
                                        "max_bytes": capture.MAX_BYTES, "lan": lan})
            device = self._device()
            if device is None:
                return
            match = PACKAGE_ROUTE.match(path)
            if match:
                try:
                    return self._json(200, capture.lookup(cfg, match.group(1)))
                except capture.CaptureError as error:
                    return self._json(400, {"error": str(error)})
            if path == "/capture/v1/status":
                from .collect import latest
                return self._json(200, {"version": __version__, "timezone": cfg.timezone, "device": device or None,
                                        "latest": latest(cfg), "last_package": capture.last_receipt(cfg),
                                        "update": update.cached(cfg), "iphone": iphone.status(cfg)})
            if path == "/capture/v1/renew":
                return self._json(200, iphone.status(cfg))
            return self._json(404, {"error": "unknown route"})

        def _capture_post(self, path: str) -> None:
            if path == "/capture/v1/pair":
                body = self._body(SMALL_BODY)
                if body is None:
                    return
                try:
                    data = json.loads(body)
                    if not isinstance(data, dict):
                        raise phone.PairingError("expected a JSON object")
                    tokens = phone.pair(cfg, data.get("code"), data.get("device_name"), data.get("device_id"))
                except phone.PairingError as error:
                    return self._json(error.status, {"error": str(error)})
                except ValueError:
                    return self._json(400, {"error": "the body is not JSON"})
                return self._json(200, {**tokens, "server": {"version": __version__, "timezone": cfg.timezone}})
            device = self._device()
            if device is None:
                return
            if path == "/capture/v1/packages":
                body = self._body(capture.MAX_BYTES)
                if body is None:
                    return
                try:
                    status, receipt = capture.receive(cfg, body, device)
                except capture.CaptureError as error:
                    return self._json(error.status, {"ok": False, "error": str(error)})
                return self._json(status, receipt)
            if path == "/capture/v1/renew":
                started = iphone.start_background(cfg)
                if started["started"]:
                    return self._json(202, started)
                if started["reason"] == "running":
                    return self._json(409, {"error": "a renewal is already running", "reason": "running"})
                return self._json(503, {"error": "this computer cannot renew the app", "reason": started["reason"]})
            return self._json(404, {"error": "unknown route"})

    return Handler


class Server(ThreadingHTTPServer):
    # the page loads about a dozen scripts at once; the stdlib backlog of 5 resets some of those connections,
    # and a module that fails to load leaves the page on "Loading…"
    request_queue_size = 128
    daemon_threads = True


def _check_daily(cfg: Config) -> None:
    """Ask GitHub for a newer version now and once a day (a no-op when [updates] check = false)."""
    def run() -> None:
        try:
            update.check(cfg)
        except Exception as error:  # an update check must never take the dashboard down
            print(f"[healthaio] update check failed: {error!r}", file=sys.stderr)
        timer = threading.Timer(timedelta(hours=24).total_seconds(), run)
        timer.daemon = True
        timer.start()
    if update.enabled(cfg) and not cfg.demo:
        threading.Thread(target=run, daemon=True).start()


def serve(cfg: Config, host: str = "127.0.0.1", port: int = 8790,
          now: Callable[[], Optional[datetime]] = lambda: None, lan: bool = False) -> None:
    if lan:
        host = "0.0.0.0"
    elif host not in ("127.0.0.1", "localhost", "::1"):
        print(f"[healthaio] warning: listening on {host}; anyone who can reach this address can read your data.",
              file=sys.stderr)
    retried = capture.retry_pending(cfg)
    if retried:
        print(f"[healthaio] wrote {retried} waiting package(s) from the phone into the tables")
    httpd = Server((host, port), make_handler(cfg, now, lan=lan))
    print(f"Health AIO {__version__} on http://localhost:{port}  (data: {cfg.data_dir})")
    if lan:
        addresses = phone.local_addresses()
        print("Phones can connect after pairing (healthaio pair): "
              + (", ".join(f"http://{a}:{port}" for a in addresses) or "no network address found"))
    _check_daily(cfg)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
