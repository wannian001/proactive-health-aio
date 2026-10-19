"""The Health AIO design kit: the files that carry Health AIO's look, and a manifest built from them as they are on disk.

    python3 -m healthaio kit json          # print the manifest (also served at /api/kit, and api/kit.json on the static site)
    python3 -m healthaio kit export DIR    # copy the kit into another app: DIR/css/..., DIR/js/..., DIR/kit.json
    python3 -m healthaio kit check DIR     # per file: up to date, outdated, modified locally or missing
    python3 -m healthaio kit lock          # after a new KIT_VERSION: record its file hashes in healthaio/kit.lock.json

Design flows one way, from healthaio to the apps that copy the kit. A copy is never edited in place: an app keeps
its own components in its own files, and a local improvement to a kit file is ported back to Health AIO, given a
new KIT_VERSION and exported again. See docs/DESIGN_KIT.md.
"""
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Bump on every change to any of the four kit files: patch for a value or drawing fix, minor for a new token, class,
# function or option, major for a rename or removal (it breaks an app that uses the old name). kit.lock.json holds
# the hashes of the current version's files, and a test fails when a file changes while the version stays the same.
KIT_VERSION = "1.9.0"
NAME = "healthaio-kit"
WEB = Path(__file__).resolve().parent / "web"
LOCK = Path(__file__).resolve().parent / "kit.lock.json"
MANIFEST = "kit.json"
# kit.json may also list files that export left in place (no longer part of the kit, changed locally): check
# keeps reporting them until they are gone
LEFT = "left_in_place"
# (path under the web folder, role), in load order
FILES: Tuple[Tuple[str, str], ...] = (
    ("css/tokens.css", "tokens"),
    ("css/kit.css", "components"),
    ("js/charts.js", "charts"),
    ("js/icons.js", "icons"),
)

UP_TO_DATE = "up to date"
OUTDATED = "outdated"
MODIFIED = "modified locally"
MISSING = "missing"


class KitError(Exception):
    """A kit command that cannot go ahead (no kit.json to compare with, a local change export would overwrite)."""


def prog() -> str:
    """How the user started Health AIO, for the commands a message tells them to run."""
    return "healthaio" if Path(sys.argv[0]).name == "healthaio" else "python3 -m healthaio"


def _semver(version: str) -> Tuple[int, ...]:
    return tuple(int(x) for x in version.split("."))


# ---- reading the kit files ---------------------------------------------------------------------------------

def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _block(css: str, selector: str) -> str:
    """The declarations of the first rule whose selector is exactly `selector` (no nested braces inside)."""
    match = re.search(r"(?:^|[\s}{])" + re.escape(selector) + r"\s*\{", css)
    if not match:
        return ""
    end = css.index("}", match.end())
    return css[match.end():end]


_DECL = re.compile(r"/\*(.*?)\*/|(--[\w-]+)\s*:\s*([^;]*?)\s*;", re.S)
_ROLE = re.compile(r"^\s*\[([\w-]+)\]")


def _declarations(body: str) -> List[Tuple[str, str, Optional[str]]]:
    """(name, value, role) in order; a comment that starts with [role] sets the role of the declarations after it."""
    out, role = [], None
    for comment, name, value in _DECL.findall(body):
        if name:
            out.append((name, " ".join(value.split()), role))
        else:
            hit = _ROLE.match(comment)
            if hit:
                role = hit.group(1)
    return out


def dark_blocks(css: str) -> Tuple[Dict[str, str], Dict[str, str]]:
    """The two copies of the dark block: (system setting, moon button). They must hold the same values."""
    media = {n: v for n, v, _ in _declarations(_block(css, ':root:not([data-mode="light"])'))}
    attr = {n: v for n, v, _ in _declarations(_block(css, ':root[data-mode="dark"]'))}
    return media, attr


def parse_tokens(css: str) -> List[Dict[str, str]]:
    """Every custom property of the light block with its light value, its dark value (the light one when dark
    mode does not redefine it) and the role from the comment above its group."""
    _, dark = dark_blocks(css)
    return [{"name": name, "light": value, "dark": dark.get(name, value), "role": role or "other"}
            for name, value, role in _declarations(_block(css, ":root"))]


_COMPONENT = re.compile(r"/\*\s*@component\s+(\S+)\s+(.*?)\*/", re.S)


