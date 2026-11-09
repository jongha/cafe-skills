---
name: order
description: "Complete a task through fixed acceptance criteria, implementation, and independent review rounds sized to the change, with a scripted verdict. Use when the user requests the order workflow or asks to finish work with repeated independent verification."
disable-model-invocation: true
argument-hint: "<what to make, or the branch to finish>"
---

# order

No cup leaves the bar untasted.

The order is the user's task from the message or host arguments that came with this skill: a bug fix, a feature, a refactor, tests, docs, or a branch to finish. If the order is empty, finish the current branch.

Reviews never end when the bar moves, each review picks only what stands out, and each fix breaks something else. So the recipe is fixed first, cuppers fill tables and run things, and a script decides when the work ends.

## Runtime setup

Read [references/runtimes.md](references/runtimes.md) for the current host (Codex, Claude Code, or Grok) and use only tools this session exposes.

The skill directory is the folder holding this `SKILL.md`, not the project. In Claude Code it is `${CLAUDE_SKILL_DIR}`; elsewhere, do not assume a provider-specific environment variable exists. Resolve [cupping.md](cupping.md) and [scripts/cafe.py](scripts/cafe.py) from it. Below, `cafe.py` means `python3 "<skill directory>/scripts/cafe.py"` with the absolute path, run from the project root. Quote paths, including paths with spaces.

Full verification needs the project files, Python 3 and the project's check tools, fresh subagents that do not inherit the conversation, and permission to use them. If any is missing, follow Limited verification in the runtime reference and hand over UNVERIFIED, which is not a judge verdict. A self-review never counts as a cupper, and a check that did not run is never reported as run.

## Size

The tasting is sized to the order: a one-line fix does not get five rounds of three cuppers. Size by the change you expect, or a branch by its diff against its base. A change in a risk area (stored data and migrations, auth and permissions, money, deleting user data, concurrency) moves up one size.

| | S | M | L |
|---|---|---|---|
| The change | at most 2 files, about 60 changed lines | at most about 6 files, 300 lines | bigger |
| Acceptance criteria | at most 3 | at most 6 | as many as the goal needs |
| Claim rehearsal | you, 3 reasons | a subagent, 5 reasons | a subagent, 10 reasons |
| Cuppers a round | 1 | 2 | 3 |
| Cupper budget | about 15 tool calls | about 25 | about 40 |
| Clean rounds to serve | 1 | 1 | 2 in a row |
| Round limit | 3 | 4 | 5 |
| Serve | you rerun every check | you rerun every check | a first-time customer, once |

Log the size before round 1: `cafe.py add <notes> 0 size S|M|L`. If the change outgrows it, raise it with `cafe.py add <notes> <round> size M|L`; the judge never lowers a size. Notes with no size row are judged as L, and `check` says so.

## House rules

- You are the barista: you brew, call the cuppers, judge defects, and fix them.
- In full verification, end only when `cafe.py check` says SERVE or CLOSE and the serve check is done.
- Drop any finding without evidence: a command and its output, a failing test, or a `file:line` with the acceptance criterion it breaks.
- Fix only what is in scope. A finding about something under "Not doing", or about code this order does not touch, goes under "Next order" in recipe.md. A P0 in code this order touches is always in scope.
- Fix the cause, not the single case: fix every place with the same cause in the code this order touches, and add a regression test.
- Every cupper is a fresh subagent. Never pass it the conversation or your reasoning. Launch it as the runtime reference says for your host; judge and fix on your own model.
- The project's own instructions win. If its CLAUDE.md or AGENTS.md limits subagents (one at a time, no model override) or forbids local builds or tests, run cuppers one after another, leave the model out, use the checks it allows, and write that under Assumptions.
- Run the narrowest check that proves the point: one test file, one command, one grep. Run the whole suite once, before you serve, and only if the project allows it.
- The user may be away. Resolve ordinary choices yourself and write them under Assumptions. Honor the host's approval and sandbox rules; an assumption cannot grant permission. Keep doing independent work while an approval or missing information is pending.
- Do something irreversible (push, deploy, deleting data, sending messages outside) only when the order asks for it in words, and only after a SERVE. Otherwise list it as left for the user, and leave the work uncommitted unless the order asks for a commit or a push.
- Talk to the user in their language.

