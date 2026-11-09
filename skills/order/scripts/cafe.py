#!/usr/bin/env python3
"""The cafe's cupping notes and verdict, used by the order skill.

  cafe.py add <notes> <round> <event> [-s P0|P1|P2] [-t yes|no] <note>
  cafe.py add-rows <notes>   rows on stdin, one per line, each written as add's arguments after <notes>.
                             All rows are written or none, so a fixed batch can be rerun as a whole.
                             A batch that is already the last rows of the notes (a retry after a cut)
                             writes nothing, so a round is never logged twice.
  cafe.py check <notes> [--max-rounds N]
  cafe.py fingerprint save <record> [<path>...]
                             records the content hash of every file the project lists (git's tracked and
                             untracked files that are not ignored, or every file without git), plus each path
                             (a nested repository by its own git, a folder by every file in it, a missing path
                             as absent); .git and .cafe are left out. Names nested repositories with changes
                             it left out.
  cafe.py fingerprint check <record>
                             "same" (exit 0) or "changed" with each path (exit 1) against the record,
                             "no record" (exit 2) without one. Content, not git: a commit changes nothing.
  cafe.py version            prints "cafe v<version>" from the cafe plugin.json beside the real script,
                             or "cafe v?" without one. Progress lines start with it.
  cafe.py self-test

events
  size    the size of the order: S, M, or L as the note. It sets the cuppers per round,
          the clean rounds needed, and the round limit. It can go up later, never down.
          Notes without a size row are judged as L, and check says so.
  cup     one cupper finished. -t yes means that cupper actually ran something (tasted it).
  defect  a finding kept on evidence. -s gives its severity.
  drop    a finding dropped (no evidence, outside the recipe, taste, duplicate).
  recipe  recipe.md changed. Clean rounds up to this round no longer count.
  rebrew  the design was rechecked after a REBREW verdict. Stall detection restarts here.

sizes   cuppers a round / clean rounds in a row to serve / round limit
  S       1 / 1 / 3
  M       2 / 1 / 4
  L       3 / 2 / 5

verdicts
  SERVE   enough clean rounds in a row after the last recipe change. Serve it.
  CLOSE   the round limit is reached. Close and report that it did not converge.
          check lists the P0/P1 notes from the last round a cupper tasted onward:
          the open defects a next order carries.
  REBREW  P0/P1 defects did not go down for two rounds in a row. Stop patching and recheck the design.
  RECUP   run another round.

A clean round has the size's cuppers, at least 1 cupper that ran something, and no P0/P1 defects.
Exit code: 0 for SERVE, 1 for any other verdict, 2 for a bad notes file.
"""
import argparse
import errno
import hashlib
import json
import locale
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import unicodedata

try:
    import fcntl
except ImportError:  # Windows
    fcntl = None
try:
    import msvcrt
except ImportError:
    msvcrt = None

HEADER = ["round", "event", "severity", "tasted", "note"]
EVENTS = ("size", "cup", "defect", "drop", "recipe", "rebrew")
ROUND_EVENTS = ("cup", "defect", "drop")
SEVERITIES = ("P0", "P1", "P2")
SERIOUS = ("P0", "P1")
SIZES = {
    "S": {"cuppers": 1, "streak": 1, "max_rounds": 3},
    "M": {"cuppers": 2, "streak": 1, "max_rounds": 4},
    "L": {"cuppers": 3, "streak": 2, "max_rounds": 5},
}
SIZE_ORDER = "SML"
DEFAULT_SIZE = "L"


class NotesError(Exception):
    pass


def validate(rnd, event, severity, tasted, note=None):
    if event not in EVENTS:
        raise NotesError(f"event must be one of {', '.join(EVENTS)}: {event!r}")
    if rnd < 0:
        raise NotesError(f"round must be 0 or more: {rnd}")
    if event in ROUND_EVENTS and rnd < 1:
        raise NotesError(f"{event} starts at round 1")
    if event == "size" and note is not None and note not in SIZES:
        raise NotesError(f"size needs S, M, or L as the note: {note!r}")
    if event == "defect":
        if severity not in SEVERITIES:
            raise NotesError(f"defect needs -s {'|'.join(SEVERITIES)}: {severity!r}")
    elif severity != "-":
        raise NotesError(f"only defect takes a severity: {event} -s {severity}")
    if event == "cup":
        if tasted not in ("yes", "no"):
            raise NotesError(f"cup needs -t yes|no: {tasted!r}")
    elif tasted != "-":
        raise NotesError(f"only cup takes -t: {event} -t {tasted}")


