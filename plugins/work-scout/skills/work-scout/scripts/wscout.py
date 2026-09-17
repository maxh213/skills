#!/usr/bin/env python3
"""wscout — read-only Slack + ClickUp lookups, built for a cheap scout model to call.

Credentials come from ~/.config/workstation/config.toml ([slack].token, [clickup].token)
and are never printed. Every command is read-only: the Slack client refuses any
method not on its read allow-list and the ClickUp client only ever issues GETs.
Output is compact text meant to be read by a model, not JSON dumps.

Run `wscout.py --help` and `wscout.py <group> --help` for the commands.
"""
import argparse
import json
import os
import re
import sys
import time
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

CFG_PATH = os.path.expanduser("~/.config/workstation/config.toml")
CACHE_DIR = os.path.expanduser("~/.cache/work-scout")
CACHE_TTL = 24 * 3600
SLACK_READ_METHODS = {
    "auth.test", "users.list", "conversations.list", "conversations.history",
    "conversations.replies", "conversations.info", "search.messages",
}
CLICKUP_LINK = re.compile(r"app\.clickup\.com/t/(?:\d+/)?([A-Za-z0-9-]+)")
CLICKUP_CUSTOM_ID = re.compile(r"\b([A-Z]{2,10}-\d{3,6})\b")


# --- plumbing ---------------------------------------------------------------

def die(msg, code=1):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


_cfg = None


def cfg():
    global _cfg
    if _cfg is None:
        try:
            with open(CFG_PATH, "rb") as fh:
                _cfg = tomllib.load(fh)
        except FileNotFoundError:
            die(f"config not found: {CFG_PATH}")
    return _cfg


def cached(name, loader, ttl=CACHE_TTL):
    os.makedirs(CACHE_DIR, exist_ok=True)
    path = os.path.join(CACHE_DIR, name + ".json")
    if os.path.exists(path) and time.time() - os.path.getmtime(path) < ttl:
        with open(path) as fh:
            return json.load(fh)
    data = loader()
    with open(path, "w") as fh:
        json.dump(data, fh)
    return data


def local(ts):
    """Epoch seconds or milliseconds -> local 'YYYY-MM-DD HH:MM'."""
    if ts in (None, "", 0, "0"):
        return "-"
    ts = float(ts)
    if ts > 1e11:
        ts /= 1000
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")


def parse_when(s):
    """today | yesterday | 3h | 2d | 1w | YYYY-MM-DD[ HH:MM] -> epoch seconds (local)."""
    if s is None:
        return None
    s = s.strip().lower()
    now = datetime.now()
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if s == "today":
        return midnight.timestamp()
    if s == "yesterday":
        return (midnight - timedelta(days=1)).timestamp()
    m = re.fullmatch(r"(\d+)\s*([hdw])", s)
    if m:
        n, unit = int(m.group(1)), m.group(2)
        delta = {"h": timedelta(hours=n), "d": timedelta(days=n), "w": timedelta(weeks=n)}[unit]
        return (now - delta).timestamp()
    try:
        return datetime.fromisoformat(s).timestamp()
    except ValueError:
        die(f"cannot parse time '{s}' (use today, yesterday, 3h, 2d, 1w or YYYY-MM-DD[ HH:MM])")


def clip(text, n):
    text = (text or "").strip()
    return text if len(text) <= n else text[:n] + f"… [truncated, {len(text)} chars total; use --full]"


# --- Slack ------------------------------------------------------------------

def slack(method, **params):
    if method not in SLACK_READ_METHODS:
        die(f"refusing non-read Slack method {method}")
    token = cfg().get("slack", {}).get("token") or die("no [slack].token in config")
    body = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None}).encode()
    for attempt in range(5):
        req = urllib.request.Request("https://slack.com/api/" + method, data=body,
                                     headers={"Authorization": "Bearer " + token})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.load(resp)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(int(e.headers.get("Retry-After", "3")))
                continue
            die(f"slack {method}: HTTP {e.code}")
        if data.get("ok"):
            return data
        if data.get("error") == "ratelimited":
            time.sleep(3 * (attempt + 1))
            continue
        die(f"slack {method}: {data.get('error')}")
    die(f"slack {method}: rate limited, gave up")


