#!/usr/bin/env python3
"""List current-sprint ClickUp tasks assigned to Max or unassigned.

Usage: sprint_tasks.py [--all]   (--all shows every task regardless of assignee)
"""
import json
import re
import sys
import tomllib
import urllib.request
from datetime import date

SPRINT_FOLDER = "90127244534"  # ClickUp IT Sprint folder
ME = "10857117"  # Max's ClickUp user ID
CONFIG = "/home/maxh/.config/workstation/config.toml"


def token():
    with open(CONFIG, "rb") as f:
        cfg = tomllib.load(f)

    def find(d, path=""):
        for k, v in d.items():
            if isinstance(v, dict):
                r = find(v, path + k + ".")
                if r:
                    return r
            elif "clickup" in (path + k).lower() and ("token" in k.lower() or "key" in k.lower()):
                return v

    t = find(cfg)
    if not t:
        sys.exit("No ClickUp token found in config.toml")
    return t


def api(tok, path):
    req = urllib.request.Request(f"https://api.clickup.com/api/v2{path}", headers={"Authorization": tok})
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def current_sprint(tok):
    """Sprint lists are named like 'Sprint {2} (7/6 - 7/19)' — M/D, no year."""
    today = date.today()
    for lst in api(tok, f"/folder/{SPRINT_FOLDER}/list")["lists"]:
        m = re.search(r"\((\d{1,2})/(\d{1,2})\s*-\s*(\d{1,2})/(\d{1,2})\)", lst["name"])
        if not m:
            continue
        m1, d1, m2, d2 = map(int, m.groups())
        start = date(today.year, m1, d1)
        end = date(today.year + (1 if m2 < m1 else 0), m2, d2)
        if start <= today <= end:
            return lst
    sys.exit("No sprint list covers today — check folder " + SPRINT_FOLDER)


def main():
    show_all = "--all" in sys.argv
    tok = token()
    sprint = current_sprint(tok)
    tasks = api(tok, f"/list/{sprint['id']}/task?subtasks=true&include_closed=false")["tasks"]

    rows = []
    for t in tasks:
        assignees = [str(a["id"]) for a in t["assignees"]]
        mine = ME in assignees
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
