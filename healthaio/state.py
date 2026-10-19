"""The app's own bookkeeping, kept apart from your data tables.

``.healthaio/`` sits next to ``healthaio.toml``. It holds the paired devices (token hashes only), an open pairing
code, every package the phone sent and what happened to it, the last automatic collection, the last iPhone app
renewal and the last update check, and what the Mac app last saw at the keyboard (sitting.json, read by the sitting
reminder). Deleting it unpairs every device.
"""
import json
import os
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Optional

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows has no flock; one writer at a time is then up to you
    fcntl = None  # type: ignore


def folder(cfg) -> Path:
    path = Path(cfg.root) / ".healthaio"
    path.mkdir(parents=True, exist_ok=True)
    return path


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def write_json(path: Path, data: Any, private: bool = False) -> None:
    """Write whole or not at all: a reader never sees half a file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    fd = os.open(tmp, flags, 0o600 if private else 0o644)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=1, default=str)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


@contextmanager
def write_lock(cfg) -> Iterator[None]:
    """One writer of the CSV tables at a time: an import, an automatic collection and a package from the phone can
    otherwise run together, and ``merge_write`` reads the table before it writes it."""
    if fcntl is None:
        yield
        return
    path = folder(cfg) / "write.lock"
    with path.open("a") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def python() -> str:
    """The interpreter running this, for the background jobs the server starts (update, iPhone renewal)."""
    return sys.executable or "python3"


def parse_iso(text: Optional[str]) -> Optional[datetime]:
    if not text:
        return None
    try:
        moment = datetime.fromisoformat(str(text).replace("Z", "+00:00"))
    except ValueError:
        return None
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)
