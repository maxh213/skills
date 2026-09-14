# task-writing

Turn a rough description into a task a stranger could pick up.

| Skill | What it does |
|---|---|
| `/write-task` | Description in, `TASK-<slug>.md` out. No interview. |
| `/grill-task` | Grills the idea first, then calls `write-task`. |

Both follow `skills/write-task/CHEAT-SHEET.md`, which covers the section anatomy
(Why / What / Scope / Done when), per-type shapes for features, bugs, spikes and
chores, plain-language rules, and a 60-second pre-save checklist. It cites its
sources at the bottom.

The rule doing the most work: **anything the description didn't say is either asked
about before writing or left out, never invented and never written into the ticket as a
question.** If `write-task` would need more than three questions to fill the gaps, it is
telling you the idea wasn't ready — that's when `/grill-task` earns its keep.

To push the resulting file into ClickUp, `/task-to-clickup TASK-<slug>.md` from the
`prompt-manager` plugin files it into the current sprint or the PM triage queue.

`/grill-task` delegates the interview to `grilling` from the
[mattpocock-skills](https://github.com/anthropics/claude-plugins-official) plugin.
Without it, the skill falls back to running the interview itself.

## Files

```text
plugins/task-writing/
  plugin.json
  skills/
    write-task/
      SKILL.md
      CHEAT-SHEET.md     # the source of truth for format
    grill-task/
      SKILL.md           # grilling → write-task
```
