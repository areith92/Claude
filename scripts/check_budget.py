#!/usr/bin/env python3
"""Fails if this month's AI spend is over the caps in governance/budgets.yml."""
import csv
import datetime
import pathlib
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent


def load_yaml(rel):
    return yaml.safe_load((ROOT / rel).read_text()) or {}


def month_totals(month=None):
    month = month or datetime.date.today().strftime("%Y-%m")
    total, per_agent = 0.0, {}
    path = ROOT / "logs" / "costs.csv"
    if path.exists():
        with path.open(newline="") as f:
            for row in csv.DictReader(f):
                if not row.get("date", "").startswith(month):
                    continue
                cost = float(row.get("cost_gbp") or 0)
                total += cost
                per_agent[row["agent"]] = per_agent.get(row["agent"], 0.0) + cost
    return total, per_agent


def check():
    caps = load_yaml("governance/budgets.yml")["ai_costs"]
    total, per_agent = month_totals()
    problems = []
    if total > caps["total_monthly_cap"]:
        problems.append(f"total {total:.2f} GBP is over cap {caps['total_monthly_cap']}")
    for agent, cost in per_agent.items():
        cap = caps["per_agent_monthly_cap"].get(agent, 0)
        if cost > cap:
            problems.append(f"{agent} {cost:.2f} GBP is over cap {cap}")
    return total, problems


if __name__ == "__main__":
    total, problems = check()
    print(f"AI spend this month: {total:.2f} GBP")
    for p in problems:
        print("OVER BUDGET:", p)
    sys.exit(1 if problems else 0)
