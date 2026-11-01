# Runbook
## Run an agent (free mode)
python scripts/run_agent.py --agent listings --task "Draft a listing for SKU-001"
Paste outbox/<file> into the AI named in it, save the reply to inbox/<same name>, commit on a branch, open a PR.

## Switch one agent to the API
1. Add the key as a GitHub Secret (ANTHROPIC_API_KEY or GEMINI_API_KEY).
2. Fill in the rates in models/costs.yml and set caps in governance/budgets.yml.
3. In governance/status.yml set provider: api for that agent only.
4. Keep dry_run: true. Check logs/costs.csv after each run.

## Stop everything
Actions > Kill switch > Run workflow (pause = true).

## Monthly
python scripts/new_accountant_pack.py and fill in the checklist.