def read_notes(path):
    if not os.path.exists(path):
        return []
    rows = []
    with open(path, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            line = line.rstrip("\n")
            if not line.strip():
                continue
            cells = line.split("\t")
            if n == 1:
                if cells != HEADER:
                    raise NotesError(f"{path}:1 wrong header. Expected: {' '.join(HEADER)}")
                continue
            if len(cells) != len(HEADER):
                raise NotesError(f"{path}:{n} has {len(cells)} cells. It needs {len(HEADER)} cells split by tabs. Write rows with 'cafe.py add'")
            rnd, event, severity, tasted, note = cells
            try:
                rnd = int(rnd)
            except ValueError:
                raise NotesError(f"{path}:{n} round is not a number: {rnd!r}")
            try:
                validate(rnd, event, severity, tasted, note)
            except NotesError as e:
                raise NotesError(f"{path}:{n} {e}")
            rows.append((rnd, event, severity, tasted, note))
    return rows


def make_row(rnd, event, severity, tasted, note):
    note = " ".join(note.split())
    if event == "size":
        note = note.upper()
    if not note:
        raise NotesError("note is empty. Say in one line what happened")
    validate(rnd, event, severity, tasted, note)
    return (rnd, event, severity, tasted, note)


def append(path, rows):
    last = max((r for r, e, *_ in read_notes(path) if e in ROUND_EVENTS), default=0)
    for rnd, event, *_ in rows:
        if rnd > last + 1:
            raise NotesError(f"round {rnd} skips rounds: the last cupping round is {last}")
        if event in ROUND_EVENTS:
            last = max(last, rnd)
    new = not os.path.exists(path) or os.path.getsize(path) == 0
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    text = "".join("\t".join(str(c) for c in row) + "\n" for row in rows)
    with open(path, "a", encoding="utf-8") as f:
        f.write(("\t".join(HEADER) + "\n" if new else "") + text)


def add(path, rnd, event, severity, tasted, note):
    append(path, [make_row(rnd, event, severity, tasted, note)])


class RowParser(argparse.ArgumentParser):
    def error(self, message):
        raise NotesError(message)


def row_args(p):
    p.add_argument("round", type=int)
    p.add_argument("event", choices=EVENTS)
    p.add_argument("note")
    p.add_argument("-s", "--severity", default="-")
    p.add_argument("-t", "--tasted", default="-")


def add_rows(path, lines):
    parser = RowParser(prog="row", add_help=False)
    row_args(parser)
    rows = []
    for n, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            a = parser.parse_args(shlex.split(line))
            rows.append(make_row(a.round, a.event, a.severity, a.tasted, a.note))
        except (NotesError, ValueError) as e:
            raise NotesError(f"row {n} ({line.strip()}): {e}. Nothing was written")
    if not rows:
        raise NotesError("no rows on stdin. Write one row per line")
    try:
        written = read_notes(path)
        if written[-len(rows):] == rows:  # a retry of a batch that went in: a second copy would count cuppers twice
            return False
        append(path, rows)
    except NotesError as e:
        raise NotesError(f"{e}. Nothing was written")
    return True


def decode_rows(data, fallback):
    """Rows on stdin: UTF-8 (a BOM allowed), as agents send them, else the console's own code page."""
    for encoding in ("utf-8-sig", fallback):
        try:
            return data.decode(encoding).splitlines()
        except (UnicodeDecodeError, LookupError, TypeError):
            continue
    raise NotesError("stdin is neither UTF-8 nor the console's encoding. Nothing was written")


def order_size(rows):
    sizes = [note for _, e, _, _, note in rows if e == "size"]
    if not sizes:
        return DEFAULT_SIZE
    return max(sizes, key=SIZE_ORDER.index)


def judge(rows, max_rounds=None, notes="<notes>"):
    size = order_size(rows)
    rule = SIZES[size]
    min_cuppers = rule["cuppers"]
    clean_streak = rule["streak"]
    if max_rounds is None:
        max_rounds = rule["max_rounds"]
    head = [f"size {size}: {min_cuppers} cupper(s) a round, {clean_streak} clean round(s) in a row to serve, "
            f"{max_rounds} round limit"]
    if not any(e == "size" for _, e, *_ in rows):
        head.append(f"no size row in {notes}, so judged as L. Log the size the recipe picked: "
                    f"cafe.py add {shlex.quote(notes)} 0 size S|M|L")

    rounds = sorted({r for r, e, *_ in rows if e in ROUND_EVENTS})
    if not rounds:
        return "RECUP", head + ["no cupping rounds yet", f"next: round 1 with {min_cuppers} cupper(s)"]
    last = rounds[-1]
    missing = [r for r in range(1, last + 1) if r not in rounds]
    if missing:
        raise NotesError(f"missing rounds: {missing}")

    stat = {r: {"cuppers": 0, "tasted": 0, "serious": 0} for r in rounds}
    last_recipe = 0
    last_rebrew = 0
    for r, e, s, tasted, _ in rows:
        if e == "cup":
            stat[r]["cuppers"] += 1
            stat[r]["tasted"] += tasted == "yes"
        elif e == "defect" and s in SERIOUS:
            stat[r]["serious"] += 1
        elif e == "recipe":
            last_recipe = max(last_recipe, r)
        elif e == "rebrew":
            last_rebrew = max(last_rebrew, r)

    def problems(r):
        st = stat[r]
        out = []
        if st["cuppers"] < min_cuppers:
            out.append(f"{st['cuppers']} cuppers ({min_cuppers} needed)")
        if st["tasted"] == 0:
            out.append("no cupper ran anything")
        if st["serious"]:
            out.append(f"{st['serious']} P0/P1 defects")
        if r <= last_recipe:
            out.append(f"before the round {last_recipe} recipe change")
        return out

    reasons = list(head)
    for r in rounds:
        p = problems(r)
        reasons.append(f"R{r}: " + ("clean" if not p else ", ".join(p)))

    streak = 0
    for r in reversed(rounds):
        if problems(r):
            break
        streak += 1
    reasons.append(f"clean rounds in a row: {streak}/{clean_streak}")

    if streak >= clean_streak:
        return "SERVE", reasons
    if last >= max_rounds:
        reasons.append(f"reached the {max_rounds} round limit")
        tasted = [r for r in rounds if stat[r]["tasted"]]
        since = tasted[-1] if tasted else rounds[0]  # a fix nobody tasted since is still open
        still = [f"open {s}: {note}" for r, e, s, _, note in rows if r >= since and e == "defect" and s in SERIOUS]
        reasons += list(dict.fromkeys(still)) or ["open P0/P1: none"]
        return "CLOSE", reasons
    nxt = f"next: round {last + 1} with {min_cuppers} cupper(s)"
    window = [stat[r]["serious"] for r in rounds if r > last_rebrew]
    if len(window) >= 3:
        a, b, c = window[-3:]
        if a > 0 and b >= a and c >= b:
            reasons += [f"P0/P1 defects are not going down: {a} -> {b} -> {c}", nxt]
            return "REBREW", reasons
    reasons.append(nxt)
    return "RECUP", reasons


SKIP_DIRS = (".git", ".cafe")


def digest(path):
    if os.path.islink(path):  # a link's own content is where it points
        try:
            return "link " + os.readlink(path)
        except OSError:
            return "link"
    if not os.path.isfile(path):  # a FIFO or device would block open
        return "not a file"
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for block in iter(lambda: f.read(1 << 20), b""):
                h.update(block)
    except OSError:
        try:
            st = os.stat(path)  # unreadable: its size and time still change when it is edited
        except OSError:
            return "unreadable"
        return f"unreadable {st.st_size} {st.st_mtime_ns}"
    try:
        executable = os.stat(path).st_mode & 0o111 and " x" or ""  # git tracks the executable bit as a change too
    except OSError:  # removed right after it was read
        return "unreadable"
    return h.hexdigest() + executable


# Repository locations a caller may export (a hook, GIT_DIR=...): each git call here names its own folder instead.
GIT_PLACES = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES",
              "GIT_COMMON_DIR", "GIT_NAMESPACE", "GIT_PREFIX")


def git_env():
    return {k: v for k, v in os.environ.items() if k not in GIT_PLACES}


def git_list(folder, *args):
    """git's names in a folder, split on NUL: with -z git quotes no name (by default it prints a non-ASCII name
    as "\\355\\225..."). Decoded as the file system names them. None where git cannot list here."""
    try:
        # -c reaches the gits this one starts (a submodule's status), where a flag would not: the user's own config
        # must not hide a new file or a submodule's changes there
        done = subprocess.run(["git", "--no-optional-locks", "-C", folder, "-c", "core.quotepath=off",
                               "-c", "status.showUntrackedFiles=normal", "-c", "diff.ignoreSubmodules=none", *args],
                              capture_output=True, env=git_env())  # no index refresh written into the user's repositories
    except OSError:
        return None
    if done.returncode:
        return None
    return [os.fsdecode(p) for p in done.stdout.split(b"\0") if p]


