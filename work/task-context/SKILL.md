---
name: task-context
description: Deep context dive on a ClickUp task — resolve the (possibly typo'd) task ID, pull the full ClickUp description/comments, verify nobody else has started it, then sweep Slack history, git/PR/commit history, live infra state, previous Claude sessions, and Animus VM memory into one verdict-first brief. Read-only. Invoke when Max says "get the context on GLOBAL-XXXXX", "deep dive this task", "has anyone started X", "search through the context of this task", "background check on this ticket", or before picking up any sprint task whose history is unclear.
---

# Task context deep-dive

Goal: one **verdict-first brief** for a ClickUp task: what it is, whether the description is
still true (descriptions go stale!), who if anyone has started it, full timeline, root-cause
hypothesis, and the recommended next step. **Read-only** — never assign, comment, re-status,
or fix anything in this skill. Ultrathink-grade: take your time, chase every pointer.

## Tokens (all local, no VM needed for most steps)

```bash
# ClickUp (workspace/team id is 4540126 "Anima International")
CU_TOKEN=$(python3 -c "
import tomllib
cfg=tomllib.load(open('$HOME/.config/workstation/config.toml','rb'))
def walk(d,p=''):
    for k,v in d.items():
        if isinstance(v,dict): yield from walk(v,p+k)
        elif 'clickup' in (p+k).lower() and ('token' in k.lower() or 'key' in k.lower()): yield v
print(next(walk(cfg)))")

# Slack (Max's user token — search.messages works with it)
SLACK_TOKEN=$(python3 -c "
import tomllib
cfg=tomllib.load(open('$HOME/.config/workstation/config.toml','rb'))
print(cfg['slack'].get('token') or list(cfg['slack'].values())[0])")
```

**ClickUp API gotchas:** custom IDs need `?custom_task_ids=true&team_id=4540126`; NO trailing
slash before `?` (301s otherwise, curl won't follow); comments endpoint wants the *internal* id
(e.g. `869duaazx`), not the custom id.

## Step 1 — Resolve the task ID (Max's IDs are often typo'd)

Try the ID as given. If 404/unauthorized, generate permutations (dropped digit, doubled digit,
transposition) and try each; also cross-check against the current sprint list
(`~/.claude/skills/sprint-tasks/scripts/sprint_tasks.py`) — a task Max just saw in a sprint
table is the likeliest referent. Pick by *context fit* (IT-flavoured, unassigned if he asked
"has anyone started it", recently discussed) and **state which ID you resolved to and why**.
If no candidate is a *confident* match (exact-ish digits AND context fit), **ask Max which task
he meant before running the full dive** — one AskUserQuestion beats a deep dive on the wrong
task (learned 2026-07-07: "154296" meant 15396, not 15419).

```bash
curl -s -H "Authorization: $CU_TOKEN" \
  "https://api.clickup.com/api/v2/task/GLOBAL-XXXXX?custom_task_ids=true&team_id=4540126"
```

## Step 2 — ClickUp: full task + comments

From the task JSON keep: name, status, assignees, watchers, **creator** (Animuś = created by a
bot cron, e.g. the exception-reporting scan), date_created vs date_updated (updated≈sprint-move),
list (which sprint), tags, and the full description. Then comments:

```bash
curl -s -H "Authorization: $CU_TOKEN" "https://api.clickup.com/api/v2/task/<internal_id>/comment"
```

**Treat the description as a snapshot from date_created** — verify every claim against live
state (Step 5) before repeating it.

## Step 3 — "Has anyone started it?" (ownership sweep)

All of: assignees empty? status still backlog? zero comments? Then in the relevant repo(s):

```bash
gh pr list --repo otwarteklatki/<repo> --state open --json number,title,author,headRefName
gh api repos/otwarteklatki/<repo>/branches --paginate -q '.[].name' | grep -i '<task-id-digits>\|<service>'
gh api "repos/otwarteklatki/<repo>/commits?path=<relevant/path>&since=<task_created_date>" \
  -q '.[] | .commit.committer.date + " " + (.commit.message | split("\n")[0])'
```

Commits *after* task creation that touch the same area = someone may have partially fixed it
already (check whether the task's Definition of Done is now met — see Step 5). Verdict is one of:
**untouched / partially addressed (by whom, what remains) / effectively done (task stale)**.

**Bug-was-a-feature gotcha (learned 2026-07-09, GLOBAL-15341):** also sweep *merged* PRs for
the behavior being reported (`gh pr list --state all` + grep titles for the feature keywords) —
the "bug" may have been introduced deliberately by an earlier ticket (site-name appending came
from PR #275/GLOBAL-14517, fixing a different SEO problem). Finding the originating ticket
gives you the constraint the fix must NOT regress; put it in the brief.

**Bot-review false-positive gotcha (learned 2026-07-09, GLOBAL-15525/PR #202):** a FAILURE
check from a review bot (the retired Anima PR Review was the worst offender) is a *claim*, not a fact — verify any "Critical"
finding against main before repeating it (e.g. "module does not exist" when the module merged
weeks earlier; the bot only reads PR-changed files). Same for the task description's own grep
claims ("dead code", "zero call sites") — re-run the grep on main yourself; the *framing* can
be wrong while the underlying gap is real (e.g. wired for window listeners but not for the
error-boundary path the live reports actually take — check the feed messages' `Source` field).

## Step 4 — Slack sweep

Key ID from the task (service name, error signature, feature slug) → search, newest first:

```bash
curl -s -H "Authorization: Bearer $SLACK_TOKEN" "https://slack.com/api/search.messages" \
  --data-urlencode "query=<service-or-keyword>" --data-urlencode "count=15" --data-urlencode "sort=timestamp"
```

For each load-bearing hit, pull the **thread replies** (`conversations.replies?channel=..&ts=..`)
— the follow-up ("I fixed it ✔️") is usually in-thread, and a hit with no replies means an ask
went unanswered. Refine with `after:YYYY-MM-DD`. Known channels are in memory
`reference_slack.md` + the write-to monitor state file (`~/workspace/.write-to-monitor-state.json`
→ `channels`). Resolve user IDs you don't recognize before attributing (whois via animus-ghost).

**Phantom-traffic gotcha (learned 2026-07-09, GLOBAL-15526):** when correlating server log
entries with Slack error reports, ALWAYS check `httpRequest.userAgent` before treating a
correlated entry as evidence — every URL posted into a Slack channel gets re-fetched by
`Slackbot-LinkExpanding` seconds later, so error alerts *generate* their own trailing GETs
(405s on POST-only endpoints) that look like a smoking gun and aren't.

## Step 5 — Live infra state (never trust the description's numbers)

Follow the pointers the task gives (console links name the service/region/project). For GCP:

```bash
# is it still failing TODAY?
gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="<svc>"
  AND httpRequest.status>=500' --project=otwarte-klatki --freshness=3d --limit=10 \
  --format='value(timestamp,httpRequest.status,httpRequest.latency)'
# what do recent requests look like overall?  (drop the status filter)
# WHY is it failing — logs around one failure timestamp (textPayload catches OOM/tracebacks):
gcloud logging read '... AND timestamp>="<t-5m>" AND timestamp<="<t+5m>"' --limit=20 \
  --format='value(timestamp,severity,textPayload,httpRequest.status)'
# resource limits (undersized 512Mi/0.17cpu defaults are a recurring failure cause here):
gcloud run services describe <svc> --region=<region> --project=otwarte-klatki \
  --format='value(spec.template.spec.timeoutSeconds, spec.template.spec.containers[0].resources.limits)'
```

Railway-side tasks: see memory `reference_railway.md` / `reference_data_tracker_db.md`.
Compare live failure mode vs the description's — **they diverge more often than not** (partial
fixes land, datasets grow, the error class shifts).

**Website-behavior tasks (learned 2026-07-09, GLOBAL-15341):** the "live infra check" is
curling the page itself — but (a) use a browser User-Agent; plain curl can come back empty
(careconf.eu does), and (b) verify you hit the org's actual property before concluding anything:
a guessed domain can be a stranger's parked page (careconference.eu = 2010 Apache parking; the
real CARE site is **careconf.eu**). Sanity-check `server`/`last-modified` headers — the
boilerplate sites show `x-powered-by: Next.js` + Cloudflare.

## Step 6 — Code reality check

`gh search code --repo otwarteklatki/<repo> '<service-name>'` → fetch the current main file(s)
(`gh api repos/.../contents/<path> -q .content | base64 -d`) and read enough to say whether the
proposed fix in the description still matches the code, and what the plausible root cause is.

## Step 7 — Previous Claude sessions + Animus memory

```bash
# local sessions that touched this topic (print first user msg per hit):
grep -l '<keyword>\|GLOBAL-XXXXX' ~/.claude/projects/-home-maxh-workspace/*.jsonl
# Animus memory — PREFER the GitHub mirror over SSH (learned 2026-07-09): the VM's
# memory/ is pushed nightly to otwarteklatki/ais-ai-workspace, and gh search code
# finds the right files in one call, no VM hop:
gh search code --repo otwarteklatki/ais-ai-workspace '<keyword>' --json path -q '.[].path'
gh api repos/otwarteklatki/ais-ai-workspace/contents/<path> -q .content | base64 -d
# SSH only for same-day memory (not yet pushed) or live VM state (crontabs, /tmp logs):
gcloud compute ssh ais-ai --zone=europe-west3-a --project=otwarte-klatki \
  --command='sudo grep -ril "<keyword>" /home/openclaw/.openclaw/workspace/memory/ | head'
```

Animus's `memory/gcp-error-reports/<date>.md` usually holds the full triage that created
bot-created tasks; `memory/projects/<project>.md` holds the campaign history. Also check the
local memory index (`MEMORY.md`) for project files on the same system.

## Step 8 — The brief (deliverable)

Lead with the verdicts, then support:

1. **Resolved task** — ID, name, link, and why you matched it (if the given ID was fuzzy).
2. **Started by anyone?** — untouched / partial / stale, with the evidence in one line each.
3. **Live state vs description** — is it still happening, at what rate, and is the failure
   mode the same one the description was written about?
4. **Timeline** — dated bullets: task created → related PRs/commits → Slack handoffs → today.
5. **Root cause hypothesis + recommended next step** — fix shape per
   `feedback_solution_shape` (infra fixes get *proposed*, not silently patched).
6. **Side findings** — adjacent tasks that overlap, security flags, stale watchers' asks.

Do NOT fix, assign, comment, or start Clockify — claiming a task is the `workflow.md` playbook,
not this skill.
