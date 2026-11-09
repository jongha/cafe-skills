# Cupping

## Cupping table

Each round pairs viewpoints and methods so no pair repeats. Use the first cuppers of the round's row by size: S takes Cupper 1, M takes Cuppers 1 and 2, L takes all three. Cupper 1 always runs things, so a one-cupper round still tastes the work.

| Round | Cupper 1 | Cupper 2 | Cupper 3 |
|---|---|---|---|
| 1 | Customer x Order sheet | Difficult customer x 30 complaints | Recipe check x Blind tasting |
| 2 | Recipe check x Order sheet | Next barista x 30 complaints | Difficult customer x Bad shot |
| 3 | Customer x 30 complaints | Recipe check x Bad shot | Next barista x Blind tasting |
| 4 | Difficult customer x Order sheet | Next barista x Bad shot | Customer x Blind tasting |
| 5 | Next barista x Order sheet | Difficult customer x Blind tasting | Customer x Bad shot |

If an L change is too big for one cupper, split the scope and launch more cuppers with the same pair.

## Viewpoints

- **Recipe check.** Is each acceptance criterion really true? Where are the gaps the criteria do not mention?
- **Customer.** Follow real use from start to finish. When it fails, what does the customer see?
- **Difficult customer.** Malformed or hostile input, requests beyond permission, the same request twice, requests at the same time, a cut midway, retries, huge input.
- **Next barista.** Look outside the changed code: callers, other readers of the same data, existing data, config and migrations, and what breaks when the next person changes it.

## Methods

- **30 complaints.** Write ways this could go wrong in real use from this viewpoint, rare ones included: up to 5 for S, 10 for M, 30 for L. Then run each and report only what reproduces.
- **Order sheet.** Build a table of inputs and states: empty, one, many, maximum, duplicate, out of order, failure midway, retry. Keep only the rows this scope can affect: up to 8 cells for S, 15 for M, all for L. Run every cell you keep.
- **Bad shot.** In a copy of the project, break the key lines of the change one at a time and run the acceptance checks: up to 3 lines for M, 5 for L. If the checks still pass, nothing guards that line. Restore each line before you break the next.
- **Blind tasting.** Before reading the recipe, write a spec of what the code actually does from the code alone. Then read the recipe and compare. Each difference is a defect or a gap in the recipe.

## Cupper brief

Use this as is and fill in only the `<>`.

```
You are a cupper at Mr. Latte's cafe. You are seeing this code for the first time.
Do not change the project. Put any files you make to check things only in <scratch path>, except test git repositories and the bad shot copy.
Never push, deploy, delete real data, call real external services, or send messages. Use only local or test resources.
Follow the project's own instructions (CLAUDE.md, AGENTS.md) about what may run here, such as builds and tests.
Run nothing in the foreground that waits on input or runs until stopped (watch modes, servers). Stop every process you start before you report. As you start any background process, append its PID (or the host's task ID) and its command to <scratch path>/pids.txt, writing the command as `ps -p "$!" -o command=` prints it when ps works.
Make test git repositories and the bad shot copy only in a temp folder outside the project: create it with `mktemp -d "${TMPDIR:-/tmp}/cafe.XXXXXX"`, write its path to <scratch path>/temp-path.txt, and delete it before you report. Inside the project, git in a folder without its own repository runs on the project's repository. If mktemp fails, or `git rev-parse --git-dir` run in that folder finds a repository (it sits inside the project or another repository), stop and report it rather than use another folder.
If your method is bad shot, first copy into the temp folder only the files `git ls-files -z -co --exclude-standard -- . ':!.cafe'` lists (split on NUL: without -z, git quotes non-ASCII names), skipping any the order deleted (without git: the project without .git, .cafe, and dependency or build folders). Add only the ignored files the checks need, link dependency folders back instead of copying them, and break lines only there.

- Recipe: <recipe.md path> (for blind tasting, read it only after your spec is written)
- Scope: <files or directories, or `git diff <base>` plus the new files this order created (git diff leaves out untracked files)>
- House notes: <house-notes.md path> (skip if missing)
- Size: <S, M, or L>
- Budget: about <15, 25, or 40> tool calls. When you reach it, stop and report what you have.
- Viewpoint: <name and description>
- Method: <name and description>

1. Hold each house note against this scope.
2. Look for defects with your viewpoint and method. Run every suspicion with the narrowest command that shows it: one test file, one function, one request. Do not run the whole test suite.
3. Mark each acceptance criterion PASS, FAIL, or NOT CHECKED.

Report, in under 40 lines
- Acceptance criteria: one line per number
- Defects: only what breaks an acceptance criterion, loses data, opens a security hole, or crashes. Each: title / criterion broken / how a real customer hits it / repro command / actual output / expected output / file:line
- Minor: any other flaw, one line each with file:line
- Ran: the commands you ran, or "none", and the PID of any process you started and could not stop
- Next order: ideas outside the recipe worth doing, one line each

Leave out guesses you did not run, naming and style taste, and risks that need some future change to matter.
For what you cannot run, give file:line and the criterion it breaks.
"No defects" is a valid answer.
```