def own_repository(folder):
    return not os.path.islink(folder) and os.path.isdir(folder) and os.path.lexists(os.path.join(folder, ".git"))


def walk(folder):
    for top, dirs, names in os.walk(folder):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        yield from (os.path.join(top, n) for n in names)


def project_files(folder, repos):
    """Every file git lists in folder (tracked, and untracked but not ignored), or every file without git.
    A nested repository git shows as a folder (untracked, or a submodule) is listed by its own git. Each
    repository listed goes into repos, so its own ignored nested repositories can be named."""
    names = git_list(folder, "ls-files", "-z", "-c", "-o", "--exclude-standard")
    if not names:  # no git, or a project inside a folder its parent repository ignores: git lists nothing
        yield from walk(folder)
        return
    repos.append(folder)
    for name in names:
        path = os.path.join(folder, name.rstrip("/"))
        if own_repository(path):
            yield from project_files(path, repos)
        else:
            yield path


def key(path):
    return os.path.normpath(path).replace(os.sep, "/")


def nfc(name):
    """One form for comparing names: git on macOS prints NFC, while the disk keeps NFD where Finder wrote it."""
    return unicodedata.normalize("NFC", name)


def served_files(paths, skip=(), repos=None):
    """Every file the project lists, then each given path: a nested repository by its own git, another folder by
    every file under it, a missing path as None. Keyed by path with / separators; .git, .cafe, and skip left out."""
    repos = [] if repos is None else repos
    skip = {nfc(s) for s in skip}
    files = {}
    for path in ["."] + list(paths):
        if path == "." or (os.path.isdir(path) and os.path.lexists(os.path.join(path, ".git"))):  # a link to one too
            found = project_files(path, repos)
        elif os.path.isdir(path):
            found = walk(path)
        elif not os.path.lexists(path):
            if not set(key(path).split("/")) & set(SKIP_DIRS) and nfc(key(path)) not in skip:
                files.setdefault(nfc(key(path)), None)
            continue
        else:
            found = [path]
        for f in found:
            k = nfc(key(f))  # one key for a file git lists in NFC and a passed folder's walk finds in NFD
            if not set(k.split("/")) & set(SKIP_DIRS) and k not in skip and os.path.basename(k) != LOCK_NAME:
                files[k] = digest(f) if os.path.lexists(f) else files.get(k)  # tracked but deleted: absent
    return files


# Folders of dependencies and builds hold other people's repositories, never a tasted file.
DEPENDENCY_DIRS = {"node_modules", "bower_components", "vendor", ".venv", "venv", "__pycache__", ".tox", ".gradle",
                   ".next", ".nuxt", ".cache", "build", "dist", "target", "Pods", "DerivedData", ".godot"}


def repositories_below(folder, depth=3):
    """Repositories under an ignored folder that is not one itself, down to depth levels."""
    if depth == 0 or os.path.basename(folder) in DEPENDENCY_DIRS:
        return
    try:
        entries = sorted(os.scandir(folder), key=lambda e: e.name)
    except OSError:
        return
    for e in entries:
        if e.is_dir(follow_symlinks=False) and e.name not in SKIP_DIRS:
            if own_repository(e.path):
                yield e.path
            else:
                yield from repositories_below(e.path, depth - 1)


def nested_with_changes(given, repos, walked=()):
    """Nested repositories that a listed repository ignores, that hold uncommitted changes, and that were not given.
    git folds an ignored folder into one entry (repos/), so a folder that is not a repository is searched below."""
    given, walked = {nfc(g) for g in given}, {nfc(g) for g in walked}  # given as the disk spells it, k as git prints it

    def covered(k):  # given as the repository itself, or under a plain folder walked whole. A path inside it records
        # only that path, and a given repository's own git leaves out the repositories it ignores: neither covers k
        k = nfc(k)
        return any(g == k or (k.startswith(g + "/") and g in walked) for g in given)

    out, seen, todo = [], set(), list(repos)
    while todo:
        repo = todo.pop(0)
        for name in git_list(repo, "ls-files", "-z", "-o", "-i", "--exclude-standard", "--directory") or []:
            top = os.path.join(repo, name.rstrip("/"))
            if not name.endswith("/") or os.path.basename(top) in DEPENDENCY_DIRS:
                continue
            for found in [top] if own_repository(top) else repositories_below(top):
                k = key(found)
                if nfc(k) in seen:
                    continue
                seen.add(nfc(k))
                todo.append(found)  # its own ignored repositories too
                if covered(k):
                    continue
                # whatever the config hides: untracked files, and a submodule's changes (ignore = dirty or all)
                status = git_list(found, "status", "--porcelain", "-z", "--untracked-files=normal",
                                  "--ignore-submodules=none")
                if status != []:  # changes, or a status git could not give (a broken submodule): either may hide one
                    out.append(k)
    return out


def real(path):
    """An absolute path whose folders have no symlink (macOS /tmp is /private/tmp), keeping the last name as given."""
    path = os.path.abspath(path)
    return os.path.join(os.path.realpath(os.path.dirname(path)), os.path.basename(path))


def true_case(folder, names):
    """names as the disk spells them (macOS matches SVC to svc), each kept as typed when no entry matches."""
    out = []
    for name in names:
        try:
            entries = os.listdir(folder)
        except OSError:
            entries = []
        if name not in entries:
            fold = unicodedata.normalize("NFC", name).lower()  # Finder writes NFD, a typed name is NFC
            same = [e for e in entries if unicodedata.normalize("NFC", e).lower() == fold]
            try:
                name = next(e for e in same if os.path.samefile(os.path.join(folder, e), os.path.join(folder, name)))
            except (StopIteration, OSError):
                pass
        out.append(name)
        folder = os.path.join(folder, name)
    return out


def relative(path, root):
    """path relative to root, found by the folders' identity, so letter case (macOS) and links give one name."""
    path = real(path)
    rest, here = [], path
    while True:
        try:
            if os.path.samefile(here, root):
                return key(os.path.join(*true_case(root, list(reversed(rest))))) if rest else "."
        except OSError:
            pass
        parent = os.path.dirname(here)
        if parent == here:
            return key(os.path.relpath(path, root))
        rest.append(os.path.basename(here))
        here = parent


def outside_root(record):
    """The record's folder must already exist: run from another folder, the project-root path names a new one."""
    folder = os.path.dirname(os.path.abspath(record))
    if not os.path.isdir(folder):
        raise NotesError(f"{folder} does not exist: cafe.py ran outside the project root, or the order folder's name "
                         f"is wrong, so {record} names the wrong folder. Run it again from the project root")


