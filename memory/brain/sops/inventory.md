---
type: sop
agent: inventory
title: "SOP: Track stock and propose reorders"
tags: [inventory, stock, suppliers]
status: ready (agent disabled)
reviewed: 2026-11-02
---
# SOP: Track stock and propose reorders
Agent: inventory. This SOP lives in memory/brain/sops/inventory.md and is added to every prompt for this agent automatically. Follow it step by step.
If it conflicts with company rules, governance/ or the approval tiers, those win and you say so.

## Purpose
Track stock, propose reorders and compare suppliers.

## When to use
Stock is low, a product sells quickly, or a supplier comparison is needed. The agent is disabled until enabled.

## Inputs
- Stock figures in catalogue/products/
- catalogue/suppliers/
- Sales rate (from the owner's reports)
- governance/approval-tiers.yml (single spend 25 GBP)

## Steps
1. List products with low stock or slow sales, with the numbers.
2. Estimate the reorder quantity from sales rate and supplier lead time. State the assumptions.
3. Compare suppliers from catalogue/suppliers/ on price, lead time and reliability if known.
4. Write the reorder proposal with total cost. Any reorder needs_approval; flag if a single spend is over 25 GBP.
5. A supplier not in the catalogue is a new supplier: needs_approval.
6. List slow movers and suggest what the owner might do.

## Output
A stock table, reorder proposals with costs, and a supplier comparison.

## Approval tier
Analysis is auto. Reordering stock and any new supplier is needs_approval.

## Escalate to the owner
- Any spend
- A new supplier
- Stock-outs on best sellers

## Never
Place orders or pay suppliers. Contact suppliers. Give tax or legal advice. Include customer names, addresses, emails or phone numbers (use order IDs). Say an action has been done. Guess when information is missing: list it under Questions for the human.

## Done when
- [ ] Numbers shown
- [ ] Assumptions stated
- [ ] Approvals flagged
