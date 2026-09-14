#!/usr/bin/env python3
"""File a TASK-<slug>.md into ClickUp: the current sprint (assigned to me) or PM TRIAGE (unassigned).

Usage:
  task_to_clickup.py options [--dest sprint|triage]
      Resolve the destination list and print its field options (Field of work,
      Project name, MoSCoW) as JSON, so names can be suggested from live data.

  task_to_clickup.py create --file TASK.md --dest sprint|triage \
      --points N --moscow "Should Have" --project "Boilerplate" \
      --field-of-work "Write to Page" [--field-of-work ...] --dod "one sentence" [--dry-run]
      Create the task. Title = the file's H1; description = the rest, as markdown.
      Prints JSON: id, custom_id, url, list. --dry-run prints the payload instead.

  task_to_clickup.py delete TASK_ID
      Delete a task (undo a filing made by mistake).

Credentials: clickup.token / clickup.user_id / clickup.sprint_folder via the plugin's
credentials.py, else ~/.config/workstation/config.toml, else CLICKUP_* env vars.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tomllib
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

DEFAULT_SPRINT_FOLDER = "90127244534"
DEFAULT_TRIAGE_LIST = "901218619665"  # Global organization (AI) → PM Triage IT → PM TRIAGE
DEFAULT_CONFIG = Path.home() / ".config" / "workstation" / "config.toml"
API = "https://api.clickup.com/api/v2"

# The sprint and triage lists carry two fields both named "MoSCoW". This one holds
# the values on 13 of 20 sprint tasks and 74 of 100 triage tasks; the other is a stray.
PREFERRED_FIELD_IDS = {"moscow": "7bda9d43-c0a9-4b43-930e-eab87306f11c"}

FIELD_NAMES = {
    "field_of_work": "Field of work",
    "project": "Project name",
    "moscow": "MoSCoW",
    "dod": "Definition Of Done",
}


# ---------------------------------------------------------------- credentials

def _plugin_scripts() -> Path | None:
    for env in ("GROK_PLUGIN_ROOT", "CLAUDE_PLUGIN_ROOT"):
        raw = os.environ.get(env)
        if raw and (Path(raw) / "scripts" / "credentials.py").exists():
            return Path(raw) / "scripts"
    # skills/task-to-clickup/scripts/this.py → plugin/scripts
    cand = Path(__file__).resolve().parents[3] / "scripts"
    return cand if (cand / "credentials.py").exists() else None


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


def credentials() -> dict:
    scripts = _plugin_scripts()
    out = {"token": None, "user_id": None, "sprint_folder": None, "triage_list": None}
    if scripts:
        sys.path.insert(0, str(scripts))
        from credentials import get_value  # type: ignore

        def opt(key):
            try:
                return get_value(key)
            except SystemExit:
                return None

        out["token"] = opt("clickup.token")
        out["user_id"] = opt("clickup.user_id")
        out["sprint_folder"] = opt("clickup.sprint_folder")
        out["triage_list"] = opt("clickup.triage_list")
    else:
        cfg = _load_cfg()
        out["token"] = os.environ.get("CLICKUP_TOKEN") or _nested(cfg, "clickup.token")
        out["user_id"] = os.environ.get("CLICKUP_USER_ID") or _nested(cfg, "clickup.user_id")
        out["sprint_folder"] = os.environ.get("CLICKUP_SPRINT_FOLDER") or _nested(cfg, "clickup.sprint_folder")
        out["triage_list"] = os.environ.get("CLICKUP_TRIAGE_LIST") or _nested(cfg, "clickup.triage_list")
    if not out["token"]:
        sys.exit("No ClickUp token — run setup-prompt-manager")
    out["sprint_folder"] = str(out["sprint_folder"] or DEFAULT_SPRINT_FOLDER)
    out["triage_list"] = str(out["triage_list"] or DEFAULT_TRIAGE_LIST)
    if not out["user_id"]:
        out["user_id"] = str(api(out["token"], "/user")["user"]["id"])
    out["user_id"] = str(out["user_id"])
    return out


# ------------------------------------------------------------------------ api

def api(tok: str, path: str, method: str = "GET", body: dict | None = None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f"{API}{path}",
        data=data,
        method=method,
        headers={"Authorization": tok, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        sys.exit(f"ClickUp {method} {path} → HTTP {e.code}: {detail}")


def current_sprint(tok: str, folder: str) -> dict:
    """Sprint lists are named like 'Sprint {2} (9/14 - 9/27)' — M/D, no year."""
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


def resolve_dest(tok: str, creds: dict, dest: str) -> dict:
    if dest == "sprint":
        lst = current_sprint(tok, creds["sprint_folder"])
        return {"dest": "sprint", "id": lst["id"], "name": lst["name"], "assign_me": True}
    lst = api(tok, f"/list/{creds['triage_list']}")
    return {"dest": "triage", "id": lst["id"], "name": lst["name"], "assign_me": False}


def list_fields(tok: str, list_id: str) -> dict:
    """Map our keys → {id, type, required, options: {name: id}} from the list's custom fields."""
    fields = api(tok, f"/list/{list_id}/field")["fields"]
    out = {}
    for key, name in FIELD_NAMES.items():
        matches = [f for f in fields if f["name"].strip().lower() == name.lower()]
        if not matches:
            continue
        pref = PREFERRED_FIELD_IDS.get(key)
        f = next((m for m in matches if m["id"] == pref), matches[0])
        options = {
            (o.get("name") or o.get("label") or "").strip(): o["id"]
            for o in (f.get("type_config") or {}).get("options") or []
        }
        out[key] = {
            "id": f["id"],
            "name": f["name"],
            "type": f["type"],
            "required": bool(f.get("required")),
            "options": options,
        }
    return out


