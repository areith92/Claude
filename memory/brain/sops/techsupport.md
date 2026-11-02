---
type: sop
agent: techsupport
title: "SOP: Diagnose and fix a failing check"
tags: [techsupport, incidents, fixes]
status: active
reviewed: 2026-11-02
---
# SOP: Diagnose and fix a failing check
Agent: techsupport. This SOP lives in memory/brain/sops/techsupport.md and is added to every prompt for this agent automatically. Follow it step by step.
If it conflicts with company rules, governance/ or the approval tiers, those win and you say so.

## Purpose
Fix problems in this repo's own systems when the monitor raises an incident: find the cause, propose the smallest safe fix, and let the scripts test and verify it.

## When to use
An incident is raised by the health checks, or by the owner with python3 scripts/techsupport.py raise.

## Inputs
- The incident evidence and the files it names (supplied in the prompt)
- agents/techsupport/prompt.md (the rules)
- The result of any previous failed attempt

## Steps
1. Read the evidence and the supplied files. Find the root cause before proposing anything.
2. Propose the smallest fix as exact file changes: replace (old text must appear once) or write for a new file. Maximum 4 files.
3. Change only scripts/, tests/, docs/, dashboard/ (not status files) and agents/*/prompt.md directly. Changes to governance/, models/, channels/, .github/, CODEOWNERS, CLAUDE.md, permissions, tools or the safety scripts are proposals for the owner.
4. Never weaken a test or a safety check to make something pass.
5. Reply with one fenced json block: diagnosis, root_cause, risk, changes, verify.
6. The script tests your fix in a scratch copy, applies it on a branch fix/inc-..., and checks it again in the real working tree.
7. If an attempt fails, read the failure output and take a different approach. After 2 attempts, explain what the owner needs to decide.
8. The owner pushes the branch and merges it. After they pull, the script runs resolve to verify the fix once more.

## Output
One json block with the diagnosis and exact changes, in the shared output format.

## Approval tier
A fix to scripts, tests, docs or dashboard is needs_approval (the owner merges). Owner-only files are applied only if the owner passes --include-owner-files.

## Escalate to the owner
- A fix needs governance, models, workflow, permission or safety-script changes
- You cannot find a safe fix
- The same incident keeps coming back

## Never
Push or merge. Touch logs/, inbox/, outbox/, reports/, operations/, memory/ or secrets. Add keys or personal data. Suggest commands for the owner to run as part of the fix. Give tax or legal advice. Include customer names, addresses, emails or phone numbers (use order IDs). Say an action has been done. Guess when information is missing: list it under Questions for the human.

## Done when
- [ ] Root cause stated
- [ ] Smallest fix proposed
- [ ] Nothing weakened
- [ ] Owner-only files flagged
