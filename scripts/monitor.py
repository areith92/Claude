#!/usr/bin/env python3
"""Free watcher for Tech Support. Runs the config, budget and secret checks and looks for stuck work.
Prints a short report and exits 1 if anything needs attention. No AI is used."""
import datetime
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
problems = []

for script in ("validate_config.py", "check_budget.py", "check_secrets.py"):
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / script)], cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        out = (r.stdout + r.stderr).strip().splitlines()
        problems.append(f"{script} failed: " + (out[-1] if out else "no output"))

today = datetime.date.today()
inbox = {p.name for p in (ROOT / "inbox").glob("*.md")}
for p in sorted((ROOT / "outbox").glob("*.md")):
    if p.name == "README.md" or p.name in inbox:
        continue
    try:
        made = datetime.datetime.strptime(p.name[:8], "%Y%m%d").date()
    except ValueError:
        continue
    if (today - made).days > 3:
        problems.append(f"prompt waiting more than 3 days for a reply: outbox/{p.name}")

lines = [f"# Monitor report {today}"]
lines += [f"- PROBLEM: {x}" for x in problems] or ["- All checks passed"]
text = "\n".join(lines) + "\n"
print(text)
(ROOT / "logs" / "audits").mkdir(parents=True, exist_ok=True)
(ROOT / "logs" / "audits" / f"monitor-{today}.md").write_text(text)
sys.exit(1 if problems else 0)
