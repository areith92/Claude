---
type: department-playbook
department: sales
title: "Sales department playbook"
tags: [sales, listings, pricing, ebay]
status: active
reviewed: 2026-11-02
---
# Sales department playbook
A department playbook lives in memory/brain/sops/departments/sales.md. It is added to the prompt of every agent in the department. It never overrides company rules, governance/ or the approval tiers.

## Purpose
Turn approved products into honest, well-priced listings that a person publishes by hand.

## Who
- listings
- pricing

## Daily routine
1. Check the Approvals page for products that were approved and have a launch pack in research/approved/.
2. Draft or improve any listing waiting for a decision. Write in plain UK English, from the facts only.
3. Re-check any price the daily watch flagged: a supplier price rise or a margin below minimum.

## Weekly routine
1. Review sold and unsold listings. Propose title, photo or price changes with a reason for each.
2. Make sure every live listing is recorded with python3 scripts/watch.py listing add, so supplier price rises are caught.

## Monthly routine
1. Re-price anything whose fees or costs changed. Update catalogue/fees.yml with the real fee figures and set confirmed: true.

## Systems and commands
- research/approved/<id>/ launch packs: listing-draft.md, catalogue-entry.yml, sample-order-checklist.md
- margin.py --price --cost --shipping: the margin calculator
- catalogue/pricing-rules.yml and catalogue/research.yml (minimum margin 30 percent, never below cost)
- watch.py listing add | list, price import, scan

## Handoffs
- From research: an approved launch pack. To compliance: every listing draft before it goes live. To marketing: the finished listing and price.
- From the daily watch: price alerts, which pricing turns into a reprice, pause or keep decision for you.

## Escalate to the owner
- A price change of more than 5 percent
- Any claim about safety, materials or branded goods you cannot back up
- A listing that would need photos you do not own

## Measures
- Margin per listing against the 30 percent minimum
- Listings with a recorded supplier price
- Days from approval to live

## Never
Publish a listing, copy another seller's text or photos, price below cost, or invent a feature. Include customer names, addresses, emails or phone numbers. Say an action has been done. Give tax or legal advice. Guess when information is missing.
