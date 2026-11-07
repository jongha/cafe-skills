# cafe-skills

[English](#english) · [한국어](#한국어)

---

## English

Mr. Latte's cafe for Claude Code. The first item on the menu is **latte**.

### latte

AI-built work has a familiar loop. You review it and find problems. You fix them and review again, and find new ones. You ask another AI and it finds still others. latte is built to end that loop. It finishes what you order end to end, and it serves only when a judge script says the cup is ready.

The loop keeps going for three reasons:

- The bar is never fixed, so every reviewer invents their own.
- A review picks the few problems that stand out, not all of them.
- A fix in one place breaks another.

latte answers each one:

| Step | What happens |
|---|---|
| 1. Recipe | Fix the acceptance criteria and the non-goals before any code. A claim rehearsal asks "this shipped and a customer complained. Why?" and adds what it finds to the recipe. |
| 2. Brew | Build the checks first, then build in small units, each one checked before the next. |
| 3. Cupping | Each round, three fresh cuppers review blind. Each gets one viewpoint and one method from a fixed table. Only defects with evidence survive. Each defect is fixed at its cause, and a regression test is added. |
| 4. Serve | `cafe.py check` decides. A first-time customer, a new agent that never saw the work, verifies each criterion on the real thing. |

**Fresh eyes with one AI.** You need only Claude Code. Most of what a second AI adds comes from fresh context and a different angle, and one model can supply both:

- **Fresh cuppers.** Each cupper is a new subagent that sees only the recipe and the code, not your conversation.
- **Viewpoints.** Recipe check, customer, difficult customer, and next barista.
- **Methods.** 30 complaints (list 30 ways it could fail, then run each), order sheet (a table of edge-case inputs to run), bad shot (break a line on purpose and see if a check catches it), and blind tasting (write a spec from the code alone, then compare it with the recipe).
- **House notes.** Each defect a round missed adds a line to `.cafe/house-notes.md`. Every later cupper reads that file first.

**When it serves.** Two clean rounds in a row: no P0 or P1 defects, at least three cuppers, and at least one cupper actually ran something. Changing the recipe resets the count. If serious defects stop going down, the verdict is REBREW, which means stop patching and recheck the design. After five rounds the verdict is CLOSE, and the report says the work did not converge.

### Install

```
/plugin marketplace add jongha/cafe-skills
/plugin install cafe@cafe-skills
```

### Use

```
/cafe:latte add CSV export to the orders page
/cafe:latte finish this branch
```

latte keeps its work in `.cafe/` at the project root. Each order gets a folder with `recipe.md`, `cupping.tsv`, and `scratch/`. Order folders stay out of git. `house-notes.md` is shared across orders, and you can commit it for your team.

### Files

```
skills/latte/SKILL.md          the workflow
skills/latte/cupping.md        cupping table, viewpoints, methods, cupper brief
skills/latte/scripts/cafe.py   cupping notes and the verdict (python3, no dependencies)
```

Run `python3 skills/latte/scripts/cafe.py self-test` to check the verdict rules.

### License

MIT

---

## 한국어

Claude Code 용 Mr. Latte 의 카페입니다. 첫 번째 메뉴는 **latte** 입니다.

### latte

AI 로 만든 결과물은 리뷰할 때마다 새 문제가 나옵니다. 고치고 다시 보면 또 나오고, 다른 AI 에게 맡기면 또 다른 문제가 나옵니다. latte 는 이 반복을 끝내려고 만들었습니다. 주문받은 것을 처음부터 끝까지 완성하고, 판정 스크립트가 통과를 내야만 내놓습니다.

반복이 끝나지 않는 이유는 셋입니다.

- 기준이 고정돼 있지 않아 리뷰어마다 기준을 새로 만듭니다.
- 리뷰가 눈에 띄는 몇 개만 집습니다.
- 한 곳을 고치면 다른 곳이 깨집니다.

latte 는 이렇게 답합니다.

| 단계 | 하는 일 |
|---|---|
| 1. 레시피 | 코드를 쓰기 전에 수용 기준과 하지 않을 것을 고정합니다. 클레임 리허설에서 "손님에게 나간 뒤 클레임이 들어왔다. 왜인가"를 먼저 묻고, 나온 것을 레시피에 더합니다 |
| 2. 추출 | 확인 방법을 먼저 만듭니다. 그다음 작은 단위로 구현하고, 단위마다 확인합니다 |
| 3. 커핑 | 라운드마다 새 커퍼 셋이 서로 모른 채 리뷰합니다. 커퍼마다 정해진 표에서 관점 하나와 방법 하나를 받습니다. 증거가 있는 디펙트만 남깁니다. 디펙트는 원인을 고치고 회귀 테스트를 더합니다 |
| 4. 서빙 | `cafe.py check` 가 판정합니다. 과정을 본 적 없는 새 에이전트가 처음 온 손님이 되어, 수용 기준을 실물로 하나씩 확인합니다 |

**AI 하나로 새 눈을 만듭니다.** Claude Code 하나면 됩니다. 다른 AI 가 주는 효과는 대부분 새로운 맥락과 다른 각도에서 나옵니다. 둘 다 모델 하나로 만들 수 있습니다.

- **새 커퍼.** 커퍼는 매번 새 서브에이전트입니다. 대화 내용은 보지 못하고 레시피와 코드만 받습니다.
- **관점.** 레시피 검수, 손님, 까다로운 손님, 다음 바리스타입니다.
- **방법.** 넷입니다.
  - 클레임 30개: 틀릴 수 있는 경우 30가지를 뽑고 하나씩 돌려 봅니다.
  - 주문표: 경계 입력의 표를 만들어 칸마다 돌려 봅니다.
  - 망친 샷: 일부러 한 줄을 망가뜨리고 확인이 알아채는지 봅니다.
  - 블라인드 테이스팅: 레시피를 보지 않고 코드만으로 명세를 쓴 뒤 레시피와 견줍니다.
- **하우스 노트.** 라운드가 놓친 디펙트마다 `.cafe/house-notes.md` 에 한 줄이 쌓입니다. 이후의 모든 커퍼가 이 파일을 먼저 읽습니다.

**언제 내놓나.** 깨끗한 라운드가 연속 두 번 나와야 내놓습니다. 깨끗한 라운드는 커퍼가 셋 이상이고, 실제로 돌려 본 커퍼가 하나 이상이고, P0·P1 디펙트가 없는 라운드입니다. 레시피를 고치면 처음부터 다시 셉니다. 심각한 디펙트 수가 줄지 않으면 REBREW 가 나옵니다. 땜질을 멈추고 설계를 다시 보라는 뜻입니다. 5라운드를 넘기면 CLOSE 가 나오고, 미수렴이라고 그대로 보고합니다.

### 설치

```
/plugin marketplace add jongha/cafe-skills
/plugin install cafe@cafe-skills
```

### 사용

```
/cafe:latte 주문 페이지에 CSV 내보내기 추가
/cafe:latte 이 브랜치 마무리해줘
```

작업 기록은 프로젝트 루트의 `.cafe/` 에 남습니다. 주문마다 폴더가 하나씩 생기고, 그 안에 `recipe.md`, `cupping.tsv`, `scratch/` 가 들어갑니다. 주문 폴더는 git 에서 뺍니다. `house-notes.md` 는 모든 주문이 함께 쓰는 파일이라 팀과 나누도록 커밋해도 됩니다.

### 파일

```
skills/latte/SKILL.md          흐름
skills/latte/cupping.md        커핑 표, 관점, 방법, 커퍼 지시문
skills/latte/scripts/cafe.py   커핑 노트 기록과 판정 (python3, 의존성 없음)
```

판정 규칙은 `python3 skills/latte/scripts/cafe.py self-test` 로 확인합니다.

### 라이선스

MIT
