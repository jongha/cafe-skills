# cafe-skills

<p align="center">
  <img src="assets/hero.jpg" alt="Mr. Latte smiles and pours latte art behind the counter. Three cupping bowls wait on the left, and a service bell and a finished latte wait on the right." width="720">
</p>

<p align="center">
  <b>No cup leaves the bar untasted.</b><br>
  맛보지 않은 잔은 손님에게 나가지 않습니다.
</p>

[English](#english) · [한국어](#한국어)

---

## English

Mr. Latte's cafe for Claude Code. Place an **order**, and it comes back finished.

### order

**Hand off any task and get it back finished.** A bug fix, a feature, a refactor, or a branch to finish: `order` takes it, never stops to ask, and keeps working until a judge script says it is ready. If it is not ready after five rounds, it reports what is still open. You do not have to review it round after round yourself.

AI-built work has a familiar loop. You review it and find problems. You fix them and review again, and find new ones. You ask another AI and it finds still others. `order` is built to end that loop.

| Why the loop never ends | What `order` does |
|---|---|
| The bar is never fixed, so every reviewer invents their own. | Writes the acceptance criteria down before any code. Every review and the final check use that one bar. |
| A review picks the few problems that stand out. | Each round, three fresh cuppers each take one viewpoint and one method from a fixed table, and run what they suspect instead of only reading. |
| A fix in one place breaks another. | Every fix gets a regression test and is tasted again by new cuppers. The work ends only after two clean rounds in a row. |

**What you get**

- **Finished means finished.** Only `cafe.py check` can end the work, not the AI's own sense of being done. If the work does not converge in five rounds, the report says so.
- **Evidence, not opinions.** A finding counts only with a command and its output, a failing test, or the line and the criterion it breaks.
- **A second opinion without a second AI.** Fresh subagents with new viewpoints and methods do what another AI would.
- **You can walk away.** It never stops to ask. Each open choice becomes a written assumption in the report. It pushes, deploys, or deletes data only when your order says so, and otherwise leaves those steps for you.
- **It learns your project.** Every defect a round missed becomes a house note that later reviews read first.

**What to order.** Any task you would hand to a careful engineer: a bug fix, a feature, a refactor, tests, docs, or a branch to finish. The recipe grows with the order, so a small order has at most three criteria and a small scope. Every order runs at least eight fresh subagents (a claim rehearsal, two rounds of three cuppers, and a first-time customer) and at most about seventeen, so it costs more than a single review. To keep that down, the subagents run on Sonnet and size their work to the change. In exchange, you do not review it round after round.

#### How it works

<p align="center">
  <img src="assets/flow.svg" alt="Your order goes through 1 Recipe, 2 Brew, 3 Cupping, and 4 Serve. After each cupping round, cafe.py check gives a verdict before anything is fixed: SERVE after two clean rounds in a row, RECUP to fix and taste again, REBREW to recheck the design, CLOSE after five rounds." width="100%">
</p>

| Step | What happens |
|---|---|
| 1. Recipe | Fix the acceptance criteria and the non-goals before any code. A claim rehearsal asks "this shipped and a customer complained. Why?" and adds to the recipe only what would break the goal in real use. Open choices become written assumptions, so it never stops to ask. |
| 2. Brew | Build the checks first, then build in small units, each one checked before the next. |
| 3. Cupping | Each round, three fresh cuppers review independently. Each gets one viewpoint and one method from a fixed table. Only defects with evidence survive. `cafe.py check` judges the round before any fix, so no untasted fix goes out. Each defect is fixed at its cause, and a regression test is added. |
| 4. Serve | A first-time customer, a new agent that never saw the work, verifies each criterion on the real thing and rechecks every finding the barista dropped. |

**Fresh eyes with one AI.** You need only Claude Code. Most of what a second AI adds comes from fresh context and a different angle, and one model can supply both:

<p align="center">
  <img src="assets/cupping.svg" alt="The cupping table: four viewpoints (recipe check, customer, difficult customer, next barista) by four methods (30 complaints, order sheet, bad shot, blind tasting). Each of five rounds uses three different pairs, and no pair repeats." width="100%">
</p>

- **Fresh cuppers.** Each cupper is a new subagent that sees only the recipe and the code, not your conversation.
- **Viewpoints.** Recipe check, customer, difficult customer, and next barista.
- **Methods.** 30 complaints (list up to 30 ways it could fail in real use, then run each), order sheet (a table of edge-case inputs to run), bad shot (break a line on purpose and see if a check catches it), and blind tasting (write a spec from the code alone, then compare it with the recipe).
- **House notes.** Each defect a round missed adds a line to `.cafe/house-notes.md`. Every later cupper reads that file first.

**When it ends.** Two clean rounds in a row: no P0 or P1 defects, at least three cuppers, and at least one cupper actually ran something. P0 and P1 count only what can happen in real use, so the bar does not creep toward contrived cases. Changing the recipe resets the count, so a late change can end in CLOSE. If serious defects stop going down, the verdict is REBREW, which means stop patching and recheck the design. After five rounds the verdict is CLOSE, and the report says the work did not converge.

### Install

```
/plugin marketplace add jongha/cafe-skills
/plugin install cafe@cafe-skills
```

### Use

```
/cafe:order fix the missing last page in pagination
/cafe:order add CSV export to the orders page
/cafe:order finish this branch and push it
```

`order` keeps its work in `.cafe/` at the project root. Each order gets a folder with `recipe.md`, `cupping.tsv`, and `scratch/`. Order folders stay out of git. `house-notes.md` is shared across orders, and you can commit it for your team. If a run stops midway, give the same order again and it continues where it stopped.

**Before you walk away.** Claude Code still asks before commands it has not been allowed to run. Use auto mode, or allow your build and test commands with `/permissions`, so the run does not wait on a prompt. The result stays uncommitted unless your order asks for a commit or a push.

### Files

```
skills/order/SKILL.md          the workflow
skills/order/cupping.md        cupping table, viewpoints, methods, cupper brief
skills/order/scripts/cafe.py   cupping notes and the verdict (python3, no dependencies)
assets/                        images for this README
```

From a clone of this repo, run `python3 skills/order/scripts/cafe.py self-test` to check the verdict rules.

### License

MIT

---

## 한국어

Claude Code 용 Mr. Latte 의 카페입니다. **order** 로 주문하면 끝까지 완성합니다.

### order

**어떤 일이든 맡기면, 끝까지 완성된 결과를 돌려받습니다.** 버그 수정, 기능 추가, 리팩터링, 브랜치 마무리 무엇이든 `order` 가 받아서, 묻느라 멈추지 않고 판정 스크립트가 준비됐다고 할 때까지 작업합니다. 5라운드를 마치고도 준비되지 않으면 남은 문제를 보고합니다. 리뷰를 몇 번이고 직접 반복하지 않아도 됩니다.

AI 로 만든 결과물은 리뷰할 때마다 새 문제가 나옵니다. 고치고 다시 보면 또 나오고, 다른 AI 에게 맡기면 또 다른 문제가 나옵니다. `order` 는 이 반복을 끝내려고 만들었습니다.

| 반복이 끝나지 않는 이유 | `order` 가 하는 일 |
|---|---|
| 기준이 고정돼 있지 않아 리뷰어마다 기준을 새로 만듭니다 | 코드를 쓰기 전에 수용 기준을 적어 둡니다. 모든 리뷰와 마지막 확인이 이 기준 하나를 씁니다 |
| 리뷰가 눈에 띄는 몇 개만 집습니다 | 라운드마다 새 커퍼 셋이 정해진 표에서 관점과 방법을 하나씩 받아, 읽기만 하지 않고 의심 가는 것을 직접 돌려 봅니다 |
| 한 곳을 고치면 다른 곳이 깨집니다 | 수정마다 회귀 테스트를 더하고, 새 커퍼가 다시 맛봅니다. 깨끗한 라운드가 연속 두 번 나와야 작업이 끝납니다 |

**좋은 점**

- **끝났다고 하면 정말 끝난 것입니다.** 작업을 끝내는 것은 AI 의 느낌이 아니라 `cafe.py check` 입니다. 5라운드 안에 수렴하지 않으면 그렇다고 보고합니다.
- **의견이 아니라 증거만 남습니다.** 명령과 출력, 실패하는 테스트, 또는 어긴 수용 기준과 코드 위치가 있어야 지적으로 인정합니다.
- **AI 하나로 두 번째 의견을 얻습니다.** 새 관점과 방법을 받은 새 서브에이전트가 다른 AI 의 몫을 합니다.
- **맡기고 자리를 비워도 됩니다.** 묻느라 멈추지 않습니다. 열린 선택은 가정으로 적어 보고서에 남깁니다. 푸시, 배포, 데이터 삭제는 주문에 적혀 있을 때만 하고, 아니면 사용자 몫으로 남깁니다.
- **쓸수록 프로젝트를 배웁니다.** 라운드가 놓친 디펙트는 하우스 노트가 되고, 이후의 리뷰가 먼저 읽습니다.

**무엇을 주문하나.** 꼼꼼한 엔지니어에게 맡길 만한 일이면 무엇이든 됩니다. 버그 수정, 기능 추가, 리팩터링, 테스트, 문서, 브랜치 마무리 같은 것입니다. 레시피는 주문 크기에 맞춰 커지므로, 작은 주문은 수용 기준이 3개 이하이고 범위도 작습니다. 어떤 주문이든 새 서브에이전트가 적어도 8번(클레임 리허설 1, 커퍼 3명씩 두 라운드, 처음 온 손님 1), 많으면 17번 안팎 돌기 때문에 한 번 리뷰하는 것보다 비용이 더 듭니다. 그래서 서브에이전트는 Sonnet 으로 돌리고, 변경 크기에 맞춰 일의 양을 줄입니다. 대신 리뷰를 몇 번이고 직접 반복하지 않아도 됩니다.

#### 작동 방식

<p align="center">
  <img src="assets/flow.svg" alt="주문은 1 레시피, 2 추출, 3 커핑, 4 서빙을 거칩니다. 커핑 라운드가 끝날 때마다 고치기 전에 cafe.py check 가 판정합니다. 깨끗한 라운드가 연속 두 번이면 SERVE, 고치고 다시 맛보면 RECUP, 설계를 다시 보면 REBREW, 5라운드를 마치고도 끝나지 않으면 CLOSE 입니다." width="100%">
</p>

| 단계 | 하는 일 |
|---|---|
| 1. 레시피 | 코드를 쓰기 전에 수용 기준과 하지 않을 것을 고정합니다. 클레임 리허설에서 "손님에게 나간 뒤 클레임이 들어왔다. 왜인가"를 먼저 묻고, 실제 사용에서 목표를 깨는 것만 레시피에 더합니다. 열린 선택은 가정으로 적어 두고, 묻느라 멈추지 않습니다 |
| 2. 추출 | 확인 방법을 먼저 만듭니다. 그다음 작은 단위로 구현하고, 단위마다 확인합니다 |
| 3. 커핑 | 라운드마다 새 커퍼 셋이 서로 모른 채 리뷰합니다. 커퍼마다 정해진 표에서 관점 하나와 방법 하나를 받습니다. 증거가 있는 디펙트만 남깁니다. 고치기 전에 `cafe.py check` 가 라운드를 판정하므로, 아무도 맛보지 않은 수정은 나가지 않습니다. 디펙트는 원인을 고치고 회귀 테스트를 더합니다 |
| 4. 서빙 | 과정을 본 적 없는 새 에이전트가 처음 온 손님이 되어, 수용 기준을 실물로 하나씩 확인하고, 바리스타가 버린 지적도 다시 판정합니다 |

**AI 하나로 새 눈을 만듭니다.** Claude Code 하나면 됩니다. 다른 AI 가 주는 효과는 대부분 새로운 맥락과 다른 각도에서 나옵니다. 둘 다 모델 하나로 만들 수 있습니다.

<p align="center">
  <img src="assets/cupping.svg" alt="커핑 표: 관점 넷(레시피 검수, 손님, 까다로운 손님, 다음 바리스타)과 방법 넷(클레임 30개, 주문표, 망친 샷, 블라인드 테이스팅)을 엮습니다. 5라운드 동안 라운드마다 다른 조합 셋을 쓰고, 같은 조합은 다시 나오지 않습니다." width="100%">
</p>

- **새 커퍼.** 커퍼는 매번 새 서브에이전트입니다. 대화 내용은 보지 못하고 레시피와 코드만 받습니다.
- **관점.** 레시피 검수, 손님, 까다로운 손님, 다음 바리스타입니다.
- **방법.** 넷입니다.
  - 클레임 30개: 실제 사용에서 틀릴 수 있는 경우를 30가지까지 뽑고 하나씩 돌려 봅니다.
  - 주문표: 경계 입력의 표를 만들어 칸마다 돌려 봅니다.
  - 망친 샷: 일부러 한 줄을 망가뜨리고 확인이 알아채는지 봅니다.
  - 블라인드 테이스팅: 레시피를 보지 않고 코드만으로 명세를 쓴 뒤 레시피와 견줍니다.
- **하우스 노트.** 라운드가 놓친 디펙트마다 `.cafe/house-notes.md` 에 한 줄이 쌓입니다. 이후의 모든 커퍼가 이 파일을 먼저 읽습니다.

**언제 끝나나.** 깨끗한 라운드가 연속 두 번 나와야 작업이 끝납니다. 깨끗한 라운드는 커퍼가 셋 이상이고, 실제로 돌려 본 커퍼가 하나 이상이고, P0·P1 디펙트가 없는 라운드입니다. P0·P1 은 실제 사용에서 일어날 수 있는 것만 셉니다. 그래야 기준이 억지 사례 쪽으로 끝없이 올라가지 않습니다. 레시피를 고치면 처음부터 다시 셉니다. 그래서 늦게 고치면 CLOSE 로 끝날 수 있습니다. 심각한 디펙트 수가 줄지 않으면 REBREW 가 나옵니다. 땜질을 멈추고 설계를 다시 보라는 뜻입니다. 5라운드를 마치고도 끝나지 않으면 CLOSE 가 나오고, 미수렴이라고 그대로 보고합니다.

### 설치

```
/plugin marketplace add jongha/cafe-skills
/plugin install cafe@cafe-skills
```

### 사용

```
/cafe:order 페이지네이션에서 마지막 페이지가 빠지는 버그 고쳐줘
/cafe:order 주문 페이지에 CSV 내보내기 추가
/cafe:order 이 브랜치 마무리하고 푸시까지 해줘
```

작업 기록은 프로젝트 루트의 `.cafe/` 에 남습니다. 주문마다 폴더가 하나씩 생기고, 그 안에 `recipe.md`, `cupping.tsv`, `scratch/` 가 들어갑니다. 주문 폴더는 git 에서 뺍니다. `house-notes.md` 는 모든 주문이 함께 쓰는 파일이라 팀과 나누도록 커밋해도 됩니다. 중간에 멈췄다면 같은 주문을 다시 내면 멈춘 곳부터 이어 갑니다.

**자리를 비우기 전에.** Claude Code 는 아직 허용하지 않은 명령을 실행하기 전에 묻습니다. auto mode 를 쓰거나, `/permissions` 로 빌드와 테스트 명령을 허용해 두어야 실행이 확인 창에서 멈추지 않습니다. 결과는 커밋하지 않은 상태로 남습니다. 커밋이나 푸시는 주문에 적었을 때만 합니다.

### 파일

```
skills/order/SKILL.md          흐름
skills/order/cupping.md        커핑 표, 관점, 방법, 커퍼 지시문
skills/order/scripts/cafe.py   커핑 노트 기록과 판정 (python3, 의존성 없음)
assets/                        이 README 의 이미지
```

판정 규칙은 이 저장소를 클론한 뒤 `python3 skills/order/scripts/cafe.py self-test` 로 확인합니다.

### 라이선스

MIT