`cafe.py check` exits 0 on SERVE and exit 1 on any other verdict; read its first line. Exit 2 means invalid notes or arguments: fix the input, keeping genuine findings, and rerun. A missing tool or a failed run is not a verdict.

## Keep the customer posted

Run `cafe.py version` once, before the first line. At each moment below, print one line like these, in the user's language, with no reasoning, starting with what it printed (`cafe v<version>`, or `cafe v?` when the version is unknown) so the user sees which skill is running:

```
[cafe v<version> 1/4 Recipe] size S, 2 criteria: last page shows, page count right for 0 and 41
[cafe v<version> 2/4 Brew] checks built, 2 of 2 fail as expected
[cafe v<version> 3/4 Cupping R1] 1 cupper tasting: Customer x Order sheet. This takes a few minutes
[cafe v<version> 3/4 Cupping R1] 1 P1, 2 P2 -> RECUP, fixing the P1: page 3 empty when the total is a full page
[cafe v<version> 4/4 Serve] rerunning 2 checks and the test suite
```

- Recipe: once, after the recipe is written: the size and each criterion in a few words.
- Brew: after the checks are built, and after each unit.
- Cupping: before each round, or before each cupper when they run one after another, naming its viewpoint and method. After `cafe.py check`, the counts, the verdict, and what you fix next.
- Serve: before the final check. Then the receipt.

If the host has a task list or plan tool (TodoWrite or TaskCreate in Claude Code, `update_plan` in Codex), mirror only the four stages and one item per cupping round once it starts, marking each as you go.

## The bar

Everything lives at the project root. `<order>` is a short slug for the task.

```
.cafe/
  house-notes.md             kinds of defects earlier rounds missed. Kept after the order is done
  <order>/recipe.md          the recipe
  <order>/cupping.tsv        cupping notes. Write only with cafe.py add or add-rows
  <order>/scratch/R<r>-<n>/  one folder per cupper, for the files it makes to check things
```

With git, add `.cafe/*/` once to the file `git rev-parse --git-path info/exclude` names, if permitted; otherwise record that and keep the folders unstaged. Never stage `.cafe/` unless the order asks.

**Cleanup.** Each cupper lists in its scratch folder the background processes it starts (`pids.txt`) and its temp folder (`temp-path.txt`). To clean up scratch folders: for each `pids.txt` line, skip a process only when `kill -0` says no such process (a refusal, such as operation not permitted, means it may still run), stop one `ps` confirms is that process (the same command), and keep every other line, and any the host would not let you stop, for "Left for you"; then delete the folder each `temp-path.txt` names if it is a `cafe.` folder whose parent is in no repository. Run it on a cupper's folder when the cupper ends without a report, on every scratch folder of the order and of its earlier numbers when you resume it, and on all of them again just before the receipt or a hand-over, which lists every line it kept. The files stay, so the list is never lost.

Before you make a folder, read each `.cafe/*/recipe.md`. If any has this order's goal, take the one with the highest number: `<order>` is 1, then `<order>-2`, `<order>-3`, and so on (compare the numbers, not the names), and run the cleanup. If its cupping.tsv has no rounds (`cafe.py check` says "no cupping rounds yet"), continue it at Brew; if it is `<order>-<n>`, first add to its recipe each open P0 or P1 of the folder before it that the recipe lacks, since a cut while starting it can leave them out, and raise the size if the criteria no longer fit it. Otherwise run `cafe.py check` on it:

- RECUP or REBREW: the order was cut off. Continue it, but recheck the current files and acceptance checks first: old evidence cannot certify new changes, so the next round tastes whatever changed.
- SERVE: go to serve. Old evidence cannot certify the current files, so serve step 1 runs again, and for L a new first-time customer runs even if one ran before. Add no rows to these notes.
- CLOSE, or a failure in that serve: these notes have spent their round limit, so more rounds in them can only CLOSE again. Start the next folder, `<order>-<n+1>`, as a new order. Its first write, before Recipe step 1, is its recipe: the old one plus each open P0 and P1 as an acceptance criterion with its repro as the check, never as a defect row. The open ones are those `cafe.py check` lists (cupping.tsv holds their exact text), and any serve failure of a finished order asked again, which has no row. Then recheck each criterion against the current files, which removes none: one that passes today stays and gets tasted. Raise the size if the criteria no longer fit it.

