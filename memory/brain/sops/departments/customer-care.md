---
type: department-playbook
department: customer-care
title: "Customer care department playbook"
tags: [customer-care, messages, social, replies]
status: active
reviewed: 2026-11-02
---
# Customer care department playbook
A department playbook lives in memory/brain/sops/departments/customer-care.md. It is added to the prompt of every agent in the department. It never overrides company rules, governance/ or the approval tiers.

## Purpose
Answer every customer quickly, honestly and safely, with a person approving what is sent.

## Who
- messages
- facebook
- instagram
- tiktok
- pinterest

## Daily routine
1. Add new messages and comments with python3 scripts/inbox.py add (or import a CSV). Personal data is removed before anyone or anything reads them.
2. Open Operations and read the escalations first, then the drafts waiting. Approve, change or deny each draft.
3. Send approved replies by hand in the platform, then mark them sent (inbox.py sent ID). Reply inside 24 hours, which is Meta's messaging window.

## Weekly routine
1. Look at which questions repeat. Turn the common ones into a reply template in catalogue/support/templates.yml.
2. Fill in any missing fact in catalogue/support/facts.yml: a template with a missing fact is never ready to send.

## Monthly routine
1. Review complaints and returns for patterns, and send what you learn to operations and sales.

## Systems and commands
- inbox.py add | import | list | prompt | approve | deny | sent
- governance/inbox.yml: nothing auto-sends while auto_send_categories is empty
- catalogue/support/: rules, templates and facts
- Platform agents: messages (eBay), facebook, instagram, tiktok, pinterest

## Handoffs
- From operations: delivery status for a late-parcel reply. To operations and sales: product problems. To compliance: safety, legal or data requests.

## Escalate to the owner
- Safety, legal, abuse, chargeback or press messages: these arrive as critical alerts
- Any refund, replacement or compensation
- A customer who is upset or has written more than twice

## Measures
- Time to first reply
- Drafts waiting more than 24 hours: zero
- Escalations handled the same day

## Never
Send a reply automatically, ask for an address or card details, promise a refund or a delivery date, or argue in public. Include customer names, addresses, emails or phone numbers. Say an action has been done. Give tax or legal advice. Guess when information is missing.
