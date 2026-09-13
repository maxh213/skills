---
name: scout
description: Delegate codebase exploration to the best available cheap model backend (Mercury 2.5 via kilo, Kimi K2.7 via kimi CLI, or Claude Haiku 4.5 via claude CLI), routing by what is installed and what subscription quota remains — measured live, with use-it-or-lose-it windows getting priority. Use whenever the user asks to explore, map, trace, or understand a codebase or subsystem — "how does X work", "where is Y handled", "what calls Z" — instead of spending this session's context and effort on raw exploration. Returns a distilled report with file citations that the main agent then works from.
---

Route read-only codebase exploration to a cheap external model so this session's context stays clean for actual work. Two principles drive everything here:

1. **The brief matters more than the model**: exploration barely benefits from expensive reasoning; it benefits from a high-quality task specification. Invest thinking in the brief.
2. **Route by measurement, not assumptions**: benchmarked across two real repos, all three backends produced usable reports from a good brief — they differ on cost, speed, and depth. `route.py` picks per-run by live quota windows.

## Routing algorithm

**0. Depth gate (always first):** if the question is adversarial/subtle ("find the bug nobody named"), or the report will directly ground expensive/risky edits and must not be wrong → skip the scouts, use the host agent's built-in `explore` subagent on the primary model at full effort. That is the escalation tier; it needs no CLI.

**1. Explicit overrides:** the user naming a backend wins. The user asking for the most thorough cheap report → haiku-max (its operational completeness won the depth contest in testing).

**2. DEFAULT — measure live quota and pick dynamically:**

```bash
# script lives next to this SKILL.md, or under the plugin root
python3 "$PLUGIN_ROOT/skills/scout/route.py"
```

Prints one evidence line per installed backend plus a final `DECISION=<mercury|kimi27|haiku-max|native>` — use that backend's recipe below. Decision order inside the script:

1. **Evaporation priority** — a fixed weekly quota window resetting within 24h with ≥20% still unused is use-it-or-lose-it quota: that backend wins outright. (Rolling short windows are rate limiters, not allowances — they never trigger this.)
2. **kilo** — balance above $1 → mercury. This is a *preference* for burning a pay-as-you-go balance before it refreshes; set `PREFER_KILO = False` in `route.py` if you don't want kilo to win by default.
3. **Most headroom (kimi vs claude)** — each backend's utilization = worst of its windows; lowest wins; tie within 10 points → haiku-max (deeper scout; the window checks self-correct the bias).

What it measures (~10s):

