# Isolation — worktrees and idempotency

Multiple agents may run idea-to-prompt / prompt-manager against the same git repo at once. Every run owns a **slug**, a **worktree**, and **namespaced** prompt/progress files. Bare `PROMPT.md` / `PROGRESS.md` are leftover from older single-agent runs; never write them when a slug is known.

## Slug

- ClickUp id `GLOBAL-15526` → `global-15526`
- Otherwise: lowercase, non-alphanumerics to `-`, collapse, trim, max 48 chars
- Compute with `scripts/worktree.py slug --from '…'`

## Claim (idempotent)

From the target git repo:

```bash
python3 "$PLUGIN_ROOT/scripts/worktree.py" claim --slug "$SLUG" --repo "$(git rev-parse --show-toplevel)"
```

The script:

1. Reuses the worktree already attached to `feat/<slug>` (idempotent resume).
2. Recreates that worktree if the branch still exists but the worktree was deleted.
3. Creates `feat/<slug>` and a sibling worktree `<repo>-<slug>` when neither exists.
4. Exits non-zero with `action: blocked` only if the destination path exists, is not a worktree, and is not empty.

Work only inside the JSON `worktree` path. Never `cd` into the main checkout or a sibling worktree. One slug → one branch → one worktree. A second agent on the same slug resumes; a second agent on a different slug gets its own worktree.

## Files in the worktree

| File | Writer |
|---|---|
| `PROMPT-<slug>.md` | idea-to-prompt |
| `PROGRESS-<slug>.md` | prompt-manager |

If a namespaced file already exists and looks complete, reuse it. Do not overwrite unless the user asked to regenerate.

If this worktree has a legacy `PROMPT.md` / `PROGRESS.md` and no namespaced file yet, **rename** them to the namespaced names (keep content). Do not delete a sibling's un-namespaced files in the main checkout.

## Resume

`PROGRESS-<slug>.md` present with unchecked items → restore the todo list and continue from the first incomplete item.

Claim `status` is `done` → show the worktree/prompt/progress paths and ask whether to resume (re-open the claim) or start a new slug (`<slug>-2`).

## Done

When every phase in the prompt is complete, `python3 scripts/worktree.py done --slug "$SLUG" --repo …`. Leave the worktree on disk; do not merge, do not push to `main`.
