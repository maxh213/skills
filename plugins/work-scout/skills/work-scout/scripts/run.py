#!/usr/bin/env python3
"""work-scout driver: hand a Slack/ClickUp research question to a cheap model, twice.

Pass 1 answers the brief. Pass 2 continues the same session with an unspecific critique
("you missed things; re-verify every citation") which forces re-derivation. Only a one-line
summary is printed; the report lands in a file so the calling agent's context stays clean.

Backends (chosen by the scout plugin's route.py unless --backend is given):
  mercury    kilo run, Mercury 2.5             (session continued with -s)
  kimi27     kimi -p, K2.7 highspeed           (session continued with -c in the run dir)
  haiku-max  claude -p, Haiku 4.5 at max effort (session continued with --resume)
"""
import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "wscout.py")
TEMPLATE = os.path.join(HERE, "brief-template.md")
RUNS = os.path.expanduser("~/.cache/work-scout/runs")
PASS_TIMEOUT = 1200

CRITIQUE = """Your report is incomplete — it missed things. Do a second, skeptical pass before finalizing:
(1) re-run the helper commands behind every citation and fix any task id, status, assignee, author, time or permalink that is wrong;
(2) actively hunt for what you missed: other channels and DMs where the same people talked in the period, thread replies, ClickUp comments, tasks created, moved into the sprint, reassigned or updated in the period without being mentioned in Slack, and anything the question implies that you did not check;
(3) drop or correct every claim not backed by tool output you saw.
Then output the complete corrected report in the same structure. Read-only: change nothing anywhere."""


def route():
    patterns = [
        os.path.join(HERE, "../../../../scout/skills/scout/route.py"),          # sibling plugin in the skills repo
        os.path.join(HERE, "../../../../../scout/*/skills/scout/route.py"),     # sibling plugin in the plugin cache
        os.path.expanduser("~/.claude/plugins/cache/*/scout/*/skills/scout/route.py"),
        os.path.expanduser("~/.claude/skills/scout/route.py"),
    ]
    cands = sorted({os.path.realpath(p) for pat in patterns for p in glob.glob(pat)})
    if not cands:
        return "native", ["route.py not found (scout plugin not installed)"]
    try:
        out = subprocess.run([sys.executable, cands[-1]], capture_output=True, text=True, timeout=300).stdout
    except subprocess.TimeoutExpired:
        return "native", ["route.py timed out"]
    m = re.search(r"DECISION=(\S+)(.*)", out)
    evidence = [l.strip() for l in out.splitlines() if l.strip() and "DECISION=" not in l]
    if m and m.group(2).strip():
        evidence.append(m.group(2).strip().lstrip("# "))
    return (m.group(1) if m else "native"), evidence


def render_brief(question, context):
    with open(TEMPLATE) as fh:
        tpl = fh.read()
    now = datetime.now().astimezone()
    subs = {"question": question.strip(), "context": (context or "(none)").strip(),
            "today": now.strftime("%Y-%m-%d"), "weekday": now.strftime("%A"),
            "tz": now.tzname() or "local", "tool": TOOL}
    for k, v in subs.items():
        tpl = tpl.replace("{{" + k + "}}", v)
    return tpl


def need(binary):
    if not shutil.which(binary):
        raise RuntimeError(f"{binary} is not installed")


def kilo_balance():
    try:
        out = subprocess.run(["kilo", "profile"], capture_output=True, text=True, timeout=30).stdout
        m = re.search(r"Balance:\s*\$([0-9]+(?:\.[0-9]+)?)", out)
        return float(m.group(1)) if m else None
    except Exception:
        return None


def run_mercury(brief, workdir, log, single):
    need("kilo")
    before = kilo_balance()

    def cost():
        after = kilo_balance()
        return round(before - after, 4) if before is not None and after is not None else None

    def kilo(extra):
        r = subprocess.run(["kilo", "run", "-m", "kilo/inception/mercury-2.5", "--variant", "high",
                            "--auto", "--dir", workdir, "--format", "json", *extra],
                           capture_output=True, text=True, timeout=PASS_TIMEOUT, cwd=workdir)
        log.write(r.stderr)
        sid, texts = None, []
        for line in r.stdout.splitlines():
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            sid = sid or ev.get("sessionID")
            if ev.get("type") == "text":
                texts.append((ev.get("part") or {}).get("text", ""))
        return sid, (texts[-1] if texts else "")

    sid, p1 = kilo([brief])
    if not p1:
        raise RuntimeError("pass 1 produced no text (see stderr.log)")
    if single or not sid:
        return p1, None, cost()
    _, p2 = kilo(["-s", sid, CRITIQUE])
    return p1, p2, cost()


