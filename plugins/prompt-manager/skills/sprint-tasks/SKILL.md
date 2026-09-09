---
name: sprint-tasks
description: >
  List current-sprint ClickUp tasks assigned to the configured user or still
  unassigned. Invoke when the user says "grab my sprint tasks", "what's in the
  sprint", "show sprint tasks", "what's unassigned this sprint", "my clickup
  tasks", or wants a quick view of available sprint work. Read-only — does not
  claim, assign, or re-status anything.
---

# Sprint tasks

One command does everything (finds the current sprint, fetches tasks, filters).

```bash
# script lives next to this SKILL.md, or under the plugin root
python3 "$PLUGIN_ROOT/skills/sprint-tasks/scripts/sprint_tasks.py"          # you + unassigned
python3 "$PLUGIN_ROOT/skills/sprint-tasks/scripts/sprint_tasks.py" --all    # everyone
```

`$PLUGIN_ROOT` is `credentials.py plugin-root` (`GROK_PLUGIN_ROOT` / `CLAUDE_PLUGIN_ROOT`). If this skill was copied into `~/.claude/skills/sprint-tasks/`, run `scripts/sprint_tasks.py` next to this file instead.

If that fails with a missing token / user id, follow `setup-prompt-manager`.

Outputs the sprint name + a JSON array of tasks (who/status/priority/points/id/name/url).

## Presenting results

Render as a markdown table: ID, task name (linked to URL), status, points, priority, assignee. Group or mark "UNASSIGNED" vs "me". Order by: MoSCoW/priority (urgent > high > normal > none), then points ascending (small wins first).

## How it works (if the script breaks)

- Token and user id: `~/.config/workstation/config.toml` (`clickup.token`, `clickup.user_id`), else env listed in `references/credentials.toml`.
- Sprint folder from `clickup.sprint_folder` (default `90127244534`); lists named `Sprint {N} (M/D - M/D)` — pick the one whose range contains today (no year in the name; handle Dec→Jan wrap).
- `GET /api/v2/list/{id}/task?subtasks=true&include_closed=false`, keep tasks where assignees is empty or contains the configured user id.

## Boundaries

- Read-only by design. Claiming a task is not this skill.
- If no sprint list covers today, say so — don't fall back to a Backlog list.