def slack_paginate(method, key, **params):
    out, cursor = [], None
    while True:
        data = slack(method, cursor=cursor, limit=1000, **params)
        out.extend(data.get(key, []))
        cursor = (data.get("response_metadata") or {}).get("next_cursor") or None
        if not cursor:
            return out


def slack_users():
    def load():
        users = {}
        for u in slack_paginate("users.list", "members"):
            p = u.get("profile") or {}
            users[u["id"]] = {
                "name": u.get("name", ""),
                "real": u.get("real_name") or p.get("real_name", ""),
                "display": p.get("display_name", ""),
                "deleted": bool(u.get("deleted")),
                "bot": bool(u.get("is_bot")),
            }
        return users
    return cached("slack_users", load)


def user_label(uid, users=None):
    users = users if users is not None else slack_users()
    u = users.get(uid)
    if not u:
        return uid or "?"
    return u["real"] or u["display"] or u["name"]


def slack_channels():
    def load():
        users = slack_users()
        chans = {}
        for c in slack_paginate("conversations.list", "channels",
                                types="public_channel,private_channel,mpim,im",
                                exclude_archived="true"):
            if c.get("is_im"):
                name = "dm:" + user_label(c.get("user"), users)
            else:
                name = c.get("name", "")
            chans[c["id"]] = {"name": name, "im": bool(c.get("is_im")),
                              "mpim": bool(c.get("is_mpim")), "user": c.get("user")}
        return chans
    return cached("slack_channels", load)


def find_users(q):
    users = slack_users()
    if re.fullmatch(r"[UW][A-Z0-9]+", q.upper()) and q.upper() in users:
        return [q.upper()]
    ql = q.lower()
    return [uid for uid, u in users.items() if not u["deleted"] and (
        ql in u["real"].lower() or ql in u["name"].lower() or ql in u["display"].lower())]


def resolve_user(q):
    hits = find_users(q)
    if len(hits) == 1:
        return hits[0]
    if not hits:
        die(f"no Slack user matches '{q}' (try `slack users <partial name>`)")
    users, ql = slack_users(), q.lower()
    exact = [h for h in hits if ql in (users[h]["real"].lower(), users[h]["name"].lower(),
                                       users[h]["display"].lower())]
    if len(exact) == 1:
        return exact[0]
    die("ambiguous Slack user '%s': %s" % (q, ", ".join(f"{h}={user_label(h)}" for h in hits[:10])))


def resolve_channel(q):
    chans = slack_channels()
    q = q.lstrip("#")
    if q in chans:
        return q
    if q.lower().startswith("dm:"):
        uid = resolve_user(q[3:])
        for cid, c in chans.items():
            if c["im"] and c.get("user") == uid:
                return cid
        die(f"no DM conversation with {user_label(uid)} ({uid})")
    ql = q.lower()
    exact = [cid for cid, c in chans.items() if c["name"].lower() == ql]
    if exact:
        return exact[0]
    hits = [cid for cid, c in chans.items() if ql in c["name"].lower()]
    if len(hits) == 1:
        return hits[0]
    if not hits:
        die(f"no Slack conversation matches '{q}' (try `slack channels <partial>`)")
    die("ambiguous conversation '%s': %s" % (q, ", ".join(chans[h]["name"] for h in hits[:15])))


def render_text(text, users):
    text = text or ""
    text = re.sub(r"<@([UW][A-Z0-9]+)(?:\|[^>]*)?>", lambda m: "@" + user_label(m.group(1), users), text)
    text = re.sub(r"<#([A-Z0-9]+)\|([^>]*)>", r"#\2", text)
    text = re.sub(r"<(https?://[^|>]+)\|([^>]*)>", r"\2 (\1)", text)
    text = re.sub(r"<(https?://[^>]+)>", r"\1", text)
    return text.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")