def match_option(options: dict, wanted: str, field_name: str) -> tuple[str, str]:
    """Return (option_name, option_id). Exact match, else case-insensitive, else unique substring — or fail loudly."""
    if wanted in options:
        return wanted, options[wanted]
    lower = {k.lower(): k for k in options}
    if wanted.lower() in lower:
        name = lower[wanted.lower()]
        return name, options[name]
    subs = [k for k in options if wanted.lower() in k.lower()]
    if len(subs) == 1:
        return subs[0], options[subs[0]]
    sys.exit(
        f"{field_name}: no option matches {wanted!r}"
        + (f" (ambiguous: {subs})" if subs else "")
        + f". Choose from: {sorted(options)}"
    )


# ---------------------------------------------------------------- task file

def parse_task_file(path: Path) -> tuple[str, str]:
    text = path.read_text(encoding="utf-8")
    m = re.search(r"^#\s+(.+?)\s*$", text, re.M)
    if not m:
        sys.exit(f"{path}: no '# Title' H1 found")
    title = m.group(1).strip()
    body = (text[: m.start()] + text[m.end():]).strip() + "\n"
    return title, body


# ---------------------------------------------------------------- commands

def cmd_options(args) -> int:
    creds = credentials()
    tok = creds["token"]
    dest = resolve_dest(tok, creds, args.dest)
    fields = list_fields(tok, dest["id"])
    payload = {
        "list": dest,
        "me": creds["user_id"],
        "fields": {
            k: {"name": v["name"], "type": v["type"], "required": v["required"], "options": sorted(v["options"])}
            for k, v in fields.items()
        },
    }
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


def cmd_create(args) -> int:
    creds = credentials()
    tok = creds["token"]
    path = Path(args.file).expanduser()
    if not path.is_file():
        sys.exit(f"no such file: {path}")
    title, body = parse_task_file(path)

    dest = resolve_dest(tok, creds, args.dest)
    fields = list_fields(tok, dest["id"])

    custom_fields = []
    resolved: dict = {}  # what each name matched, so a loose match is visible
    missing_required = []

    fow = fields.get("field_of_work")
    if fow:
        if args.field_of_work:
            pairs = [match_option(fow["options"], w, fow["name"]) for w in args.field_of_work]
            resolved[fow["name"]] = [n for n, _ in pairs]
            custom_fields.append({"id": fow["id"], "value": [i for _, i in pairs]})
        elif fow["required"]:
            missing_required.append(fow["name"])

    proj = fields.get("project")
    if proj and args.project:
        name, oid = match_option(proj["options"], args.project, proj["name"])
        resolved[proj["name"]] = name
        custom_fields.append({"id": proj["id"], "value": oid})

    mos = fields.get("moscow")
    if mos and args.moscow:
        name, oid = match_option(mos["options"], args.moscow, mos["name"])
        resolved[mos["name"]] = name
        custom_fields.append({"id": mos["id"], "value": oid})

    dod = fields.get("dod")
    if dod:
        if args.dod:
            resolved[dod["name"]] = args.dod.strip()
            custom_fields.append({"id": dod["id"], "value": args.dod.strip()})
        elif dod["required"]:
            missing_required.append(dod["name"])

    if missing_required:
        sys.exit("required in ClickUp but not given: " + ", ".join(missing_required))

    payload: dict = {
        "name": title,
        "markdown_content": body,
        "custom_fields": custom_fields,
    }
    if args.points is not None:
        payload["points"] = args.points
    if dest["assign_me"]:
        payload["assignees"] = [int(creds["user_id"])]

    if args.dry_run:
        json.dump({"list": dest, "resolved": resolved, "payload": payload}, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    task = api(tok, f"/list/{dest['id']}/task", "POST", payload)
    if not task.get("custom_id"):
        # GLOBAL-nnnnn is assigned a beat after creation; one re-read picks it up.
        task = api(tok, f"/task/{task['id']}") or task
    result = {
        "id": task["id"],
        "custom_id": task.get("custom_id"),
        "url": task["url"],
        "name": task["name"],
        "status": (task.get("status") or {}).get("status"),
        "points": task.get("points"),
        "assignees": [a["username"] for a in task.get("assignees", [])],
        "resolved": resolved,
        "list": dest,
    }
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


def cmd_delete(args) -> int:
    creds = credentials()
    api(creds["token"], f"/task/{args.task_id}", "DELETE")
    print(json.dumps({"deleted": args.task_id}))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("options", help="destination list + field options as JSON")
    p.add_argument("--dest", choices=["sprint", "triage"], default="sprint")

    p = sub.add_parser("create", help="create the task from a TASK-*.md file")
    p.add_argument("--file", required=True)
    p.add_argument("--dest", choices=["sprint", "triage"], required=True)
    p.add_argument("--points", type=int)
    p.add_argument("--moscow")
    p.add_argument("--project")
    p.add_argument("--field-of-work", action="append", default=[])
    p.add_argument("--dod")
    p.add_argument("--dry-run", action="store_true")

    p = sub.add_parser("delete", help="delete a task by id")
    p.add_argument("task_id")

    args = parser.parse_args()
    return {"options": cmd_options, "create": cmd_create, "delete": cmd_delete}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
