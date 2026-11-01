# AI commerce business (eBay UK)

A private repo that runs a UK-only eBay business with AI agents, under human approval.
The repo is the company: agents propose work through files and pull requests, the owner approves.

## Free mode (default)
`governance/status.yml` has `provider: manual`. In this mode nothing calls a paid API:

1. Run `python scripts/run_agent.py --agent listings --task "Draft a listing for SKU-001"`
2. The script writes a ready-to-paste prompt to `outbox/`.
3. Paste it into claude.ai or Google AI Studio (the file says which), then save the reply in `inbox/` with the same file name.
4. Review the result in a pull request. Nothing goes live without you.

## Upgrading later
Switch one agent at a time to API mode (see `docs/runbook.md`): add the API key as a GitHub Secret,
set the AI cost caps in `governance/budgets.yml`, fill in `models/costs.yml`, then set the agent's `provider: api`.

## Layout
`governance/` rules and budgets (owner only) | `agents/` one folder per agent | `models/` model routing and costs |
`memory/` GBrain notes | `catalogue/` master product data | `channels/` eBay now, Shopify later |
`logs/` actions and costs | `reports/` | `scripts/` | `tests/` | `docs/`

## Rules that never change
No secrets in the repo. No customer personal data in the repo, logs or memory. Agents propose, humans approve.
