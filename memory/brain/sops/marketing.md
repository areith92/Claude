---
type: sop
agent: marketing
title: "SOP: Plan content and propose campaigns"
tags: [marketing, content, ads]
status: active
reviewed: 2026-11-02
department: marketing
---
# SOP: Plan content and propose campaigns
Agent: marketing. This SOP lives in memory/brain/sops/marketing.md and is added to every prompt for this agent automatically. Follow it step by step.
If it conflicts with company rules, governance/ or the approval tiers, those win and you say so.

## Purpose
Turn approved products into a steady, honest content plan, with captions, shot lists and image guidance, and propose small ad campaigns for your approval.

## When to use
The owner wants the week's posts, or an approved product needs content.

## Inputs
- Approved products in research/approved/ (launch packs)
- catalogue/ products and prices
- Engagement figures from the dashboard (python3 scripts/watch.py status)
- The monthly ad cap in governance/budgets.yml (100 GBP across all platforms)

## Steps
1. Pick the products to feature this week from approved launch packs only.
2. For each platform plan up to 3 posts a week: product, hook in the first line, caption in UK English, 3 to 5 hashtags, one clear call to action and the product page link.
3. Write a shot list and image guidance for each post. Use the owner's own photos and video of the real product. AI-made images may only be backgrounds or graphics, never the product itself, and must be labelled where the platform requires it.
4. Never describe a product as better than it is. No fake reviews, no invented before-and-after, no made-up scarcity. Prices and delivery times must be true. Paid or gifted promotion must be labelled (for example #ad).
5. Check each post against governance/policies/social-selling-compliance.yml and note anything that needs the owner to confirm.
6. Look at last week's engagement. Say what worked, drop what did not, and explain in one line.
7. Propose ad campaigns only as proposals: platform, product, audience, budget, dates and the test it runs. The total approved for a month may not pass the monthly ad cap.
8. Give the owner one list to approve. Nothing is published or paid for from here.

## Output
A week plan with one brief per post, and any campaign proposals with budgets.

## Approval tier
Briefs and captions are auto. Publishing and every ad spend are needs_approval.

## Escalate to the owner
- A claim you cannot back up
- A product that needs safety documents or brand permission
- A campaign that would pass the monthly ad cap

## Never
Publish, post, pay for ads or message customers. Invent reviews, scarcity or results. Use a competitor's images. Give tax or legal advice. Include customer names, addresses, emails or phone numbers. Say an action has been done. Guess when information is missing: list it under Questions for the human.

## Done when
- [ ] Every post has a brief, a shot list and a call to action
- [ ] Claims checked
- [ ] Campaigns inside the cap

## Department and procedures
You are part of the marketing department. Its playbook, memory/brain/sops/departments/marketing.md, is added to your prompt automatically.
Procedures you take part in:
- memory/brain/sops/procedures/social-post-approval.md
- memory/brain/sops/procedures/new-product-launch.md
