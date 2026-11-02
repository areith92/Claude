---
type: procedure
title: "Late or missing parcel"
tags: [delivery, late, customer]
status: active
reviewed: 2026-11-02
---
# Procedure: Late or missing parcel
A cross-department procedure. It never overrides company rules, governance/ or the approval tiers. A person approves anything live.

## Purpose
Deal with a parcel that is past its promised delivery time before the customer has to chase.

## Trigger
The daily watch raises a parcel_overdue alert, or a customer asks where an order is.

## Roles
- operations
- customer care
- the owner decides compensation

## Steps
1. Read the alert: parcel, order, carrier, tracking and how many days late.
2. Check the carrier's tracking and update the parcel status and last event with watch.py ship update.
3. Contact the supplier or courier by hand. Ask for a new date or a trace, and note what they say.
4. Draft a short, honest message to the customer with the order ID, using the delivery_delay template. Say what you know and when you will update them. Do not promise a delivery date you cannot meet.
5. If it is 3 days or more past the promise, or the carrier says lost, decide with the owner: reship, refund, or wait. Never promise before the owner decides.
6. Record the outcome. Acknowledge the alert. Note the supplier's performance for the monthly score.

## Records
- Alert, parcel events and the decision

## Escalate to the owner
- Any refund or compensation
- A pattern of late parcels from one supplier

## Done when
- [ ] Customer updated
- [ ] Alert acknowledged
- [ ] Supplier noted
