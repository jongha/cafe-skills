# Cupping

## Cupping table

Each round pairs viewpoints and methods so no pair repeats. From round 6, start again at round 1.

| Round | Cupper 1 | Cupper 2 | Cupper 3 |
|---|---|---|---|
| 1 | Recipe check x Blind tasting | Difficult customer x 30 complaints | Customer x Order sheet |
| 2 | Recipe check x Order sheet | Next barista x 30 complaints | Difficult customer x Bad shot |
| 3 | Customer x 30 complaints | Next barista x Blind tasting | Recipe check x Bad shot |
| 4 | Difficult customer x Order sheet | Customer x Blind tasting | Next barista x Bad shot |
| 5 | Difficult customer x Blind tasting | Next barista x Order sheet | Customer x Bad shot |

If the change is too big for one cupper, split the scope and launch more cuppers with the same pair.

## Viewpoints

- **Recipe check.** Is each acceptance criterion really true? Where are the gaps the criteria do not mention?
- **Customer.** Follow real use from start to finish. When it fails, what does the customer see?
- **Difficult customer.** Strange input, requests beyond permission, the same request twice, requests at the same time, a cut midway, retries, huge input.
- **Next barista.** Look outside the changed code: callers, other readers of the same data, existing data, config and migrations, and what breaks when the next person changes it.

## Methods

- **30 complaints.** Write 30 ways this could go wrong from this viewpoint, unlikely ones included. Then run each and report only what reproduces.
- **Order sheet.** Build a table of inputs and states: empty, one, many, maximum, duplicate, out of order, failure midway, retry. Run every cell.
- **Bad shot.** Break key lines one at a time on purpose and run the checks. If the checks still pass, nothing guards that line. Restore each line right away.
- **Blind tasting.** Before reading the recipe, write a spec of what the code actually does from the code alone. Then read the recipe and compare. Each difference is a defect or a gap in the recipe.

## Cupper brief

Use this as is and fill in only the `<>`.

```
You are a cupper for latte. You are seeing this code for the first time.
Do not change source. Only if your method is bad shot, change a line for a moment, then restore it right away.
Put any files you make to check things only in <scratch path>.

- Recipe: <recipe.md path> (for blind tasting, read it only after your spec is written)
- Scope: <files, directories, or a git diff range>
- House notes: <house-notes.md path> (skip if missing)
- Viewpoint: <name and description>
- Method: <name and description>

1. Hold each house note against this scope.
2. Look for defects with your viewpoint and method. Run every suspicion.
3. Mark each acceptance criterion PASS, FAIL, or NOT CHECKED.

Report
- Acceptance criteria: one line per number
- Defects: title / criterion broken / repro command / actual output / expected output / file:line
- Ran: the commands you ran, or "none"
- Next order: ideas outside the recipe worth doing, one line each

Leave out guesses you did not run, naming and style taste, and risks that need some future change to matter.
For what you cannot run, give file:line and the criterion it breaks.
"No defects" is a valid answer.
```
