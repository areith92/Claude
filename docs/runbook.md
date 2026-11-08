# Runbook
## Run an agent (free mode)
python scripts/run_agent.py --agent sourcing --task "Scan 20 products for <keywords>"
Open the model named in outbox/<file> on claude.ai, paste it, save the reply to inbox/<same name>, commit on a branch, open a PR.
To use a stronger model for one run: add --tier opus (only allowed where models/routing.yml lists an escalate tier).

## Switch one agent to the API
1. Add ANTHROPIC_API_KEY as a GitHub Secret (and as a Codespaces secret if you run it there).
2. Fill in the rates in models/costs.yml. Check the AI caps in governance/budgets.yml.
3. In governance/status.yml set provider: api for that agent only. Keep dry_run: true.
4. Check logs/costs.csv after each run. Paid runs are refused once a cap is reached.

## Stop everything
Actions > Kill switch > Run workflow (pause = true).

## Watch for problems
The Monitor workflow runs daily and opens an issue if a check fails. Tech Support picks the issue up.

## Monthly
python scripts/new_accountant_pack.py and fill in the checklist.
