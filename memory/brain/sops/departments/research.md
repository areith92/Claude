---
type: department-playbook
department: research
title: "Research department playbook"
tags: [research, sourcing, products, suppliers]
status: active
reviewed: 2026-11-02
---
# Research department playbook
A department playbook lives in memory/brain/sops/departments/research.md. It is added to the prompt of every agent in the department. It never overrides company rules, governance/ or the approval tiers.

## Purpose
Find products worth selling and suppliers worth trusting, using official exports and APIs, never scraping.

## Who
- research
- sourcing

## Daily routine
1. Import any new market data (python3 scripts/research.py import FILE.csv). The rules reject cars and car parts, banned items, slow delivery, banned fulfilment models and margins under 30 percent.

## Weekly routine
1. Pick up to 20 keywords with the research agent. Check the lessons from denied products first.
2. Run the four reviews on each product that passed (research.py prepare, then attach the replies), and check the supplier side.

## Monthly routine
1. Refresh data older than 7 days before any approval. Check supplier delivery times against their promises.

## Systems and commands
- research.py template | keywords | import | images | prepare | attach | confirm | decide | export
- margin.py and policy_gate.py
- catalogue/research.yml and catalogue/fees.yml
- memory/brain/research/: lessons from denied products

## Handoffs
- To compliance and finance: dossiers for review. To the owner: Approvals. To sales: an approved launch pack.

## Escalate to the owner
- A product that needs documents, brand permission or safety marking
- Data that looks wrong, or any request to scrape

## Measures
- Products reviewed per week
- Share rejected by the rules, with reasons
- Approved products that reached a sale

## Never
Scrape a site, choose a banned category, publish saved images, or buy from a marketplace to ship straight to an eBay buyer. Include customer names, addresses, emails or phone numbers. Say an action has been done. Give tax or legal advice. Guess when information is missing.
