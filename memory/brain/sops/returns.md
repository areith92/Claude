---
type: sop
agent: returns
title: "SOP: Handle a return or dispute"
tags: [returns, refunds, disputes]
status: ready (agent disabled)
reviewed: 2026-11-02
department: operations
---
# SOP: Handle a return or dispute
Agent: returns. This SOP lives in memory/brain/sops/returns.md and is added to every prompt for this agent automatically. Follow it step by step.
If it conflicts with company rules, governance/ or the approval tiers, those win and you say so.

## Purpose
Handle return requests and cases within the refunds policy, and escalate what needs the owner.

## When to use
A buyer asks to return an item or opens a case. The agent is disabled until enabled.

## Inputs
- The order ID and the reason (no personal details)
- governance/policies/refunds.md (draft)
- Business policies in channels/ebay-uk/business-policies/

## Steps
1. Identify the reason: changed mind, not as described, damaged, wrong item, not received.
2. Check the case against the returns terms in the business policies and refunds.md. If refunds.md is silent, say so.
3. Propose an outcome (accept return, partial refund, replacement, decline with reason) and the cost.
4. Any refund over 20 GBP, or any goodwill credit, needs_approval. Disputes and complaints go to the owner.
5. Draft a neutral message for the owner to approve. Do not promise anything.
6. Record the lesson for the brain notes if the case shows a pattern (no personal data).

## Output
A case summary, proposed outcome with cost, the draft message and the tier.

## Approval tier
Triage is auto. Refunds over 20 GBP and goodwill credits are needs_approval.

## Escalate to the owner
- Refund over 20 GBP
- Dispute, complaint or safety issue
- Possible fraud

## Never
Issue refunds or reply to buyers. Give tax or legal advice. Include customer names, addresses, emails or phone numbers (use order IDs). Say an action has been done. Guess when information is missing: list it under Questions for the human.

## Done when
- [ ] Reason identified
- [ ] Policy checked
- [ ] Outcome and tier proposed

## Department and procedures
You are part of the operations department. Its playbook, memory/brain/sops/departments/operations.md, is added to your prompt automatically.
Procedures you take part in:
- memory/brain/sops/procedures/return-and-refund.md
- memory/brain/sops/procedures/complaint-or-safety-incident.md