def run_kimi(brief, workdir, log, single):
    need("kimi")

    def kimi(prompt, cont):
        cmd = ["kimi", "-p", prompt, "-m", "kimi-code/kimi-for-coding-highspeed"] + (["-c"] if cont else [])
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=PASS_TIMEOUT, cwd=workdir)
        log.write(r.stderr)
        return "\n".join(re.sub(r"^• ?", "", l) for l in r.stdout.splitlines()).strip()

    p1 = kimi(brief, False)
    if not p1:
        raise RuntimeError("pass 1 produced no text (see stderr.log)")
    if single:
        return p1, None, None
    return p1, kimi(CRITIQUE, True), None


def run_haiku(brief, workdir, log, single):
    need("claude")
    env = {k: v for k, v in os.environ.items() if not k.startswith("CLAUDECODE") and k != "CLAUDE_CODE_ENTRYPOINT"}

    def claude(prompt, resume):
        cmd = ["claude", "-p", prompt, "--model", "haiku", "--effort", "max",
               "--dangerously-skip-permissions", "--output-format", "json"] + (["--resume", resume] if resume else [])
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=PASS_TIMEOUT, cwd=workdir, env=env)
        log.write(r.stderr)
        try:
            d = json.loads(r.stdout)
        except ValueError:
            raise RuntimeError("claude output was not JSON: " + (r.stdout or r.stderr)[:300])
        return d.get("result", ""), d.get("session_id"), float(d.get("total_cost_usd") or 0)

    p1, sid, c1 = claude(brief, None)
    if not p1:
        raise RuntimeError("pass 1 produced no text (see stderr.log)")
    if single or not sid:
        return p1, None, c1
    p2, _, c2 = claude(CRITIQUE, sid)
    return p1, p2, c1 + c2


RUNNERS = {"mercury": run_mercury, "kimi27": run_kimi, "haiku-max": run_haiku}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--question", help="the one question to answer (renders the bundled brief template)")
    ap.add_argument("--context", default="", help="extra hints: channels, people, time range, what to check")
    ap.add_argument("--brief", help="use this brief file verbatim instead of --question/--context")
    ap.add_argument("--backend", default="auto", choices=["auto", "mercury", "kimi27", "haiku-max"])
    ap.add_argument("--single-pass", action="store_true", help="skip the skeptical second pass (orientation only)")
    ap.add_argument("--name", help="slug appended to the run directory name")
    a = ap.parse_args()

    if a.brief:
        with open(a.brief) as fh:
            brief = fh.read()
    elif a.question:
        brief = render_brief(a.question, a.context)
    else:
        ap.error("--question or --brief is required")

    backend, evidence = (a.backend, []) if a.backend != "auto" else route()
    run_id = datetime.now().strftime("%Y%m%d-%H%M%S") + (f"-{a.name}" if a.name else "")
    workdir = os.path.join(RUNS, run_id)
    os.makedirs(workdir)
    with open(os.path.join(workdir, "brief.md"), "w") as fh:
        fh.write(brief)
    with open(os.path.join(workdir, "README.md"), "w") as fh:
        fh.write("Scratch directory for one work-scout run. Nothing here belongs to any project.\n")

    if backend == "native":
        print(f"BACKEND=native RUN={workdir}")
        for e in evidence:
            print("  " + e)
        print(f"No cheap backend available: run the lookups yourself with {TOOL} (brief at {workdir}/brief.md).")
        return

    t0 = time.time()
    with open(os.path.join(workdir, "stderr.log"), "w") as log:
        try:
            p1, p2, cost = RUNNERS[backend](brief, workdir, log, a.single_pass)
        except Exception as e:
            print(f"BACKEND={backend} FAILED after {time.time() - t0:.0f}s: {e}")
            print(f"  log: {workdir}/stderr.log — retry with --backend <other> (see route evidence below)")
            for ev in evidence:
                print("  " + ev)
            sys.exit(1)
    elapsed = time.time() - t0
    with open(os.path.join(workdir, "pass1.md"), "w") as fh:
        fh.write(p1)
    final = p2 if p2 else p1
    with open(os.path.join(workdir, "report.md"), "w") as fh:
        fh.write(final)
    with open(os.path.join(workdir, "meta.json"), "w") as fh:
        json.dump({"backend": backend, "seconds": round(elapsed), "cost_usd": cost, "passes": 1 if p2 is None else 2,
                   "evidence": evidence, "started": run_id}, fh, indent=1)
    cost_s = f"${cost:.3f}" if cost is not None else "n/a"
    print(f"BACKEND={backend} PASSES={1 if p2 is None else 2} TIME={elapsed:.0f}s COST={cost_s} "
          f"WORDS={len(final.split())}")
    print(f"REPORT={workdir}/report.md")
    print(f"PASS1={workdir}/pass1.md")
    for ev in evidence:
        print("  " + ev)


if __name__ == "__main__":
    main()