def parse_components(css: str) -> List[Dict[str, str]]:
    """Each '@component <class> <doc>' comment of kit.css."""
    return [{"class": cls, "doc": " ".join(doc.split())} for cls, doc in _COMPONENT.findall(css)]


_EXPORT = re.compile(r"^export\s+(function|const)\s+([A-Za-z_$][\w$]*)", re.M)


def _balanced(text: str, start: int) -> int:
    """Index just past the parenthesis that closes the one at text[start], skipping quoted strings."""
    depth, i, quote = 0, start, None
    while i < len(text):
        c = text[i]
        if quote:
            if c == "\\":
                i += 1
            elif c == quote:
                quote = None
        elif c in "\"'`":
            quote = c
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    raise ValueError("unbalanced parentheses")


def parse_exports(js: str, file: str) -> List[Dict[str, str]]:
    """Every export of a kit script: name, signature, the one-line comment right above it, kind and file."""
    out = []
    for match in _EXPORT.finditer(js):
        kind, name = match.groups()
        before = js[:match.start()].rstrip("\n").split("\n")[-1].strip()
        doc = before[2:].strip() if before.startswith("//") and not before.startswith("// ----") else ""
        rest = js[match.end():]
        signature, what = name, "constant"
        if kind == "function":
            open_at = rest.index("(")
            signature, what = name + rest[open_at:_balanced(rest, open_at)], "function"
        else:
            value = rest.lstrip()[1:].lstrip()  # past "="
            if value.startswith("("):
                close = _balanced(value, 0)
                if value[close:].lstrip().startswith("=>"):
                    signature, what = name + value[:close], "function"
        out.append({"name": name, "signature": " ".join(signature.split()), "doc": doc, "kind": what, "file": file})
    return out


def manifest(src: Path = WEB) -> Dict[str, Any]:
    """The kit as it is on disk under `src` (Health AIO's web folder): files with hashes, tokens, components, charts."""
    src = Path(src)
    files = []
    for path, role in FILES:
        data = (src / path).read_bytes()
        files.append({"path": path, "role": role, "sha256": _sha256(data), "bytes": len(data)})
    text = {path: (src / path).read_text(encoding="utf-8") for path, _ in FILES}
    return {
        "name": NAME,
        "version": KIT_VERSION,
        "files": files,
        "tokens": parse_tokens(text["css/tokens.css"]),
        "components": parse_components(text["css/kit.css"]),
        "charts": parse_exports(text["js/charts.js"], "js/charts.js") + parse_exports(text["js/icons.js"], "js/icons.js"),
    }


