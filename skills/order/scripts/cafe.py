#!/usr/bin/env python3
"""The cafe's cupping notes and verdict, used by the order skill.

  cafe.py add <notes> <round> <event> [-s P0|P1|P2] [-t yes|no] <note>
  cafe.py add-rows <notes>   rows on stdin, one per line, each written as add's arguments after <notes>.
                             All rows are written or none, so a fixed batch can be rerun as a whole.
  cafe.py check <notes> [--max-rounds N]
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
  REBREW  P0/P1 defects did not go down for two rounds in a row. Stop patching and recheck the design.
  RECUP   run another round.

A clean round has the size's cuppers, at least 1 cupper that ran something, and no P0/P1 defects.
Exit code: 0 for SERVE, 1 for any other verdict, 2 for a bad notes file.
"""
import argparse
import os
import shlex
import sys
import tempfile

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
        append(path, rows)
    except NotesError as e:
        raise NotesError(f"{e}. Nothing was written")


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

        with open(path, "a", encoding="utf-8") as f:
            f.write("2 cup - yes a row split by spaces\n")
        expect_error("row not split by tabs", lambda: read_notes(path))

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
    sub.add_parser("self-test", help="check the verdict rules")
    args = p.parse_args()

    try:
        if args.cmd == "add":
            add(args.notes, args.round, args.event, args.severity, args.tasted, args.note)
            return 0
        if args.cmd == "add-rows":
            add_rows(args.notes, sys.stdin.read().splitlines())
            return 0
        if args.cmd == "check":
            verdict, reasons = judge(read_notes(args.notes), args.max_rounds, args.notes)
            print(verdict)
            for line in reasons:
                print(f"  {line}")
            return 0 if verdict == "SERVE" else 1
        return self_test()
    except NotesError as e:
        print(f"notes error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
