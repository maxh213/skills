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
import urllib.request
from datetime import date
from pathlib import Path

DEFAULT_SPRINT_FOLDER = "90127244534"
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


def token_and_ids() -> tuple[str, str, str]:
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
    return str(tok), str(me), str(folder or DEFAULT_SPRINT_FOLDER)


def api(tok: str, path: str):
    req = urllib.request.Request(
        f"https://api.clickup.com/api/v2{path}",
        headers={"Authorization": tok},
    )
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def current_sprint(tok: str, folder: str):
    """Sprint lists are named like 'Sprint {2} (7/6 - 7/19)' — M/D, no year."""
    today = date.today()
    for lst in api(tok, f"/folder/{folder}/list")["lists"]:
        m = re.search(r"\((\d{1,2})/(\d{1,2})\s*-\s*(\d{1,2})/(\d{1,2})\)", lst["name"])
        if not m:
            continue
        m1, d1, m2, d2 = map(int, m.groups())
        start = date(today.year, m1, d1)
        end = date(today.year + (1 if m2 < m1 else 0), m2, d2)
        if start <= today <= end:
            return lst
    sys.exit("No sprint list covers today — check folder " + folder)


def main():
    show_all = "--all" in sys.argv
    tok, me, folder = token_and_ids()
    sprint = current_sprint(tok, folder)
    tasks = api(tok, f"/list/{sprint['id']}/task?subtasks=true&include_closed=false")["tasks"]

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

    print(f"Sprint: {sprint['name']}  (list {sprint['id']})\n")
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
