---
name: work-scout
description: Delegate Slack and ClickUp research to a cheap model (Mercury via kilo, Kimi K2.7, or Haiku 4.5, routed by live quota) that searches twice and returns a cited report file, so this session's context never fills with raw messages and tasks. Use whenever the user asks what someone said, showed, flagged or asked in Slack or ClickUp — "what did X show me this morning", "what did I miss in #channel", "what's the status/history of GLOBAL-123", "has anyone started X", "catch me up on Y" — instead of walking the Slack and ClickUp APIs in this session.
---

Slack and ClickUp research is cheap to *do* and expensive to *hold*: one morning in one channel plus three task bodies is 20k tokens of context this session will never need again. Same principle as the `scout` skill for code: a cheap scout does the walking, gets asked twice, and this session reads only the distilled report.

## When to scout, when to just look

- **Scout** open-ended questions: what did someone show or ask, what happened on a topic, catch-up on a channel, the history behind a task, "has anyone started X".
- **Look directly** when the target is one known thing and the output is small: one task by id, one thread, one person's id. Use the helper yourself:

The scripts live in `scripts/` next to this SKILL.md (the base directory printed when the skill loads):

```bash
S=<base directory of this skill>/scripts
W=$S/wscout.py
python3 $W --help                                   # groups: whoami, slack, clickup
python3 $W clickup task GLOBAL-15937 --no-comments  # one task, ~30 lines
python3 $W slack search --from rahela --since today # one person's day, all channels
```

The helper is read-only by construction (Slack method allow-list, ClickUp GET only), reads tokens from `~/.config/workstation/config.toml` and never prints them. Names resolve fuzzily (people, channels, `dm:<name>`, lists); ambiguity is an error listing the candidates.

## Steps

1. **Write the question as one sentence** and put everything you already know in `--context`: names, channels, the time range, what a complete answer contains. The brief matters more than the model; the template in `scripts/brief-template.md` supplies method, rules and report shape, so context only needs the specifics.

2. **Run the driver in the background** (2 to 6 minutes):

```bash
python3 $S/run.py --name <slug> \
  --question "What tasks did Rahela flag to Max this morning, and what is asked of him for each?" \
  --context "Check #global-it-team first, then everything she posted today incl. DMs. Read each linked task with comments."
```

   It routes with the `scout` plugin's `route.py`, found as a sibling plugin or in `~/.claude/skills/scout` (override with `--backend mercury|kimi27|haiku-max`; with no router it reports `native` and you run the helper yourself), runs pass 1, then resumes the same session with the critique ("you missed things; re-verify every citation") for pass 2, and prints only:

```
BACKEND=mercury PASSES=2 TIME=44s COST=$0.010 WORDS=518
REPORT=~/.cache/work-scout/runs/<run>/report.md
PASS1=~/.cache/work-scout/runs/<run>/pass1.md
```

   Measured on the same question (2026-09-17, "what did Rahela flag to Max this morning"): Mercury 44s, $0.01, 518 words, every fact right. Haiku-max 175s, $0.24, 1188 words, more history but one ask from a neighbouring task attributed to the wrong one. Mercury is the right default; reach for haiku-max only when the question needs history beyond a day or two.

   `--single-pass` is orientation only, never grounding for an answer. `FAILED` means auth, quota or an empty pass: rerun with `--backend` set to the next backend in the evidence lines the driver prints.

3. **Read `report.md` only.** Treat it as a map: spot-check one or two load-bearing citations with the helper (a task's current status, a thread's author) before repeating them to the user. A wrong citation gets a targeted follow-up question, not a blind rerun. If pass 2 dropped something pass 1 had, diff the two files and ask for it back.

4. **Answer the user yourself**, with ClickUp tasks as inline links, and say which backend ran, how long it took and what it cost. The report is visible only to you.

## Run directory

`~/.cache/work-scout/runs/<timestamp>-<slug>/` holds `brief.md`, `pass1.md`, `report.md`, `stderr.log` and `meta.json`. The scout's working directory is this folder, so it has nothing to wander into. Caches of Slack users and channels and ClickUp members and lists live in `~/.cache/work-scout/*.json` for 24 hours; delete them if a new person or sprint list is not resolving.
