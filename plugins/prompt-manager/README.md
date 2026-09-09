# prompt-manager

Anima IT workflow as one plugin: list sprint work, deep-dive a task, turn it into a `PROMPT-<slug>.md`, then execute it in an isolated git worktree.

## Skills

| Skill | What it does |
|---|---|
| `setup-prompt-manager` | Search agent memory + local env, then write missing credentials to `~/.config/workstation/config.toml` (mode 0600) |
| `sprint-tasks` | Current-sprint ClickUp tasks for you + unassigned |
| `task-context` | Read-only verdict-first brief on a ClickUp task |
| `idea-to-prompt` | Interview → namespaced `PROMPT-<slug>.md` in a claimed worktree |
| `prompt-manager` | Execute that prompt in the same worktree, resume via `PROGRESS-<slug>.md` |
| `prompt-manager-full-run` | Orchestrates the above. Pass `--skip-thoughts` to skip the extra feedback step |

## Install

Grok:

```bash
grok plugin marketplace add maxh213/skills
grok plugin install prompt-manager --trust
```

Claude Code: add this repo as a marketplace, or copy each folder under `skills/` into `~/.claude/skills/`.

Then run `/setup-prompt-manager` once per machine.

## Layout

```
plugins/prompt-manager/
  plugin.json
  references/           # credential catalog + isolation rules
  scripts/              # credentials.py, worktree.py
  skills/
```
