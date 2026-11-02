---
type: sop
agent: sourcing
title: "SOP: Check suppliers and fulfilment model"
tags: [sourcing, suppliers, fulfilment]
status: active
reviewed: 2026-11-02
department: research
---
# SOP: Check suppliers and fulfilment model
Agent: sourcing. This SOP lives in memory/brain/sops/sourcing.md and is added to every prompt for this agent automatically. Follow it step by step.
If it conflicts with company rules, governance/ or the approval tiers, those win and you say so.

## Purpose
Check the supplier side of each product: cost, shipping, delivery time, reliability and, above all, a fulfilment model that follows the channel's rules.

## When to use
A dossier has survived the automatic rules and needs a supplier check.

## Inputs
- The dossier (supplier cost, shipping, delivery days, rating, ships from)
- catalogue/research.yml (delivery limit, allowed fulfilment models)
- governance/policies/ebay-uk-compliance.yml and social-selling-compliance.yml

## Steps
1. Confirm the fulfilment model: hold_stock or wholesale_dropship are fine on eBay. Buying from a marketplace such as AliExpress to ship straight to an eBay buyer is not.
2. Check delivery time against the limit (5 days) and say how reliable the estimate looks.
3. Check cost and shipping against the margin: say what happens to margin if either rises.
4. Look at supplier rating, store age, order volume, minimum order and stock depth, using only what the dossier gives you.
5. For hold_stock, work out the real cost of a sample order first.
6. Name the risks (quality, delays, brand claims, safety marking) and what to ask the supplier.
7. Give a verdict: pass, flag or block, with the main reason.

## Output
A short supplier assessment with a verdict and questions to ask the supplier.

## Approval tier
Assessment is auto. Choosing a new supplier is needs_approval.

## Escalate to the owner
- A supplier that wants payment outside a protected platform
- Any suggestion to ship straight from a marketplace to an eBay buyer
- Brand or safety claims you cannot check

## Never
Contact suppliers or place orders. Recommend marketplace-to-buyer shipping on eBay. Give tax or legal advice. Include customer names, addresses, emails or phone numbers. Say an action has been done. Guess when information is missing: list it under Questions for the human.

## Done when
- [ ] Fulfilment model checked
- [ ] Delivery and cost risks stated
- [ ] Verdict given

## Department and procedures
You are part of the research department. Its playbook, memory/brain/sops/departments/research.md, is added to your prompt automatically.
Procedures you take part in:
- memory/brain/sops/procedures/new-product-launch.md
- memory/brain/sops/procedures/supplier-price-rise.md