def project_of(record):
    """The project a record belongs to: the folder holding the .cafe it sits in (so check works from any folder,
    and the record moves with the project), else the folder save or check runs from."""
    parts = os.path.abspath(record).split(os.sep)  # before links are resolved: .cafe itself may be a link
    if ".cafe" in parts[:-1]:
        i = len(parts) - 1 - parts[::-1].index(".cafe")
        return os.path.realpath(os.sep.join(parts[:i]) or os.sep)
    try:
        return os.path.realpath(os.getcwd())
    except FileNotFoundError:
        raise NotesError("the folder cafe.py ran from was deleted. Run it again from the project root")


class InFolder:
    def __init__(self, folder):
        try:
            self.back = os.getcwd()
        except FileNotFoundError:  # the folder it ran from was deleted: nothing to go back to
            self.back = None
        self.folder = folder

    def __enter__(self):
        os.chdir(self.folder)

    def __exit__(self, *exc):
        if self.back is not None:
            os.chdir(self.back)


LOCK_SECONDS = 60  # under the 120-second limit hosts often put on one tool call, so the error shows
LOCK_NAME = ".cafe-fingerprint.lock"  # one per folder: no project file has this name, and it adds no length to a name


class RecordLock:
    """One save of a record at a time: a save merges the paths the record has, so two at once (parallel tool calls)
    would drop one. The lock is LOCK_NAME beside the record, kept afterwards: a removed lock could be taken anew while
    another save still holds the old one. The wait is bounded (CAFE_LOCK_SECONDS), so a hung save ends in an error."""

    def __init__(self, record):
        self.path = os.path.join(os.path.dirname(record), LOCK_NAME)
        self.fd = None

    def held_elsewhere(self):
        try:
            if fcntl is not None:
                fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            elif msvcrt is not None:
                os.lseek(self.fd, 0, os.SEEK_SET)
                msvcrt.locking(self.fd, msvcrt.LK_NBLCK, 1)
        except BlockingIOError:
            return True
        except OSError as e:
            if fcntl is None and e.errno in (errno.EACCES, errno.EDEADLK):  # msvcrt: locked by another save
                return True
            return False  # a file system without locks: save as before
        return False

    @staticmethod
    def seconds():
        try:
            seconds = float(os.environ.get("CAFE_LOCK_SECONDS", LOCK_SECONDS))
        except ValueError:
            return LOCK_SECONDS
        return seconds if 0 <= seconds <= 3600 else LOCK_SECONDS  # nan, inf, or below 0 would never end the wait

    def __enter__(self):
        seconds = self.seconds()
        try:
            self.fd = os.open(self.path, os.O_RDONLY | os.O_CREAT, 0o644)  # read is enough to lock: a lock another
            # user left read-only still works
        except OSError as e:
            raise NotesError(f"cannot save: cannot open the lock {self.path}: {e}. Nothing was saved")
        end = time.monotonic() + seconds
        while self.held_elsewhere():
            if time.monotonic() >= end:
                os.close(self.fd)
                raise NotesError(f"this save waited {seconds:g} seconds for another save that holds {self.path}. "
                                 "Wait for that one to end, or stop it, and save again. Nothing was saved")
            time.sleep(0.1)
        return self

    def __exit__(self, *exc):
        if fcntl is None and msvcrt is not None:
            try:
                os.lseek(self.fd, 0, os.SEEK_SET)
                msvcrt.locking(self.fd, msvcrt.LK_UNLCK, 1)
            except OSError:
                pass
        os.close(self.fd)  # closing it also releases flock


def own_files(record, root):
    """The record and its lock: neither is a file of the project, wherever the record sits."""
    return {relative(record, root), relative(os.path.join(os.path.dirname(record), LOCK_NAME), root)}


def fingerprint_save(record, paths):
    """Record every file the project lists and the given paths. Returns the number of files recorded, the paths
    recorded as absent (deleted, or a wrong name), and the nested repositories with changes left out."""
    record = os.path.normpath(record)  # cupping.tsv/ or a/../cupping.tsv is that file: the guard and the write see one path
    for p in paths:
        if len(p) > 1 and p[0] == p[-1] == '"' and not os.path.lexists(p):
            raise NotesError(f"{p} is not there and looks like a name git quoted. Give the name as the file system "
                             "has it (git -z prints it so). Nothing was saved")
    outside_root(record)
    root = project_of(record)
    paths = [relative(p.rstrip("/\\") or p, root) for p in paths]  # one name for each form
    saved_paths(record)  # refused before the lock, so a mixed-up argument leaves no <name>.lock beside a source
    with RecordLock(record):  # from reading the paths the record has to writing it
        return save_locked(record, saved_paths(record) + paths, root)  # saving again keeps the paths given before


def saved_paths(record):
    """The paths an existing record has, [] without one. Replace only a record: a mixed-up argument must not
    overwrite the notes or a source."""
    if not os.path.lexists(record):
        return []
    try:
        with open(record, encoding="utf-8") as f:
            old = json.load(f)
    except (OSError, ValueError, RecursionError):
        old = None
    if not (isinstance(old, dict) and old.get("cafe") == "fingerprint" and isinstance(old.get("paths"), list)):
        raise NotesError(f"{record} exists and is not a fingerprint record, so save will not replace it. "
                         "Give the record path, .cafe/<order>/served.json. Nothing was saved")
    return [p for p in old["paths"] if isinstance(p, str)]


def save_locked(record, paths, root):
    paths = list(dict.fromkeys(paths))
    record = real(record)
    repos = []
    with InFolder(root):
        files = served_files(paths, own_files(record, root), repos)
        walked = {p for p in paths if p != "." and os.path.isdir(p) and not os.path.lexists(os.path.join(p, ".git"))}
        nested = nested_with_changes(set(paths), repos, walked)
    data = {"cafe": "fingerprint", "version": 1, "paths": paths, "files": files}
    folder = os.path.dirname(record)
    try:
        os.makedirs(folder, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=folder, prefix=".fingerprint.")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=1, sort_keys=True)
            os.replace(tmp, record)  # whole or not at all: a cut leaves the old record or none
        except BaseException:
            os.unlink(tmp)
            raise
    except OSError as e:
        raise NotesError(f"cannot save {record}: {e}. Nothing was saved")
    return sum(v is not None for v in files.values()), [k for k, v in files.items() if v is None], nested


def fingerprint_check(record):
    """("same" | "changed" | "no record", lines): every file the project lists and the recorded paths, against the record."""
    record = os.path.normpath(record)
    if not os.path.exists(record):
        outside_root(record)
        return "no record", [f"nothing saved at {record}"]
    try:
        with open(record, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError, RecursionError) as e:
        raise NotesError(f"{record} is not a fingerprint record: {e!r}"[:300])
    if not isinstance(data, dict):
        data = {}
    paths, old = data.get("paths"), data.get("files")
    if (data.get("cafe") != "fingerprint" or not isinstance(paths, list)
            or not all(isinstance(p, str) for p in paths) or not isinstance(old, dict)):
        raise NotesError(f"{record} is not a fingerprint record: it needs paths and files")
    root = project_of(record)
    with InFolder(root):
        new = served_files(paths, own_files(record, root))
    lines = []
    for k in sorted(set(old) | set(new)):
        a, b = old.get(k), new.get(k)
        if a != b:
            lines.append(f"{'added' if a is None else 'removed' if b is None else 'changed'}: {k}")
    return ("changed" if lines else "same"), lines


