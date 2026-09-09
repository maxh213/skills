#!/usr/bin/env python3
"""Probe, read, and write workstation credentials. Never prints secret values
unless the caller asked for `get`/`export` (those are for other scripts, not chat).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import stat
import subprocess
import sys
import tomllib
import urllib.error
import urllib.request
from pathlib import Path

from paths import catalog_path, config_path

SECRET_KINDS = {"secret"}


def load_catalog() -> list[dict]:
    data = tomllib.loads(catalog_path().read_text())
    return list(data.get("item") or [])


def nested_get(d: dict, dotted: str):
    cur = d
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def load_config() -> dict:
    p = config_path()
    if not p.is_file():
        return {}
    with p.open("rb") as f:
        return tomllib.load(f)


def toml_escape(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def set_config_value(dotted: str, value: str) -> Path:
    """Insert or replace dotted.key in the TOML file, preserving comments."""
    p = config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    text = p.read_text() if p.is_file() else ""
    parts = dotted.split(".")
    if len(parts) < 2:
        raise SystemExit(f"config key must be section.key, got {dotted!r}")
    section = ".".join(parts[:-1])
    key = parts[-1]
    header = f"[{section}]"
    assign = re.compile(rf"^(\s*{re.escape(key)}\s*=\s*).+$", re.M)
    line = f"{key} = {toml_escape(value)}"

    if header in text:
        # Replace existing assignment inside that section if present.
        start = text.index(header)
        nxt = re.search(r"\n\[", text[start + len(header) :])
        end = start + len(header) + nxt.start() if nxt else len(text)
        block = text[start:end]
        if assign.search(block):
            block = assign.sub(rf"\1{toml_escape(value)}", block, count=1)
        else:
            if not block.endswith("\n"):
                block += "\n"
            block = block.rstrip("\n") + "\n" + line + "\n"
            if nxt:
                block += "\n"
        text = text[:start] + block + text[end:]
    else:
        if text and not text.endswith("\n"):
            text += "\n"
        text += f"\n{header}\n{line}\n"

    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(text)
    os.chmod(tmp, stat.S_IRUSR | stat.S_IWUSR)
    tmp.replace(p)
    os.chmod(p, stat.S_IRUSR | stat.S_IWUSR)
    return p


def env_value(item: dict) -> str | None:
    for name in item.get("env") or []:
        v = os.environ.get(name)
        if v:
            return v
    return None


def resolve_item(item: dict, cfg: dict) -> tuple[str | None, str | None]:
    """Return (value, source) where source is env|config|default."""
    v = env_value(item)
    if v:
        return v, "env"
    ck = item.get("config_key")
    if ck:
        got = nested_get(cfg, ck)
        if got is not None and str(got) != "":
            return str(got), "config"
    default = item.get("default")
    if default is not None and str(default) != "":
        return str(default), "default"
    return None, None


def _http_json(url: str, headers: dict) -> tuple[int, dict | None]:
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = json.loads(resp.read().decode())
            return resp.status, body
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception:
        return 0, None


def verify(item: dict, value: str | None) -> dict:
    kind = item.get("verify")
    if not kind:
        return {"ok": bool(value), "identity": None}
    if kind == "clickup":
        if not value:
            return {"ok": False, "identity": None}
        code, body = _http_json(
            "https://api.clickup.com/api/v2/user",
            {"Authorization": value},
        )
        user = (body or {}).get("user") or {}
        ident = user.get("username") or user.get("email")
        uid = user.get("id")
        if uid is not None:
            ident = f"{ident} ({uid})" if ident else str(uid)
        return {"ok": code == 200 and bool(user), "identity": ident}
    if kind == "clickup_user":
        return {"ok": bool(value) and str(value).isdigit(), "identity": value}
    if kind == "slack":
        if not value:
            return {"ok": False, "identity": None}
        code, body = _http_json(
            "https://slack.com/api/auth.test",
            {"Authorization": f"Bearer {value}"},
        )
        ok = bool(body and body.get("ok"))
        ident = (body or {}).get("user")
        return {"ok": ok, "identity": ident}
    if kind == "github":
        # CLI auth counts even without a stored token.
        try:
            r = subprocess.run(
                ["gh", "auth", "status"],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if r.returncode == 0:
                return {"ok": True, "identity": "gh"}
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        if not value:
            return {"ok": False, "identity": None}
        code, body = _http_json(
            "https://api.github.com/user",
            {
                "Authorization": f"Bearer {value}",
                "User-Agent": "prompt-manager-setup",
                "Accept": "application/vnd.github+json",
            },
        )
        return {"ok": code == 200, "identity": (body or {}).get("login")}
    if kind == "gcloud":
        try:
            r = subprocess.run(
                ["gcloud", "auth", "list", "--format=json"],
                capture_output=True,
                text=True,
                timeout=20,
            )
            if r.returncode == 0 and r.stdout.strip():
                accts = json.loads(r.stdout)
                active = [a.get("account") for a in accts if a.get("status") == "ACTIVE"]
                return {"ok": bool(accts), "identity": (active[0] if active else None)}
        except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
            pass
        return {"ok": False, "identity": None}
    if kind == "railway":
        return {"ok": bool(value), "identity": "token-present" if value else None}
    return {"ok": bool(value), "identity": None}


def github_cli_ok() -> bool:
    try:
        r = subprocess.run(["gh", "auth", "status"], capture_output=True, timeout=15)
        return r.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def status_payload() -> dict:
    cfg = load_config()
    p = config_path()
    mode = None
    if p.is_file():
        mode = oct(p.stat().st_mode & 0o777)
    items = {}
    missing_required = []
    for item in load_catalog():
        value, source = resolve_item(item, cfg)
        # github is satisfied by gh auth even with no stored token
        if item["key"] == "github.token" and not value and github_cli_ok():
            source = "gh"
            present = True
            vrf = {"ok": True, "identity": "gh"}
        else:
            present = value is not None
            vrf = verify(item, value) if present or item.get("verify") == "gcloud" else {
                "ok": False,
                "identity": None,
            }
            if item.get("verify") == "gcloud":
                present = vrf["ok"]
                source = source or ("cli" if present else None)
        rec = {
            "present": present,
            "source": source,
            "kind": item.get("kind"),
            "required": bool(item.get("required")),
            "description": item.get("description"),
            "memory_queries": item.get("memory_queries") or [],
            "env": item.get("env") or [],
            "verified": vrf["ok"] if present else False,
            "identity": vrf["identity"] if present else None,
        }
        items[item["key"]] = rec
        if rec["required"] and not rec["present"]:
            missing_required.append(item["key"])
    tok = items.get("clickup.token") or {}
    uid = items.get("clickup.user_id")
    if uid is not None and not uid.get("present") and tok.get("identity"):
        m = re.search(r"\((\d+)\)\s*$", str(tok["identity"]))
        if m:
            uid["derived"] = m.group(1)
    return {
        "config_path": str(p),
        "config_exists": p.is_file(),
        "config_mode": mode,
        "items": items,
        "missing_required": missing_required,
        "ready": not missing_required,
    }


def get_value(key: str) -> str:
    cfg = load_config()
    for item in load_catalog():
        if item["key"] == key:
            value, _ = resolve_item(item, cfg)
            if value is None:
                raise SystemExit(f"missing {key} — run setup-prompt-manager")
            return value
    # allow raw dotted config reads for keys not in the catalog
    got = nested_get(cfg, key)
    if got is None or str(got) == "":
        raise SystemExit(f"missing {key} — run setup-prompt-manager")
    return str(got)


def cmd_status(_args) -> int:
    json.dump(status_payload(), sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


def cmd_get(args) -> int:
    sys.stdout.write(get_value(args.key))
    if sys.stdout.isatty():
        sys.stdout.write("\n")
    return 0


def cmd_export(args) -> int:
    mapping = {
        "clickup.token": "CU_TOKEN",
        "clickup.user_id": "CLICKUP_USER_ID",
        "clickup.team_id": "CLICKUP_TEAM_ID",
        "clickup.sprint_folder": "CLICKUP_SPRINT_FOLDER",
        "slack.token": "SLACK_TOKEN",
        "github.token": "GITHUB_TOKEN",
        "github.org": "GITHUB_ORG",
        "gcp.project": "GCP_PROJECT",
        "railway.token": "RAILWAY_TOKEN",
    }
    keys = args.keys or list(mapping)
    for key in keys:
        env_name = mapping.get(key)
        if not env_name:
            raise SystemExit(f"no export mapping for {key}")
        try:
            val = get_value(key)
        except SystemExit:
            continue
        sys.stdout.write(f"export {env_name}={shlex.quote(val)}\n")
    return 0


def cmd_set(args) -> int:
    if args.from_file:
        value = Path(args.from_file).read_text().strip()
    else:
        value = sys.stdin.read().strip()
    if not value:
        raise SystemExit("empty value")
    catalog = {i["key"]: i for i in load_catalog()}
    item = catalog.get(args.key)
    dest = (item or {}).get("config_key") or args.key
    path = set_config_value(dest, value)
    rec = {"ok": True, "key": args.key, "config_path": str(path), "mode": "0600"}
    if item:
        vrf = verify(item, value)
        rec["verified"] = vrf["ok"]
        rec["identity"] = vrf["identity"]
    json.dump(rec, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


def cmd_catalog(_args) -> int:
    json.dump(load_catalog(), sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


def cmd_plugin_root(_args) -> int:
    from paths import plugin_root

    sys.stdout.write(str(plugin_root()) + "\n")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status", help="JSON probe of every catalog item (no secret values)")
    p_get = sub.add_parser("get", help="print one value (for scripts, not chat)")
    p_get.add_argument("key")
    p_ex = sub.add_parser("export", help="print shell export lines")
    p_ex.add_argument("keys", nargs="*")
    p_set = sub.add_parser("set", help="write a value from stdin or --from-file into 0600 config")
    p_set.add_argument("key")
    p_set.add_argument("--from-file")
    sub.add_parser("catalog", help="print the credential catalog")
    sub.add_parser("plugin-root", help="print the plugin root")

    args = parser.parse_args()
    return {
        "status": cmd_status,
        "get": cmd_get,
        "export": cmd_export,
        "set": cmd_set,
        "catalog": cmd_catalog,
        "plugin-root": cmd_plugin_root,
    }[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
