---
type: index
title: SOP index
tags: [sops, index]
---
# SOPs (standard operating procedures)
One SOP per agent. They live in memory/brain/ so every agent and person finds instructions in one place.
scripts/run_agent.py adds the agent's own SOP, plus up to two related notes found by keyword search, to every prompt. Search by hand with:
python3 scripts/brain_search.py "your question" --agent listings

| Agent | SOP | Status |
|---|---|---|
| orchestrator | Plan, delegate, review, digest | active |
| listings | Draft an eBay UK listing | active |
| orders | Review new orders and shipping | active |
| messages | Triage buyer messages and draft replies | active |
| finance | Reconcile and prepare the accountant pack | active |
| compliance | Check a proposal against the rules | active |
| reviewer | Independent second opinion | active |
| monitor | Watch spend, health and errors | active |
| pricing | Propose a price change | ready (agent disabled) |
| inventory | Track stock and propose reorders | ready (agent disabled) |
| returns | Handle a return or dispute | ready (agent disabled) |
| analytics | Margin per product and dashboard data | ready (agent disabled) |
| techsupport | Diagnose and fix a failing check | active |
| research | Find and rank product opportunities | active |
| sourcing | Check suppliers and fulfilment model | active |

## Changing a SOP
Edit the file and open a pull request. The tests check that every agent in governance/status.yml has a SOP with these headings:
Purpose, When to use, Inputs, Steps, Output, Approval tier, Escalate to the owner, Never, Done when.
A SOP never overrides company rules, governance/ or the approval tiers. Policies in governance/policies/ that are still drafts are not filled in by SOPs: the agent asks.
No customer personal data in any note.

## GBrain
These are plain markdown files. GBrain can be pointed at memory/brain/ later; nothing here depends on it.
