#!/usr/bin/env python3
"""Scout router: pick a codebase-exploration backend by CLI availability and
subscription quota headroom, measured live.

Decision logic (see SKILL.md next to this file):
  1. EVAPORATION PRIORITY: a fixed quota window (weekly) resetting within
     RESET_SOON_HOURS with >= MIN_REMAINING_PCT still unused is use-it-or-lose-it
     quota — burn that backend first, ahead of everything else. Rolling short
     windows (5h rate limiters) don't evaporate, so they don't trigger this.
  2. kilo/Mercury next whenever installed and balance > KILO_MIN_BALANCE — but
     only when PREFER_KILO is True (set it False if you have no kilo plan to
     burn; kilo then becomes a last-resort fallback before "native").
  3. Otherwise pick whichever of kimi vs claude has MORE headroom, where each
     backend's utilization is the WORST of its windows (weekly, short window)
     — i.e. its binding constraint. Tie within TIE_POINTS -> claude's haiku
     (deeper scout in benchmarking; self-corrects via the window checks).

Prints evidence lines, then a final `DECISION=<backend>` line.
Backends: mercury | kimi27 | haiku-max | native (nothing else available).
Always exits 0.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from datetime import datetime, timezone

# --- configuration -----------------------------------------------------------
PREFER_KILO = True        # kilo wins by default when solvent (burn the prepaid balance)
KILO_MIN_BALANCE = 1.0    # dollars
TIE_POINTS = 10           # headroom tie margin between kimi and claude
RESET_SOON_HOURS = 24     # a fixed window resetting within this horizon is "about to evaporate"
MIN_REMAINING_PCT = 20    # ...and only worth prioritizing if at least this much is left
KIMI_WEB_PORT = 59177     # port for the throwaway `kimi web` used to read usage
# ------------------------------------------------------------------------------


def sh(cmd, timeout=45):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return (r.stdout or "") + (r.stderr or "")
    except Exception:
        return ""


def hours_until(dt):
    return (dt - datetime.now(timezone.utc)).total_seconds() / 3600


def probe_kilo():
    if not shutil.which("kilo"):
        return None
    m = re.search(r"Balance:\s*\$([0-9]+(?:\.[0-9]+)?)", sh("kilo profile", 30))
    if not m:
        return {"installed": True, "ok": False, "note": "balance unreadable"}
    bal = float(m.group(1))
    return {"installed": True, "ok": bal > KILO_MIN_BALANCE, "balance": bal,
            "note": f"kilo balance ${bal:.2f}"}


def probe_kimi():
    if not shutil.which("kimi"):
        return None
    log = os.path.join(tempfile.gettempdir(), "scout-kimiweb.log")
    proc = None
    try:
        with open(log, "w") as fh:
            proc = subprocess.Popen(["kimi", "web", "--no-open", "--port", str(KIMI_WEB_PORT)],
                                    stdout=fh, stderr=subprocess.STDOUT)
        token = None
        for _ in range(40):
            time.sleep(0.5)
            try:
                text = open(log).read()
            except OSError:
                continue
            m = re.search(r"token=([A-Za-z0-9._-]+)", text) or re.search(r"Bearer ([A-Za-z0-9._-]+)", text)
            if m:
                token = m.group(1)
                break
            if proc.poll() is not None:
                break
        if not token:
            return {"installed": True, "ok": False, "note": "kimi web token not found"}
        req = urllib.request.Request(
            f"http://127.0.0.1:{KIMI_WEB_PORT}/api/v1/oauth/usage",
            headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.load(resp)["data"]
        weekly = data["summary"]["used"] / data["summary"]["limit"] * 100
        reset_h = None
        if data["summary"].get("reset_at"):
            reset_h = hours_until(datetime.fromisoformat(
                data["summary"]["reset_at"].replace("Z", "+00:00")))
        short = None
        for lim in data.get("limits", []):
            if lim["window"]["unit"] == "hour":
                short = lim["used"] / lim["limit"] * 100
        binding = max(weekly, short or 0)
        note = f"kimi weekly {weekly:.0f}% used"
        if reset_h is not None:
            note += f" (resets in {reset_h:.0f}h)"
        if short is not None:
            note += f", 5h {short:.0f}% used"
        return {"installed": True, "ok": True, "weekly": round(weekly),
                "weekly_remaining": round(100 - weekly), "weekly_reset_h": reset_h,
                "short": round(short or 0), "binding": round(binding), "note": note}
    except Exception as e:
        return {"installed": True, "ok": False, "note": f"kimi probe failed: {e}"}
    finally:
        if proc:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except Exception:
                proc.kill()


def parse_claude_reset(text):
    # "resets Sep 13, 11pm (Europe/London)" -> hours from now, or None
    m = re.search(r"resets (\w{3} \d{1,2}), (\d{1,2})(?::(\d{2}))?\s*(am|pm)(?: \(([^)]+)\))?", text)
    if not m:
        return None
    month = datetime.strptime(m.group(1).split()[0], "%b").month
    day = int(m.group(1).split()[1])
    hour = int(m.group(2)) % 12 + (12 if m.group(4) == "pm" else 0)
    minute = int(m.group(3) or 0)
    now = datetime.now(timezone.utc)
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo(m.group(5)) if m.group(5) else timezone.utc
    except Exception:
        tz = timezone.utc
    dt = datetime(now.year, month, day, hour, minute, tzinfo=tz)
    if (dt - now).total_seconds() < -2 * 86400:
        dt = dt.replace(year=now.year + 1)
    return hours_until(dt)


def probe_claude():
    if not shutil.which("claude"):
        return None
    out = sh('claude -p "/usage"', 90)
    week = re.search(r"Current week \(all models\):[^\n]*", out)
    sess = re.search(r"Current session:\s*(\d+)% used", out)
    if not week:
        return {"installed": True, "ok": False, "note": "claude usage unreadable"}
    wline = week.group(0)
    wm = re.search(r"(\d+)% used", wline)
    weekly = int(wm.group(1))
    session = int(sess.group(1)) if sess else 0
    reset_h = parse_claude_reset(wline)
    binding = max(weekly, session)
    note = f"claude weekly {weekly}% used"
    if reset_h is not None:
        note += f" (resets in {reset_h:.0f}h)"
    note += f", session {session}% used"
    return {"installed": True, "ok": True, "weekly": weekly,
            "weekly_remaining": 100 - weekly, "weekly_reset_h": reset_h,
            "short": session, "binding": binding, "note": note}


def main():
    kilo, kimi, claude = probe_kilo(), probe_kimi(), probe_claude()

    for probe in (kilo, kimi, claude):
        if probe:
            print("  " + probe["note"])

    # 1. Evaporation priority: fixed weekly window resetting soon with real headroom.
    evap = []
    for name, probe in (("kimi27", kimi), ("haiku-max", claude)):
        if (probe and probe.get("ok")
                and probe.get("weekly_reset_h") is not None
                and probe["weekly_reset_h"] <= RESET_SOON_HOURS
                and probe.get("weekly_remaining", 0) >= MIN_REMAINING_PCT):
            evap.append((name, probe["weekly_remaining"], probe["weekly_reset_h"]))
    if evap:
        evap.sort(key=lambda e: (-e[1], e[2]))
        name, remaining, reset_h = evap[0]
        print(f"DECISION={name}  # quota evaporates in {reset_h:.0f}h with "
              f"{remaining}% left — burn it before it resets")
        return

    # 2. kilo preference (configurable).
    if kilo and kilo.get("ok") and PREFER_KILO:
        print(f"DECISION=mercury  # {kilo['note']} (kilo preferred: burn the prepaid balance)")
        return

    # 3. Most headroom between the two subscriptions.
    candidates = []
    if kimi and kimi.get("ok"):
        candidates.append(("kimi27", kimi["binding"]))
    if claude and claude.get("ok"):
        candidates.append(("haiku-max", claude["binding"]))

    if candidates:
        candidates.sort(key=lambda c: c[1])
        (best, best_u), *rest = candidates
        if rest and abs(best_u - rest[0][1]) <= TIE_POINTS and any(b == "haiku-max" for b, _ in candidates):
            best, best_u = "haiku-max", dict(candidates)["haiku-max"]
            why = f"tie within {TIE_POINTS}pts -> deeper scout"
        else:
            why = "most headroom"
        print(f"DECISION={best}  # binding utilization {best_u}% ({why})")
        return

    # 4. kilo as last resort when PREFER_KILO is off and nothing else is up.
    if kilo and kilo.get("ok"):
        print(f"DECISION=mercury  # {kilo['note']} (only available backend)")
        return

    print("DECISION=native  # no CLI backend with readable quota; use built-in explore agent")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"router error: {e}")
        print("DECISION=native  # probe failure; use built-in explore agent")
    sys.exit(0)