## 1. Recipe

A recipe The bar already wrote for `<order>-<n>` keeps every criterion through these steps: step 1 picks a size that fits them, and step 2 only adds to the recipe; never trim or drop a criterion to fit a size.

1. Restate the order in your own words: the goal, the problem it solves, and the smallest change you expect. Where the order leaves a choice open, pick the reasonable option and write it under Assumptions with the option you did not pick. Pick the size and log it.
2. Write `.cafe/<order>/recipe.md`, with acceptance criteria within the size's limit.

   ```markdown
   # <order>
   Goal: <one sentence>
   Size: <S|M|L>, <files and lines you expect, and the risk area if any>

   ## Acceptance criteria
   1. <a statement that a check proves true or false>. Check: `<command>`

   ## Not doing
   - <out of scope>

   ## Assumptions
   - <a choice you made, and the option you did not pick>

   ## Next order
   - <ideas from cupping that are outside the recipe>
   ```

3. Claim rehearsal, as many reasons and by whom the size table says: "This cup went out and a customer complained. Write the possible reasons." A fresh subagent gets only the goal and the draft recipe. Add a reason to the acceptance criteria only if it would break the goal in real use; put the rest under Assumptions or Next order.
4. The recipe is now fixed. Only a change to the acceptance criteria or to "Not doing" is a recipe change; adding an assumption or a next order is not. Log one with `cafe.py add <notes> <round> recipe "<what and why>"`, where `<round>` is the last round judged, or 0 before round 1. Clean rounds up to that round stop counting, so a late change can end in CLOSE.

To finish existing code, read the goal from the branch, its commits, and the PR description; Brew then only builds the missing checks and makes them pass.

## 2. Brew

1. Build the check for each acceptance criterion first: an existing test, command, or grep when one proves it, and a new test or short script only when none does. A subagent is never a check. For a criterion nothing can run, such as a doc's wording, the check names what to read (`file:line` or a grep), and the cuppers read it. If a check cannot run here (it needs a service or credentials you lack, or the project forbids it), use the nearest one that can and write the gap under Assumptions.
2. Run the checks now. A check for new or changed behavior must fail; a check that guards existing behavior may pass.
3. Build in small units, running the checks after each and moving on only when they pass. When every check passes, go to cupping. If a check still fails after three different approaches, go to cupping anyway and log it as `defect -s P1` in round 1; the round limit now bounds the work.

## 3. Cupping

For each round R, starting at 1:

1. Save `git rev-parse HEAD`, `git status --short`, and `git diff` to `.cafe/<order>/scratch/R<R>-before.txt`, or without git, a list of files with their modification times.
2. Take round R's row from the cupping table and as many of its cuppers as the size needs. Each brief is the cupper brief with only the `<>` filled in and nothing added. The scope must include uncommitted changes and the new files this order created; `git diff` alone leaves out untracked files.
3. Launch the cuppers with the host's subagent tool, in parallel if capacity and the project's instructions permit, otherwise one after another in separate fresh contexts. Wait for every report before you record or judge the round. Only the barista writes cupping.tsv. If a cupper ends without a report (an error, a crash, a cut-off), run the cleanup (The bar) on its scratch folder. Then launch one new cupper with the same brief and scratch folder `R<r>-<n>b` in the same round; log cup rows only for cuppers that reported. If the new one also ends without a report, give it the same cleanup; the host has lost its subagents, so keep the notes and hand over as in Limited verification.
4. Compare the project with the saved state. Restore only changes a cupper made; keep pre-existing and concurrent user changes. Never reset the whole working tree. Stop each process a cupper reported still running, by its PID, and nothing else.
5. Write one row per cupper: `R cup -t yes|no "<viewpoint> x <method>"`. `yes` means that cupper ran something: a check, the code, a command, or a doc's examples.
6. Judge each finding: keep it as `R defect -s P0|P1|P2 "<note>"` or drop it as `R drop "<reason>"`. Reproduce a finding yourself only when you would keep it as P0 or P1. Log the cupper's Minor list as P2 or drop without reproducing it. Findings with one cause are one defect. A finding that repeats an earlier round's P0 or P1 is still open: log it again as a defect in this round, never as a duplicate drop. A P0 or P1 note names its repro command.

   - P0: data loss, security, crash
   - P1: breaks an acceptance criterion
   - P2: any other flaw whose cost you can name
   - P0 and P1 must happen in real use: normal input, a mistake real customers make, an attack, or a failure that really happens (a crash, a restart, a retry, two at once). A case that needs a contrived setup, such as a symlinked data file, the year 9999, or invisible characters in an ID, is P2 at most
   - Naming, style, and taste are not defects
   - A flaw in a check you built counts only when it hides a real failure of this order. Otherwise it is a drop
   - A gap or a conflict in the recipe that matters in real use: fix the recipe and log `recipe`. Anything else is a next order

   Then log steps 5 and 6 in one call. A bad row writes nothing; fix it and rerun the whole command.

   ```
   cafe.py add-rows <notes> <<'ROWS'
   1 cup -t yes "Customer x Order sheet"
   1 defect -s P1 "page 3 empty when the total is a full page"
   ROWS
   ```