- **kimi** (Kimi Code membership) — boots a throwaway `kimi web` and reads `GET /api/v1/oauth/usage`: weekly % used + reset timestamp, rolling-5h % used. (The TUI `/usage` is not scriptable — `kimi -p "/usage"` just forwards text to the model — but the local web server's REST endpoint carries the same numbers.)
- **claude** (Claude subscription) — `claude -p "/usage"`: weekly all-models % used + "resets …" time, current-session %.
- **kilo** — `kilo profile` balance.
- Per the Kimi membership docs, all requests — CLI, IDE, third-party tools, API keys — share one membership quota per account; that is exactly why the *windows*, not the plan names, drive the choice. Context is never shared either way — every scout is a separate CLI process.

**3. Failure fallback:** if the chosen backend errors on auth/quota/balance (kilo: balance/402; kimi: 401/quota; claude: usage limit), pick the next-best headroom from the router's evidence lines (or re-run it) and mention the fallback to the user.

**Nothing installed / probes fail:** the router prints `DECISION=native` → the host agent's built-in exploration.

## The brief (the crucial part — same for every backend)

The explorer starts with zero context. Write the brief to a file (e.g. `/tmp/scout-brief.md`) and include:

1. **Repo path and shape** — absolute path, stack, key layout facts you already know.
2. **The exact question** — one question, scoped. Not "explain everything".
3. **Required report structure** — numbered sections you will rely on later.
4. **Citation rule** — every claim needs a file path, line numbers where possible.
5. **Anti-hallucination rule** — "if a layer does not exist, say so explicitly instead of guessing."
6. **Read-only rule** — "do not modify, create, or delete any files."
7. **Closing deliverable** — e.g. "end with a Key files list of the 5–10 most important files."

## Backend recipes

### Mercury 2.5 two-pass loop (kilo)

Mercury's first pass is fast and strategically correct but citations drift; a forced second pass fixed 100% of citation errors in testing and added edge-case depth. Loop by default:

```bash
cd <repo-root>

# Pass 1
kilo run -m kilo/inception/mercury-2.5 --variant high --auto --dir <repo-root> \
  --format json "$(cat /tmp/scout-brief.md)" > /tmp/scout-p1.jsonl 2>/dev/null

# Extract session id + report
python3 - <<'EOF'
import json
texts, sid = [], None
for line in open('/tmp/scout-p1.jsonl'):
    try: ev = json.loads(line)
    except: continue
    sid = sid or ev.get('sessionID')
    if ev.get('type') == 'text': texts.append(ev['part']['text'])
open('/tmp/scout-p1.md','w').write(texts[-1] if texts else '')
print('SESSION:', sid)
EOF

# Pass 2: forced reflection on the SAME session
kilo run -s <SESSION> -m kilo/inception/mercury-2.5 --variant high --auto --dir <repo-root> \
  --format json "Your analysis is incomplete — it missed things. Do a second, skeptical pass over your own report before finalizing: (1) re-verify every file:line citation against the actual code and fix any that are wrong; (2) for each section, actively hunt for anything you missed — entry points, admin tooling, scripts, routes, deployment configs, edge-case handling (retries, replays, failures); (3) drop or correct any claim not supported by the files you cite. Then output the complete corrected report in the same structure. Do not modify any files." \
  > /tmp/scout-p2.jsonl 2>/dev/null

# Final report = last text event of pass 2 (same python snippet on scout-p2.jsonl)
```

- `--format json` events carry `sessionID`; report = last `text` event's `part.text`.
- The critique stays unspecific on purpose ("you missed something", not "you got X wrong") — it forces re-derivation instead of patching.
- **Diff pass 1 vs pass 2**: loops occasionally drop a correct finding while fixing others; ask for lost findings back in a targeted follow-up.
- Cost/time measured: ~$0.03 and ~2 min per loop. Quick mode (single pass, ~30s, ~$0.006): drop `--format json`, pipe through `sed 's/\x1b\[[0-9;]*m//g'` — use only for orientation, never as grounding for edits.

### K2.7 (kimi CLI)

```bash
cd <repo-root> && kimi -p "$(cat /tmp/scout-brief.md)" -m kimi-code/kimi-for-coding-highspeed 2>/dev/null
```

- `-p` print mode: report on stdout, thinking/progress on stderr; auto permissions by default, never blocks.
- K2.7 highspeed has no effort knob — it *is* the low-effort tier, which is the point.
- Output has a `• ` transcript prefix per line; strip if quoting.
- Measured: ~85–130s, top-3 accuracy in both test rounds. Note the membership quota is shared across all the account's sessions and tools — the router weighs this live.

### Haiku 4.5 max effort (claude CLI)

```bash
cd <repo-root> && claude -p "$(cat /tmp/scout-brief.md)" --model haiku --effort max \
  --dangerously-skip-permissions --output-format json 2>/dev/null \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['result'])"
```

- `--model haiku` = `claude-haiku-4-5-20251001`. `--effort max` is mandatory: measured on a real repo, default effort missed the core architectural mechanism of a task while max effort found it and ran faster.
- JSON wrapper: `result` = report; `modelUsage`/`total_cost_usd` (list-price equivalent) for accounting.
- `--dangerously-skip-permissions` — read-only briefs in trusted dirs only.
- Measured: 100–150s, best citation precision and operational completeness (flow diagrams, env inventories) of the scouts.

## Working with the result

- Treat every scout report as a map, not ground truth: spot-check 2–3 load-bearing citations with Read/Grep before building on them.
- Gaps or a failed citation → targeted follow-up brief (or escalate to the built-in `explore` agent), not a blind re-run.
- The report is visible only to you — summarize the relevant parts to the user yourself, and say which backend produced it and what it cost.
