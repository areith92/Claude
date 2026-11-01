#!/usr/bin/env python3
"""Builds the weekly summary (no AI needed). Usage: python scripts/weekly_report.py [--out file.md]"""
import argparse
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_budget import ROOT, load_yaml, month_totals  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--out")
args = ap.parse_args()

status = load_yaml("governance/status.yml")
caps = load_yaml("governance/budgets.yml")["ai_costs"]
total, per_agent = month_totals()
enabled = [n for n, c in (status.get("agents") or {}).items() if c.get("enabled")]
outbox = {p.name for p in (ROOT / "outbox").glob("*.md") if p.name != "README.md"}
inbox = {p.name for p in (ROOT / "inbox").glob("*.md")}
actions = [p for p in (ROOT / "logs" / "actions").glob("*.md")]

lines = [
    f"# Weekly report {datetime.date.today()}",
    f"- Paused: {status.get('paused')} | Provider: {status.get('provider')}",
    f"- Enabled agents: {', '.join(enabled)}",
    f"- AI spend this month: {total:.2f} GBP of cap {caps['total_monthly_cap']} GBP",
    f"- Prompts waiting for a reply in inbox/: {len(outbox - inbox)}",
    f"- Proposals logged: {len(actions)}",
    "",
    "## Decisions waiting on the owner",
    "- Review open pull requests and proposals above.",
]
text = "\n".join(lines) + "\n"
print(text)
if args.out:
    open(args.out, "w").write(text)
else:
    (ROOT / "reports" / "weekly" / f"{datetime.date.today()}.md").write_text(text)