7. If an earlier round missed this defect, add a line to the house notes: `- <what was missed>. Look for: <what would have caught it>`
8. Run `cafe.py check .cafe/<order>/cupping.tsv` before you fix anything, and follow the verdict. No cupper would taste a fix made after the last round.

| Verdict | Do |
|---|---|
| SERVE | Leave the source as it is. List the round's P2s as remaining risks and go to serve |
| RECUP | Fix every P0 and P1 at its cause and rerun the checks. Fix a P2 only when it takes a few lines in code this order already changed. Leave the rest as remaining risks. Run the next round |
| REBREW | Stop patching. Write down in one sentence the premise the failed fixes shared, and test that premise first. Fix the design, log `rebrew` at round R, and run the next round |
| CLOSE | Leave the source as it is. Go to serve and report that it did not converge, with the open defects. Never lower the bar to reach SERVE |

## 4. Serve

1. Check the finished work.
   - S and M: rerun every acceptance check yourself, and the whole suite once if the project allows it. Keep each command and its output for the receipt.
   - L: once per order, a first-time customer: a fresh subagent that never saw the work gets only recipe.md, the result, and cupping.tsv. It checks each acceptance criterion on the real thing, reporting PASS or FAIL with evidence, and rechecks every `drop` and P2 row for any that really are P0 or P1 in real use. If it reopens the order, the next SERVE goes straight to the receipt, because the new rounds' cuppers tasted the fix.
2. If anything fails or turns out to be P0 or P1, reproduce it, log it as `defect -s P0|P1` under the last round, add a house note, run `cafe.py check`, and follow the verdict. In a serve for a finished order asked again, add no row to the old notes (the house note still goes in): once it reproduces, start the next folder at once, as The bar says, with the failure in its first write.
3. On SERVE, do the irreversible steps the order asked for, such as a commit and a push. After CLOSE, leave them for the user.
4. Hand over the receipt: this template with the labels in the user's language, and "none" for an empty item.

   ```markdown
   ## Order up: <the goal in your own words>

   **SERVE** · size <S|M|L> · <rounds> rounds · <cup rows> cuppers · notes in `.cafe/<order>/`

   Runtime: <host> · cafe v<version> · Verification: full

   Cupping: <each round line from the last cafe.py check, such as R1 2 P0/P1 defects · R2 clean>

   | # | Acceptance criterion | Result | Evidence |
   |---|---|---|---|
   | 1 | <criterion> | PASS | `<command>` → <the output that proves it> |

   - **Changed:** <files>, +<added> −<removed>, <uncommitted, or the commit and where it was pushed>
   - **Left for you:** <irreversible steps the order did not ask for, or that CLOSE held back, and each process line the cleanup kept>
   - **Assumed:** <each choice you made>, not <the option you did not pick>
   - **Remaining risks:** <each P2 left, and what it costs>
   - **Next orders:** <ideas outside the recipe>
   - **House notes:** <lines this order added>
   ```

   After CLOSE, the heading is `## Order closed: <goal>`, the verdict is **CLOSE**, and the list starts with **Open defects:** each open P0 or P1 with its repro command.
