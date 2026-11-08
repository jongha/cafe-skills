---
name: order
description: "Complete a task through fixed acceptance criteria, implementation, and independent review rounds sized to the change, with a scripted verdict. Use when the user requests the order workflow or asks to finish work with repeated independent verification."
disable-model-invocation: true
argument-hint: "<what to make, or the branch to finish>"
---

# order

The order is the user's task accompanying this skill invocation. Read it from the current user message or the host's supplied arguments; no argument substitution is required.

No cup leaves the bar untasted.

Any task fits: a bug fix, a feature, a refactor, tests, docs, or a branch to finish. If the order is empty, finish the current branch.

## Runtime setup

Read [references/runtimes.md](references/runtimes.md) for the current host: Codex, Claude Code, or Grok. Use only tools actually exposed in this session, and the subagent model that reference sets for the host.

Locate this loaded `SKILL.md`. Its parent directory is the skill directory, independent of the project being worked on. In Claude Code it is `${CLAUDE_SKILL_DIR}`. Resolve [scripts/cafe.py](scripts/cafe.py) and [cupping.md](cupping.md) relative to it. In all commands below, `cafe.py` means `python3 "/absolute/path/to/this/skill/scripts/cafe.py"`, run from the target project root. Quote paths, including paths with spaces. Do not assume a provider-specific environment variable exists.

Full verification needs access to the target files, Python 3 and the required check tools, and fresh subagents that can inspect those files without inheriting the conversation. If any of these is unavailable, use the limited workflow in the runtime reference. Never count a self-review as an independent cupper or claim a check ran when it did not.

Reviews keep finding new problems for three reasons. The bar is not fixed. A review picks the few problems that stand out. A fix in one place breaks another. This skill fixes the recipe first, turns finding into filling tables and running things, and lets a script decide when the work ends.

The tasting is sized to the order. A one-line fix does not get five rounds of three cuppers. Pick the size first and let it set the work.

## Size

Pick the size from the change you expect. Risk areas are stored data and migrations, auth and permissions, money, deleting user data, and concurrency.

- **S**: at most two files and about 60 changed lines, in no risk area. Most bug fixes and doc edits.
- **M**: at most about six files and 300 lines, or an S-sized change in a risk area.
- **L**: anything bigger, or an M-sized change in a risk area.

To finish a branch, size it by the branch's diff against its base.

| | S | M | L |
|---|---|---|---|
| Acceptance criteria | at most 3 | at most 6 | as many as the goal needs |
| Claim rehearsal | you, 3 reasons | a subagent, 5 reasons | a subagent, 10 reasons |
| Cuppers a round | 1 | 2 | 3 |
| Cupper budget | about 15 tool calls | about 25 | about 40 |
| Clean rounds to serve | 1 | 1 | 2 in a row |
| Round limit | 3 | 4 | 5 |
| Serve | you rerun every check | you rerun every check | a first-time customer, once |

Log the size before round 1 with `cafe.py add <notes> 0 size S|M|L`. The judge reads the cuppers, the clean rounds, and the round limit from it. If the change grows past its size while you brew or fix, raise it with `cafe.py add <notes> <round> size M|L`. The judge never lowers a size. An order from before sizes has no size row and is judged as L. Add one before its next round.

## House rules

- You are the barista. You brew, call the cuppers, judge defects, and fix them.
- In full verification, end only when `cafe.py check` says SERVE or CLOSE and the serve check is done. If required capabilities or permissions are unavailable, report UNVERIFIED with the missing evidence; it is not a judge verdict.
- Drop any finding without evidence. Evidence is a command and its output, a failing test, or a `file:line` with the acceptance criterion it breaks.
- Fix only what is in scope. A finding about something under "Not doing", or about code this order does not touch, goes under "Next order" in recipe.md. A P0 in code this order touches is always in scope.
- Fix the cause, not the single case. Find every place in the code this order touches with the same cause, fix them together, and add a regression test.
- Every cupper is a fresh subagent. Never pass it the conversation or your reasoning.
- Use the host's native subagent tool, parameters, and subagent model from the runtime reference. Stay on your own model for judging and fixing. Fresh contexts matter; a particular provider does not.
- The project's own instructions win. If its CLAUDE.md or AGENTS.md limits subagents (one at a time, no model override) or forbids running builds or tests locally, follow it: run cuppers one after another, leave the model out, and use the checks the project allows. Write that under Assumptions.
- Run the narrowest check that proves the point: one test file, one command, one grep. Run the whole suite once, before you serve, and only if the project allows it.
- The user handed this off and may be away. Resolve ordinary choices yourself and write them under Assumptions. Honor the host's approval and sandbox requirements; an assumption cannot grant permission. Continue independent work while required approval or missing information is pending.
- Do something irreversible (push, deploy, deleting data, sending messages outside) only when the order asks for it in words, and only after a SERVE. Otherwise list it in the report as left for the user. Leave the work uncommitted unless the order asks for a commit or a push.
- Talk to the user in their language.

