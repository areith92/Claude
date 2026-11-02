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

## Department playbooks
One playbook per department in memory/brain/sops/departments/: the daily, weekly and monthly routine, the commands to use, handoffs, escalation and measures. scripts/run_agent.py adds an agent's department playbook to its prompt.
- company: Company routine: the owner and the orchestrator
- sales: Sales department playbook
- operations: Operations department playbook
- customer-care: Customer care department playbook
- finance: Finance department playbook
- compliance: Compliance department playbook
- monitoring: Monitoring department playbook
- tech-support: Tech support department playbook
- research: Research department playbook
- marketing: Marketing department playbook

## Procedures across departments
Step-by-step procedures in memory/brain/sops/procedures/. Agents and people follow them when the trigger happens.
- new-product-launch: New product launch
- order-to-delivery: Order to delivery
- late-parcel: Late or missing parcel
- supplier-price-rise: Supplier price rise
- return-and-refund: Return and refund
- complaint-or-safety-incident: Complaint or safety incident
- customer-data-request: Customer data request
- data-breach: Data breach
- month-end-close: Month-end close
- weekly-owner-review: Weekly owner review
- social-post-approval: Social post approval

## Changing a SOP
Edit the file and open a pull request. The tests check that every agent in governance/status.yml has a SOP with these headings:
Purpose, When to use, Inputs, Steps, Output, Approval tier, Escalate to the owner, Never, Done when.
A SOP never overrides company rules, governance/ or the approval tiers. Policies in governance/policies/ that are still drafts are not filled in by SOPs: the agent asks.
No customer personal data in any note.

## GBrain
These are plain markdown files. GBrain can be pointed at memory/brain/ later; nothing here depends on it.
