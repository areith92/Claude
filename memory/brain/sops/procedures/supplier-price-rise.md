---
type: procedure
title: "Supplier price rise"
tags: [pricing, supplier, margin]
status: active
reviewed: 2026-11-02
---
# Procedure: Supplier price rise
A cross-department procedure. It never overrides company rules, governance/ or the approval tiers. A person approves anything live.

## Purpose
Protect margin when a supplier's price goes up, including for orders already paid.

## Trigger
The daily watch raises supplier_price_rise, margin_below_minimum or order_exposed.

## Roles
- pricing
- operations
- the owner decides

## Steps
1. Read the alert. Check the new price on the supplier's page and record it (watch.py price import) so the margin shows correctly.
2. Work out the new margin with margin.py. Below 30 percent is a problem; below zero means every sale loses money.
3. For each order flagged order_exposed (paid, supplier not yet ordered): work out the loss and choose with the owner: fulfil anyway, ask the supplier for the old price, or cancel and refund within the platform's rules.
4. For the listing: reprice (a change over 5 percent needs the owner), pause it, or keep it if the margin is still fine.
5. If the customer must be told, use a template and never blame them. Record the decision.
6. Ask sourcing for a cheaper supplier of the same product.

## Records
- The new price, the margin before and after, and the decision

## Escalate to the owner
- Any listing selling at a loss
- Any cancellation or refund

## Done when
- [ ] Price recorded
- [ ] Orders decided
- [ ] Listing repriced, paused or kept
