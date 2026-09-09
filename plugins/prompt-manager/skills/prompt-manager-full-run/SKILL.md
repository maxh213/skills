---
name: prompt-manager-full-run
description: >
  Run the full prompt-manager workflow: setup if needed, sprint-tasks, user
  picks a task, task-context, optional user thoughts/feedback, idea-to-prompt,
  then prompt-manager in a claimed worktree. Use when the user wants a full
  sprint-to-implementation run, "run prompt manager", or /prompt-manager-full-run.
  Pass --skip-thoughts (or --skip-feedback) to skip the gather-thoughts step.
argument-hint: "[--skip-thoughts] [TASK-ID]"
---

# Prompt-manager full run

Orchestrator only. Load each child skill's `SKILL.md` and follow it; do not restate those skills here.

## Flags

Parse `$ARGUMENTS` and the user message:

| Flag | Effect |
|---|---|
| `--skip-thoughts`, `--skip-feedback`, `--skip-gather` | Skip step 5 |
| a ClickUp id (`GLOBAL-12345` or digits) | That is the selected task; skip waiting on step 3 |

## Plugin root

Same resolution as setup-prompt-manager (`GROK_PLUGIN_ROOT` / `CLAUDE_PLUGIN_ROOT` / `credentials.py plugin-root`). Child skills live in `$PLUGIN_ROOT/skills/<name>/SKILL.md`.

## Steps

1. **Setup.** `python3 "$PLUGIN_ROOT/scripts/credentials.py" status`. If `ready` is false, follow `setup-prompt-manager/SKILL.md` first. Stop if required credentials are still missing.
2. **Sprint tasks.** Follow `sprint-tasks/SKILL.md`. Present the table.
3. **Select.** If a task id was passed, use it. Otherwise ask the user to pick one row. Confirm the resolved id before continuing.
4. **Task context.** Follow `task-context/SKILL.md` for that id. Keep the verdict-first brief.
5. **Thoughts / feedback** (default on). Ask once for extra constraints, corrections to the brief, or implementation preferences. If they have none, continue. **Skip this entire step** when a skip flag is set.
6. **Idea → prompt.** Follow `idea-to-prompt/SKILL.md`. The idea is the brief plus any step-5 notes. Target repo is the user's cwd git repo unless they named another. This step claims the worktree and writes `PROMPT-<slug>.md`. If the claim is `reused` and `previous_status` is `done`, ask before regenerating.
7. **Prompt manager.** Follow `prompt-manager/SKILL.md` against that worktree and prompt file.

Stop after a child skill stops (wrong task, occupied/blocked worktree, user rejected the draft prompt).
