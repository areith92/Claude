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
    if ".git" in f.parts or ".migration-backup" in f.parts:
        continue
    load(f.relative_to(ROOT))

status = load("governance/status.yml")
routing = load("models/routing.yml")
budgets = load("governance/budgets.yml")
models = routing.get("models") or {}

if not isinstance(status.get("paused"), bool):
    errors.append("status.yml: paused must be true or false")
if status.get("provider") not in ("manual", "api"):
    errors.append("status.yml: provider must be manual or api")

caps = (budgets.get("ai_costs") or {})
per_agent = caps.get("per_agent_monthly_cap") or {}
for name, cfg in (status.get("agents") or {}).items():
    base = ROOT / "agents" / name
    for needed in ("prompt.md", "permissions.yml", "tools.yml"):
        if not (base / needed).exists():
            errors.append(f"agents/{name}/{needed} is missing")
    if not (ROOT / "memory" / "brain" / "sops" / f"{name}.md").exists():
        errors.append(f"memory/brain/sops/{name}.md is missing")
    r = (routing.get("agents") or {}).get(name)
    if r is None:
        errors.append(f"models/routing.yml has no entry for agent {name}")
    else:
        for key in ("tier", "escalate"):
            if key in r and r[key] not in models:
                errors.append(f"routing.yml: {name} uses unknown model tier {r[key]}")
    if name not in per_agent:
        errors.append(f"budgets.yml has no AI cap for agent {name}")
    perms = load(f"agents/{name}/permissions.yml")
    if perms.get("execute_live_actions") is not False:
        errors.append(f"agents/{name}/permissions.yml: execute_live_actions must be false")

for name in per_agent:
    if name not in (status.get("agents") or {}):
        errors.append(f"budgets.yml has a cap for unknown agent {name}")
if sum(per_agent.values()) > (caps.get("total_monthly_cap") or 0) + 0.1:
    errors.append("budgets.yml: per-agent AI caps add up to more than total_monthly_cap")

for ch in ("ebay-uk", "shopify", "social"):
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
