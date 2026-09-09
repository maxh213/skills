---
name: prompt-manager
description: Use this skill when the user gives a large, complex, multi-step prompt or asks for a long-running implementation task in a single project. Break the work into a tracked todo list, execute it incrementally across all phases, and check off progress as you go. Resume from saved progress if the task spans multiple turns or sessions.
---

# Prompt Manager Skill

When the user drops a big prompt (spec, feature request, multi-file task, etc.) for a single project, treat it as a project, not a one-shot answer.

## 1. Parse and Plan

- Read the full prompt carefully.
- Identify discrete deliverables: files to create, functions to change, commands to run, research to do.
- If the task has explicit phases or milestones, map them out.
- Call `TodoList` with a concrete checklist before doing any significant work.
- Each todo should be a single actionable step (e.g., "Read session-store.ts", "Add OAuth route", "Run tests").
- Also create/update a `PROGRESS.md` in the project root with the same checklist, grouped by phase.

## 2. Execute Incrementally — And Keep Going

- Mark exactly one todo `in_progress` at a time.
- Do the work for that todo.
- Verify it: run tests, build, lint, or inspect output as appropriate.
- Mark it `done` in both `TodoList` and `PROGRESS.md` before moving on.
- Update the todo list whenever the plan changes (new blockers, new subtasks, completed work).
- **When all todos for the current phase are done, do not stop and wait for the user.** Immediately look for the next phase/feature group in the prompt or `PROGRESS.md` and continue working on it.
- Only pause and summarize when the entire task is complete, the user explicitly asks you to stop, or you hit an unresolvable blocker.

## 3. Communicate State

- After each significant step, give the user a one-line status update: what just finished, what's next, any blockers.
- Do not dump raw tool output unless the user asks or it is needed to diagnose a failure.
- If a step fails, say so plainly and propose the next action.

## 4. Long-Running / Multi-Session Work

- Keep `PROGRESS.md` in the project root in sync with `TodoList` at all times.
- At the end of each turn, save the current checklist state to `PROGRESS.md`.
- At the start of a resumed session, read `PROGRESS.md` first and restore the todo list from it.
- If the user picks the task back up after a break, read `PROGRESS.md` and continue from the next incomplete item.

## 5. Scope Control

- Do not add features the user did not ask for.
- If the prompt is ambiguous, make a reasonable assumption and state it, then proceed.
- If the user corrects you, update the todo list and continue from the corrected direction.

## 6. Completion

- "All todos are done" means **every phase, feature, and fix** from the original prompt is complete, not just the current phase.
- When everything is done, run final verification (tests, build, etc.).
- Summarize what was delivered across all phases.
- List any known caveats or follow-up items.
