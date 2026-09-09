---
name: prompt-manager
description: >
  Execute a large multi-step implementation prompt incrementally in a claimed
  git worktree, with a namespaced PROGRESS-<slug>.md that survives sessions.
  Idempotent: resume if that progress file already exists. Use when the user
  gives a big prompt, asks to continue a prompt-manager run, or runs
  /prompt-manager.
---

# Prompt Manager

Treat the prompt as a project, not a one-shot answer. Read `$PLUGIN_ROOT/references/isolation.md` and follow it. Plugin root via `credentials.py plugin-root`.

## 0. Resolve worktree and files

- Prompt path from `$ARGUMENTS`, or `PROMPT-<slug>.md` in a claimed worktree.
- Slug from the filename (`PROMPT-global-15526.md` → `global-15526`) or `worktree.py slug`.
- Claim (idempotent):

```bash
python3 "$PLUGIN_ROOT/scripts/worktree.py" claim --slug "$SLUG" --repo "$REPO"
```

- `cd` to the JSON `worktree`. Stay there. Use the claim's `prompt_file` and `progress_file`.
- If the progress file already has a checklist, restore todos from it and continue at the first incomplete item. Do not rebuild the plan from scratch unless the user asked to reset.

If `action` is `blocked`, stop.

## 1. Parse and Plan

- Read the full prompt carefully.
- Identify discrete deliverables: files to create, functions to change, commands to run, research to do.
- If the task has explicit phases or milestones, map them out.
- Call `TodoList` with a concrete checklist before doing any significant work (skip this rebuild when resuming).
- Each todo should be a single actionable step (e.g., "Read session-store.ts", "Add OAuth route", "Run tests").
- Keep `PROGRESS-<slug>.md` in sync with that checklist, grouped by phase.

## 2. Execute Incrementally — And Keep Going

- Mark exactly one todo `in_progress` at a time.
- Do the work for that todo inside this worktree.
- Verify it: run tests, build, lint, or inspect output as appropriate.
- Mark it `done` in both `TodoList` and `PROGRESS-<slug>.md` before moving on.
- Update the todo list whenever the plan changes (new blockers, new subtasks, completed work).
- **When all todos for the current phase are done, do not stop and wait for the user.** Immediately look for the next phase/feature group in the prompt or progress file and continue working on it.
- Only pause and summarize when the entire task is complete, the user explicitly asks you to stop, or you hit an unresolvable blocker.

## 3. Communicate State

- After each significant step, give the user a one-line status update: what just finished, what's next, any blockers.
- Do not dump raw tool output unless the user asks or it is needed to diagnose a failure.
- If a step fails, say so plainly and propose the next action.

## 4. Long-Running / Multi-Session Work

- Keep `PROGRESS-<slug>.md` in sync with `TodoList` at all times.
- At the end of each turn, save the current checklist state to that file.
- At the start of a resumed session, read it first and restore the todo list from it.

## 5. Scope Control

- Do not add features the user did not ask for.
- If the prompt is ambiguous, make a reasonable assumption and state it, then proceed.
- If the user corrects you, update the todo list and continue from the corrected direction.

## 6. Completion

- "All todos are done" means **every phase, feature, and fix** from the original prompt is complete, not just the current phase.
- When everything is done, run final verification (tests, build, etc.).
- `python3 "$PLUGIN_ROOT/scripts/worktree.py" done --slug "$SLUG" --repo "$REPO"`
- Summarize what was delivered across all phases. List the worktree, branch, and remaining follow-ups.
- Do not merge. Do not push to `main`.