def clickup_ids(text):
    ids = []
    for m in CLICKUP_LINK.finditer(text or ""):
        if m.group(1) not in ids:
            ids.append(m.group(1))
    for m in CLICKUP_CUSTOM_ID.finditer(text or ""):
        if m.group(1) not in ids:
            ids.append(m.group(1))
    return ids


def print_msg(m, users, chan_name=None, indent="", permalink=None):
    who = user_label(m.get("user"), users) if m.get("user") else (m.get("username") or m.get("bot_id") or "?")
    head = f"{indent}[{local(m['ts'])}]"
    if chan_name:
        head += f" #{chan_name}"
    print(f"{head} {who}: {render_text(m.get('text', ''), users)}")
    for a in m.get("attachments") or []:
        title = a.get("title") or a.get("fallback") or ""
        if title and title != "[no preview available]":
            print(f"{indent}   ↳ attachment: {title[:200]}")
    for f in m.get("files") or []:
        print(f"{indent}   ↳ file: {f.get('name') or f.get('title')}")
    ids = clickup_ids(m.get("text", ""))
    if ids:
        print(f"{indent}   ↳ clickup: {', '.join(ids)}")
    if m.get("reply_count"):
        print(f"{indent}   ↳ thread: {m['reply_count']} replies (ts={m['ts']})")
    if permalink:
        print(f"{indent}   ↳ link: {permalink}")


def cmd_whoami(a):
    me = slack("auth.test")
    print(f"slack: {me.get('user')} ({me.get('user_id')}) in workspace {me.get('team')}")
    team = cu_team()
    uid = str(cfg().get("clickup", {}).get("user_id", ""))
    name = team["members"].get(uid, {}).get("name", "?")
    print(f"clickup: user {uid} ({name}) in workspace {team['name']} (team_id {team['id']})")
    print(f"local time now: {datetime.now().strftime('%Y-%m-%d %H:%M')} ({datetime.now().astimezone().tzname()})")


def cmd_slack_users(a):
    users = slack_users()
    hits = find_users(a.query) if a.query else list(users)
    for uid in hits[:a.limit]:
        u = users[uid]
        flags = " [bot]" if u["bot"] else ""
        print(f"{uid}  {u['real'] or '-'}  (@{u['name']}, display '{u['display']}'){flags}")
    if not hits:
        print("no matches")


def cmd_slack_channels(a):
    chans = slack_channels()
    ql = (a.query or "").lower()
    rows = [(cid, c) for cid, c in chans.items() if ql in c["name"].lower()]
    rows.sort(key=lambda r: r[1]["name"])
    for cid, c in rows[:a.limit]:
        kind = "dm" if c["im"] else "group-dm" if c["mpim"] else "channel"
        print(f"{cid}  {c['name']}  ({kind})")
    if not rows:
        print("no matches")


def cmd_slack_search(a):
    users = slack_users()
    q = a.query or ""
    if a.frm:
        q += f" from:<@{resolve_user(a.frm)}>"
    if a.channel:
        cid = resolve_channel(a.channel)
        c = slack_channels()[cid]
        if c["im"] or c["mpim"]:
            die("--in only works for channels; for DMs use `slack channel dm:<name> --since ...`")
        q += f" in:#{c['name']}"
    since = parse_when(a.since)
    if since:
        # Slack's after: is exclusive of the day itself, so ask a day early and filter locally.
        q += " after:" + (datetime.fromtimestamp(since) - timedelta(days=1)).strftime("%Y-%m-%d")
    q = q.strip()
    if not q:
        die("empty search: give a query and/or --from/--in/--since")
    matches, page, total = [], 1, 0
    while True:
        data = slack("search.messages", query=q, count=100, page=page, sort="timestamp", sort_dir="desc")
        msgs = data["messages"]
        total = msgs.get("total", 0)
        matches.extend(msgs.get("matches", []))
        pages = (msgs.get("paging") or {}).get("pages", 1)
        if page >= pages or len(matches) >= a.limit or (since and matches and float(matches[-1]["ts"]) < since):
            break
        page += 1
    if since:
        matches = [m for m in matches if float(m["ts"]) >= since]
    matches = sorted(matches, key=lambda m: float(m["ts"]))[-a.limit:]
    print(f"query: {q}  -> showing {len(matches)} of {total} matches")
    for m in matches:
        print_msg(m, users, chan_name=(m.get("channel") or {}).get("name"), permalink=m.get("permalink"))


