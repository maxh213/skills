# work-scout

The `scout` idea applied to Slack and ClickUp: a cheap model does the searching, gets asked twice, and the main session reads only a cited report. One morning of one channel plus three task bodies is 20k tokens the session never needs again; this keeps them out.

## Requirements

- `~/.config/workstation/config.toml` with `[slack].token` (a user token, `xoxp-`) and `[clickup].token` plus `[clickup].user_id`. The helper reads them; nothing prints them.
- At least one of the kilo, kimi or claude CLIs, logged in.
- The `scout` plugin, for its `route.py` quota router. Without it the driver reports `native` and the main agent runs the helper itself.

## Pieces

- `skills/work-scout/scripts/wscout.py` — read-only helper the scout calls. Slack methods are allow-listed, ClickUp is GET only. Fuzzy resolution of people, channels, `dm:<name>` and lists; compact text output with ClickUp ids extracted from Slack links.
- `skills/work-scout/scripts/run.py` — two-pass driver. Routes via `route.py`, runs pass 1, resumes the same session with an unspecific critique for pass 2, writes `report.md` and `pass1.md` under `~/.cache/work-scout/runs/<run>/`, prints one summary line.
- `skills/work-scout/scripts/brief-template.md` — the brief: method, rules, report shape. A run only needs `--question` and `--context`.

## Measured

Same question ("what did Rahela flag to Max this morning"), 2026-09-17:

| Backend | Time | Cost | Words | Accuracy |
|---|---|---|---|---|
| Mercury (kilo) | 44s | $0.01 | 518 | every fact right |
| Haiku 4.5 max (claude) | 175s | $0.24 | 1188 | more history, one ask attributed to the wrong task |

Mercury is the right default. Pass 2 rewrote 52 lines of pass 1 on the Mercury run.
