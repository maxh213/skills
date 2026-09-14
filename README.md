# skills

Public agent skills for Grok, Claude, agy, kimi, opencode, etc.

All work skills ship as one plugin, **prompt-manager**, so teammates install a single package.

Personal tooling ships as separate plugins: **scout** (quota-routed codebase exploration across kilo/kimi/claude CLIs) and **task-writing** (turn a rough description into a task a stranger can pick up).

## Install (Grok)

```bash
grok plugin marketplace add maxh213/skills
grok plugin install prompt-manager --trust
grok plugin install scout --trust        # optional, personal tooling
grok plugin install task-writing --trust # optional, personal tooling
```

Then `/setup-prompt-manager` once, then `/prompt-manager-full-run`.

## Install (Claude Code)

```bash
claude plugin marketplace add maxh213/skills
claude plugin install prompt-manager@maxh213-skills
claude plugin install scout@maxh213-skills        # optional, personal tooling
claude plugin install task-writing@maxh213-skills # optional, personal tooling
```

Restart Claude Code afterwards — plugin skills are enumerated at startup.

Alternatively, copy each folder under any plugin's `skills/` directory into `~/.claude/skills/`.

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
    task-to-clickup/     # TASK-<slug>.md -> current sprint (assigned) or PM TRIAGE (unassigned)
    guide-me/            # task-context dive, one plain-English paragraph out

plugins/scout/
  plugin.json
  skills/
    scout/
      SKILL.md           # routing rationale, brief discipline, backend recipes
      route.py           # live quota probes + DECISION=<backend> picker

plugins/task-writing/
  plugin.json
  skills/
    write-task/
      SKILL.md           # description in, TASK-<slug>.md out
      CHEAT-SHEET.md     # section anatomy, per-type shapes, 60-second check
    grill-task/
      SKILL.md           # grilling -> write-task
```

Secrets are read from `~/.config/workstation/config.toml` at runtime (mode 0600). Nothing is embedded.

`prompt-manager-full-run` accepts `--skip-thoughts` to skip the extra feedback step between task-context and idea-to-prompt.

`scout` needs at least one of the kilo, kimi, or claude CLIs installed and logged in; see `plugins/scout/README.md` for how routing works.

`task-writing` writes nothing the description didn't say: a gap that changes the work is asked about first, and the rest is left out. Tickets never carry open questions. `/grill-task` uses the `grilling` skill from mattpocock-skills when it's installed, and runs the interview itself when it isn't.

`/task-to-clickup TASK-<slug>.md` files a task file into ClickUp: the current sprint (assigned to you, status `backlog`) or the PM TRIAGE queue (unassigned). It asks for sprint points and MoSCoW, proposes Field of work, Project name, Project category and a one-line Definition of Done from the file, and creates the task only after you confirm. The triage list id is `clickup.triage_list` in the credential catalog.

`/guide-me GLOBAL-XXXXX` runs the whole `task-context` dive and answers in one plain-English paragraph: what is wrong, where (one file link), the fix with its one caution, and whether anyone has started it. Shaped by the [i-have-adhd](https://github.com/ayghri/i-have-adhd) rules, then cut further: no steps, no estimates, nothing the reader will not read.
