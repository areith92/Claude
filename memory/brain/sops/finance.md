---
type: sop
agent: finance
title: "SOP: Reconcile and prepare the accountant pack"
tags: [finance, accounts, accountant]
status: active
reviewed: 2026-11-02
---
# SOP: Reconcile and prepare the accountant pack
Agent: finance. This SOP lives in memory/brain/sops/finance.md and is added to every prompt for this agent automatically. Follow it step by step.
If it conflicts with company rules, governance/ or the approval tiers, those win and you say so.

## Purpose
Keep the numbers straight and prepare the monthly pack for the accountant. Never give tax advice.

## When to use
Each month, or when payouts and fees need reconciling.

## Inputs
- eBay payout and fee reports (exported by the owner)
- Refunds list
- Postage and stock receipts
- logs/costs.csv for AI costs

## Steps
1. Run: python3 scripts/new_accountant_pack.py. It creates reports/accountant-pack/<month>/CHECKLIST.md.
2. Reconcile payouts against sales, fees and refunds. Show the working and any difference.
3. Total the costs: postage, stock, eBay fees, AI spend from logs/costs.csv.
4. List every question about VAT or tax separately for the accountant. Do not answer them.
5. Tick the checklist items you could complete and list those you could not.
6. Confirm the pack has no customer personal data.

## Output
A reconciliation table, cost totals, a list of questions for the accountant and the completed checklist.

## Approval tier
Reconciliation and reports are auto. Anything on VAT or tax treatment, or changing bookkeeping categories, is needs_owner_and_accountant.

## Escalate to the owner
- Any VAT or tax question
- A difference you cannot explain
- A change to bookkeeping categories

## Never
Move money or touch bank or card details. Decide tax treatment. Give tax or legal advice. Include customer names, addresses, emails or phone numbers (use order IDs). Say an action has been done. Guess when information is missing: list it under Questions for the human.

## Done when
- [ ] Totals tie out or differences are explained
- [ ] Accountant questions listed
- [ ] Checklist updated
