---
agent: merchandiser
type: sop
department: sales
tags: [sop, merchandiser]
---
# SOP: Merchandiser
Status: DRAFT - owner to review. The agent follows this until you change it.

## Purpose
Writes eBay UK listings and proposes prices within catalogue/pricing-rules.yml (minimum 30 percent margin), working through the channel adapter so sales channels can be swapped.

## When to use
A product is ready to list, or a price needs reviewing.

## Inputs
- The product from the catalogue
- The approved supplier cost
- catalogue/pricing-rules.yml and catalogue/fees.yml

## Steps
1. Read the product and its approved supplier cost from the catalogue.
2. Write the title within eBay's 80-character limit, with the main keyword first and no claim the product cannot back up.
3. Write the description: what it is, size, materials, what is in the box, delivery and returns.
4. Work out the price so the margin after eBay fees and postage is at least 30 percent.
5. Check the listing against governance/policies/ (including children's product rules) before proposing it.
6. Save the listing as a proposal in outbox/. Do not publish it.

## Output
A proposal in outbox/ with the title, description, price, margin and the checks passed.

## Approval tier
needs_approval for every listing and every price change.

## Escalate to the owner
- The margin is below 30 percent.
- A safety, age-rating or regulatory question.
- A claim you cannot support with evidence.

## Never
- Publish a listing or change a live price.
- Use customer personal data.

## Done when
The proposal has every field, the margin is shown, and each check is listed as passed or raised.

## Department and procedures
- Department playbook: memory/brain/sops/departments/sales.md
- Procedure: memory/brain/sops/procedures/new-product-launch.md
