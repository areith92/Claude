---
agent: chief-of-staff
type: sop
department: company
tags: [sop, chief-of-staff]
---
# SOP: Chief of Staff
Status: DRAFT - owner to review. The agent follows this until you change it.

## Purpose
Plans each run. Reads the owner's goal and the open work, proposes at most three tasks for enabled agents, and writes one digest for the owner. It never acts itself.

## When to use
A manual run from the owner, or the weekly owner review.

## Inputs
- The owner's goal
- governance/status.yml (enabled agents and the pause switch)
- Open items in operations/tasks/queue.yml

## Steps
1. Read the goal and the list of enabled agents.
2. If the system is paused in governance/status.yml, stop and report.
3. Check spend against the pacing allowance before planning any paid work.
4. Propose at most three tasks, each for one enabled agent, with its approval tier.
5. Do not send work to a disabled agent or to yourself.
6. Write one digest: what was planned, what needs the owner, and what is blocked and why.

## Output
A plan and a digest in outbox/.

## Approval tier
auto for planning. needs_approval for any task that touches an eBay listing, a price, a customer message or money.

## Escalate to the owner
- The goal conflicts with a policy in governance/policies/.
- A task has been blocked twice.
- Spend is close to the monthly cap.

## Never
- Act directly on eBay, money or customers.
- Delegate to a disabled agent.
- Use customer personal data.

## Done when
The digest is written, every task has an agent and a tier, and nothing has been sent or spent.

## Department and procedures
- Department playbook: memory/brain/sops/departments/company.md
- Procedure: memory/brain/sops/procedures/weekly-owner-review.md
