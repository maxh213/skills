---
name: grill-task
description: >
  Grill a rough task idea in a relentless interview first, then write it up as a
  task file. Use when the user explicitly asks to be grilled, challenged,
  questioned or stress-tested before the task is written, or /grill-task. For a
  straight write-up with no interview, use write-task instead.
argument-hint: "[description] [--out PATH]"
---

# Grill, then write the task

Two steps, in order. Do not write anything until the grilling is done.

## 1. Grill

Call the Skill tool with `grilling` (Matt Pocock's skill; if that name does not resolve, try `mattpocock-skills:grilling`).

Seed its design tree with the task's own anatomy, so the interview converges on something writable instead of wandering into architecture. The decisions a task needs settled:

- **Why** — who is affected, how often, what it costs, and what happens if we don't do it.
- **What** — the one sentence that finishes "this is done when…". If it needs an "and", is it two tasks?
- **Scope** — what's out, especially the thing a reader would assume is in. What must *not* happen.
- **Constraints** — what can't change, what it must use, what gates it.
- **Done when** — the yes/no checks, including the failure path and one edge case, with numbers instead of "fast" or "robust".
- **Size** — one outcome, one person, a few days? If not, where does it split?
- **Links** — the design, the epic, the incident, the related ticket.

Let `grilling` run its own rounds and format. Do not start drafting mid-interview.

<stop-condition>

`grilling` on its own runs until every branch of a design tree is settled. That is the wrong target here. **You are gathering enough to describe the task, not enough to execute it.**

Stop when you could write the Why, the What and the Done when. Then stop, even if plenty is still unknown — the assignee settles the rest by doing the work.

Never ask:

- How the work should be carried out. That is the implementer's call, and the cheat sheet says so.
- Who approves it, or how it gets signed off.
- What the user meant by their own shorthand.
- Anything whose answer would not change a word of the description.

Two rounds is normal. If you are starting a fourth, you are planning the work rather than describing it — write the task instead.

</stop-condition>

<fallback>

If `grilling` will not resolve at all, say so, then run the interview yourself directly from the list above: ask in rounds, number each question, give your recommended answer, and wait for the user before the next round.

</fallback>

## 2. Write

Call the Skill tool with `write-task`, passing the user's original description plus everything the grilling settled, and any `--out PATH` the user gave.

`write-task` owns the format, the cheat sheet, the checklist and the file. Do not duplicate its rules here — just hand it the sharpened material.

One difference from a cold `write-task` run: after a proper grilling there should be almost nothing left to mark as an open question. If you are still about to write three or more, the frontier was not actually empty — go back to step 1 for another round.
