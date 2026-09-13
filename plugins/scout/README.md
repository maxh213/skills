# scout

Quota-routed codebase exploration for agent CLIs. One skill that delegates
read-only repo scouting ("how does X work", "where is Y handled") to the
cheapest live model backend, keeping the main session's context clean for the
actual work.

## Backends

| Backend | CLI | Model | Cost profile |
|---|---|---|---|
| `mercury` | [kilo](https://kilo.ai) | Mercury 2.5 (high reasoning, two-pass reflection loop) | cents per run against the kilo balance |
| `kimi27` | [kimi](https://www.kimi.com/code/) | K2.7 highspeed | Kimi Code membership quota |
| `haiku-max` | [claude](https://claude.com/claude-code) | Haiku 4.5 at `--effort max` | Claude subscription quota |

## Routing

`route.py` (next to `SKILL.md`) measures all three live and prints
`DECISION=<backend>`:

1. **Evaporation priority** — a fixed weekly quota window resetting within 24h
   with ≥20% left is use-it-or-lose-it: burn it first.
2. **kilo** — wins by default when its balance is solvent
   (`PREFER_KILO = True`; flip to `False` in `route.py` to opt out).
3. **Most headroom** — kimi vs claude, each scored by its worst usage window;
   tie within 10 points → haiku-max.

Kimi quota is read from the local `kimi web` server's
`GET /api/v1/oauth/usage` (weekly + rolling-5h windows); Claude's from
`claude -p "/usage"`; kilo's from `kilo profile`.

## Install

Copy `skills/scout/` into your agent's skills directory
(`~/.claude/skills/`, `~/.agents/skills/`, etc.) or install this repo as a
marketplace plugin. Requires at least one of the three CLIs to be installed
and logged in; with none, the router falls back to the host agent's built-in
exploration (`DECISION=native`).

## Why the brief matters more than the model

Benchmarked on two real repos (a Next.js/.NET app with a hallucination-trap
question, a Rails app with a deep trace question): every backend produced a
strategically correct report from the same well-specified brief — the
differentiators were citation precision and depth, not the headline answer.
The skill therefore invests in brief discipline (structure, citation rules,
anti-hallucination rules) and a forced self-correction loop for the cheapest
backend, and spends effort only where it pays.
