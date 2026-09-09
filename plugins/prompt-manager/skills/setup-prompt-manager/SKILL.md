---
name: setup-prompt-manager
description: >
  Securely gather credentials for the prompt-manager plugin. Searches the
  agent's own memory first, probes local env/config/CLIs, and only then asks
  for missing values. Writes secrets to ~/.config/workstation/config.toml
  (mode 0600). Use when setting up prompt-manager, onboarding a teammate,
  ClickUp/Slack/GitHub tokens are missing, or the user runs /setup-prompt-manager.
---

# Setup prompt-manager

Goal: every catalog credential is either present and verified, or explicitly skipped as optional. Never print a secret value. Never write a secret to memory, git, or chat.

## 0. Resolve plugin root

```bash
python3 "${GROK_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:?}}/scripts/credentials.py" plugin-root
```

If those env vars are unset, the `scripts/` directory next to this skill's plugin root is `../../scripts` relative to this `SKILL.md`.

`PLUGIN_ROOT` below means that path. `credentials.py` is `$PLUGIN_ROOT/scripts/credentials.py`.

## 1. Load the catalog

```bash
python3 "$PLUGIN_ROOT/scripts/credentials.py" catalog
python3 "$PLUGIN_ROOT/scripts/credentials.py" status
```

The catalog (`references/credentials.toml`) is the list of credentials. Iterate it. Do not hardcode a parallel list in this skill.

## 2. Search this agent's memory

For **each catalog item**, search whatever memory this agent actually has — do not assume a single product:

- Grok: `memory_search` / `memory_get` if those tools exist; also read `~/.grok/memory/MEMORY.md` and the workspace `MEMORY.md` when present.
- Claude: project/user `MEMORY.md`, `CLAUDE.md`, and memory tools if present.
- Any agent: notes, recall, or "what do I remember about \<query\>" using that item's `memory_queries` plus its `key` and `description`.

Record hits as **hints** only: "token lives in file X", "user already has gh auth", "ClickUp user id is 10857117". If memory contains a secret, use it to populate config via `set` (step 4) and do not echo it.

Memory is a hint, not proof. Every hint still has to survive the probe in step 3.

## 3. Probe the machine

Merge `credentials.py status` with the hints:

- `present` + `verified` → done for that item.
- `present` + not verified → report the failure, do not print the value, try the next source (env, then config, then a path memory named).
- missing + memory named a file path → read that file into `set --from-file` (still no echo).
- missing + env listed in the item → already covered by `status` (`source: env`).
- `github.token` is optional when `source` is `gh` (`gh auth status` succeeded).
- If `clickup.token` is verified and `clickup.user_id` has a `derived` field, `set clickup.user_id` to that number without asking.

## 4. Gather only what's still missing

Required items still missing: ask the user, one item at a time. Prefer they append the key to `~/.config/workstation/config.toml` themselves (file is 0600). If they paste a value instead:

```bash
# value on stdin — do not pass it as a command-line argument
python3 "$PLUGIN_ROOT/scripts/credentials.py" set <key>
```

or `--from-file` pointing at a user-written 0600 file, then delete that file.

Optional items still missing: ask once whether to add them now. Skip if they say later.

After each `set`, re-run `status` for that key. Confirm with `verified` / `identity` only.

## 5. Persist non-secret facts to memory

Write (to the agent's durable memory, not the config):

- prompt-manager credentials live in `~/.config/workstation/config.toml`
- which catalog keys are present (names only)
- ClickUp user id and team id, GitHub username/org, GCP project — **ids, never tokens**

## 6. Done

Show a table: key, present, source, verified, identity. List `missing_required`. If `ready` is true, tell them to run `/prompt-manager-full-run`.
