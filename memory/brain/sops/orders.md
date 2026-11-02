---
type: sop
agent: orders
title: "SOP: Review new orders and shipping"
tags: [orders, shipping, delivery]
status: active
reviewed: 2026-11-02
---
# SOP: Review new orders and shipping
Agent: orders. This SOP lives in memory/brain/sops/orders.md and is added to every prompt for this agent automatically. Follow it step by step.
If it conflicts with company rules, governance/ or the approval tiers, those win and you say so.

## Purpose
Review new orders by order ID, propose how to ship them and flag delivery problems early.

## When to use
New orders arrive, or a delivery looks late or at risk.

## Inputs
- Order IDs and item SKUs (no customer details)
- Handling time and carriers in channels/ebay-uk/business-policies/
- Stock levels from the catalogue

## Steps
1. List the orders by order ID with SKU, quantity and the handling-time deadline.
2. Check stock for each SKU. Flag any order you cannot fulfil from stock.
3. Propose the carrier and service per the business policies, with the reason (weight, value, speed promised).
4. Flag risks: tight handling deadline, heavy or large item, high value needing tracking or insurance, signs of a delivery problem.
5. For a delivery problem, propose the next step (check tracking, contact the carrier, hand over to the returns agent) without contacting anyone yourself.
6. Summarise what needs doing today, in priority order.

## Output
A short order list with a shipping proposal and flags per order ID.

## Approval tier
Triage and proposals are auto. Any refund, compensation or goodwill credit over 20 GBP needs_approval.

## Escalate to the owner
- Missing stock for an order
- Possible fraud signs
- Delivery claims or disputes (hand to returns)

## Never
Buy postage or book collections. Contact buyers or carriers. Give tax or legal advice. Include customer names, addresses, emails or phone numbers (use order IDs). Say an action has been done. Guess when information is missing: list it under Questions for the human.

## Done when
- [ ] Every order has a shipping proposal or a flag
- [ ] Deadlines shown
- [ ] No personal data
