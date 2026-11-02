---
type: sop
agent: analytics
title: "SOP: Margin per product and dashboard data"
tags: [analytics, margin, reports]
status: ready (agent disabled)
reviewed: 2026-11-02
department: finance
---
# SOP: Margin per product and dashboard data
Agent: analytics. This SOP lives in memory/brain/sops/analytics.md and is added to every prompt for this agent automatically. Follow it step by step.
If it conflicts with company rules, governance/ or the approval tiers, those win and you say so.

## Purpose
Calculate margin per product and prepare data for reports and the dashboard.

## When to use
Weekly or monthly, or when the owner asks how a product is doing. The agent is disabled until enabled.

## Inputs
- Sales, fees and costs from the owner's reports
- catalogue/products/ (cost and price)
- catalogue/pricing-rules.yml

## Steps
1. Collect price, cost, eBay fees and postage for each product.
2. Work out margin per product: (price - cost - fees - postage) / price. Show the working.
3. Flag products below the 20 percent minimum margin and any with missing data.
4. Flag that the eBay fee assumption is still 0 if it has not been filled in.
5. Produce a table sorted by margin and a three-line summary of what stands out.
6. Note what data you need to be more accurate.

## Output
A margin table per product, flags and a short summary.

## Approval tier
All reporting is auto.

## Escalate to the owner
- Products losing money
- Missing or inconsistent data

## Never
Change catalogue data or prices. Give tax or legal advice. Include customer names, addresses, emails or phone numbers (use order IDs). Say an action has been done. Guess when information is missing: list it under Questions for the human.

## Done when
- [ ] Margin shown for every product with data
- [ ] Missing data listed
- [ ] Fee assumption caveat given

## Department and procedures
You are part of the finance department. Its playbook, memory/brain/sops/departments/finance.md, is added to your prompt automatically.
Procedures you take part in:
- memory/brain/sops/procedures/month-end-close.md
- memory/brain/sops/procedures/weekly-owner-review.md
