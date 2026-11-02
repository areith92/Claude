#!/usr/bin/env python3
"""Health checks. The monitor runs these; a failing check is raised as a Tech Support incident.
Usage: python scripts/monitor_checks.py [--alert-file /tmp/monitor.md]
Set MONITOR_SKIP=tests,secrets to skip checks (used by the tests)."""
import argparse
import datetime
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable
CHECKS = [
    ("config", "Config files are valid", "high", [PY, "scripts/validate_config.py"]),
    ("tests", "Unit tests pass", "high", [PY, "-m", "unittest", "discover", "tests"]),
    ("secrets", "No secrets in tracked files", "high", [PY, "scripts/check_secrets.py"]),
    ("budget", "AI spend is within caps", "high", [PY, "scripts/check_budget.py"]),
    ("dashboard", "Dashboard data builds", "medium",
     [PY, "-c", "import sys; sys.path.insert(0, 'scripts'); import build_dashboard as b; b.build()"]),
]


def tail(text, n):
    lines = text.strip().splitlines()
    return "\n".join(lines[-n:])


def run_checks(root=ROOT, only=None, skip=None, evidence_lines=40):
    skip = set(filter(None, os.environ.get("MONITOR_SKIP", "").split(","))) | set(skip or [])
    out = []
    for key, title, severity, cmd in CHECKS:
        if (only and key not in only) or key in skip:
            continue
        try:
            r = subprocess.run(cmd, cwd=str(root), capture_output=True, text=True, timeout=600)
            ok, text = r.returncode == 0, r.stdout + r.stderr
        except subprocess.TimeoutExpired:
            ok, text = False, "The check timed out after 10 minutes."
        out.append({"key": key, "title": title, "severity": severity, "ok": ok, "evidence": tail(text, evidence_lines)})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--alert-file")
    a = ap.parse_args()
    results = run_checks()
    for r in results:
        print(("PASS " if r["ok"] else "FAIL ") + r["key"] + ": " + r["title"])
    failing = [r for r in results if not r["ok"]]
    if a.alert_file:
        body = ""
        if failing:
            body = f"# Monitor: {len(failing)} check(s) failing {datetime.date.today()}\n\n" + "\n\n".join(
                f"## {r['key']}: {r['title']}\n" + r["evidence"][-1500:] for r in failing) + \
                "\n\nTo get a fix: python3 scripts/techsupport.py detect, then python3 scripts/techsupport.py run <incident id>\n"
        open(a.alert_file, "w").write(body)
    return 1 if failing else 0


if __name__ == "__main__":
    sys.exit(main())
