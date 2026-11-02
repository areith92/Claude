---
type: procedure
title: "Month-end close"
tags: [finance, month-end, accountant]
status: active
reviewed: 2026-11-02
---
# Procedure: Month-end close
A cross-department procedure. It never overrides company rules, governance/ or the approval tiers. A person approves anything live.

## Purpose
Close the month with figures the accountant can use.

## Trigger
The last working day of the month.

## Roles
- finance
- analytics
- the owner

## Steps
1. Check every order, refund and shipment is recorded for the month. Fix gaps by hand.
2. Replace estimated fees with real ones from the fee statements wherever you can.
3. Run watch.py pnl and note the weekly figures, ad spend and AI spend.
4. Compare AI spend and ad spend with their caps. Note any deferral and why.
5. Prepare the accountant pack with new_accountant_pack.py and flag VAT, duty and anything unusual.
6. Review the month: best and worst products, late parcels, refunds. Write three lessons into memory/brain/.
7. Export the month's data and keep a copy somewhere safe.

## Records
- The accountant pack and the month's lessons

## Escalate to the owner
- A loss-making month
- Figures that do not match the statements

## Done when
- [ ] Pack prepared
- [ ] Lessons recorded
- [ ] Data exported
