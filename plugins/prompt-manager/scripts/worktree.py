#!/usr/bin/env python3
"""Idempotent git worktree claim for prompt-manager runs."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import socket
import subprocess
import sys
import time
from pathlib import Path


def run(cmd: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, check=check, capture_output=True, text=True)


def slugify(raw: str) -> str:
    s = raw.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return (s[:48].strip("-") or "run")


def git_toplevel(repo: Path) -> Path:
    raw = run(["git", "rev-parse", "--show-toplevel"], cwd=repo).stdout.strip()
    return Path(raw).resolve()


def git_common_dir(repo: Path) -> Path:
    raw = Path(run(["git", "rev-parse", "--git-common-dir"], cwd=repo).stdout.strip())
    if raw.is_absolute():
        return raw.resolve()
    return (repo / raw).resolve()


def claim_dir(repo: Path) -> Path:
    d = git_common_dir(repo) / "prompt-manager"
    d.mkdir(parents=True, exist_ok=True)
    return d


def claim_path(repo: Path, slug: str) -> Path:
    return claim_dir(repo) / f"{slug}.json"


def load_claim(repo: Path, slug: str) -> dict | None:
    p = claim_path(repo, slug)
    if not p.is_file():
        return None
    return json.loads(p.read_text())


def save_claim(repo: Path, data: dict) -> Path:
    p = claim_path(repo, data["slug"])
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n")
    tmp.replace(p)
    return p


def worktree_list(repo: Path) -> list[dict]:
    out = run(["git", "worktree", "list", "--porcelain"], cwd=repo).stdout
    rows = []
    cur: dict = {}
    for line in out.splitlines():
        if line.startswith("worktree "):
            if cur:
                rows.append(cur)
            cur = {"worktree": line.split(" ", 1)[1]}
        elif line.startswith("branch "):
            ref = line.split(" ", 1)[1]
            cur["branch"] = ref.removeprefix("refs/heads/")
        elif line.startswith("HEAD "):
            cur["head"] = line.split(" ", 1)[1]
        elif line == "detached":
            cur["detached"] = True
    if cur:
        rows.append(cur)
    return rows


def find_worktree(repo: Path, *, path: Path | None = None, branch: str | None = None) -> dict | None:
    for row in worktree_list(repo):
        if path and Path(row["worktree"]).resolve() == path.resolve():
            return row
        if branch and row.get("branch") == branch:
            return row
    return None


def dump(data: dict, ok: bool) -> int:
    json.dump(data, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0 if ok else 1


def cmd_slug(args) -> int:
    print(slugify(args.from_text))
    return 0


def _new_claim(slug: str, branch: str, worktree: Path) -> dict:
    return {
        "slug": slug,
        "branch": branch,
        "worktree": str(worktree),
        "prompt_file": f"PROMPT-{slug}.md",
        "progress_file": f"PROGRESS-{slug}.md",
        "pid": os.getpid(),
        "hostname": socket.gethostname(),
        "claimed_at": time.time(),
        "status": "claimed",
    }


def cmd_claim(args) -> int:
    repo = git_toplevel(Path(args.repo).resolve())
    slug = slugify(args.slug)
    branch = args.branch or f"feat/{slug}"
    dest = Path(args.path) if args.path else repo.parent / f"{repo.name}-{slug}"
    lock_path = claim_dir(repo) / f"{slug}.lock"
    with lock_path.open("a+") as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        return _claim_locked(repo, slug, branch, dest, args.base)


def _claim_locked(repo: Path, slug: str, branch: str, dest: Path, base: str | None) -> int:
    existing = load_claim(repo, slug)
    listed = find_worktree(repo, branch=branch) or find_worktree(repo, path=dest)

    if listed:
        dest = Path(listed["worktree"])
        data = _new_claim(slug, listed.get("branch") or branch, dest)
        if existing:
            data["previous_status"] = existing.get("status")
        data["action"] = "reused"
        data["ok"] = True
        path = save_claim(repo, data)
        data["claim"] = str(path)
        return dump(data, True)

    if dest.exists() and not (dest / ".git").exists() and any(dest.iterdir()):
        return dump(
            {
                "ok": False,
                "action": "blocked",
                "slug": slug,
                "worktree": str(dest),
                "error": "destination exists, is not a git worktree, and is not empty",
            },
            False,
        )

    heads = run(
        ["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"],
        cwd=repo,
        check=False,
    )
    if heads.returncode == 0:
        run(["git", "worktree", "add", str(dest), branch], cwd=repo)
        action = "recreated"
    else:
        run(["git", "worktree", "add", "-b", branch, str(dest), base or "HEAD"], cwd=repo)
        action = "created"

    data = _new_claim(slug, branch, dest)
    data["action"] = action
    data["ok"] = True
    path = save_claim(repo, data)
    data["claim"] = str(path)
    return dump(data, True)


def cmd_status(args) -> int:
    repo = git_toplevel(Path(args.repo).resolve())
    slug = slugify(args.slug)
    data = load_claim(repo, slug) or {}
    data["ok"] = bool(data)
    data["slug"] = slug
    data["claim"] = str(claim_path(repo, slug))
    if data.get("worktree"):
        data["worktree_present"] = Path(data["worktree"]).is_dir()
        data["worktree_listed"] = bool(find_worktree(repo, path=Path(data["worktree"])))
    return dump(data, data["ok"])


def cmd_done(args) -> int:
    repo = git_toplevel(Path(args.repo).resolve())
    slug = slugify(args.slug)
    data = load_claim(repo, slug)
    if not data:
        return dump({"ok": False, "error": "no claim", "slug": slug}, False)
    data["status"] = "done"
    data["pid"] = None
    path = save_claim(repo, data)
    data["ok"] = True
    data["claim"] = str(path)
    data["action"] = "done"
    return dump(data, True)


def cmd_list(args) -> int:
    repo = git_toplevel(Path(args.repo).resolve())
    rows = []
    for p in sorted(claim_dir(repo).glob("*.json")):
        try:
            rows.append(json.loads(p.read_text()))
        except json.JSONDecodeError:
            continue
    return dump({"ok": True, "repo": str(repo), "claims": rows}, True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_slug = sub.add_parser("slug")
    p_slug.add_argument("--from", dest="from_text", required=True)

    p_claim = sub.add_parser("claim")
    p_claim.add_argument("--slug", required=True)
    p_claim.add_argument("--repo", default=".")
    p_claim.add_argument("--branch")
    p_claim.add_argument("--path")
    p_claim.add_argument("--base")

    p_status = sub.add_parser("status")
    p_status.add_argument("--slug", required=True)
    p_status.add_argument("--repo", default=".")

    p_done = sub.add_parser("done")
    p_done.add_argument("--slug", required=True)
    p_done.add_argument("--repo", default=".")

    p_list = sub.add_parser("list")
    p_list.add_argument("--repo", default=".")

    args = parser.parse_args()
    return {
        "slug": cmd_slug,
        "claim": cmd_claim,
        "status": cmd_status,
        "done": cmd_done,
        "list": cmd_list,
    }[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
