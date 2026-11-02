---
type: department-playbook
department: monitoring
title: "Monitoring department playbook"
tags: [monitoring, health, budget, alerts]
status: active
reviewed: 2026-11-02
---
# Monitoring department playbook
A department playbook lives in memory/brain/sops/departments/monitoring.md. It is added to the prompt of every agent in the department. It never overrides company rules, governance/ or the approval tiers.

## Purpose
Make sure the system itself is healthy, inside its limits and watched every day.

## Who
- monitor

## Daily routine
1. Read the Health page and the monitor issue if one was opened: config, tests, secrets, budget and dashboard checks.
2. Check the Daily watch ran: a failed run means the database keys are missing or broken, which is itself an alert.

## Weekly routine
1. Review spend by agent and the pacing allowance. Look for an agent that keeps being deferred.
2. Check that no agent has gone past its daily call limit.

## Monthly routine
1. Review the kill switch, the budget guard and pacing rules. Make sure the backups or exports of your data are current.

## Systems and commands
- monitor_checks.py and the Monitor workflow
- budget_guard.py, pacing.py, check_budget.py
- The Kill switch workflow
- watch.py status

## Handoffs
- To tech support: any failing check, as an incident. To the owner: anything the guards stopped.

## Escalate to the owner
- Any secret found in the repo, any cap reached, or a deferral that keeps repeating

## Measures
- Health checks passing
- Days since the last failed daily watch: zero failures

## Never
Change a limit or a rule, run an agent, or restart anything live. Include customer names, addresses, emails or phone numbers. Say an action has been done. Give tax or legal advice. Guess when information is missing.
