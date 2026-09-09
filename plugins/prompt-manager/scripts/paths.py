"""Locate the prompt-manager plugin root and the workstation config file."""

from __future__ import annotations

import os
from pathlib import Path


def plugin_root() -> Path:
    for env in ("GROK_PLUGIN_ROOT", "CLAUDE_PLUGIN_ROOT"):
        raw = os.environ.get(env)
        if raw:
            p = Path(raw).expanduser().resolve()
            if p.is_dir():
                return p
    here = Path(__file__).resolve().parent
    if here.name == "scripts":
        cand = here.parent
        if (cand / "plugin.json").exists() or (cand / ".claude-plugin" / "plugin.json").exists():
            return cand
        # skills/<name>/scripts/this.py → plugin root is parents[2]
        if len(here.parents) >= 2:
            cand = here.parents[2]
            if (cand / "plugin.json").exists() or (cand / ".claude-plugin" / "plugin.json").exists():
                return cand
    raise FileNotFoundError(
        "Cannot locate the prompt-manager plugin root. "
        "Set GROK_PLUGIN_ROOT or CLAUDE_PLUGIN_ROOT, or run from the installed plugin."
    )


def catalog_path() -> Path:
    return plugin_root() / "references" / "credentials.toml"


def isolation_path() -> Path:
    return plugin_root() / "references" / "isolation.md"


def config_path() -> Path:
    raw = os.environ.get("WORKSTATION_CONFIG")
    if raw:
        return Path(raw).expanduser()
    return Path.home() / ".config" / "workstation" / "config.toml"
