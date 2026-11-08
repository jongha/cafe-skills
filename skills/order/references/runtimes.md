# Runtime adapters

Use the section for the actual host, not the model name. Every host reads the same `SKILL.md`; Codex ignores its Claude-only header fields.

## Codex

- Invoke with `$order <task>` in the CLI or IDE, or select the skill in the app. The task comes from the user message.
- Use the native subagent tool (often `spawn_agent`). Select a fresh context with `fork_turns: "none"` or `fork_context: false`, only if that field exists in the exposed schema. Do not pass Claude's `subagent_type` or `model: "sonnet"`; subagents use the configured model.
- Give each reviewer its brief and absolute file paths, without the parent conversation, previous reviews, or proposed answers. Wait with the host's wait tool, and release finished agents if the host needs the slots.
- `agents/openai.yaml` keeps this skill explicit-only. It does not set models or grant tools.

## Claude Code

- The plugin command is `/cafe:order <task>`; a standalone installation uses `/order <task>`.
- Use the Agent tool with `subagent_type: "general-purpose"` and `model: "sonnet"` to keep time and tokens down; leave the model out if Sonnet is unavailable. Start a new agent for each brief; never resume a previous reviewer.

## Grok Build / Grok CLI

- Use `/order <task>` or `/skills order`, or ask in words ("Use the order skill to fix …").
- Use the native subagent tool (`task`) and start child sessions without inherited history. Use only its documented parameters and the configured model; Codex and Claude parameter names do not carry over.
- If subagents are disabled or a fresh context cannot be selected, use limited verification. Do not silently change global settings or claim isolated reviewers ran.

## Limited verification

When full verification is unavailable:

1. State the missing capability once. Write the recipe and make the changes and checks the available tools permit. If files cannot be written, give a patch or the content in the response.
2. Use the cupping viewpoints for a bounded self-review. Label it self-review; do not write `cup` rows for it or invent rehearsal or customer subagents. Do not run empty rounds to manufacture CLOSE.
3. Keep real command output and label every unrun criterion NOT CHECKED. If notes cannot be written, keep the evidence in the response. If Python cannot run, do not simulate a `cafe.py` verdict.
4. Hand over **UNVERIFIED**: the changes, the checks that actually ran, remaining findings, and what full verification needs. Leave commit, push, deployment, and other gated external actions pending. Never relabel UNVERIFIED as SERVE or CLOSE.

If a full run loses a required tool or permission midway, keep the real notes and hand over the same way. On resume, verify the current files before reusing evidence.
