#!/usr/bin/env python3
"""Builds dashboard/status.json and dashboard/status.js from the repo's own files. No customer data, no timestamps.
Usage: python scripts/build_dashboard.py [--alert-file /tmp/alert.md]
With --alert-file, an alert message is written there when AI spend needs attention (the file is empty otherwise)."""
import argparse
import csv
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import yaml  # noqa: E402
from budget_guard import read_stop_marker, spend_state  # noqa: E402
from check_budget import ROOT, load_yaml, month_totals  # noqa: E402


def build():
    status = load_yaml("governance/status.yml")
    caps = load_yaml("governance/budgets.yml")["ai_costs"]
    total, per_agent = month_totals()
    cap = caps["total_monthly_cap"]
    alert_at = caps.get("alert_at_percent", 80)
    marker = read_stop_marker(ROOT)
    state = spend_state(total, cap, alert_at, bool(marker and marker.get("scope") == "total"))
    month = datetime.date.today().strftime("%Y-%m")
    rows = []
    path = ROOT / "logs" / "costs.csv"
    if path.exists():
        with path.open(newline="") as f:
            rows = list(csv.DictReader(f))
    qp = ROOT / "operations" / "tasks" / "queue.yml"
    tasks = ((yaml.safe_load(qp.read_text()) or {}).get("tasks") or []) if qp.exists() else []
    queue = {}
    for t in tasks:
        queue[t["status"]] = queue.get(t["status"], 0) + 1
    digests = sorted((ROOT / "reports" / "digests").glob("*.md"))
    pct = round(total / cap * 100, 1) if cap > 0 else 0

    alerts = []
    if state == "stopped":
        alerts.append(f"AI spend stopped: {total:.2f} of {cap} GBP used in {month}. Agents will not call paid models until next month, or until the cap is raised in governance/budgets.yml.")
    elif state == "warning":
        alerts.append(f"AI spend warning: {pct:.0f}% of the {cap} GBP monthly cap is used ({total:.2f} GBP).")
    elif state == "off":
        alerts.append("Paid API use is off: the monthly cap in governance/budgets.yml is 0.")
    if marker and marker.get("scope") == "agent":
        alerts.append(f"{marker['agent']} reached its own monthly cap ({marker['spent_gbp']} of {marker['cap_gbp']} GBP).")
    if status.get("paused"):
        alerts.append("All agents are paused (kill switch).")

    title = ""
    if state == "stopped":
        title = f"AI budget STOPPED {month}"
    elif state == "warning":
        title = f"AI budget warning {month}"
    elif marker and marker.get("scope") == "agent":
        title = f"AI agent cap reached {marker['agent']} {month}"

    data = {
        "month": month,
        "as_of": rows[-1]["date"] if rows else None,
        "mode": {"provider": status.get("provider"), "paused": bool(status.get("paused")),
                 "dry_run_default": bool(status.get("default_dry_run"))},
        "spend": {"spent_gbp": round(total, 4), "cap_gbp": cap, "remaining_gbp": round(max(cap - total, 0), 4),
                  "percent": pct, "state": state, "alert_at_percent": alert_at},
        "per_agent": [{"agent": a, "spent_gbp": round(per_agent.get(a, 0), 4), "cap_gbp": c}
                      for a, c in caps["per_agent_monthly_cap"].items() if c or per_agent.get(a)],
        "alerts": alerts,
        "queue": queue,
        "latest_digest": digests[-1].name if digests else None,
        "recent_costs": [{"date": r["date"], "agent": r["agent"], "model": r["model"],
                          "tokens": int(r["input_tokens"] or 0) + int(r["output_tokens"] or 0),
                          "cost_gbp": float(r["cost_gbp"] or 0)} for r in rows[-10:]][::-1],
    }
    body = "# " + title + "\n\n" + "\n".join("- " + x for x in alerts) + \
           "\n\nTo continue before next month, raise total_monthly_cap in governance/budgets.yml by pull request.\n" if title else ""
    return data, body


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--alert-file")
    a = ap.parse_args()
    data, body = build()
    out = ROOT / "dashboard"
    out.mkdir(exist_ok=True)
    text = json.dumps(data, indent=2) + "\n"
    (out / "status.json").write_text(text)
    (out / "status.js").write_text("window.DASHBOARD = " + text.rstrip() + ";\n")
    if a.alert_file:
        open(a.alert_file, "w").write(body)
    print(f"Dashboard data written. AI spend {data['spend']['spent_gbp']} of {data['spend']['cap_gbp']} GBP ({data['spend']['state']}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
