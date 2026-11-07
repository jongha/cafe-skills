---
name: latte
description: "Mr. Latte's signature. Finishes what you order, end to end. Fixes the recipe (acceptance criteria) first. Each round, fresh cuppers taste the work from a new viewpoint with a new method and actually run it, and the barista fixes defects until a judge script says SERVE. Runs on one AI. Use for /latte, 'finish this end to end', 'make it complete', or when every review keeps finding new problems."
disable-model-invocation: true
argument-hint: "<what to make, or the branch to finish>"
---

# latte

Order: $ARGUMENTS

No cup leaves the bar untasted.

Reviews keep finding new problems for three reasons. The bar is not fixed. A review picks the few problems that stand out. A fix in one place breaks another. latte fixes the recipe first, turns finding into filling tables and running things, and lets a script decide when to serve.

## House rules

- You are the barista. You brew, call the cuppers, judge defects, and fix them.
- Serve only when `cafe.py check` says SERVE. Never declare done yourself.
- Drop any finding without evidence. Evidence is a command and its output, a failing test, or a `file:line` with the acceptance criterion it breaks.
- Do not fix findings outside the recipe. Add each as one line under "Next order" in recipe.md.
- Fix the cause, not the single case. Find every place with the same cause, fix them together, and add a regression test.
- Every cupper is a fresh subagent. Never pass it the conversation or your reasoning.
- Ask before anything irreversible: push, deploy, deleting data, sending messages outside. Do everything else without asking.
- Talk to the user in their language.

`cafe.py` means `python3 ${CLAUDE_SKILL_DIR}/scripts/cafe.py`. The cupping table and the cupper brief are in `${CLAUDE_SKILL_DIR}/cupping.md`.

## The bar

Everything lives at the project root. `<order>` is a short slug for the task.

```
.cafe/
  house-notes.md        kinds of defects earlier rounds missed. Kept after the order is done
  <order>/recipe.md      the recipe
  <order>/cupping.tsv    cupping notes. Write only with cafe.py add
  <order>/scratch/       files cuppers make to check things
```

Add `.cafe/*/` to `.git/info/exclude` so order folders stay out of git. House notes can be committed to share with the team.

## 1. Recipe

1. Restate the order in your own words: the goal, the problem it solves, and the smallest change you expect.
2. Write `.cafe/<order>/recipe.md`.

   ```markdown
   # <order>
   Goal: <one sentence>

   ## Acceptance criteria
   1. <a statement that running something proves true or false>. Check: `<command>`

   ## Not doing
   - <out of scope>

   ## Next order
   - <ideas from cupping that are outside the recipe>
   ```

3. Claim rehearsal. Give a fresh subagent only the goal and the draft recipe, and ask: "This cup went out and a customer complained. Write 10 possible reasons." Add what belongs in the recipe to the acceptance criteria.
4. The recipe is now fixed. If you change it later, run `cafe.py add <notes> <round> recipe "<what and why>"`. The judge stops counting clean rounds up to that round.

If the order is to finish existing code, read the goal from the branch, the commits, and the PR description. Write the recipe, run the claim rehearsal, then go to cupping.

## 2. Brew

1. Build the check for each acceptance criterion first: a test, a script, or a command. Run it now and watch it fail.
2. Build in small units. Run the checks after each unit and move on only when they pass.
3. When every check passes, go to cupping.

## 3. Cupping

For each round R, starting at 1:

1. Take round R's three cuppers from the cupping table. Each brief is the cupper brief with only the `<>` filled in. Add nothing else.
2. Launch the cuppers that are not on bad shot in one message (`subagent_type: "general-purpose"`). A bad shot cupper edits source for a moment, so launch it alone after the others finish.
3. Compare `git status --short` and `git diff --stat` from before and after the cuppers. Revert any source change they left.
4. For each cupper, run `cafe.py add <notes> R cup -t yes|no "<viewpoint> x <method>"`. `yes` means that cupper actually ran something.
5. Reproduce every finding yourself and judge it. Keep it as `defect -s P0|P1|P2` or drop it as `drop`, with the reason in the note.
   - P0: data loss, security, crash
   - P1: breaks an acceptance criterion
   - P2: any other flaw whose cost you can name
   - Naming, style, and taste are not defects
   - A gap or a conflict in the recipe that touches the goal: fix the recipe and log `recipe`. Anything else is a next order
6. Fix the defects. Find the cause, fix every instance, add a regression test, and rerun every check.
7. If an earlier round missed this defect, add a line to the house notes: `- <what was missed>. Look for: <what would have caught it>`
8. Run `cafe.py check .cafe/<order>/cupping.tsv` and follow the verdict.

| Verdict | Do |
|---|---|
| SERVE | Go to serve |
| RECUP | Run the next round |
| REBREW | Stop patching. Write down in one sentence the premise the failed fixes shared, and test that premise first. Fix the design, log `rebrew`, and run the next round |
| CLOSE | Go to serve and report that it did not converge. Never lower the bar to reach SERVE |

## 4. Serve

1. Serve a first-time customer. Give a fresh subagent that never saw the work only recipe.md and the result. It checks each acceptance criterion on the real thing and reports PASS or FAIL with evidence.
2. On any FAIL, log `defect -s P1` under the next round number, add a house note, and go back to cupping.
3. Report:
   - Order: the goal in your own words
   - Verdict: SERVE or CLOSE, and the number of rounds
   - Evidence for each acceptance criterion
   - Remaining risks and next orders
   - Lines added to the house notes

If you can pick more than one model, such as opus and sonnet, mix them across cuppers. If another AI's CLI is available, one cupper can use it. latte works the same without either.