def cmd_slack_channel(a):
    users, chans = slack_users(), slack_channels()
    cid = resolve_channel(a.channel)
    since = parse_when(a.since)
    msgs, cursor = [], None
    while True:
        data = slack("conversations.history", channel=cid, oldest=since, limit=200, cursor=cursor)
        msgs.extend(data.get("messages", []))
        cursor = (data.get("response_metadata") or {}).get("next_cursor") or None
        if not cursor or len(msgs) >= a.limit:
            break
    msgs = sorted(msgs, key=lambda m: float(m["ts"]))[-a.limit:]
    print(f"#{chans[cid]['name']} ({cid}): {len(msgs)} messages since {a.since}")
    for m in msgs:
        print_msg(m, users)
        if m.get("reply_count") and not a.no_threads:
            replies = slack("conversations.replies", channel=cid, ts=m["ts"], limit=200)["messages"][1:]
            for r in replies:
                print_msg(r, users, indent="    ")


def cmd_slack_thread(a):
    users, chans = slack_users(), slack_channels()
    cid = resolve_channel(a.channel)
    msgs = slack("conversations.replies", channel=cid, ts=a.ts, limit=200)["messages"]
    print(f"thread in #{chans[cid]['name']} ({len(msgs)} messages incl. parent)")
    for i, m in enumerate(msgs):
        print_msg(m, users, indent="" if i == 0 else "    ")


# --- ClickUp ----------------------------------------------------------------

def cu(path, **params):
    token = cfg().get("clickup", {}).get("token") or die("no [clickup].token in config")
    url = "https://api.clickup.com/api/v2" + path
    params = {k: v for k, v in params.items() if v is not None}
    if params:
        url += "?" + urllib.parse.urlencode(params, doseq=True)
    for attempt in range(5):
        req = urllib.request.Request(url, headers={"Authorization": token})  # GET only
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(int(e.headers.get("Retry-After", "5")))
                continue
            body = e.read().decode(errors="replace")[:300]
            die(f"clickup {path}: HTTP {e.code} {body}")
    die(f"clickup {path}: rate limited, gave up")


def cu_team():
    def load():
        teams = cu("/team")["teams"]
        want = str(cfg().get("clickup", {}).get("team_id", ""))
        t = next((t for t in teams if str(t["id"]) == want), teams[0])
        members = {}
        for m in t.get("members", []):
            u = m.get("user", {})
            members[str(u.get("id"))] = {"name": u.get("username") or "", "email": u.get("email") or ""}
        return {"id": t["id"], "name": t["name"], "members": members}
    return cached("clickup_team", load)


def member_name(uid):
    return cu_team()["members"].get(str(uid), {}).get("name") or str(uid)


def resolve_member(q):
    if q == "me":
        return str(cfg().get("clickup", {}).get("user_id") or die("no [clickup].user_id in config"))
    if q.isdigit():
        return q
    ql = q.lower()
    members = cu_team()["members"]
    hits = [uid for uid, m in members.items() if ql in m["name"].lower() or ql in m["email"].lower()]
    if len(hits) == 1:
        return hits[0]
    if not hits:
        die(f"no ClickUp member matches '{q}' (try `clickup members <partial>`)")
    die("ambiguous ClickUp member '%s': %s" % (q, ", ".join(f"{h}={members[h]['name']}" for h in hits[:10])))


