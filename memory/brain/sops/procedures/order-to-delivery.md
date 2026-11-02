---
type: procedure
title: "Order to delivery"
tags: [orders, delivery, shipping]
status: active
reviewed: 2026-11-02
---
# Procedure: Order to delivery
A cross-department procedure. It never overrides company rules, governance/ or the approval tiers. A person approves anything live.

## Purpose
Follow every order from payment to a delivered parcel.

## Trigger
A new order arrives.

## Roles
- operations
- finance
- customer care when something goes wrong

## Steps
1. Record the order by order ID only (watch.py order add, status new): revenue, supplier cost, postage and the platform fee.
2. Check the supplier's current price. If it has risen so the order would lose money, stop and follow the supplier-price-rise procedure.
3. Place the supplier order, or pick the stock. Mark the order ordered.
4. Record the parcel (watch.py ship add) with the carrier, tracking number, ship date and the delivery time promised.
5. The daily watch checks the parcel against that promise every morning. Update its status by hand when tracking changes.
6. On delivery, mark it delivered (watch.py ship update --status delivered). A late arrival is noted for the supplier's score.
7. Finance sees the order in profit and loss. Close the order.

## Records
- Order, shipment and any alert in the data store

## Escalate to the owner
- A parcel past its promise
- A delivery exception

## Done when
- [ ] Delivered and recorded
- [ ] Any alert acknowledged