def emit(lines):
    """Print lines. A reader that stops early (head) is no error, so the exit code stays the verdict's."""
    if sys.stdout is None:  # started with stdout closed: nothing to print to, and no reason to fail
        return
    try:
        for line in lines:
            print(line)
        sys.stdout.flush()
    except BrokenPipeError:
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())  # no second error when Python flushes at exit


def version(script=__file__):
    """The version in the cafe plugin.json at the root of the real skill folder, or "?" without one.
    plugin.json is the only place the version is written, so a progress line cannot show a stale one."""
    root = os.path.realpath(script)
    for _ in range(4):  # scripts/cafe.py -> order -> skills -> the repository or plugin root
        root = os.path.dirname(root)
    try:
        with open(os.path.join(root, ".claude-plugin", "plugin.json"), encoding="utf-8-sig") as f:
            manifest = json.load(f)
    except (OSError, ValueError):
        return "?"
    if not isinstance(manifest, dict) or manifest.get("name") != "cafe":
        return "?"
    found = manifest.get("version")
    return found.strip() if isinstance(found, str) and found.strip() else "?"


def self_test():
    def notes(*specs):
        return [s if len(s) == 5 else (*s, "t") for s in specs]

    def size(z, r=0):
        return (r, "size", "-", "-", z)

    def clean(r, n=3, tasted="yes"):
        return [(r, "cup", "-", tasted)] + [(r, "cup", "-", "no")] * (n - 1)

    def dirty(r, k, sev="P1", n=3):
        return clean(r, n) + [(r, "defect", sev, "-")] * k

    cases = [
        ("no notes", notes(), "RECUP"),
        ("two clean rounds after defects", notes(*dirty(1, 2), *clean(2), *clean(3)), "SERVE"),
        ("one clean round is not enough", notes(*dirty(1, 1), *clean(2)), "RECUP"),
        ("a recipe change breaks the streak", notes(*clean(1), *clean(2), (2, "recipe", "-", "-")), "RECUP"),
        ("two clean rounds after a recipe change", notes(*clean(1), (1, "recipe", "-", "-"), *clean(2), *clean(3)), "SERVE"),
        ("a recipe change before the next round", notes(*clean(1), *clean(2), (3, "recipe", "-", "-")), "RECUP"),
        ("the round with a recipe change does not count", notes(*clean(1), *clean(2), (2, "recipe", "-", "-"), *clean(3)), "RECUP"),
        ("cupping that ran nothing is not clean", notes(*clean(1, tasted="no"), *clean(2, tasted="no")), "RECUP"),
        ("two cuppers are not enough", notes(*clean(1, n=2), *clean(2, n=2)), "RECUP"),
        ("P2 does not block", notes(*dirty(1, 3, "P2"), *dirty(2, 1, "P2")), "SERVE"),
        ("five rounds without converging", notes(*dirty(1, 3), *dirty(2, 2), *dirty(3, 1), *clean(4), *dirty(5, 1)), "CLOSE"),
        ("converging on round five", notes(*dirty(1, 3), *dirty(2, 2), *dirty(3, 1), *clean(4), *clean(5)), "SERVE"),
        ("defects stall", notes(*dirty(1, 1), *dirty(2, 1), *dirty(3, 2)), "REBREW"),
        ("defects going down keep going", notes(*dirty(1, 3), *dirty(2, 3), *dirty(3, 1)), "RECUP"),
        ("stall count restarts after rebrew", notes(*dirty(1, 1), *dirty(2, 1), *dirty(3, 1), (3, "rebrew", "-", "-"), *dirty(4, 1)), "RECUP"),
        ("the rebrew round is left out of the stall count", notes(*dirty(1, 1), *dirty(2, 1), (2, "rebrew", "-", "-"), *dirty(3, 1), *dirty(4, 1)), "RECUP"),
        ("zero defects in a row is not a stall", notes(*clean(1, tasted="no"), *clean(2, tasted="no"), *clean(3, tasted="no")), "RECUP"),
        ("a first defect after rounds with none is not a stall", notes(*clean(1, tasted="no"), *clean(2, tasted="no"), *dirty(3, 1)), "RECUP"),
        ("no size row is judged as L", notes(*clean(1, n=1)), "RECUP"),
        ("S serves on one clean round of one cupper", notes(size("S"), *clean(1, n=1)), "SERVE"),
        ("S serves after a fix and one clean round", notes(size("S"), *dirty(1, 2, n=1), *clean(2, n=1)), "SERVE"),
        ("S needs a cupper that ran something", notes(size("S"), *clean(1, n=1, tasted="no")), "RECUP"),
        ("S closes at three rounds", notes(size("S"), *dirty(1, 1, n=1), *dirty(2, 1, n=1), *dirty(3, 1, n=1)), "CLOSE"),
        ("M needs two cuppers", notes(size("M"), *clean(1, n=1)), "RECUP"),
        ("M serves on one clean round of two", notes(size("M"), *dirty(1, 1, n=2), *clean(2, n=2)), "SERVE"),
        ("M closes at four rounds", notes(size("M"), *dirty(1, 3, n=2), *dirty(2, 2, n=2), *dirty(3, 1, n=2), *dirty(4, 1, n=2)), "CLOSE"),
        ("L still needs two clean rounds", notes(size("L"), *clean(1)), "RECUP"),
        ("size never goes down", notes(size("L"), size("S"), *clean(1, n=1)), "RECUP"),
        ("raising the size raises the bar", notes(size("S"), *dirty(1, 1, n=1), size("M", 1), *clean(2, n=1)), "RECUP"),
        ("S after a recipe change", notes(size("S"), *clean(1, n=1), (1, "recipe", "-", "-"), *clean(2, n=1)), "SERVE"),
    ]
    failed = 0
    for name, rows, want in cases:
        got, _ = judge(rows)
        ok = got == want
        failed += not ok
        print(f"{'ok  ' if ok else 'FAIL'} {name}: {got}" + ("" if ok else f" (expected {want})"))

    def warned(rows):
        return any("no size row" in line for line in judge(rows)[1])

    ok = warned(notes()) and warned(notes(*clean(1))) and not warned(notes(size("L"), *clean(1)))
    failed += not ok
    print(f"{'ok  ' if ok else 'FAIL'} check says when there is no size row")

    closing = [size("S"), (1, "cup", "-", "yes", "t"), (1, "defect", "P1", "-", "old bug"),
               (2, "cup", "-", "yes", "t"), (2, "defect", "P0", "-", "lost rows"), (2, "defect", "P1", "-", "empty page"),
               (2, "defect", "P2", "-", "typo"), (3, "cup", "-", "yes", "t"), (3, "defect", "P1", "-", "empty page"),
               (3, "defect", "P1", "-", "empty page")]
    got, lines = judge(closing)
    still = [line for line in lines if line.startswith("open ")]
    ok = got == "CLOSE" and still == ["open P1: empty page"]
    got2, lines2 = judge(notes(size("L"), *dirty(1, 1), *dirty(2, 1), *dirty(3, 2), *dirty(4, 1), *clean(5)))
    ok = ok and got2 == "CLOSE" and "open P0/P1: none" in lines2
    _, lines3 = judge(notes(size("S"), *dirty(1, 1, n=1)))
    ok = ok and not any(line.startswith("open ") for line in lines3)
    untasted = [size("S"), (1, "cup", "-", "yes", "t"), (1, "defect", "P1", "-", "first"),
                (2, "cup", "-", "yes", "t"), (2, "defect", "P1", "-", "fix untested"), (3, "cup", "-", "no", "t")]
    got4, lines4 = judge(untasted)
    ok = ok and got4 == "CLOSE" and [line for line in lines4 if line.startswith("open ")] == ["open P1: fix untested"]
    read_only = untasted + [(3, "defect", "P1", "-", "found by reading")]  # a later untasted round's finding is open too
    got5, lines5 = judge(read_only)
    ok = ok and got5 == "CLOSE" and [line for line in lines5 if line.startswith("open ")] == [
        "open P1: fix untested", "open P1: found by reading"]
    never = [size("S"), (1, "cup", "-", "no", "t"), (1, "defect", "P1", "-", "read only"),
             (2, "cup", "-", "no", "t"), (3, "cup", "-", "no", "t")]  # no round tasted: open from round 1
    got6, lines6 = judge(never)
    ok = ok and got6 == "CLOSE" and [line for line in lines6 if line.startswith("open ")] == ["open P1: read only"]
    failed += not ok
    print(f"{'ok  ' if ok else 'FAIL'} CLOSE lists only the last round's P0/P1: {still}")

    got, _ = judge(notes(size("S"), *dirty(1, 1, n=1), *dirty(2, 1, n=1)), max_rounds=2)
    ok = got == "CLOSE"
    failed += not ok
    print(f"{'ok  ' if ok else 'FAIL'} --max-rounds overrides the size: {got}")

    def expect_error(name, fn):
        nonlocal failed
        try:
            fn()
        except NotesError:
            print(f"ok   {name}: error")
            return
        failed += 1
        print(f"FAIL {name}: expected an error")

    ok = (decode_rows("1 drop '빈 페이지'\n".encode(), "cp1252") == ["1 drop '빈 페이지'"]
          and decode_rows(b"\xef\xbb\xbf1 drop x", "utf-8") == ["1 drop x"]
          and decode_rows(b"1 drop caf\xe9", "cp1252") == ["1 drop café"])
    failed += not ok
    print(f"{'ok  ' if ok else 'FAIL'} stdin rows: UTF-8, a BOM, or the console's code page")
    expect_error("stdin in no encoding it can read", lambda: decode_rows(b"1 drop \xff\xfe", "utf-8"))
    expect_error("missing round", lambda: judge(notes(*clean(1), *clean(3))))
    expect_error("defect without severity", lambda: validate(1, "defect", "-", "-"))
    expect_error("unknown severity", lambda: validate(1, "defect", "P9", "-"))
    expect_error("cup without tasted", lambda: validate(1, "cup", "-", "-"))
    expect_error("cup in round 0", lambda: validate(0, "cup", "-", "yes"))
    expect_error("severity on a cup", lambda: validate(1, "cup", "P1", "yes"))
    expect_error("tasted on a defect", lambda: validate(1, "defect", "P1", "yes"))
    expect_error("unknown size", lambda: validate(0, "size", "-", "-", "XL"))
    expect_error("severity on a size", lambda: validate(0, "size", "P1", "-", "S"))

    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "order", "cupping.tsv")
        add(path, 0, "size", "-", "-", " m ")
        add(path, 0, "recipe", "-", "-", "added criterion 3")
        for i in range(3):
            add(path, 1, "cup", "-", "yes" if i == 0 else "no", f"cupper\t{i}\nnewline")
        add(path, 1, "defect", "P1", "-", "crash on an empty order")
        rows = read_notes(path)
        ok = (len(rows) == 6 and rows[0][4] == "M" and rows[2][4] == "cupper 0 newline"
              and judge(rows)[0] == "RECUP" and order_size(rows) == "M")
        failed += not ok
        print(f"{'ok  ' if ok else 'FAIL'} write with add and read back")
        expect_error("a round that skips rounds", lambda: add(path, 3, "cup", "-", "yes", "typo"))
        skip = os.path.join(d, "skip.tsv")
        add(skip, 1, "cup", "-", "yes", "a x b")
        add(skip, 2, "recipe", "-", "-", "a recipe row may sit one round ahead")
        expect_error("a recipe row does not open a round to skip into", lambda: add(skip, 3, "cup", "-", "yes", "typo"))

        batch = ["2 cup -t yes 'Customer x Order sheet'", "", '2 defect -s P1 "it\'s empty"', "2 drop 'no evidence'"]
        before = open(path, encoding="utf-8").read()
        expect_error("a bad row in a batch", lambda: add_rows(path, batch[:2] + ["2 defect 'no severity'"] + batch[3:]))
        expect_error("an unclosed quote in a batch", lambda: add_rows(path, batch[:1] + ["2 drop 'open"]))
        expect_error("an empty batch", lambda: add_rows(path, ["", "  "]))
        ok = open(path, encoding="utf-8").read() == before
        failed += not ok
        print(f"{'ok  ' if ok else 'FAIL'} a rejected batch writes nothing")
        add_rows(path, batch)
        rows = read_notes(path)
        ok = len(rows) == 9 and rows[-2] == (2, "defect", "P1", "-", "it's empty") and judge(rows)[0] == "RECUP"
        failed += not ok
        print(f"{'ok  ' if ok else 'FAIL'} a fixed batch writes every row once")
        again = add_rows(path, [line.replace("Order sheet", "Order  sheet") for line in batch])
        ok = again is False and read_notes(path) == rows
        add_rows(path, ["2 drop 'another'"])
        ok = ok and len(read_notes(path)) == 10
        failed += not ok
        print(f"{'ok  ' if ok else 'FAIL'} a rerun of the last batch writes nothing; a new batch appends")

        tree = os.path.join(d, "served")
        os.makedirs(os.path.join(tree, "src", ".cafe"))
        os.makedirs(os.path.join(tree, ".cafe", "o"))  # the order's folder exists by SERVE
        for name, text in (("a.txt", "a"), ("src/b.txt", "b"), ("src/.cafe/x", "x")):
            with open(os.path.join(tree, name), "w", encoding="utf-8") as f:
                f.write(text)
        record = os.path.join(tree, ".cafe", "o", "served.json")
        here = os.getcwd()
        os.chdir(tree)
        try:
            saved = fingerprint_save(record, ["a.txt", "src", "gone.txt"])[0]
            states = [fingerprint_check(record)[0]]
            with open("src/b.txt", "w", encoding="utf-8") as f:
                f.write("b2")
            states.append(fingerprint_check(record))
            with open("src/b.txt", "w", encoding="utf-8") as f:
                f.write("b")
            with open("src/.cafe/y", "w", encoding="utf-8") as f:
                f.write("y")
            states.append(fingerprint_check(record)[0])
            with open("gone.txt", "w", encoding="utf-8") as f:
                f.write("g")
            states.append(fingerprint_check(record))
            states.append(fingerprint_check("none.json")[0])
        finally:
            os.chdir(here)
        ok = (saved == 2 and states[0] == "same" and states[1] == ("changed", ["changed: src/b.txt"])
              and states[2] == "same" and states[3] == ("changed", ["added: gone.txt"]) and states[4] == "no record")
        failed += not ok
        print(f"{'ok  ' if ok else 'FAIL'} fingerprint: same, changed, added, .cafe left out, no record")
        with open(record, "w", encoding="utf-8") as f:
            f.write("[1, 2]")
        expect_error("a record that is not a fingerprint", lambda: fingerprint_check(record))
        expect_error("a name git quoted", lambda: fingerprint_save(record, ['"\\355\\225\\234.md"']))
        expect_error("a save run outside the project root", lambda: fingerprint_save(os.path.join(tree, "src", ".cafe", "o", "s.json"), []))
        expect_error("a check run outside the project root", lambda: fingerprint_check(os.path.join(tree, "src", ".cafe", "o", "s.json")))

        def g(folder, *args):  # git_env: an exported GIT_DIR must not send these commits to the caller's repository
            subprocess.run(["git", "-C", folder, "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false",
                            "-c", "core.hooksPath=/dev/null", *args], check=True, capture_output=True, env=git_env())

        def write(name, text):
            os.makedirs(os.path.dirname(name) or ".", exist_ok=True)
            with open(name, "w", encoding="utf-8") as f:
                f.write(text)

        if shutil.which("git") is None:
            print("skip fingerprint over git: no git on this host")
        else:
            repo = os.path.join(d, "repo")
            os.makedirs(os.path.join(repo, ".cafe"))
            os.chdir(repo)
            try:
                g(".", "init", "-q")
                for name, text in (("한글 이름.md", "a"), ("old.txt", "o"), ("keep.txt", "k"), (".gitignore", "*.log\nsvc/\nrepos/\n")):
                    write(name, text)
                unborn = fingerprint_save(".cafe/unborn.json", [])[0]  # no commit yet
                g(".", "add", "-A")
                g(".", "commit", "-qm", "base")
                g(".", "checkout", "-qb", "feature")  # a branch to finish: its own commit is served too
                write("feature.py", "f")
                g(".", "add", "-A")
                g(".", "commit", "-qm", "branch")
                for name, text in (("한글 이름.md", "edited"), ("새 파일.txt", "new"), ("debug.log", "ignored"),
                                   (".cafe/notes.tsv", "x"), ("sub/.cafe/x", "x"), ("inner/app.js", "a"),
                                   ("inner/.gitignore", "node_modules/\n"), ("inner/node_modules/m.js", "m"), ("svc/x.ts", "x")):
                    write(name, text)
                os.remove("old.txt")
                g(".", "mv", "keep.txt", "moved.txt")
                g("inner", "init", "-q")
                g("inner", "add", "-A")
                g("inner", "commit", "-qm", "inner")
                g("svc", "init", "-q")
                g("svc", "config", "status.showUntrackedFiles", "no")  # a setting that hides svc's only change from status
                write("svc/.gitignore", "inner/\n")  # svc ignores a repository of its own, as a worktree folder is
                write("svc/inner/i.js", "i")
                g("svc/inner", "init", "-q")
                write("repos/group/c/app.js", "c")  # a repository two levels under an ignored plain folder
                g("repos/group/c", "init", "-q")
                saved, absent, nested = fingerprint_save(".cafe/served.json", [])
                files = sorted(json.load(open(".cafe/served.json", encoding="utf-8"))["files"])
                g(".", "add", "-A")
                g(".", "commit", "-qm", "served")
                states = [fingerprint_check(".cafe/served.json")[0]]
                os.chdir("inner")
                states[0] += " " + fingerprint_check("../.cafe/served.json")[0]  # from a subfolder: the same answer
                os.chdir("..")
                write("keep.txt", "back")
                states.append(fingerprint_check(".cafe/served.json"))
                os.remove("keep.txt")
                write("inner/app.js", "a2")
                states.append(fingerprint_check(".cafe/served.json"))
                with_svc = fingerprint_save(".cafe/svc.json", ["svc"])
                part = fingerprint_save(".cafe/part.json", ["repos/group/c/app.js"])  # a file in it does not cover it
            except (OSError, subprocess.CalledProcessError) as e:
                files, states, with_svc, part = None, None, None, None
                print(f"FAIL fingerprint over git: a git step failed ({e})")
            finally:
                os.chdir(here)
            ok = (files == [".gitignore", "feature.py", "inner/.gitignore", "inner/app.js", "moved.txt", "old.txt",
                            "새 파일.txt", "한글 이름.md"]
                  and unborn == 4 and saved == 7 and absent == ["old.txt"] and nested == ["repos/group/c", "svc", "svc/inner"]
                  and states == ["same same", ("changed", ["added: keep.txt"]), ("changed", ["changed: inner/app.js"])]
                  and with_svc[2] == ["repos/group/c", "svc/inner"] and with_svc[0] == 9
                  and "repos/group/c" in part[2])  # the 7, svc/x.ts, svc/.gitignore
            failed += not ok
            if not ok:
                print("  got", files, unborn, saved, absent, nested, states, with_svc)
            print(f"{'ok  ' if ok else 'FAIL'} fingerprint over git: no commit yet, a branch's commits, non-ASCII names, "
                  "renamed, deleted, ignored, .cafe at any depth, nested repositories, from a subfolder")

            repo = os.path.join(d, "hidden")
            os.makedirs(os.path.join(repo, ".cafe", "o"))
            os.chdir(repo)
            wait = os.environ.get("CAFE_LOCK_SECONDS")
            try:
                g(".", "init", "-q")
                nfd = unicodedata.normalize("NFD", "서비스")  # as Finder names a folder; git on macOS prints NFC
                write(".gitignore", f"svc/\n서비스/\n{nfd}/\n")  # a git that keeps bytes (Linux) matches the NFD line
                write("svc/lib/l.js", "l1")
                g("svc/lib", "init", "-q")
                g("svc/lib", "add", "-A")
                g("svc/lib", "commit", "-qm", "lib")
                g("svc", "init", "-q")
                g("svc", "add", "lib")
                write("svc/.gitmodules", '[submodule "lib"]\n\tpath = lib\n\turl = ./lib\n\tignore = all\n')
                g("svc", "add", ".gitmodules")
                g("svc", "commit", "-qm", "svc")
                write("svc/lib/l.js", "l2")  # svc's status hides it: its submodule says ignore = all
                write(os.path.join(nfd, "a.js"), "a")
                g(nfd, "init", "-q")
                hidden = [nfc(k) for k in fingerprint_save(".cafe/o/s.json", [])[2]]
                passed = fingerprint_save(".cafe/o/s.json", ["서비스"])[2]
                with RecordLock(".cafe/o/s.json"):  # a save still running: the next one waits, then gives up
                    os.environ["CAFE_LOCK_SECONDS"] = "0.3"
                    try:
                        fingerprint_save(".cafe/o/s.json", [])
                        waited = "saved"
                    except NotesError:
                        waited = "refused"
            except (OSError, subprocess.CalledProcessError) as e:
                hidden, passed, waited = None, None, None
                print(f"FAIL hidden changes: a git step failed ({e})")
            finally:
                os.environ.pop("CAFE_LOCK_SECONDS", None)
                if wait is not None:
                    os.environ["CAFE_LOCK_SECONDS"] = wait
                os.chdir(here)
            ok = hidden == ["svc", "서비스"] and passed == ["svc"] and waited == "refused"
            failed += not ok
            print(f"{'ok  ' if ok else 'FAIL'} a submodule's ignore setting, an NFD folder passed, a save that waits: "
                  f"{hidden} {passed} {waited}")

        with open(path, "a", encoding="utf-8") as f:
            f.write("2 cup - yes a row split by spaces\n")
        expect_error("row not split by tabs", lambda: read_notes(path))

        script = os.path.join(d, "root", "skills", "order", "scripts", "cafe.py")
        manifest = os.path.join(d, "root", ".claude-plugin", "plugin.json")
        got = [version(script)]
        os.makedirs(os.path.dirname(manifest))
        for text in ('{"name": "cafe", "version": "9.8.7"}', '﻿{"name": "cafe", "version": "9.8.6"}',
                     '{"name": "other", "version": "1.0.0"}', '{"name": "cafe"}', "{not json"):
            with open(manifest, "w", encoding="utf-8") as f:
                f.write(text)
            got.append(version(script))
        ok = got == ["?", "9.8.7", "9.8.6", "?", "?", "?"]
        failed += not ok
        print(f"{'ok  ' if ok else 'FAIL'} version reads only the cafe plugin.json: {got}")

    print("self-test", "passed" if not failed else f"failed {failed}")
    return 0 if not failed else 1