def cu_lists():
    """All lists in the workspace: {list_id: {name, folder, space}}. Cached; first build is slow."""
    def load():
        team = cu_team()
        out = {}
        for space in cu(f"/team/{team['id']}/space", archived="false").get("spaces", []):
            for folder in cu(f"/space/{space['id']}/folder", archived="false").get("folders", []):
                for lst in folder.get("lists", []):
                    out[str(lst["id"])] = {"name": lst["name"], "folder": folder["name"], "space": space["name"]}
            for lst in cu(f"/space/{space['id']}/list", archived="false").get("lists", []):
                out[str(lst["id"])] = {"name": lst["name"], "folder": "", "space": space["name"]}
        return out
    return cached("clickup_lists", load)


def resolve_list(q):
    lists = cu_lists()
    if q in lists:
        return q
    ql = q.lower()
    hits = [lid for lid, l in lists.items() if ql in l["name"].lower()]
    if len(hits) == 1:
        return hits[0]
    if not hits:
        die(f"no ClickUp list matches '{q}' (try `clickup lists <partial>`)")
    die("ambiguous list '%s': %s" % (q, "; ".join(f"{lists[h]['name']} [{lists[h]['folder']}]" for h in hits[:10])))


def current_sprint_list():
    today = datetime.now()
    pat = re.compile(r"\((\d{1,2})/(\d{1,2})\s*-\s*(\d{1,2})/(\d{1,2})\)")
    for lid, l in cu_lists().items():
        if "sprint" not in (l["name"] + " " + l["folder"]).lower():
            continue
        m = pat.search(l["name"])
        if not m:
            continue
        m1, d1, m2, d2 = map(int, m.groups())
        start = datetime(today.year, m1, d1)
        end = datetime(today.year + (1 if m2 < m1 else 0), m2, d2, 23, 59)
        if start <= today <= end:
            return lid, l
    return None, None


def task_ref(s):
    m = CLICKUP_LINK.search(s)
    if m:
        s = m.group(1)
    if re.fullmatch(r"[A-Za-z]+-\d+", s):
        return s.upper(), {"custom_task_ids": "true", "team_id": cu_team()["id"]}
    return s, {}


def task_line(t):
    assignees = ", ".join(a.get("username", "?") for a in t.get("assignees", [])) or "unassigned"
    lst = (t.get("list") or {}).get("name", "?")
    return (f"{t.get('custom_id') or t['id']} | {t['status']['status']} | {assignees} | {lst} | "
            f"updated {local(t.get('date_updated'))} | {t['name']}")


def custom_field_value(f):
    v = f.get("value")
    if v in (None, "", []):
        return None
    opts = (f.get("type_config") or {}).get("options") or []
    if f["type"] == "drop_down":
        for o in opts:
            if o.get("id") == v or o.get("orderindex") == v:
                return o.get("name")
        return str(v)
    if f["type"] == "labels":
        names = [o.get("label") for o in opts if o.get("id") in v]
        return ", ".join(names) if names else str(v)
    if isinstance(v, (dict, list)):
        return json.dumps(v)[:200]
    return str(v)


