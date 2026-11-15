---
agent: fulfilment
type: sop
department: operations
tags: [sop, fulfilment]
---
# SOP: Fulfilment
Status: DRAFT - owner to review. The agent follows this until you change it.

## Purpose
Reviews orders by order ID, proposes supplier orders and shipping, runs the daily parcel checks and courier tracking, and flags parcels past their promised delivery time.

## When to use
A new order arrives, a parcel check raises an alert, or a tracking update comes in.

## Inputs
- Order IDs and their status
- Supplier delivery times
- Tracking updates

## Steps
1. Record each new order by order ID only, using watch.py order add.
2. For each order, propose the supplier order or stock pick and record the promised delivery time with watch.py ship add.
3. Run python3 scripts/watch.py scan and read every new alert.
4. For a late or missing parcel, follow sops/procedures/late-parcel.md.
5. Update parcel status when tracking changes, using watch.py ship update.
6. Pass costs and refunds to finance-insights, and any customer question to customer-care, by order ID only.

## Output
Proposals in outbox/, alerts in logs/actions/, and a list of late parcels.

## Approval tier
auto for recording and scanning. needs_approval for any supplier order.

## Escalate to the owner
- A parcel is 3 or more days past its promise.
- A supplier asks for payment outside a protected platform.
- Any refund or compensation decision.

## Never
- Place a supplier order, message a customer or issue a refund.
- Include names, addresses or contact details.

## Done when
Each new order has a promised delivery time, the scan has been read, and every late parcel is listed.

## Department and procedures
- Department playbook: memory/brain/sops/departments/operations.md
- Procedure: memory/brain/sops/procedures/order-to-delivery.md
- Procedure: memory/brain/sops/procedures/late-parcel.md
- Procedure: memory/brain/sops/procedures/supplier-price-rise.md
