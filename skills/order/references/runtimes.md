# Runtime adapters

The workflow and judge are shared. The host supplies file access, command execution, approvals, and subagents. Use the section matching the actual host, not just the model name. Every host reads the same `SKILL.md`: Codex ignores the Claude-only header fields, and Grok honors them.

## Codex

- Invoke the installed skill with `$order <task>` in the CLI/IDE, or select the skill in the app. The task comes from the user message.
- Use the available native subagent tool (often `spawn_agent`). Select a fresh context: `fork_turns: "none"` or `fork_context: false` only if that field exists in the exposed tool schema. Do not pass Claude's `subagent_type` or `model: "sonnet"`. Subagents use the configured model.
- Give each reviewer its brief and absolute file paths, without the parent conversation, previous reviews, or proposed answers. Wait for completion using the host's wait tool. Release finished agents if the host offers that operation and needs the slots.
- `agents/openai.yaml` keeps this skill explicit-only. It does not configure agent models or grant tools.

## Claude Code

- The plugin command is `/cafe:order <task>`. A standalone installation uses `/order <task>`.
- Use the Agent tool with `subagent_type: "general-purpose"` and `model: "sonnet"` to keep time and tokens down. If Sonnet is not available, leave the model out. Start a new agent for each brief; do not resume a previous reviewer.
- `${CLAUDE_SKILL_DIR}` in `SKILL.md` is the skill directory.

## Grok Build / Grok CLI

- Use `/order <task>` or `/skills order`. Natural-language invocation such as “Use the order skill to fix …” also supplies the task explicitly.
- Grok also loads Claude Code skills and installed Claude plugins. When two skills share a name, Grok keeps the one from the higher-priority location.
- Use the native subagent tool (`task`). Start child sessions without inherited conversation history. Use only its documented parameters and the configured model; neither Codex nor Claude parameter names are portable.
- If subagents are disabled or a fresh context cannot be selected, use limited verification. Do not silently change global settings or claim three isolated reviewers ran.

## Limited verification

When full verification is unavailable:

1. State the missing capability once. Write the recipe and make the changes and checks that the available tools permit. If files cannot be written, provide a patch or the requested content in the response.
2. Use the cupping viewpoints for a bounded self-review. Label it as self-review; do not create `cup` rows for it or invent claim-rehearsal/customer subagents. Do not run five empty rounds trying to manufacture CLOSE.
3. Preserve real command output and label every unrun criterion NOT CHECKED. If notes cannot be written, keep the evidence in the response. If Python cannot run, do not simulate a `cafe.py` verdict.
4. Hand over **UNVERIFIED**, the changes, checks that actually ran, remaining findings, and what is needed to resume full verification. Leave commit, push, deployment, and other gated external actions pending. Never relabel UNVERIFIED as SERVE or CLOSE.

If a full run loses a required tool or permission midway, preserve the real notes and follow the same handoff. On resume, verify the current files before reusing evidence.