From `check`, exit 1 is a normal verdict other than SERVE, so read the first line. Exit 2 means invalid notes or arguments; inspect the error, correct the input without removing genuine findings, and run it again. Missing tools or failed execution are not verdicts.

## Keep the customer posted

The user should see where the order is without reading your work. At each moment listed below, print one line in this shape, with the stage name and the rest in the user's language. One line per moment, and no reasoning.

```
[cafe 1/4 Recipe] size S, 2 criteria: last page shows, page count right for 0 and 41
[cafe 2/4 Brew] checks built, 2 of 2 fail as expected
[cafe 2/4 Brew] unit 1 of 2 done, checks 1 of 2 pass
[cafe 3/4 Cupping R1] 1 cupper tasting: Customer x Order sheet. This takes a few minutes
[cafe 3/4 Cupping R1] 1 P1, 2 P2 -> RECUP, fixing the P1: page 3 empty when the total is a full page
[cafe 3/4 Cupping R2] clean -> SERVE
[cafe 4/4 Serve] rerunning 2 checks and the test suite
```

- Recipe: once, after the recipe is written: the size and each criterion in a few words.
- Brew: after the checks are built, and after each unit.
- Cupping: before you launch a round, naming each cupper's viewpoint and method. When cuppers run one after another, one line before each. After `cafe.py check`, the counts, the verdict, and what you fix next.
- Serve: before the final check. Then the receipt.

If the host has a task list or plan tool (TodoWrite or TaskCreate in Claude Code, `update_plan` in Codex), mirror the order there too: one item per stage, and one item per cupping round once you start it. Mark each one in progress and done as you go. Keep the list to these items.

## The bar

Everything lives at the project root. `<order>` is a short slug for the task.

```
.cafe/
  house-notes.md             kinds of defects earlier rounds missed. Kept after the order is done
  <order>/recipe.md          the recipe
  <order>/cupping.tsv        cupping notes. Write only with cafe.py add
  <order>/scratch/R<r>-<n>/  one folder per cupper, for the files it makes to check things
```

When git is available, add `.cafe/*/` once to the file that `git rev-parse --git-path info/exclude` names, if permitted, so order folders stay out of git. If it is not writable, record that and keep the folders unstaged. Never stage `.cafe/` unless the order asks.

Before you make a folder, read each `.cafe/*/recipe.md`. If one has this order's goal, continue it. Recheck the current files and acceptance checks before relying on an earlier verdict, especially after switching hosts. If the reviewed result has changed, run fresh rounds; old evidence cannot certify new changes. If its cupping.tsv has rounds, run `cafe.py check` and follow the verdict. Otherwise start at Brew.

## 1. Recipe

1. Restate the order in your own words: the goal, the problem it solves, and the smallest change you expect. When the order leaves a choice open, pick the reasonable option and write it under Assumptions, with the option you did not pick. Pick the size and log it.
2. Write `.cafe/<order>/recipe.md`. Keep the acceptance criteria within the size's limit.

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

3. Claim rehearsal. Ask: "This cup went out and a customer complained. Write the possible reasons." For S, write 3 reasons yourself. For M and L, give a fresh subagent only the goal and the draft recipe, and ask for 5 or 10. Add a reason to the acceptance criteria only if it would break the goal in real use. Put the rest under Assumptions or Next order.
4. The recipe is now fixed. Only a change to the acceptance criteria or to "Not doing" is a recipe change. Adding an assumption or a next order is not. For a recipe change, run `cafe.py add <notes> <round> recipe "<what and why>"`, where `<round>` is the last round judged, or 0 before round 1. The judge stops counting clean rounds up to that round, so a late change can end in CLOSE.

If the order is to finish existing code, read the goal from the branch, the commits, and the PR description. Write the recipe and run the claim rehearsal. Then build the checks that are missing (Brew step 1), make them pass, and go to cupping.

## 2. Brew