def to_json(data: Dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


# ---- export and check ------------------------------------------------------------------------------------

def check(dest: Path, src: Path = WEB) -> Tuple[Dict[str, Any], List[Dict[str, str]]]:
    """Compare the copy in `dest` with its own kit.json (what was exported) and with the kit in `src`.

    Returns (the recorded manifest, rows of {path, status, note}, some with a hint that replaces the status's usual
    one); status is one of UP_TO_DATE, OUTDATED, MODIFIED, MISSING. A file that differs from the hash recorded at
    export was changed locally: that change is worth porting back to Health AIO.
    """
    dest = Path(dest)
    recorded = read_recorded(dest)
    current = manifest(src)
    was = {f["path"]: f for f in recorded["files"]}
    now = {f["path"]: f for f in current["files"]}
    old_v, new_v = recorded.get("version", "?"), current["version"]
    # equal versions with different files: the kit was changed without a version bump (a test in Health AIO forbids it)
    versions = f"{old_v} → {new_v}" if old_v != new_v else f"still {new_v}: changed without a version bump"
    rows = []
    for path in list(now) + [p for p in was if p not in now]:
        target = dest / path
        rec, cur = was.get(path), now.get(path)
        if not target.is_file():
            rows.append({"path": path, "status": MISSING, "note": "not in this copy" if cur else "no longer part of the kit"})
            continue
        sha = _sha256(target.read_bytes())
        if rec is None:  # a file the kit gained after this copy was made, already put here by hand
            rows.append({"path": path, "status": UP_TO_DATE if sha == cur["sha256"] else OUTDATED,
                         "note": "" if sha == cur["sha256"] else f"not recorded at export ({versions})"})
        elif sha != rec["sha256"]:
            note = "differs from the copy exported"
            if cur is not None and cur["sha256"] != rec["sha256"]:
                note += f"; the kit has also changed since ({versions})"
            rows.append({"path": path, "status": MODIFIED, "note": note})
        elif cur is None:
            rows.append({"path": path, "status": OUTDATED, "note": "no longer part of the kit"})
        elif rec["sha256"] != cur["sha256"]:
            rows.append({"path": path, "status": OUTDATED, "note": f"the kit changed since this copy was exported ({versions})"})
        else:
            rows.append({"path": path, "status": UP_TO_DATE, "note": ""})
    for path in recorded.get(LEFT, []):
        if path not in now and path not in was and (dest / path).is_file():
            rows.append({"path": path, "status": OUTDATED, "hint": "", "note": "no longer part of the kit; export left it "
                         "in place because it was changed locally: delete it once nothing loads it"})
    if all(r["status"] == UP_TO_DATE for r in rows) and {k: v for k, v in recorded.items() if k != LEFT} != current:
        rows.append({"path": MANIFEST, "status": OUTDATED, "note": f"the manifest changed ({versions})"})
    return recorded, rows


def read_recorded(dest: Path) -> Dict[str, Any]:
    """The kit.json in `dest`, checked to be one that export wrote; a KitError says how to recover otherwise."""
    file = Path(dest) / MANIFEST
    rewrite = f"run `{prog()} kit export {dest} --force` to rewrite it (and the kit files)"
    try:
        recorded = json.loads(file.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise KitError(f"{dest} has no {MANIFEST}: copy the kit there first with `{prog()} kit export {dest}`")
    except ValueError as error:
        raise KitError(f"{file} is not readable JSON ({error}); {rewrite}")
    files = recorded.get("files") if isinstance(recorded, dict) else None
    left = recorded.get(LEFT, []) if isinstance(recorded, dict) else None
    if not (isinstance(files, list) and all(isinstance(f, dict) and isinstance(f.get("path"), str)
                                            and isinstance(f.get("sha256"), str) for f in files)
            and isinstance(left, list) and all(isinstance(x, str) for x in left)):
        raise KitError(f"{file} is not a {MANIFEST} written by `export`; {rewrite}")
    return recorded


def export(dest: Path, src: Path = WEB, force: bool = False, notes: Optional[List[str]] = None) -> List[str]:
    """Copy the kit files into `dest` (keeping css/... and js/...), write dest/kit.json and return the paths written.

    Refuses, unless `force`, to overwrite a copy whose files were changed locally (port those changes back first),
    a kit.json that export did not write, or a file of the same name that no export put there. A file an earlier
    export wrote that the kit no longer has is removed when untouched and left in place, on record in kit.json,
    when it was changed; `notes` gets a line for each.
    """
    dest = Path(dest)
    data = manifest(src)
    recorded: Optional[Dict[str, Any]] = None
    if (dest / MANIFEST).is_file():
        try:
            recorded = read_recorded(dest)
        except KitError:
            if not force:
                raise
        if recorded is not None and not force:
            _, rows = check(dest, src)
            changed = [r["path"] for r in rows if r["status"] == MODIFIED]
            if changed:
                raise KitError(f"{', '.join(changed)} in {dest} changed since the last export; port the change back to "
                               "Health AIO first, or pass --force to overwrite it (a file the kit no longer has is left in place)")
    if not force:
        # never overwrite a file of the same name that no export put there (a first export, or a file the kit gained)
        known = {f["path"] for f in recorded["files"]} if recorded is not None else set()
        foreign = [f["path"] for f in data["files"] if f["path"] not in known and (dest / f["path"]).is_file()
                   and _sha256((dest / f["path"]).read_bytes()) != f["sha256"]]
        if foreign:
            what = ("already exists and is not this kit's file; move it", "already exist and are not this kit's files; move them")
            raise KitError(f"{', '.join(str(dest / p) for p in foreign)} {what[len(foreign) > 1]} away or pass --force "
                           "to overwrite")
    written = []
    for path, _ in FILES:
        target = dest / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(Path(src) / path, target)
        written.append(path)
    # files an earlier export wrote that the kit no longer has: removed when untouched, left (and kept on record) when not
    kit_paths = {path for path, _ in FILES}
    removed, left = [], []
    if recorded is not None:
        for f in recorded["files"]:
            target = dest / f["path"]
            if f["path"] in kit_paths or not target.is_file():
                continue
            if _sha256(target.read_bytes()) == f["sha256"]:
                target.unlink()
                removed.append(f["path"])
            else:
                left.append(f["path"])
        left += [p for p in recorded.get(LEFT, []) if p not in kit_paths and p not in left and (dest / p).is_file()]
    if left:
        data = {**data, LEFT: left}
    (dest / MANIFEST).write_text(to_json(data), encoding="utf-8")
    if notes is not None:
        notes += [f"removed {dest / p} (no longer part of the kit)" for p in removed]
        notes += [f"left {dest / p} in place (no longer part of the kit, changed locally): delete it once nothing loads it" for p in left]
    return written + [MANIFEST]


# ---- the version lock ------------------------------------------------------------------------------------

def lock_data(src: Path = WEB, version: str = KIT_VERSION) -> Dict[str, Any]:
    """What kit.lock.json holds: the version and the SHA-256 of each kit file."""
    return {"version": version, "files": {path: _sha256((Path(src) / path).read_bytes()) for path, _ in FILES}}


def read_lock(path: Path = LOCK) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return None


def lock_problem(src: Path = WEB, path: Path = LOCK, version: str = KIT_VERSION) -> Optional[str]:
    """Why kit.lock.json does not fit the kit files and KIT_VERSION, or None when it does."""
    locked, now = read_lock(path), lock_data(src, version)
    if locked == now:
        return None
    if not locked or not isinstance(locked.get("files"), dict) or not isinstance(locked.get("version"), str):
        return f"{Path(path).name} is missing or unreadable: run `{prog()} kit lock`"
    if locked["version"] == version:
        changed = sorted(set(now["files"]) ^ set(locked["files"]) | {p for p in now["files"] if locked["files"].get(p) != now["files"][p]})
        return (f"{', '.join(changed)} changed but KIT_VERSION is still {version}: bump KIT_VERSION in healthaio/kit.py, "
                f"add its row to the version table in docs/DESIGN_KIT.md (both halves), then run `{prog()} kit lock`")
    if _semver(version) <= _semver(locked["version"]):
        return f"KIT_VERSION {version} is not newer than {locked['version']} in {Path(path).name}"
    return f"KIT_VERSION is {version} but {Path(path).name} still records {locked['version']}: run `{prog()} kit lock`"


def write_lock(src: Path = WEB, path: Path = LOCK, version: str = KIT_VERSION) -> bool:
    """Record the current files under `version`; False when the lock is already current. Refuses a lock that
    would give changed files the version they already had."""
    problem = lock_problem(src, path, version)
    if problem is None:
        return False
    locked = read_lock(path)
    if locked and isinstance(locked.get("version"), str) and isinstance(locked.get("files"), dict) \
            and _semver(version) <= _semver(locked["version"]):
        raise KitError(problem)
    Path(path).write_text(json.dumps(lock_data(src, version), indent=2) + "\n", encoding="utf-8")
    return True


# ---- command line ----------------------------------------------------------------------------------------

HINT = {
    MODIFIED: "port the change back to Health AIO if it is worth keeping, then export again",
    OUTDATED: "run `{prog} kit export {dir}`",
    MISSING: "run `{prog} kit export {dir}`",
}


def run(args) -> int:
    """`healthaio kit json | export DIR | check DIR | lock`; check exits 0 only when every file is up to date."""
    if args.kit_command == "json":
        print(to_json(manifest()), end="")
        return 0
    try:
        if args.kit_command == "lock":
            changed = write_lock()
            print(f"{LOCK.name}: {'recorded' if changed else 'already records'} {NAME} {KIT_VERSION}")
            return 0
        if args.kit_command == "export":
            notes: List[str] = []
            for path in export(Path(args.dir), force=args.force, notes=notes):
                print(f"wrote {Path(args.dir) / path}")
            for line in notes:
                print(line)
            print(f"{NAME} {KIT_VERSION} exported to {args.dir}. Keep your own components in your own files and run "
                  f"`{prog()} kit check {args.dir}` after each Health AIO update.")
            return 0
        recorded, rows = check(Path(args.dir))
    except KitError as error:
        print(f"healthaio kit: {error}")
        return 1
    print(f"{NAME} in {args.dir}: exported {recorded.get('version', '?')}, current {KIT_VERSION}")
    width = max(len(r["status"]) for r in rows)
    for r in rows:
        hint = r["hint"] if "hint" in r else HINT.get(r["status"], "").format(dir=args.dir, prog=prog())
        tail = " — ".join(x for x in (r["note"], hint) if x)
        print(f"  {r['status']:<{width}}  {r['path']}{f'  ({tail})' if tail else ''}")
    return 0 if all(r["status"] == UP_TO_DATE for r in rows) else 1