def print_task(t, full=False, max_chars=6000):
    prio = (t.get("priority") or {}).get("priority") or "-"
    assignees = ", ".join(a.get("username", "?") for a in t.get("assignees", [])) or "unassigned"
    creator = (t.get("creator") or {}).get("username", "?")
    lst, folder = (t.get("list") or {}).get("name", "?"), (t.get("folder") or {}).get("name", "")
    print(f"{t.get('custom_id') or t['id']}  {t['name']}")
    print(f"  status: {t['status']['status']} | priority: {prio} | assignees: {assignees} | creator: {creator}")
    print(f"  list: {lst}" + (f" / {folder}" if folder else ""))
    print(f"  created {local(t.get('date_created'))} | updated {local(t.get('date_updated'))} | "
          f"due {local(t.get('due_date'))} | closed {local(t.get('date_closed'))}")
    print(f"  url: {t.get('url')}")
    if t.get("parent"):
        print(f"  parent task: {t['parent']}")
    if full:
        for f in t.get("custom_fields") or []:
            v = custom_field_value(f)
            if v:
                print(f"  field {f['name']}: {v}")
    desc = t.get("markdown_description") or t.get("description") or ""
    if desc.strip():
        print("  description:")
        for line in clip(desc, 10**9 if full else max_chars).splitlines():
            print("    " + line)
    else:
        print("  description: (empty)")


def cmd_clickup_task(a):
    for ref in a.ids:
        tid, extra = task_ref(ref)
        t = cu(f"/task/{tid}", include_markdown_description="true", **extra)
        print_task(t, full=a.full, max_chars=a.max_chars)
        if not a.no_comments:
            comments = cu(f"/task/{t['id']}/comment").get("comments", [])
            print(f"  comments ({len(comments)}, oldest first):")
            for c in sorted(comments, key=lambda c: int(c.get("date", 0))):
                who = (c.get("user") or {}).get("username", "?")
                text = clip(c.get("comment_text", ""), 10**9 if a.full else a.max_chars)
                print(f"  - [{local(c.get('date'))}] {who}: {text}")
        print()


def cmd_clickup_tasks(a):
    team = cu_team()
    params = {"order_by": "updated", "subtasks": "true",
              "include_closed": "true" if a.include_closed else None}
    if a.assignee:
        params["assignees[]"] = [resolve_member(x) for x in a.assignee]
    since = parse_when(a.since)
    if since:
        params["date_updated_gt"] = int(since * 1000)
    created = parse_when(a.created_since)
    if created:
        params["date_created_gt"] = int(created * 1000)
    if a.list:
        params["list_ids[]"] = [resolve_list(x) for x in a.list]
    if a.status:
        params["statuses[]"] = a.status
    tasks, page = [], 0
    while True:
        data = cu(f"/team/{team['id']}/task", page=page, **params)
        tasks.extend(data.get("tasks", []))
        if data.get("last_page", True) or len(tasks) >= a.limit:
            break
        page += 1
    tasks = tasks[:a.limit]
    print(f"{len(tasks)} tasks (newest update first)")
    for t in tasks:
        print(task_line(t))


def cmd_clickup_sprint(a):
    lid, l = current_sprint_list()
    if not lid:
        die("no sprint list covering today found (looked for lists named like 'Sprint {N} (M/D - M/D)')")
    print(f"current sprint: {l['name']} [{l['folder']}] (list {lid})")
    a.list, a.since, a.created_since, a.status = [lid], None, None, None
    cmd_clickup_tasks(a)


def cmd_clickup_lists(a):
    ql = (a.query or "").lower()
    rows = [(lid, l) for lid, l in cu_lists().items() if ql in (l["name"] + " " + l["folder"] + " " + l["space"]).lower()]
    for lid, l in sorted(rows, key=lambda r: (r[1]["space"], r[1]["folder"], r[1]["name"]))[:a.limit]:
        print(f"{lid}  {l['name']}  [{l['folder'] or 'no folder'} / {l['space']}]")
    if not rows:
        print("no matches")


def cmd_clickup_members(a):
    members = cu_team()["members"]
    ql = (a.query or "").lower()
    rows = [(uid, m) for uid, m in members.items() if ql in m["name"].lower() or ql in m["email"].lower()]
    for uid, m in sorted(rows, key=lambda r: r[1]["name"].lower())[:a.limit]:
        print(f"{uid}  {m['name']}  {m['email']}")
    if not rows:
        print("no matches")


# --- CLI --------------------------------------------------------------------

