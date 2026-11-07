---
name: order
description: "Place an order at Mr. Latte's cafe and get it back finished, end to end. Takes any task, big or small, and never stops to ask. Fixes the recipe (acceptance criteria) first. Each round, fresh cuppers taste the work from a new viewpoint with a new method and actually run it, and the barista fixes defects until a judge script says SERVE. Runs on one AI. Use as /cafe:order <task>."
disable-model-invocation: true
argument-hint: "<what to make, or the branch to finish>"
---

# order

Order: $ARGUMENTS

No cup leaves the bar untasted.

Any task fits: a bug fix, a feature, a refactor, tests, docs, or a branch to finish. If the order is empty, finish the current branch. Size the recipe to the order. A small order, one you expect to touch one or two files, gets at most 3 acceptance criteria. A feature gets more.

Reviews keep finding new problems for three reasons. The bar is not fixed. A review picks the few problems that stand out. A fix in one place breaks another. This skill fixes the recipe first, turns finding into filling tables and running things, and lets a script decide when the work ends.

## House rules

- You are the barista. You brew, call the cuppers, judge defects, and fix them.
- End only when `cafe.py check` says SERVE or CLOSE. Never declare done yourself.
- Drop any finding without evidence. Evidence is a command and its output, a failing test, or a `file:line` with the acceptance criterion it breaks.
- Fix only what is in scope. A finding about something under "Not doing", or about code this order does not touch, goes under "Next order" in recipe.md. A P0 in code this order touches is always in scope.
- Fix the cause, not the single case. Find every place with the same cause, fix them together, and add a regression test.
- Every cupper is a fresh subagent. Never pass it the conversation or your reasoning.
- Run every subagent you launch on sonnet (`model: "sonnet"`) to keep time and tokens down. Stay on your own model for judging and fixing. If sonnet is not available, leave the model out.
- The user handed this off and may be away. Never stop to ask. When a choice is open, pick what a careful engineer would pick and write it under Assumptions.
- Do something irreversible (push, deploy, deleting data, sending messages outside) only when the order asks for it in words, and only after a SERVE. Otherwise list it in the report as left for the user. Leave the work uncommitted unless the order asks for a commit or a push.
- Talk to the user in their language.

`cafe.py` means `python3 ${CLAUDE_SKILL_DIR}/scripts/cafe.py`. From `check`, exit 1 is a normal verdict other than SERVE, so read the first line. Exit 2 means a bad line in the notes. Fix that line by hand and run it again. The cupping table and the cupper brief are in `${CLAUDE_SKILL_DIR}/cupping.md`.

## The bar

Everything lives at the project root. `<order>` is a short slug for the task.

```
.cafe/
  house-notes.md             kinds of defects earlier rounds missed. Kept after the order is done
  <order>/recipe.md          the recipe
  <order>/cupping.tsv        cupping notes. Write only with cafe.py add
  <order>/scratch/R<r>-<n>/  one folder per cupper, for the files it makes to check things
```

Add `.cafe/*/` to the file that `git rev-parse --git-path info/exclude` names, so order folders stay out of git. Never stage `.cafe/` unless the order asks.

Before you make a folder, read each `.cafe/*/recipe.md`. If one has this order's goal, continue it. If its cupping.tsv has rounds, run `cafe.py check` and follow the verdict. Otherwise start at Brew.

## 1. Recipe

1. Restate the order in your own words: the goal, the problem it solves, and the smallest change you expect. When the order leaves a choice open, pick the reasonable option and write it under Assumptions, with the option you did not pick.
2. Write `.cafe/<order>/recipe.md`.

   ```markdown
   # <order>
   Goal: <one sentence>

   ## Acceptance criteria
   1. <a statement that a check proves true or false>. Check: `<command>`

   ## Not doing
   - <out of scope>

   ## Assumptions
   - <a choice you made, and the option you did not pick>

   ## Next order
   - <ideas from cupping that are outside the recipe>
   ```

3. Claim rehearsal. Give a fresh subagent only the goal and the draft recipe, and ask: "This cup went out and a customer complained. Write 10 possible reasons." For a small order, ask for 5. Add a reason to the acceptance criteria only if it would break the goal in real use. Put the rest under Assumptions or Next order.
4. The recipe is now fixed. Only a change to the acceptance criteria or to "Not doing" is a recipe change. Adding an assumption or a next order is not. For a recipe change, run `cafe.py add <notes> <round> recipe "<what and why>"`, where `<round>` is the last round judged, or 0 before round 1. The judge stops counting clean rounds up to that round, so a late change can end in CLOSE.

