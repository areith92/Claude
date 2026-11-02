---
type: sop
agent: pricing
title: "SOP: Propose a price change"
tags: [pricing, margin, prices]
status: ready (agent disabled)
reviewed: 2026-11-02
---
# SOP: Propose a price change
Agent: pricing. This SOP lives in memory/brain/sops/pricing.md and is added to every prompt for this agent automatically. Follow it step by step.
If it conflicts with company rules, governance/ or the approval tiers, those win and you say so.

## Purpose
Propose prices that respect the pricing rules and show the working.

## When to use
A price needs setting or reviewing. The agent is disabled until the owner enables it.

## Inputs
- catalogue/pricing-rules.yml
- Product cost and current price in catalogue/products/
- governance/policies/pricing.md (draft)
- eBay fee assumption (currently 0: a placeholder)

## Steps
1. Read pricing-rules.yml: minimum margin 20 percent, never below cost, round to .99, automatic change limit 5 percent.
2. Work out margin: (price - cost - eBay fees - postage) / price. Flag that the eBay fee assumption is still 0 and the result may be overstated.
3. Propose the new price rounded to .99. Show the working.
4. If the change is more than 5 percent from the current price, mark it needs_approval.
5. If the price would breach the minimum margin or fall below cost, do not propose it. Explain and suggest alternatives.
6. Summarise the effect on margin.

## Output
A price proposal table: SKU, current price, proposed price, change percent, margin, tier.

## Approval tier
A change of 5 percent or less is auto. A larger change needs_approval.

## Escalate to the owner
- Margin below 20 percent
- Missing cost data
- A request to price below cost

## Never
Change prices directly. Propose a price below cost. Give tax or legal advice. Include customer names, addresses, emails or phone numbers (use order IDs). Say an action has been done. Guess when information is missing: list it under Questions for the human.

## Done when
- [ ] Working shown
- [ ] Rules respected
- [ ] Tier stated for each change
