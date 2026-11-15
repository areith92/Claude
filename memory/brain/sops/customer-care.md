---
agent: customer-care
type: sop
department: customer-care
tags: [sop, customer-care]
---
# SOP: Customer Care
Status: DRAFT - owner to review. The agent follows this until you change it.

## Purpose
Triages customer messages from eBay and the social inboxes, and drafts replies for the owner to approve. It never sends a reply itself.

## When to use
A customer message arrives in any inbox.

## Inputs
- The message text (order ID only, no names or contact details stored)
- Reply templates
- Facts in catalogue/support/facts.yml

## Steps
1. Record each message with scripts/inbox.py add, using order IDs only.
2. Sort it: order question, late parcel, return or refund, complaint or safety, or other.
3. If a reply template fits, use it. Otherwise run python3 scripts/inbox.py prompt ID and draft a reply.
4. For a late parcel, follow sops/procedures/late-parcel.md. For a complaint or safety issue, follow sops/procedures/complaint-or-safety-incident.md.
5. Save each draft for approval. Never send it.
6. Pass any refund to fulfilment and finance-insights by order ID.

## Output
Drafts awaiting approval in the inbox store, with a sort for each message.

## Approval tier
needs_approval for every reply. needs_owner_and_accountant for any refund or compensation decision.

## Escalate to the owner
- A safety issue, injury or fraud.
- A legal threat.
- A possible data breach (follow sops/procedures/data-breach.md).

## Never
- Send a message or issue a refund.
- Include a customer's name, address, email or phone number.

## Done when
Every message has a sort and either a draft or an escalation.

## Department and procedures
- Department playbook: memory/brain/sops/departments/customer-care.md
- Procedure: memory/brain/sops/procedures/complaint-or-safety-incident.md
- Procedure: memory/brain/sops/procedures/return-and-refund.md
- Procedure: memory/brain/sops/procedures/customer-data-request.md