def build_parser():
    p = argparse.ArgumentParser(prog="wscout.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    top = p.add_subparsers(dest="group", required=True)

    top.add_parser("whoami", help="who the requester is on Slack and ClickUp, and the local time").set_defaults(fn=cmd_whoami)

    s = top.add_parser("slack", help="Slack lookups (read-only)").add_subparsers(dest="cmd", required=True)
    x = s.add_parser("users", help="find Slack users by (partial) name")
    x.add_argument("query", nargs="?"); x.add_argument("--limit", type=int, default=30); x.set_defaults(fn=cmd_slack_users)
    x = s.add_parser("channels", help="find channels / DMs by (partial) name")
    x.add_argument("query", nargs="?"); x.add_argument("--limit", type=int, default=50); x.set_defaults(fn=cmd_slack_channels)
    x = s.add_parser("search", help="search messages across all channels and DMs (fastest way to find what someone said)")
    x.add_argument("query", nargs="?", default="", help="free text; may be empty when --from/--in/--since are given")
    x.add_argument("--from", dest="frm", help="author (partial name or user id)")
    x.add_argument("--in", dest="channel", help="channel name")
    x.add_argument("--since", help="today | yesterday | 3h | 2d | 1w | YYYY-MM-DD")
    x.add_argument("--limit", type=int, default=50); x.set_defaults(fn=cmd_slack_search)
    x = s.add_parser("channel", help="read a channel or DM (dm:<name>) with thread replies")
    x.add_argument("channel"); x.add_argument("--since", default="2d"); x.add_argument("--limit", type=int, default=200)
    x.add_argument("--no-threads", action="store_true"); x.set_defaults(fn=cmd_slack_channel)
    x = s.add_parser("thread", help="read one thread by channel + parent ts")
    x.add_argument("channel"); x.add_argument("ts"); x.set_defaults(fn=cmd_slack_thread)

    c = top.add_parser("clickup", help="ClickUp lookups (read-only)").add_subparsers(dest="cmd", required=True)
    x = c.add_parser("members", help="find workspace members by (partial) name or email")
    x.add_argument("query", nargs="?"); x.add_argument("--limit", type=int, default=30); x.set_defaults(fn=cmd_clickup_members)
    x = c.add_parser("task", help="full task(s) by custom id (GLOBAL-123), raw id or URL, with comments")
    x.add_argument("ids", nargs="+"); x.add_argument("--no-comments", action="store_true")
    x.add_argument("--full", action="store_true", help="untruncated description/comments plus custom fields")
    x.add_argument("--max-chars", type=int, default=6000); x.set_defaults(fn=cmd_clickup_task)
    x = c.add_parser("tasks", help="filter tasks: by assignee, update/creation time, list, status")
    x.add_argument("--assignee", action="append", help="member name, id or 'me' (repeatable)")
    x.add_argument("--since", help="updated after: today | 2d | YYYY-MM-DD ...")
    x.add_argument("--created-since", help="created after: same formats")
    x.add_argument("--list", action="append", help="list name or id (repeatable)")
    x.add_argument("--status", action="append", help="status name (repeatable)")
    x.add_argument("--include-closed", action="store_true"); x.add_argument("--limit", type=int, default=50)
    x.set_defaults(fn=cmd_clickup_tasks)
    x = c.add_parser("sprint", help="tasks in the sprint list whose date range covers today")
    x.add_argument("--assignee", action="append"); x.add_argument("--include-closed", action="store_true")
    x.add_argument("--limit", type=int, default=100); x.set_defaults(fn=cmd_clickup_sprint)
    x = c.add_parser("lists", help="find lists by (partial) name, folder or space")
    x.add_argument("query", nargs="?"); x.add_argument("--limit", type=int, default=50); x.set_defaults(fn=cmd_clickup_lists)
    return p


def main():
    args = build_parser().parse_args()
    try:
        args.fn(args)
    except BrokenPipeError:
        pass


if __name__ == "__main__":
    main()
