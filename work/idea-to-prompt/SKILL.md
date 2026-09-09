---
name: idea-to-prompt
description: Use when the user has a rough idea, vague feature request, or half-formed project and wants it turned into a structured implementation prompt. Interview them with a few targeted questions, then write a PROMPT.md with phases, deliverables, and binary success criteria, ready to hand to the prompt-manager skill.
---

# Idea → Prompt Skill

The user's rough idea is the input: `$ARGUMENTS` (or whatever they describe in chat).
Your job is NOT to implement anything. Your only deliverable is a `PROMPT.md`.

## 1. Interview First

Before drafting anything, ask clarifying questions — but only about things the
idea doesn't already answer. One round, 3–5 questions max, covering whichever
of these are unclear:

- **Purpose / user**: who is this for and what problem does it solve?
- **Core functionality**: what are the 2–5 must-have behaviours? What's the
  smallest version that would be useful?
- **Technical context**: stack, existing repo/files it touches, integrations,
  hosting, constraints (e.g. "must run on Cloud Run", "no new dependencies").
- **Definition of done**: how will we know it works? What can be checked
  automatically (tests, build, lint, a curl that returns 200)?
- **Out of scope**: anything explicitly NOT wanted.

If the user says "just make sensible choices", make them, and record each
assumption in the prompt so the implementing agent doesn't re-litigate them.

## 2. Draft PROMPT.md

Write the prompt in this structure:

```
# <Project name>

## Overview
2–4 sentences: what is being built and why.

## Context & Constraints
Stack, relevant existing files/paths, conventions to follow,
things that must not change, assumptions made during planning.

## Phases
### Phase 1: <name>
- Task 1 (single actionable step)
- Task 2
Deliverables: <files/behaviours that exist at end of phase>
Verify: <exact command(s) that must exit 0, e.g. `npm test`, `pnpm build`>

### Phase 2: <name>
... (same shape; order phases so each builds on the last and the
project is in a working state at every phase boundary)

## Success Criteria (all must be true)
- [ ] Binary, testable statements only — "endpoint X returns 200 with
      valid payload", "coverage ≥ 80%", never "code is clean".

## Out of Scope
Explicit list. Include stretch goals here, clearly marked as
"do not build unless asked".

## Rules for the Implementing Agent
- Never delete, skip, or weaken a test to make it pass; flag suspect
  tests in PROGRESS.md instead.
- Record failed approaches and key decisions in PROGRESS.md as you go.
- Commit after each completed phase.
```

## 3. Self-Review Before Delivering

Re-read the draft as if you were the implementing agent with zero other
context. Fix anything that fails these checks:

- Could any task be interpreted two ways? Disambiguate it.
- Does every phase have a `Verify:` command a machine can run?
- Are all file paths, names, and terms defined?
- Is the scope the *minimum* useful version? Move nice-to-haves to Out of Scope.
- Would this loop forever on any criterion that isn't binary?

## 4. Deliver

- Write the result to `PROMPT.md` in the project root.
- Show the user a short summary: phases, success criteria count, assumptions made.
- Ask if they want edits. When they're happy, tell them to kick off with:
  "Read PROMPT.md and execute it using the prompt-manager skill."
- Do not start implementing yourself.