1. Build the check for each acceptance criterion first. Use an existing test, a command, or a grep when one proves it. Write a new test or a short script only when nothing existing does. A subagent is never a check: for a criterion nothing can run, such as the wording of a doc, the check names what to read (`file:line` or a grep), and the cuppers read it. If a check cannot run here, for example because it needs a service or credentials you do not have, or the project forbids it, use the nearest check that can run and write the gap under Assumptions.
2. Run the checks now. A check for new or changed behavior must fail. A check that guards existing behavior may pass.
3. Build in small units. Run the checks after each unit and move on only when they pass. If a check still fails after three different approaches, go to cupping anyway and log it as `defect -s P1` in round 1. The round limit now bounds the work.
4. When every check passes, go to cupping.

## 3. Cupping

For each round R, starting at 1:

1. Save `git status --short` and `git diff` to `.cafe/<order>/scratch/R<R>-before.txt`. Without git, save a list of files with their modification times.
2. Take round R's row from the cupping table and use its first cuppers: one for S, two for M, all three for L. Each brief is the cupper brief with only the `<>` filled in. Add nothing else. The scope must include uncommitted changes.
3. Launch the round's cuppers using the current host's subagent tool. Run them in parallel if capacity and the project's instructions permit; otherwise run them sequentially in separate fresh contexts. Wait for every report before recording or judging the round. Only the barista writes cupping.tsv.
4. Compare the project with the saved state. Restore only changes attributable to a cupper; preserve pre-existing and concurrent user changes. Never reset the whole working tree.
5. For each cupper, run `cafe.py add <notes> R cup -t yes|no "<viewpoint> x <method>"`. `yes` means that cupper ran something: a check, the code, a command, or the examples in a doc.
6. Judge each finding. Keep it as `defect -s P0|P1|P2` or drop it as `drop`, with the reason in the note. Reproduce a finding yourself only when you would keep it as P0 or P1. Log the cupper's Minor list as P2 or drop without reproducing it. Log findings with one cause as one defect.
   - P0: data loss, security, crash
   - P1: breaks an acceptance criterion
   - P2: any other flaw whose cost you can name
   - P0 and P1 must happen in real use: normal input, a mistake real customers make, an attack, or a failure that really happens (a crash, a restart, a retry, two at once). A case that needs a contrived setup, such as a symlinked data file, the year 9999, or invisible characters in an ID, is P2 at most
   - Naming, style, and taste are not defects
   - A flaw in a check you built counts only when it hides a real failure of this order. Otherwise it is a drop
   - A gap or a conflict in the recipe that matters in real use: fix the recipe and log `recipe`. Anything else is a next order
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
   - L: serve a first-time customer, once per order. Give a fresh subagent that never saw the work only recipe.md, the result, and cupping.tsv. It checks each acceptance criterion on the real thing and reports PASS or FAIL with evidence. It also rechecks every `drop` and P2 row and says which ones really are P0 or P1 in real use. If it reopens the order, the next SERVE goes straight to the receipt, because the new rounds' cuppers tasted the fix.
2. If anything fails or turns out to be P0 or P1, reproduce it, log it as `defect -s P0|P1` under the last round, add a house note, run `cafe.py check`, and follow the verdict.
3. On SERVE, do the irreversible steps the order asked for, such as a commit and a push. After CLOSE, leave them for the user.
4. Hand over the receipt. Fill in this template, with the labels in the user's language. Write "none" for an empty item.

   ```markdown
   ## Order up: <the goal in your own words>

   **SERVE** · size <S|M|L> · <rounds> rounds · <cup rows> cuppers · notes in `.cafe/<order>/`

   Runtime: <host> · Verification: full

   Cupping: <each round line from the last cafe.py check, such as R1 2 P0/P1 defects · R2 clean>

   | # | Acceptance criterion | Result | Evidence |
   |---|---|---|---|
   | 1 | <criterion> | PASS | `<command>` → <the output that proves it> |

   - **Changed:** <files>, +<added> −<removed>, <uncommitted, or the commit and where it was pushed>
   - **Left for you:** <irreversible steps the order did not ask for, or that CLOSE held back>
   - **Assumed:** <each choice you made>, not <the option you did not pick>
   - **Remaining risks:** <each P2 left, and what it costs>
   - **Next orders:** <ideas outside the recipe>
   - **House notes:** <lines this order added>
   ```

   After CLOSE, the heading is `## Order closed: <goal>`, the verdict is **CLOSE**, and the list starts with **Open defects:** each open P0 or P1 with its repro command.
