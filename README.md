# skills

Public agent skills for Claude, agy, kimi, opencode, etc.

Each skill lives in its own directory with a `SKILL.md`:

```text
skills/
  <skill-name>/
    SKILL.md
```

Install by copying a skill folder into your agent's skills directory, for example `~/.claude/skills/`.

## Layout

- `work/` — skills tied to Anima International's IT workflow (ClickUp sprints, task deep-dives, prompt planning). They read API tokens from `~/.config/workstation/config.toml` at runtime; nothing is embedded.
