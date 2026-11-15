---
agent: tech-support
type: sop
department: tech-support
tags: [sop, tech-support]
---
# SOP: Tech Support
Status: DRAFT - owner to review. The agent follows this until you change it.

## Purpose
Takes problems from the monitoring checks, finds and tests a fix, and opens a pull request. Low-risk fixes merge automatically once the tests pass in GitHub. Owner-only files wait for the owner.

## When to use
A monitoring check fails and raises an incident.

## Inputs
- The incident in operations/incidents/
- The failing check output
- The files it names

## Steps
1. Read the incident and the failing check output.
2. Find the root cause from the evidence. Write one diagnosis.
3. Propose the smallest fix as exact file changes, at most four files, through scripts/techsupport.py.
4. Test the fix with python3 scripts/techsupport.py test INC-... in a scratch copy.
5. If the test passes, the fix is pushed as a tech-support/ branch with a pull request. Owner-only files are not pushed; the owner decides.
6. If two attempts fail, stop and escalate with the evidence.

## Output
A diagnosis and the proposed changes in outbox/, plus a branch for the owner.

## Approval tier
auto for diagnosis and tests. needs_approval for any change to governance, models, CODEOWNERS or the safety scripts.

## Escalate to the owner
- Two failed fixes.
- A change to a safety script.
- A problem that involves customer data (follow sops/procedures/data-breach.md).

## Never
- Push to main, or merge a change to an owner-only file.
- Touch secrets.
- Change a safety rule without approval.

## Done when
The fix passes the test in a scratch copy, or the incident is escalated with the evidence.

## Department and procedures
- Department playbook: memory/brain/sops/departments/tech-support.md
- Procedure: memory/brain/sops/procedures/data-breach.md
