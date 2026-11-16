#!/usr/bin/env python3
"""List current-sprint ClickUp tasks assigned to the configured user or unassigned.

Usage: sprint_tasks.py [--all]   (--all shows every task regardless of assignee)
"""
from __future__ import annotations

import json
import os
import re
import sys
import tomllib
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

# Several of these can have a sprint covering today. Tie-break order when the
# user's own tasks (then unassigned tasks) don't decide. The configured
# clickup.sprint_folder is appended when it isn't already listed.
SPRINT_FOLDERS = (
    "901211261515",  # EU Project Team
    "901214999237",  # Sprints
)
DEFAULT_SPRINT_FOLDER = "90127244534"  # IT sprint Folder; checked last via clickup.sprint_folder
DEFAULT_CONFIG = Path.home() / ".config" / "workstation" / "config.toml"


def _plugin_scripts() -> Path | None:
    for env in ("GROK_PLUGIN_ROOT", "CLAUDE_PLUGIN_ROOT"):
        raw = os.environ.get(env)
        if raw:
            cand = Path(raw) / "scripts"
            if (cand / "credentials.py").exists():
                return cand
    # this file is skills/sprint-tasks/scripts/sprint_tasks.py → plugin/scripts
    cand = Path(__file__).resolve().parents[3] / "scripts"
    if (cand / "credentials.py").exists():
        return cand
    return None


def _nested(d: dict, dotted: str):
    cur = d
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def _load_cfg() -> dict:
    p = Path(os.environ.get("WORKSTATION_CONFIG", DEFAULT_CONFIG)).expanduser()
    if not p.is_file():
        return {}
    with p.open("rb") as f:
        return tomllib.load(f)


def user_id_from_api(tok: str) -> str:
    data = api(tok, "/user")
    uid = (data.get("user") or {}).get("id")
    if not uid:
        sys.exit("ClickUp /user did not return an id — run setup-prompt-manager")
    return str(uid)


def token_and_ids() -> tuple[str, str, list[str]]:
    scripts = _plugin_scripts()
    tok = me = folder = None
    if scripts:
        sys.path.insert(0, str(scripts))
        from credentials import get_value  # type: ignore

        tok = get_value("clickup.token")
        try:
            me = get_value("clickup.user_id")
        except SystemExit:
            me = None
        try:
            folder = get_value("clickup.sprint_folder")
        except SystemExit:
            folder = DEFAULT_SPRINT_FOLDER
    else:
        cfg = _load_cfg()
        tok = os.environ.get("CLICKUP_TOKEN") or _nested(cfg, "clickup.token")
        me = os.environ.get("CLICKUP_USER_ID") or _nested(cfg, "clickup.user_id")
        folder = (
            os.environ.get("CLICKUP_SPRINT_FOLDER")
            or _nested(cfg, "clickup.sprint_folder")
            or DEFAULT_SPRINT_FOLDER
        )
    if not tok:
        sys.exit("No ClickUp token — run setup-prompt-manager")
    if not me:
        me = user_id_from_api(str(tok))
    folders = list(SPRINT_FOLDERS)
    extra = str(folder or DEFAULT_SPRINT_FOLDER)
    if extra not in folders:
        folders.append(extra)
    return str(tok), str(me), folders


def api(tok: str, path: str):
    req = urllib.request.Request(
        f"https://api.clickup.com/api/v2{path}",
        headers={"Authorization": tok},
    )
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def covering_sprint(lists: list, today: date) -> dict | None:
    """Sprint lists are named like 'Sprint {2} (7/6 - 7/19)' — M/D, no year."""
    for lst in lists:
        m = re.search(r"\((\d{1,2})/(\d{1,2})\s*-\s*(\d{1,2})/(\d{1,2})\)", lst["name"])
        if not m:
            continue
        m1, d1, m2, d2 = map(int, m.groups())
        start = date(today.year, m1, d1)
        end = date(today.year + (1 if m2 < m1 else 0), m2, d2)
        if start <= today <= end:
            return lst
    return None


def open_tasks(tok: str, list_id: str) -> list:
    """All open tasks on a list. ClickUp pages at 100."""
    tasks: list = []
    page = 0
    while True:
        batch = api(
            tok,
            f"/list/{list_id}/task?subtasks=true&include_closed=false&page={page}",
        )["tasks"]
        tasks.extend(batch)
        if len(batch) < 100:
            return tasks
        page += 1


def pick_sprint(candidates: list[dict]) -> dict:
    """Prefer the covering sprint the user actually has work in.

    Most open tasks assigned to them, then most unassigned, then earlier folder.
    """
    return max(candidates, key=lambda c: (c["mine"], c["unassigned"], -c["order"]))


def current_sprint(tok: str, folders: list[str], me: str) -> tuple[dict, list]:
    """Covering sprint for this user, plus its open tasks. Skip a folder that 404s."""
    today = date.today()
    candidates = []
    for order, folder in enumerate(folders):
        try:
            lists = api(tok, f"/folder/{folder}/list")["lists"]
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                sys.exit(f"ClickUp auth failed (HTTP {e.code}) — run setup-prompt-manager")
            continue
        found = covering_sprint(lists, today)
        if not found:
            continue
        tasks = open_tasks(tok, found["id"])
        mine = sum(1 for t in tasks if any(str(a["id"]) == me for a in t["assignees"]))
        unassigned = sum(1 for t in tasks if not t["assignees"])
        candidates.append({
            "id": found["id"],
            "name": found["name"],
            "folder_id": folder,
            "order": order,
            "mine": mine,
            "unassigned": unassigned,
            "tasks": tasks,
        })
    if not candidates:
        sys.exit("No sprint list covers today — checked folders " + ", ".join(folders))
    chosen = pick_sprint(candidates)
    return (
        {"id": chosen["id"], "name": chosen["name"], "folder_id": chosen["folder_id"]},
        chosen["tasks"],
    )


def main():
    show_all = "--all" in sys.argv
    tok, me, folders = token_and_ids()
    sprint, tasks = current_sprint(tok, folders, me)

    rows = []
    for t in tasks:
        assignees = [str(a["id"]) for a in t["assignees"]]
        mine = me in assignees
        if not show_all and assignees and not mine:
            continue
        rows.append({
            "who": "me" if mine else ("UNASSIGNED" if not assignees else ",".join(a["username"] for a in t["assignees"])),
            "status": t["status"]["status"],
            "priority": (t.get("priority") or {}).get("priority") or "none",
            "points": t.get("points"),
            "id": t.get("custom_id") or t["id"],
            "name": t["name"],
            "url": t["url"],
        })

    print(f"Sprint: {sprint['name']}  (list {sprint['id']}, folder {sprint['folder_id']})\n")
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
