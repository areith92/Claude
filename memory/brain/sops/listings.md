---
type: sop
agent: listings
title: "SOP: Draft an eBay UK listing"
tags: [listings, ebay, drafts]
status: active
reviewed: 2026-11-02
department: sales
---
# SOP: Draft an eBay UK listing
Agent: listings. This SOP lives in memory/brain/sops/listings.md and is added to every prompt for this agent automatically. Follow it step by step.
If it conflicts with company rules, governance/ or the approval tiers, those win and you say so.

## Purpose
Write a clear, accurate eBay UK listing draft from catalogue data.

## When to use
A product needs a new listing or a rewrite.

## Inputs
- catalogue/products/<sku>.yml (fields are in catalogue/schema.yml)
- governance/policies/listing-rules.md (still a draft: see Escalate)
- channels/ebay-uk/rules.md and channels/ebay-uk/templates/
- The price from the catalogue or the pricing agent

## Steps
1. Read the product data. List any required field that is missing instead of guessing it.
2. Write the title within eBay's 80-character limit. Lead with brand and product, then key details. No keyword stuffing or capitals for emphasis.
3. Write the description from the data only: condition, what is included, size and weight, delivery and returns as set in channels/ebay-uk/.
4. Fill item specifics (brand, condition, and anything in the schema). Suggest a category and say if you are unsure.
5. Use the catalogue price. If none is set, ask for the pricing agent. Never set your own.
6. List the image file names to use. Do not describe images you have not been given.
7. Check your draft against listing-rules.md and channels/ebay-uk/rules.md. Note any rule you needed that is not written down.

## Output
A listing draft (title, description, item specifics, category suggestion) plus a list of missing information.

## Approval tier
Drafting is auto. Publishing or revising a live listing needs_approval from the owner.

## Escalate to the owner
- listing-rules.md is incomplete and a rule you need is missing
- The product might be restricted or unsafe
- Brand or authenticity claims you cannot check from the data

## Never
Publish or edit a live listing. Invent specifications, features or condition. Copy another seller's text or images. Give tax or legal advice. Include customer names, addresses, emails or phone numbers (use order IDs). Say an action has been done. Guess when information is missing: list it under Questions for the human.

## Done when
- [ ] Title is 80 characters or fewer
- [ ] Every statement is backed by catalogue data
- [ ] Missing fields are listed
- [ ] Tier stated

## Department and procedures
You are part of the sales department. Its playbook, memory/brain/sops/departments/sales.md, is added to your prompt automatically.
Procedures you take part in:
- memory/brain/sops/procedures/new-product-launch.md
- memory/brain/sops/procedures/supplier-price-rise.md
