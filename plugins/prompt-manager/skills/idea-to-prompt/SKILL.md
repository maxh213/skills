---
name: idea-to-prompt
description: >
  Turn a rough idea, vague feature request, or ClickUp brief into a structured
  implementation prompt. Interviews first, then writes PROMPT-<slug>.md in a
  claimed git worktree, ready for the prompt-manager skill. Use when the user
  wants an idea turned into a prompt, or /idea-to-prompt.
---

# Idea → Prompt

The user's rough idea is the input: `$ARGUMENTS` (or the brief handed off by prompt-manager-full-run).
Do not implement. The only deliverable is `PROMPT-<slug>.md` in a claimed worktree.

Read `$PLUGIN_ROOT/references/isolation.md` and follow it for slug, claim, and file names. `$PLUGIN_ROOT` is `python3 …/scripts/credentials.py plugin-root`.

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

## 2. Claim a worktree

Target repo = cwd's git root, or the repo the user named.

```bash
SLUG=$(python3 "$PLUGIN_ROOT/scripts/worktree.py" slug --from "$SLUG_SOURCE")
python3 "$PLUGIN_ROOT/scripts/worktree.py" claim --slug "$SLUG" --repo "$REPO"
```

`$SLUG_SOURCE` is the ClickUp id when one is in play, otherwise the project name.

If `action` is `blocked`, stop and tell the user. If `reused` and the claim's `prompt_file` already exists, show a short summary and ask reuse vs regenerate — skip the write on reuse.

All later writes happen in the JSON `worktree` path. Use the claim's `prompt_file` / `progress_file` names.

## 3. Draft PROMPT-\<slug\>.md

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
  tests in PROGRESS-<slug>.md instead.
- Record failed approaches and key decisions in PROGRESS-<slug>.md as you go.
- Commit after each completed phase.
- Stay inside this worktree. Do not touch sibling worktrees or the main checkout.
```

## 4. Self-Review Before Delivering

Re-read the draft as if you were the implementing agent with zero other
context. Fix anything that fails these checks:

- Could any task be interpreted two ways? Disambiguate it.
- Does every phase have a `Verify:` command a machine can run?
- Are all file paths, names, and terms defined?
- Is the scope the *minimum* useful version? Move nice-to-haves to Out of Scope.
- Would this loop forever on any criterion that isn't binary?

## 5. Deliver

- Write `PROMPT-<slug>.md` in the claimed worktree.
- Show the user: worktree path, branch, slug, phase list, success-criteria count, assumptions.
- Ask if they want edits. When they're happy, tell them to run prompt-manager on that file in that worktree.
- Do not start implementing yourself.
