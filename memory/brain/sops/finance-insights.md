---
agent: finance-insights
type: sop
department: finance
tags: [sop, finance-insights]
---
# SOP: Finance Insights
Status: DRAFT - owner to review. The agent follows this until you change it.

## Purpose
Reconciles sales, fees, postage and refunds, keeps the margin and cost figures up to date, and prepares the accountant pack.

## When to use
Each week, at month end, or when the owner asks for figures.

## Inputs
- logs/costs.csv
- Order records and the Seller Hub export
- Supplier price changes

## Steps
1. Check AI spend against the budget with python3 scripts/check_budget.py.
2. Reconcile orders, fees, postage and refunds by order ID.
3. Update the margin for each product and flag any product below 30 percent.
4. Follow sops/procedures/month-end-close.md at month end and prepare the accountant pack with scripts/new_accountant_pack.py.
5. Flag supplier price rises to merchandiser and fulfilment.

## Output
A reconciliation summary and the accountant pack in reports/.

## Approval tier
auto for reading and reconciling. needs_approval for any change to a price or a budget. needs_owner_and_accountant for any VAT or tax position.

## Escalate to the owner
- A figure cannot be reconciled.
- Spend is close to the monthly cap.
- Any VAT or tax question.

## Never
- Give tax or legal advice.
- Move money or change a budget.
- Use customer personal data.

## Done when
The reconciliation has no unexplained differences, or each one is listed for the owner.

## Department and procedures
- Department playbook: memory/brain/sops/departments/finance.md
- Procedure: memory/brain/sops/procedures/month-end-close.md
