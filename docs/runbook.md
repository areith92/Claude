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

## Orchestrator (free mode)
1. python scripts/orchestrate.py plan --goal "Draft the first three listings"
   Paste the prompt from outbox/ into Claude and save the reply in inbox/ with the same file name.
2. python scripts/orchestrate.py ingest inbox/<that file> --delegate
   Paste each new outbox/ prompt into the AI it names and save each reply in inbox/ with the same file name.
3. python scripts/orchestrate.py review   (optional second look; paste, save the reply in inbox/)
4. python scripts/orchestrate.py digest   then read the newest file in reports/digests/
5. python scripts/orchestrate.py decide T-YYYYMMDD-001 approved --reason "why"
   Approved work is done by hand. Then: python scripts/orchestrate.py complete T-YYYYMMDD-001
6. Commit on a branch and open a pull request. Merging records your sign-off.
python scripts/orchestrate.py status shows the queue at any time. The Kill switch workflow stops everything.
