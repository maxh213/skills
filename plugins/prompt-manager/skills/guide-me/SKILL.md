---
name: guide-me
description: >
  Run the full task-context dive on a ClickUp task, then answer in one plain-English
  paragraph: what is wrong, where, the fix, and whether anyone has started it.
  Nothing else. Use when the user says "guide me on GLOBAL-XXXXX", "what do I do
  next on this task", "where do I start", or /guide-me. Read-only.
argument-hint: "GLOBAL-XXXXX"
---

# Guide me

Same dive as `task-context`, one paragraph of output. The reader has ADHD: the digging is thorough, the answer is one paragraph they can read in fifteen seconds and act on.

`$PLUGIN_ROOT` is `python3 …/scripts/credentials.py plugin-root`.

## 1. Dive

Follow `$PLUGIN_ROOT/skills/task-context/SKILL.md` steps 1 to 7 in full: resolve the ID, ClickUp task and comments, ownership sweep, Slack, live state, code, previous sessions. Chase every pointer. Nothing here shortens the research; only step 8 (the brief) is replaced by the output below.

If the ID does not resolve confidently, ask which task before diving, as `task-context` says.

## 2. Answer

If the `i-have-adhd` skill is installed, load it before writing. Either way the answer follows these rules, condensed from that skill (Ayoub G., MIT) plus one of Max's own: plain English.

**Plain English first.** The reader wants to understand the problem in one read, not decode it. Write as if explaining to a colleague who does not code:

- Say what is wrong and where, in one sentence: "Signing up waits for a Salesforce check it does not need. It happens in one file, on one line."
- Name at most one file and one line, as a link. Nothing else from the code appears in the text: no function names, no variable names, no flag names, no acronyms. "The donor check" beats `UpdateDonorStatus`; "a setting" beats an env var name.
- Say the fix in plain words: "Remove the check. Before you do, look for anything else that reads the two values it fills in."
- Commands are allowed only when the reader is meant to run them, one at most, in a code block.
- If the answer takes more effort to read than the ticket does, it has failed.

**Shape: one paragraph, then one line.**

- **The paragraph**, three or four short sentences: what is wrong, in plain words; where it happens, as one file-and-line link; the fix, with the one caution that matters. That is the whole answer.
- **The line**: "Nobody has started it." Or who has, and what they did, in one sentence. If the description turned out stale or the fix already landed, that replaces the line and leads.
- Nothing else. No numbered steps, no time estimates, no state line, no timeline, no side findings, no "Later", no "Next", no preamble, no offer of a fuller brief. If the reader wants more they will ask.
- Under 80 words total.
- Plain statements. No "might", "perhaps", "seems".

## Shape

```
When someone signs up, the API first asks Salesforce whether they are a donor.
The check is not needed for signing up, and if Salesforce is slow the sign-up
hangs with it. It happens in one place: <file>, line N (link). Remove the check;
first look for anything else that reads the two values it fills in.

Nobody has started it.
```

## Boundaries

- Read-only, like `task-context`: no assigning, commenting, re-statusing or fixing.
- One task per run.
- Brevity applies to the answer, never to the dive. A short answer built on a shallow dive is the failure mode.
