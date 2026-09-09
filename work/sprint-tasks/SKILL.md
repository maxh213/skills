---
name: sprint-tasks
description: List current-sprint ClickUp tasks that are assigned to Max or still unassigned. Invoke when Max says "grab my sprint tasks", "what's in the sprint", "show sprint tasks", "what's unassigned this sprint", "my clickup tasks", or wants a quick view of available sprint work. Read-only — does not claim, assign, or re-status anything.
---

# Sprint tasks

One command does everything (finds the current sprint, fetches tasks, filters):

```bash
python3 ~/.claude/skills/sprint-tasks/scripts/sprint_tasks.py          # Max's + unassigned (default)
python3 ~/.claude/skills/sprint-tasks/scripts/sprint_tasks.py --all    # everyone's tasks
```

Outputs the sprint name + a JSON array of tasks (who/status/priority/points/id/name/url).

## Presenting results

Render as a markdown table: ID, task name (linked to URL), status, points, priority, assignee. Group or mark "UNASSIGNED" vs "me". Order by: MoSCoW/priority (urgent > high > normal > none), then points ascending (small wins first) — same ranking as workflow.md.

## How it works (if the script breaks)

- Token: first `clickup` token/key found in `~/.config/workstation/config.toml`.
- Sprint folder `90127244534`; lists named `Sprint {N} (M/D - M/D)` — pick the one whose range contains today (no year in the name; handle Dec→Jan wrap).
- `GET /api/v2/list/{id}/task?subtasks=true&include_closed=false`, keep tasks where assignees is empty or contains Max (`10857117`).

## Boundaries

- Read-only by design. Claiming a task (assign + "work in progress" + Clockify) is the **workflow.md** playbook / `sprint-loop` skill, not this one.
- If no sprint list covers today, say so — don't fall back to the Backlog list (`901214398683`).
