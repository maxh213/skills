# skills

Public agent skills for Grok, Claude, agy, kimi, opencode, etc.

All work skills ship as one plugin, **prompt-manager**, so teammates install a single package.

## Install (Grok)

```bash
grok plugin marketplace add maxh213/skills
grok plugin install prompt-manager --trust
```

Then `/setup-prompt-manager` once, then `/prompt-manager-full-run`.

## Install (Claude Code)

Add this repo as a marketplace, or copy each folder under `plugins/prompt-manager/skills/` into `~/.claude/skills/`.

## Layout

```text
plugins/prompt-manager/
  plugin.json
  references/            # credential catalog + worktree isolation
  scripts/               # credentials.py, worktree.py
  skills/
    setup-prompt-manager/
    sprint-tasks/
    task-context/
    idea-to-prompt/
    prompt-manager/
    prompt-manager-full-run/
```

Secrets are read from `~/.config/workstation/config.toml` at runtime (mode 0600). Nothing is embedded.

`prompt-manager-full-run` accepts `--skip-thoughts` to skip the extra feedback step between task-context and idea-to-prompt.
