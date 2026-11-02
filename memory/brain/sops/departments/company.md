---
type: department-playbook
department: company
title: "Company routine: the owner and the orchestrator"
tags: [company, orchestrator, owner, routine]
status: active
reviewed: 2026-11-02
---
# Company routine: the owner and the orchestrator
A department playbook lives in memory/brain/sops/departments/company.md. It is added to the prompt of every agent in the department. It never overrides company rules, governance/ or the approval tiers.

## Purpose
Keep the whole business running in a small daily and weekly loop. Agents propose, you decide, and nothing live happens without you.

## Who
- orchestrator and the owner

## Daily routine
1. Open the dashboard (python3 scripts/dashboard_server.py). Look at Operations first: alerts, late parcels, customer drafts and escalations.
2. Deal with every critical alert the same day. Acknowledge it once you have acted, so the badge shows only what is new.
3. Clear the Approvals page: approve or deny each product, with a reason when you deny.
4. Run python3 scripts/orchestrate.py digest for the ranked list of what needs you, and python3 scripts/pacing.py status to see the AI allowance left.

## Weekly routine
1. Follow the weekly-owner-review procedure: profit and loss, deliveries, supplier prices, ad spend, customer messages and open approvals.
2. Set next week's goal with python3 scripts/orchestrate.py plan --goal "...". The orchestrator delegates at most 3 tasks a run.

## Monthly routine
1. Follow the month-end-close procedure with the finance department.
2. Read the compliance rule files whose review date is close, and fill in any missing facts in catalogue/support/facts.yml.
3. Check spending caps in governance/budgets.yml and pacing in governance/pacing.yml still suit you.

## Systems and commands
- orchestrate.py plan | ingest | review | digest | decide | complete | status
- dashboard_server.py: Operations, Approvals, Finances, Health
- pacing.py status | plan | run-next
- watch.py status
- The GitHub issues the daily watch and monitor open for you

## Handoffs
- Every department reports to the orchestrator through proposals in outbox/ and logs/actions/.
- The orchestrator never executes: it plans, delegates and summarises. You approve.

## Escalate to the owner
- Any spend above the caps, or any request to raise a cap
- A blocked product, a safety or legal message, or a data incident
- An agent asking to do something live

## Measures
- Critical alerts open for more than 24 hours: zero
- Approvals waiting more than 3 days: zero
- Weekly profit, and late parcels

## Never
Let an agent act live, raise a cap to get past a deferral, or edit data to silence an alert. Include customer names, addresses, emails or phone numbers. Say an action has been done. Give tax or legal advice. Guess when information is missing.
