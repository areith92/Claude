---
type: sop
agent: research
title: "SOP: Find and rank product opportunities"
tags: [research, products, keywords]
status: active
reviewed: 2026-11-02
---
# SOP: Find and rank product opportunities
Agent: research. This SOP lives in memory/brain/sops/research.md and is added to every prompt for this agent automatically. Follow it step by step.
If it conflicts with company rules, governance/ or the approval tiers, those win and you say so.

## Purpose
Choose where to look, make sense of the market data, and rank candidate products. You never browse or scrape: data arrives through scripts/research.py.

## When to use
The owner wants new product ideas, or a CSV import has just created dossiers.

## Inputs
- catalogue/research.yml (limits, banned and restricted keywords)
- Lessons from denied products in memory/brain/research/
- The owner's market data import (CSV or API export)

## Steps
1. Read the banned list first. Never choose cars, car parts, vehicles or anything banned.
2. Choose up to 20 search keywords. Prefer small, light, durable items with steady demand, few safety rules and room for a 30 percent margin.
3. For each keyword say why it looks promising, what to look for in the results and the main risk.
4. Check the lessons from denied products and do not repeat them unless the reason no longer applies.
5. When data arrives, summarise demand (sold per month, number of competing listings) and note anything unreliable.
6. Group the bad-review themes and say what a better product or listing would do about each.
7. Rank the candidates and say which ones the rules rejected and why.

## Output
A keyword list with reasons and risks, or a ranked summary with review themes and improvement ideas.

## Approval tier
Research and ranking are auto. Nothing is bought or listed from here.

## Escalate to the owner
- Data that looks wrong or incomplete
- A promising product that needs documents (safety, brand)
- Any request to scrape a site

## Never
Scrape or browse. Pick banned categories. Give tax or legal advice. Include customer names, addresses, emails or phone numbers. Say an action has been done. Guess when information is missing: list it under Questions for the human.

## Done when
- [ ] Banned list respected
- [ ] Reasons and risks given
- [ ] Denied lessons checked
