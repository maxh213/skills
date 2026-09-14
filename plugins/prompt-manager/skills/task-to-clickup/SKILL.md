---
name: task-to-clickup
description: >
  File a TASK-<slug>.md (from write-task or grill-task) into ClickUp as a new
  task, either in the current sprint assigned to the user or in the PM TRIAGE
  queue unassigned, with the team's fields filled: sprint points, MoSCoW, Field
  of work, Project name, Project category, Definition of Done. Use when the user wants a task file
  pushed, filed, sent or added to ClickUp, or /task-to-clickup.
argument-hint: "TASK-<slug>.md [--sprint | --triage]"
---

# Task file → ClickUp

One task file in, one ClickUp task out. The file is the source of truth: its H1 becomes the task name and everything below it becomes the description, verbatim.

```bash
SCRIPT="$PLUGIN_ROOT/skills/task-to-clickup/scripts/task_to_clickup.py"
```

`$PLUGIN_ROOT` is `credentials.py plugin-root` (`GROK_PLUGIN_ROOT` / `CLAUDE_PLUGIN_ROOT`). A missing token means `setup-prompt-manager` first.

## 1. Take the file

`$ARGUMENTS` names the file. Read it.

Given a description instead of a path, call the Skill tool with `write-task` (or `task-writing:write-task`) first, then continue with the file it wrote. Given a `TASK-*.md` in the cwd and no argument, confirm that is the one.

## 2. Pick the destination

| Flag | List | Assignee | Status |
|---|---|---|---|
| `--sprint` | current `Sprint {N} (M/D - M/D)` list | the user | `backlog` |
| `--triage` | `PM TRIAGE` (PM Triage IT folder) | nobody | `open not reviewed` |

No flag: ask which, in one line. Sprint puts the user on the hook this sprint; triage hands it to the PMs. Never default this.

## 3. Load the live options

```bash
python3 "$SCRIPT" options --dest sprint|triage
```

Returns the resolved list and, for **Field of work**, **Project name**, **Project categories** and **MoSCoW**, the exact option names ClickUp accepts. Suggest only names from this output. The option lists change; the script output is current, this file is not.

## 4. Propose the fields, ask for the rest

One round. Present a table of every field with its proposed value, then wait.

| Field | Source |
|---|---|
| **Sprint points** | Ask. The team uses 1, 2, 3, 5, 8, 13. |
| **MoSCoW** | Ask: Must / Should / Could / Won't Have. |
| **Field of work** | Propose one option (rarely two) from step 3 that names the system the task touches. Required by ClickUp. |
| **Project name** | Propose one option from step 3. None fits: say so and propose the nearest, or leave it empty. |
| **Project categories** | Propose one of: Business projects, Risk / security / compliance, Platform / internal improvements, Unplanned work. Tooling, infra and process work is Platform; a spike or decision on a tool is Platform too. |
| **Definition of Done** | Propose one sentence, under 25 words, that restates *What* and the decisive *Done when* checks. Required by ClickUp. A short-text field: one line, no bullets. |

The DoD traces to the file, like everything in `write-task`: it restates what the file already commits to and adds nothing. Points and MoSCoW come from the user, never from a guess.

Where the harness offers a structured question tool, use it for points and MoSCoW with the options above; otherwise ask in prose. The user may correct any proposed value in the same reply.

## 5. Confirm, then create

Dry-run first with the agreed values, exact option names quoted:

```bash
python3 "$SCRIPT" create --file TASK-x.md --dest sprint \
  --points 2 --moscow "Should Have" --project "Boilerplate" \
  --field-of-work "Boilerplate" --category "Platform / internal improvements" \
  --dod "One sentence." --dry-run
```

Show the `resolved` block, points, list name and who it is assigned to, and ask for a yes. `resolved` shows what each name matched; a name that matched something other than intended (matching is exact, then case-insensitive, then unique substring) gets fixed here, not after filing. An unmatched name exits non-zero with the option list: pick from it and rerun.

On yes, run the same command without `--dry-run`. Creation is the only write; nothing before it touches ClickUp.

## 6. Hand back

Print the result's `url`, `custom_id` (GLOBAL-nnnnn), list name and assignee, and the field table as filed.

Then append the link to the file's **Links** section, creating the section if the file has none:

```markdown
- ClickUp: https://app.clickup.com/t/xxxxxxx (GLOBAL-nnnnn)
```

Filed by mistake: `python3 "$SCRIPT" delete <id>` removes the task. Say so once, in the hand-back.

## Boundaries

- One file, one task, one write. A file whose *What* needs an "and" goes back to `write-task` to split, not into ClickUp twice.
- A question in the file ("Open question", "Assumption", "TBC", a line ending in "?") does not go to ClickUp. Settle it with the user and rewrite the line as a statement, or delete it, before step 2.
- Points, MoSCoW and the destination are the user's calls. Proposed values wait for a confirmation that names them.
