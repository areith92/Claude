#!/usr/bin/env python3
"""Checks that the YAML config files are valid and consistent."""
import pathlib
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
errors, warnings = [], []


def load(rel):
    try:
        return yaml.safe_load((ROOT / rel).read_text()) or {}
    except Exception as exc:
        errors.append(f"{rel}: cannot parse ({exc})")
        return {}


for f in ROOT.rglob("*.yml"):
    if ".git" in f.parts:
        continue
    load(f.relative_to(ROOT))

status = load("governance/status.yml")
routing = load("models/routing.yml")
budgets = load("governance/budgets.yml")

if not isinstance(status.get("paused"), bool):
    errors.append("status.yml: paused must be true or false")
if status.get("provider") not in ("manual", "api"):
    errors.append("status.yml: provider must be manual or api")
for name, cfg in (status.get("agents") or {}).items():
    base = ROOT / "agents" / name
    for needed in ("prompt.md", "permissions.yml", "tools.yml"):
        if not (base / needed).exists():
            errors.append(f"agents/{name}/{needed} is missing")
    if name not in (routing.get("agents") or {}):
        errors.append(f"models/routing.yml has no entry for agent {name}")
    if name not in (budgets.get("ai_costs", {}).get("per_agent_monthly_cap") or {}):
        errors.append(f"budgets.yml has no AI cap for agent {name}")
    perms = load(f"agents/{name}/permissions.yml")
    if perms.get("execute_live_actions") is not False:
        errors.append(f"agents/{name}/permissions.yml: execute_live_actions must be false")

for ch in ("ebay-uk", "shopify"):
    cfg = load(f"channels/{ch}/config.yml")
    if not isinstance(cfg.get("enabled"), bool):
        errors.append(f"channels/{ch}/config.yml: enabled must be true or false")

if "YOUR-GITHUB-USERNAME" in (ROOT / "CODEOWNERS").read_text():
    warnings.append("CODEOWNERS still has the placeholder username")

for w in warnings:
    print("WARNING:", w)
for e in errors:
    print("ERROR:", e)
print("Config OK" if not errors else f"{len(errors)} error(s)")
sys.exit(1 if errors else 0)
