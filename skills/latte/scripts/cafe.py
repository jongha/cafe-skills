#!/usr/bin/env python3
"""The cafe's cupping notes and verdict, used by the latte skill.

  cafe.py add <notes> <round> <event> [-s P0|P1|P2] [-t yes|no] <note>
  cafe.py check <notes> [--max-rounds N]
  cafe.py self-test

events
  cup     one cupper finished. -t yes means that cupper actually ran something (tasted it).
  defect  a finding kept on evidence. -s gives its severity.
  drop    a finding dropped (no evidence, outside the recipe, taste, duplicate).
  recipe  recipe.md changed. Clean rounds up to this round no longer count.
  rebrew  the design was rechecked after a REBREW verdict. Stall detection restarts here.

verdicts
  SERVE   two clean rounds in a row after the last recipe change. Serve it.
  CLOSE   the round limit is reached. Close and report that it did not converge.
  REBREW  P0/P1 defects did not go down for two rounds in a row. Stop patching and recheck the design.
  RECUP   run another round.

A clean round has at least 3 cuppers, at least 1 cupper that ran something, and no P0/P1 defects.
Exit code: 0 for SERVE, 1 for any other verdict, 2 for a bad notes file.
"""
import argparse
import os
import sys
import tempfile

HEADER = ["round", "event", "severity", "tasted", "note"]
EVENTS = ("cup", "defect", "drop", "recipe", "rebrew")
ROUND_EVENTS = ("cup", "defect", "drop")
SEVERITIES = ("P0", "P1", "P2")
SERIOUS = ("P0", "P1")
MIN_CUPPERS = 3
CLEAN_STREAK = 2
MAX_ROUNDS = 5


class NotesError(Exception):
    pass


def validate(rnd, event, severity, tasted):
    if event not in EVENTS:
        raise NotesError(f"event must be one of {', '.join(EVENTS)}: {event!r}")
    if rnd < 0:
        raise NotesError(f"round must be 0 or more: {rnd}")
    if event in ROUND_EVENTS and rnd < 1:
        raise NotesError(f"{event} starts at round 1")
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
                validate(rnd, event, severity, tasted)
            except NotesError as e:
                raise NotesError(f"{path}:{n} {e}")
            rows.append((rnd, event, severity, tasted, note))
    return rows


def add(path, rnd, event, severity, tasted, note):
    validate(rnd, event, severity, tasted)
    note = " ".join(note.split())
    if not note:
        raise NotesError("note is empty. Say in one line what happened")
    read_notes(path)
    new = not os.path.exists(path) or os.path.getsize(path) == 0
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        if new:
            f.write("\t".join(HEADER) + "\n")
        f.write("\t".join([str(rnd), event, severity, tasted, note]) + "\n")


def judge(rows, max_rounds=MAX_ROUNDS):
    rounds = sorted({r for r, e, *_ in rows if e in ROUND_EVENTS})
    if not rounds:
        return "RECUP", ["no cupping rounds yet"]
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
        if st["cuppers"] < MIN_CUPPERS:
            out.append(f"{st['cuppers']} cuppers ({MIN_CUPPERS} needed)")
        if st["tasted"] == 0:
            out.append("no cupper ran anything")
        if st["serious"]:
            out.append(f"{st['serious']} P0/P1 defects")
        if r <= last_recipe:
            out.append(f"before the round {last_recipe} recipe change")
        return out

    reasons = []
    for r in rounds:
        p = problems(r)
        reasons.append(f"R{r}: " + ("clean" if not p else ", ".join(p)))

    streak = 0
    for r in reversed(rounds):
        if problems(r):
            break
        streak += 1
    reasons.append(f"clean rounds in a row: {streak}/{CLEAN_STREAK}")

    if streak >= CLEAN_STREAK:
        return "SERVE", reasons
    if last >= max_rounds:
        reasons.append(f"reached the {max_rounds} round limit")
        return "CLOSE", reasons
    window = [stat[r]["serious"] for r in rounds if r > last_rebrew]
    if len(window) >= 3:
        a, b, c = window[-3:]
        if c > 0 and b >= a and c >= b:
            reasons.append(f"P0/P1 defects are not going down: {a} -> {b} -> {c}")
            return "REBREW", reasons
    return "RECUP", reasons


def self_test():
    def notes(*specs):
        return [(r, e, s, t, "t") for r, e, s, t in specs]

    def clean(r, n=3, tasted="yes"):
        return [(r, "cup", "-", tasted)] + [(r, "cup", "-", "no")] * (n - 1)

    def dirty(r, k, sev="P1"):
        return clean(r) + [(r, "defect", sev, "-")] * k

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
    ]
    failed = 0
    for name, rows, want in cases:
        got, _ = judge(rows)
        ok = got == want
        failed += not ok
        print(f"{'ok  ' if ok else 'FAIL'} {name}: {got}" + ("" if ok else f" (expected {want})"))

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

    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "order", "cupping.tsv")
        add(path, 0, "recipe", "-", "-", "added criterion 3")
        for i in range(3):
            add(path, 1, "cup", "-", "yes" if i == 0 else "no", f"cupper\t{i}\nnewline")
        add(path, 1, "defect", "P1", "-", "crash on an empty order")
        rows = read_notes(path)
        ok = len(rows) == 5 and rows[1][4] == "cupper 0 newline" and judge(rows)[0] == "RECUP"
        failed += not ok
        print(f"{'ok  ' if ok else 'FAIL'} write with add and read back")
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
    a.add_argument("round", type=int)
    a.add_argument("event", choices=EVENTS)
    a.add_argument("note")
    a.add_argument("-s", "--severity", default="-")
    a.add_argument("-t", "--tasted", default="-")
    c = sub.add_parser("check", help="decide whether it is ready to serve")
    c.add_argument("notes")
    c.add_argument("--max-rounds", type=int, default=MAX_ROUNDS)
    sub.add_parser("self-test", help="check the verdict rules")
    args = p.parse_args()

    try:
        if args.cmd == "add":
            add(args.notes, args.round, args.event, args.severity, args.tasted, args.note)
            return 0
        if args.cmd == "check":
            verdict, reasons = judge(read_notes(args.notes), args.max_rounds)
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
