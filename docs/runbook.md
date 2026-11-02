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

## AI spend cap and alerts
- governance/budgets.yml sets total_monthly_cap (GBP) and a cap per agent. A call that could take spend past a cap is never sent.
- At alert_at_percent (80) the dashboard shows a warning and the Budget alert workflow opens a GitHub issue. At the cap it opens a STOPPED issue.
- The cap resets on the first of each month. To continue sooner, raise total_monthly_cap by pull request.
- View the dashboard: python3 scripts/build_dashboard.py, then python3 -m http.server 8000 --directory dashboard.
- The caps use estimated prices in models/costs.yml. Also set a monthly spend limit in the Anthropic Console as the independent backstop.

## Tech Support (monitor, diagnose, fix, verify)
1. python3 scripts/techsupport.py detect   runs the health checks and raises an incident for each failing one.
2. python3 scripts/techsupport.py run INC-...   Claude diagnoses, the fix is tested in a scratch copy, applied on a branch fix/inc-..., and checked again in your working tree.
   Free route: add --manual, paste the prepared prompt into Claude, save the reply in inbox/, then ingest, test and implement (the command prints them).
3. You are told FIX READY. Push the branch, open and merge the pull request, then: git checkout main && git pull && python3 scripts/techsupport.py resolve INC-...
Tech Support only changes scripts/, tests/, docs/, dashboard/ and agent briefs. Fixes to governance, models, workflows, permissions and the safety scripts are
proposals; they are applied only if you run implement with --include-owner-files. It never pushes or merges. The dashboard page Tech Support shows every incident.
The Monitor workflow runs the same checks daily and opens a GitHub issue if one fails.

## SOPs and the brain
Every agent has a SOP in memory/brain/sops/<agent>.md. scripts/run_agent.py adds that SOP, plus up to two related notes found by keyword search in memory/brain/, to every prompt.
Search by hand: python3 scripts/brain_search.py "your question" [--agent listings]. Add or change a SOP by pull request; the tests check every agent has one with the standard headings.
The SOP never overrides company rules, governance/ or the approval tiers. Add supplier notes, decisions and lessons as markdown under memory/brain/ (no customer personal data).