def main():
    p = argparse.ArgumentParser(description="cafe cupping notes and verdict")
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add", help="add one row to the cupping notes")
    a.add_argument("notes")
    row_args(a)
    b = sub.add_parser("add-rows", help="add rows from stdin, one per line as add's arguments; all or none")
    b.add_argument("notes")
    c = sub.add_parser("check", help="decide whether it is ready to serve")
    c.add_argument("notes")
    c.add_argument("--max-rounds", type=int, default=None, help="override the size's round limit")
    f = sub.add_parser("fingerprint", help="record the served files on SERVE, or check them against the record")
    fsub = f.add_subparsers(dest="fp", required=True)
    fs = fsub.add_parser("save", help="record every file the project lists, and each nested repository or path given")
    fs.add_argument("record")
    fs.add_argument("paths", nargs="*")
    fc = fsub.add_parser("check", help="same, changed, or no record")
    fc.add_argument("record")
    sub.add_parser("version", help='print "cafe v<version>" for the progress lines')
    sub.add_parser("self-test", help="check the verdict rules")
    args = p.parse_args()
    for stream in (sys.stdout, sys.stderr):  # a note must never crash check on a console that cannot print it
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="backslashreplace")

    if args.cmd == "version":
        emit([f"cafe v{version()}"])
        return 0
    try:
        if args.cmd == "add":
            add(args.notes, args.round, args.event, args.severity, args.tasted, args.note)
            return 0
        if args.cmd == "add-rows":
            data = sys.stdin.buffer.read() if sys.stdin is not None else b""
            if not add_rows(args.notes, decode_rows(data, locale.getpreferredencoding(False))):
                emit([f"these rows are already the last rows of {args.notes}, so nothing was written (a rerun of a batch "
                      "that went in). To log the same rows again, tell them apart in the note"])
            return 0
        if args.cmd == "check":
            if not os.path.exists(args.notes):
                outside_root(args.notes)  # no notes and no order folder: run from a subfolder, not "no rounds yet"
            verdict, reasons = judge(read_notes(args.notes), args.max_rounds, args.notes)
            emit([verdict] + [f"  {line}" for line in reasons])
            return 0 if verdict == "SERVE" else 1
        if args.cmd == "fingerprint":
            try:
                os.getcwd()
            except FileNotFoundError:  # the folder it ran from was deleted: an absolute record still names its project
                if not os.path.isabs(args.record):
                    raise NotesError("the folder cafe.py ran from was deleted. Run it again from the project root")
                os.chdir(project_of(args.record) if ".cafe" in args.record.split(os.sep) else os.path.dirname(args.record))
            if args.fp == "save":
                n, absent, nested = fingerprint_save(args.record, args.paths)
                emit([f"saved {n} file(s) to {args.record}"] + [f"  absent (deleted, or a wrong name): {p}" for p in absent]
                     + [f"  nested repository with changes, not recorded: {p} (pass it if a tasted file is in it)"
                        for p in nested])
                return 0
            result, lines = fingerprint_check(args.record)
            emit([result] + [f"  {line}" for line in lines])
            return {"same": 0, "changed": 1}.get(result, 2)
        return self_test()
    except NotesError as e:
        try:
            if sys.stderr is not None:  # closed: say nothing rather than print the error as if it were output
                print(f"notes error: {e}", file=sys.stderr)
        except BrokenPipeError:  # a closed stderr changes no exit code
            pass
        return 2


if __name__ == "__main__":
    try:
        code = main()
    except SystemExit as e:  # argparse: --help, or a bad argument
        code = e.code
    except BrokenPipeError:  # self-test into a reader that stopped early: it did not finish
        code = 1
    try:
        if sys.stdout is not None:
            sys.stdout.flush()
    except BrokenPipeError:
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())  # no second error when Python exits
    sys.exit(code)
