# skills

Public agent skills for Grok, Claude, agy, kimi, opencode, etc.

All work skills ship as one plugin, **prompt-manager**, so teammates install a single package.

Personal tooling ships as separate plugins: **scout** (quota-routed codebase exploration across kilo/kimi/claude CLIs).

## Install (Grok)

```bash
grok plugin marketplace add maxh213/skills
grok plugin install prompt-manager --trust
grok plugin install scout --trust        # optional, personal tooling
```

Then `/setup-prompt-manager` once, then `/prompt-manager-full-run`.

## Install (Claude Code)

```bash
claude plugin marketplace add maxh213/skills
claude plugin install prompt-manager@maxh213-skills
claude plugin install scout@maxh213-skills        # optional, personal tooling
```

Restart Claude Code afterwards — plugin skills are enumerated at startup.

Alternatively, copy each folder under `plugins/prompt-manager/skills/` (work skills) or `plugins/scout/skills/` (scout) into `~/.claude/skills/`.

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

plugins/scout/
  plugin.json
  skills/
    scout/
      SKILL.md           # routing rationale, brief discipline, backend recipes
      route.py           # live quota probes + DECISION=<backend> picker
```

Secrets are read from `~/.config/workstation/config.toml` at runtime (mode 0600). Nothing is embedded.

`prompt-manager-full-run` accepts `--skip-thoughts` to skip the extra feedback step between task-context and idea-to-prompt.

`scout` needs at least one of the kilo, kimi, or claude CLIs installed and logged in; see `plugins/scout/README.md` for how routing works.