If the order is to finish existing code, read the goal from the branch, the commits, and the PR description. Write the recipe and run the claim rehearsal. Then build the checks that are missing (Brew step 1), make them pass, and go to cupping.

## 2. Brew

1. Build the check for each acceptance criterion first: a test, a script, or a command. For a criterion nothing can run, such as the wording of a doc, the check is a fresh subagent that reads the result and quotes where it passes or fails. If a check cannot run here, for example because it needs a service or credentials you do not have, use the nearest check that can run and write the gap under Assumptions.
2. Run the checks now. A check for new or changed behavior must fail. A check that guards existing behavior may pass.
3. Build in small units. Run the checks after each unit and move on only when they pass. If a check still fails after three different approaches, go to cupping anyway and log it as `defect -s P1` in round 1. The round limit now bounds the work.
4. When every check passes, go to cupping.

## 3. Cupping

For each round R, starting at 1:

1. Save `git status --short` and `git diff` to `.cafe/<order>/scratch/R<R>-before.txt`. Without git, save a list of files with their modification times.
2. Take round R's three cuppers from the cupping table. Each brief is the cupper brief with only the `<>` filled in. Add nothing else. The scope must include uncommitted changes.
3. Launch all three cuppers in one message (`subagent_type: "general-purpose"`, `model: "sonnet"`).
4. Compare the project with the saved state. If a cupper changed it, undo that change and keep yours.
5. For each cupper, run `cafe.py add <notes> R cup -t yes|no "<viewpoint> x <method>"`. `yes` means that cupper ran something: a check, the code, a command, or the examples in a doc.
6. Reproduce every finding yourself and judge it. Keep it as `defect -s P0|P1|P2` or drop it as `drop`, with the reason in the note.
   - P0: data loss, security, crash
   - P1: breaks an acceptance criterion
   - P2: any other flaw whose cost you can name
   - P0 and P1 must happen in real use: normal input, a mistake real customers make, an attack, or a failure that really happens (a crash, a restart, a retry, two at once). A case that needs a contrived setup, such as a symlinked data file, the year 9999, or invisible characters in an ID, is P2 at most
   - Naming, style, and taste are not defects
   - A gap or a conflict in the recipe that matters in real use: fix the recipe and log `recipe`. Anything else is a next order
7. If an earlier round missed this defect, add a line to the house notes: `- <what was missed>. Look for: <what would have caught it>`
8. Run `cafe.py check .cafe/<order>/cupping.tsv` before you fix anything, and follow the verdict. No cupper would taste a fix made after the last round.

| Verdict | Do |
|---|---|
| SERVE | Leave the source as it is. List the round's P2s as remaining risks and go to serve |
| RECUP | Fix every defect, rerun every check, and run the next round |
| REBREW | Stop patching. Write down in one sentence the premise the failed fixes shared, and test that premise first. Fix the design, log `rebrew` at round R, and run the next round |
| CLOSE | Leave the source as it is. Go to serve and report that it did not converge, with the open defects. Never lower the bar to reach SERVE |

## 4. Serve

1. Serve a first-time customer. Give a fresh subagent that never saw the work only recipe.md, the result, and cupping.tsv. It checks each acceptance criterion on the real thing and reports PASS or FAIL with evidence. It also rechecks every `drop` and P2 row and says which ones really are P0 or P1 in real use.
2. If anything fails or turns out to be P0 or P1, reproduce it, log it as `defect -s P0|P1` under the last round, add a house note, run `cafe.py check`, and follow the verdict.
3. On SERVE, do the irreversible steps the order asked for, such as a commit and a push. After CLOSE, leave them for the user.
4. Hand over the receipt. Fill in this template, with the labels in the user's language. Write "none" for an empty item.

   ```markdown
   ## Order up: <the goal in your own words>

   **SERVE** · <rounds> rounds · <cup rows> cuppers · notes in `.cafe/<order>/`

   Cupping: <each round line from the last cafe.py check, such as R1 2 P0/P1 defects · R2 clean · R3 clean>

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

