#!/usr/bin/env bash
# AI commerce business (eBay UK) - repo bootstrap. Ten Claude-powered agents, free-first.
#   New empty repo:                  bash bootstrap.sh            (username defaults to areith92)
#   Repo made with the earlier       bash bootstrap.sh --migrate
#   bootstrap (renames the agents, backs up everything it replaces in .migration-backup/)
# Run from the ROOT of the repo.
set -euo pipefail

MIGRATE=0
if [ "${1:-}" = "--migrate" ]; then MIGRATE=1; shift; fi
GH_USER="${1:-areith92}"

generate() {
mkdir -p .github/workflows .github/ISSUE_TEMPLATE governance/policies governance/pipelines \
  agents/_shared agents/_future models memory/brain/sops memory/ingest \
  catalogue/products catalogue/suppliers catalogue/categories \
  channels/_shared channels/ebay-uk/templates channels/ebay-uk/business-policies channels/shopify channels/social/playbooks \
  integrations operations/sops logs/actions logs/decisions logs/audits \
  reports/weekly reports/monthly reports/accountant-pack outbox inbox \
  dashboard tests/evals tests/simulations tests/fixtures scripts docs/decisions

# ---------------------------------------------------------------- root files

cat > README.md <<'EOF'
# AI commerce business (eBay UK)

A private repo that runs a UK-only eBay business with ten Claude-powered agents, under human approval.
The repo is the company: agents propose work in files and pull requests, the owner approves.

## The team (full detail in docs/roster.md)
- Product research pipeline: Sourcing, Merchandiser, Finance and Insights, Compliance, Reviewer, then your Approve or Deny.
- Operations: Fulfilment, Customer Care, Marketing, Tech Support.
- Chief of Staff plans each run and writes the single digest.

## Free mode (default)
`governance/status.yml` has `provider: manual`, so nothing calls a paid API:

1. Run `python scripts/run_agent.py --agent sourcing --task "Scan 20 products for the keywords ..."`
2. A ready-to-paste prompt is written to `outbox/`, with the Claude model to pick (Haiku, Sonnet or Opus).
3. Paste it into claude.ai, then save the reply in `inbox/` with the same file name.
4. Review it in a pull request. Nothing goes live without you.

## Upgrading later
See `docs/runbook.md`: add ANTHROPIC_API_KEY as a GitHub Secret, fill in `models/costs.yml`, then set `provider: api` for one agent at a time.
The AI cost caps in `governance/budgets.yml` are enforced before every paid call.

## Rules that never change
No secrets in the repo. No customer personal data in the repo, logs, memory or prompts. Agents propose, humans approve.
EOF

cat > CLAUDE.md <<'EOF'
# Instructions for Claude in this repo
- Read governance/policies/, agents/_shared/company-rules.md and your own SOP (memory/brain/sops/<agent>.md) before doing any work.
- Never edit: governance/, CODEOWNERS, .github/, agents/*/permissions.yml. Propose changes in a pull request instead.
- Never write secrets, API keys, customer names, addresses, emails or phone numbers anywhere in the repo.
- Work in proposals: write to outbox/, inbox/ or logs/actions/. Do not perform live actions.
- Respect governance/status.yml: if paused is true, stop. Stay inside dry-run unless the file says otherwise.
- Check governance/approval-tiers.yml and say which tier each proposal falls under.
- Use UK English and GBP. Do not give tax or legal advice; flag questions for the accountant.
EOF

cat > CODEOWNERS <<EOF
# Enforced only when branch protection with "Require review from Code Owners" is on
# (free on public repos; GitHub Pro or Team for private repos).
/governance/            @${GH_USER}
/agents/*/permissions.yml @${GH_USER}
/.github/               @${GH_USER}
/models/                @${GH_USER}
/channels/*/config.yml  @${GH_USER}
/CODEOWNERS             @${GH_USER}
EOF

cat > SECURITY.md <<'EOF'
# Security
- Secrets live in GitHub Settings > Secrets and variables > Actions. Never in files, issues or PRs.
- If a key is ever committed: revoke it at the provider first, then clean the repo.
- Emergency stop: run the "Kill switch" workflow (sets paused: true in governance/status.yml).
- No customer personal data in the repo, logs, memory or AI prompts.
EOF

cat > .env.example <<'EOF'
# Names only. Put real values in GitHub Secrets, never in the repo.
ANTHROPIC_API_KEY=
EBAY_CLIENT_ID=
EBAY_CLIENT_SECRET=
EBAY_REFRESH_TOKEN=
SHOPIFY_STORE_DOMAIN=
SHOPIFY_ADMIN_TOKEN=
EOF

cat > .gitignore <<'EOF'
.env
.env.*
!.env.example
__pycache__/
*.pyc
.DS_Store
.venv/
.migration-backup/
EOF

# ---------------------------------------------------------------- governance

cat > governance/status.yml <<'EOF'
paused: false              # true stops every agent run (use the Kill switch workflow)
provider: manual           # manual = free copy/paste mode | api = call the Claude API
default_dry_run: true      # agents only propose; no live actions exist in this version
agents:
  # Stage 1: the product research pipeline plus tech support
  chief-of-staff:   {enabled: true,  dry_run: true}
  sourcing:         {enabled: true,  dry_run: true}
  merchandiser:     {enabled: true,  dry_run: true}
  finance-insights: {enabled: true,  dry_run: true}
  compliance:       {enabled: true,  dry_run: true}
  reviewer:         {enabled: true,  dry_run: true}
  tech-support:     {enabled: true,  dry_run: true}
  # Stage 2: switch on once you are selling
  fulfilment:       {enabled: false, dry_run: true}
  customer-care:    {enabled: false, dry_run: true}
  marketing:        {enabled: false, dry_run: true}
# To move one agent to the API later, add:  provider: api   (inside its braces)
EOF

cat > governance/budgets.yml <<'EOF'
currency: GBP
ai_costs:                  # per-agent caps must add up to no more than the total
  total_monthly_cap: 5
  per_agent_monthly_cap:
    chief-of-staff: 0.80
    sourcing: 1.00
    merchandiser: 0.60
    fulfilment: 0.40
    customer-care: 0.50
    marketing: 0.50
    finance-insights: 0.40
    compliance: 0.30
    reviewer: 0.30
    tech-support: 0.20
spend:                     # real-money limits that need your approval to use
  promoted_listings_monthly_cap: 0
  stock_purchases_monthly_cap: 0
  social_ads_monthly_cap: 100
  other_monthly_cap: 0
EOF

cat > governance/approval-tiers.yml <<'EOF'
# Starter values. Change them to suit you.
tiers:
  auto:
    approval: none
    examples: [orders to approved suppliers inside the stock budget, draft listing text, triage a message, reconcile fees, internal reports]
  needs_approval:
    approval: owner
    examples: [publish or revise a listing, price change over threshold, new supplier, refund over threshold, promoted listings spend, social ad spend, publishing social posts]
  needs_owner_and_accountant:
    approval: owner and accountant
    examples: [VAT or tax treatment, new sales channel, change to bookkeeping categories]
  never:
    approval: not allowed
    examples: [move money, change governance, change agent permissions, store customer personal data, message buyers outside eBay]
thresholds:
  price_change_pct: 5
  refund_gbp: 20
  single_spend_gbp: 25
EOF

cat > governance/approvers.yml <<EOF
owner: ${GH_USER}
accountant: ""             # GitHub username if they have one; otherwise record their OK as a PR comment
EOF

cat > governance/risk-register.md <<'EOF'
# Risk register
| Risk | Likelihood | Impact | Control |
|---|---|---|---|
| Agent publishes a wrong or non-compliant listing | Medium | Medium | Dry-run, Compliance and Reviewer agents, owner approval |
| Runaway AI cost | Low | Medium | Caps in budgets.yml, cost log, check_budget.py |
| Customer data leaks into prompts or the repo | Medium | High | pii_guard.py, memory-policy.md, no personal data in logs |
| eBay account action from bad automation | Low | High | Official APIs only, no scraping, human approval for live actions |
| Wrong VAT or tax handling | Medium | High | Accountant sign-off tier |
EOF

for p in pricing refunds listing-rules vat-and-tax data-protection; do
cat > governance/policies/$p.md <<EOF
# Policy: $p
Status: DRAFT - owner to complete. Agents must follow this file once filled in.

## Rules
- (add your rules here)

## Needs human approval
- (list what must be approved)
EOF
done
cat >> governance/policies/vat-and-tax.md <<'EOF'

## Note
Agents never give tax advice. They prepare data and flag questions for the accountant.
EOF
cat >> governance/policies/data-protection.md <<'EOF'

## Note
No customer names, addresses, emails or phone numbers in this repo, in logs, in memory or in AI prompts.
Check with your accountant or the ICO whether you need to register as a data controller.
EOF

cat > governance/pipelines/product-research.yml <<'EOF'
name: product-research
cadence: manual at first (weekly once trusted)
stages:
  - agent: sourcing
    task: Scan about 20 eBay UK products on keywords you choose (never cars or car parts). For each, find the wholesale or manufacturer item cost, shipping cost and delivery time from suppliers you have an agreement with, or from stock you hold. Never a retailer or marketplace shipping straight to the buyer (eBay forbids it).
  - agent: merchandiser
    task: Propose an eBay UK price and draft a listing for each product that passes the delivery rule.
  - agent: finance-insights
    task: Work out profit after eBay fees, postage and item cost. Reject anything under the minimum margin.
  - agent: compliance
    task: Check each remaining product against eBay rules, UK consumer-law notes and company policy.
  - agent: reviewer
    task: Give an independent second opinion on what is left.
  - approval: owner
    via: Approve or Deny on the dashboard (a pull request until the dashboard exists)
rules:
  max_products_per_run: 20
  excluded_categories: [cars, car parts]
  min_margin_pct: 30
  max_delivery_days: 5
  approved_suppliers_skip_approval: true
EOF
# ---------------------------------------------------------------- agents

cat > agents/_shared/company-rules.md <<'EOF'
# Company rules for every agent
- You are part of a small UK-only eBay business. Currency is GBP. Use UK English.
- You propose; humans approve. Never claim an action has been performed.
- Follow governance/policies/ and governance/approval-tiers.yml. State which approval tier your proposal falls under.
- Never include customer personal data (names, addresses, emails, phone numbers). Refer to orders by order ID only.
- Do not give tax or legal advice. Flag it for the accountant.
- If information is missing, say what is missing instead of guessing.
EOF

cat > agents/_shared/output-schema.md <<'EOF'
# Output format
Reply with:
1. Summary (two sentences).
2. Proposal (what you suggest, with numbers where relevant).
3. Approval tier (auto / needs_approval / needs_owner_and_accountant).
4. Risks and assumptions.
5. Questions for the human (if any).
EOF

mkagent() {  # name | title | model tier | what it does
  local name="$1" title="$2" tier="$3" does="$4"
  mkdir -p "agents/$name/evals"
  : > "agents/$name/evals/.gitkeep"
  cat > "agents/$name/prompt.md" <<EOF
# Agent: $title
Model tier: $tier (see models/routing.yml)

## Role
$does

## Before you start
Read your SOP at memory/brain/sops/$name.md and follow it. If it is missing or still a draft, say so.

## Boundaries
- Propose only. No live actions.
- Stay inside governance/policies/ and the budgets in governance/budgets.yml.
- No customer personal data.
EOF
  cat > "agents/$name/permissions.yml" <<EOF
agent: $name
can_read: [catalogue/, governance/policies/, memory/brain/, logs/, reports/]
can_propose: [outbox/, logs/actions/]
cannot: [governance/, agents/, CODEOWNERS, .github/, secrets, customer personal data]
execute_live_actions: false
EOF
  cat > "agents/$name/tools.yml" <<EOF
# Tools this agent may use. Live API tools are added later, one at a time, by pull request.
tools: [read_repo_files, write_proposal]
future_tools: []
EOF
  cat > "memory/brain/sops/$name.md" <<EOF
# SOP: $title
Status: DRAFT - owner to complete. The $name agent reads this before every run.

## Purpose
$does

## Steps
1. (write the steps this agent follows each run)

## Inputs and outputs
- Inputs: (what it needs)
- Outputs: proposals in outbox/, inbox/ or logs/actions/

## Escalate to the owner when
- (list the cases)

## Never
- Act without approval, or use customer personal data.
EOF
}

mkagent chief-of-staff "Chief of Staff" sonnet "Plans each run (max 3 delegated tasks), produces the single digest and approval queue, and keeps the SOP library in memory/brain/sops up to date."
mkagent sourcing "Sourcing" haiku "Scans about 20 eBay UK products on keywords it chooses (never cars or car parts), then finds wholesale or manufacturer cost, shipping cost and delivery time (within 5 days) from suppliers you have an agreement with, or from stock you hold, and maintains catalogue/suppliers/approved-suppliers.yml. Never proposes buying from a retailer or marketplace (such as AliExpress or Amazon) and shipping straight to the buyer, which eBay does not allow."
mkagent merchandiser "Merchandiser" haiku "Writes eBay UK listings and proposes prices within catalogue/pricing-rules.yml (minimum 30 percent margin), working through the channel adapter so sales channels can be swapped."
mkagent finance-insights "Finance and Insights" haiku "Checks margins (minimum 30 percent), tracks spend against earnings and profit and loss, reports engagement, buyers and abandoned carts, and prepares the accountant pack. Never gives tax advice."
mkagent compliance "Compliance" sonnet "Checks proposals against eBay rules, UK consumer-law notes, advertising rules and data protection."
mkagent reviewer "Reviewer" sonnet "Gives an independent, adversarial second opinion in a fresh context before proposals reach the owner. Use the opus tier for high-risk items."
mkagent fulfilment "Fulfilment" haiku "Reviews orders by order ID, proposes supplier orders and shipping, runs the daily parcel checks and courier tracking, and flags parcels past their delivery time."
mkagent customer-care "Customer Care" haiku "Handles buyer messages from eBay and social channels, returns and disputes, using built-in replies and the refund limits. Escalates tricky cases."
mkagent marketing "Marketing" haiku "Drafts social posts and replies using one playbook per platform, plans the monthly ad budget and email follow-ups. Drafts need owner approval before publishing."
mkagent tech-support "Tech Support" opus "Takes problems flagged by the monitoring scripts, finds and tests a fix, and proposes it as a pull request. The owner decides whether to merge."

cat > agents/_future/README.md <<'EOF'
# Future agents
Not built yet. The likely first split is a platform out of Marketing (one agent per social platform) once its volume justifies it.
To add one: copy agents/merchandiser/ as a pattern, register it in governance/status.yml, models/routing.yml and governance/budgets.yml, and add a SOP in memory/brain/sops/.
EOF
cat > memory/brain/sops/README.md <<'EOF'
One SOP per agent (memory/brain/sops/<agent>.md). Agents read their SOP before each run. Fill them in as you learn how you want each job done.
EOF
# ---------------------------------------------------------------- models
cat > models/routing.yml <<'EOF'
# tier = the Claude model the agent normally uses. escalate = a stronger tier it may be switched to (run_agent.py --tier).
agents:
  chief-of-staff:   {tier: sonnet}
  sourcing:         {tier: haiku}
  merchandiser:     {tier: haiku}
  finance-insights: {tier: haiku}
  compliance:       {tier: sonnet}
  reviewer:         {tier: sonnet, escalate: opus}
  fulfilment:       {tier: haiku}
  customer-care:    {tier: haiku, escalate: sonnet}
  marketing:        {tier: haiku}
  tech-support:     {tier: opus}
models:
  haiku:
    provider: anthropic
    model: claude-haiku-5-5        # check docs.claude.com for current model names
    label: Claude Haiku 5.5
    max_tokens: 1500
    paste_into: https://claude.ai
  sonnet:
    provider: anthropic
    model: claude-sonnet-5-5
    label: Claude Sonnet 5.5
    max_tokens: 1500
    paste_into: https://claude.ai
  opus:
    provider: anthropic
    model: claude-opus-5-5
    label: Claude Opus 5.5
    max_tokens: 1500
    paste_into: https://claude.ai
EOF

cat > models/costs.yml <<'EOF'
# Fill in GBP per million tokens from the Claude pricing page BEFORE using api mode.
# A tier with rates left at 0 is refused by run_agent.py.
haiku:
  input_per_mtok_gbp: 0
  output_per_mtok_gbp: 0
sonnet:
  input_per_mtok_gbp: 0
  output_per_mtok_gbp: 0
opus:
  input_per_mtok_gbp: 0
  output_per_mtok_gbp: 0
EOF

cat > models/fallbacks.yml <<'EOF'
on_api_error: switch_agent_to_manual
on_budget_exceeded: stop_and_notify_owner
on_provider_outage: use_manual_mode
EOF

# ---------------------------------------------------------------- memory

cat > memory/README.md <<'EOF'
# Memory
`brain/` holds plain markdown notes (suppliers, decisions, lessons). It works as ordinary files now.
Connect GBrain to this folder when you are ready (check its docs for setup). Read memory/memory-policy.md first.
EOF
cat > memory/memory-policy.md <<'EOF'
# Memory policy
Allowed: supplier notes, product knowledge, pricing lessons, decisions and why they were made.
Never store: customer names, addresses, emails, phone numbers, payment details, passwords or API keys.
Refer to orders by order ID only.
EOF
: > memory/brain/.gitkeep
cat > memory/ingest/README.md <<'EOF'
Scripts that feed the brain go here (later). Every ingest script must strip personal data first.
EOF

# ---------------------------------------------------------------- catalogue

for d in products suppliers categories; do : > catalogue/$d/.gitkeep; done
cat > catalogue/schema.yml <<'EOF'
product:
  sku: string
  title: string
  description: string
  brand: string
  condition: new|used|refurbished
  cost_gbp: number
  price_gbp: number
  stock: integer
  weight_g: integer
  category: string
  supplier: string
  images: [string]
  channel_overrides: {ebay-uk: {}, shopify: {}}
EOF
cat > catalogue/pricing-rules.yml <<'EOF'
currency: GBP
min_margin_pct: 30
never_below_cost: true
round_to: 0.99
max_auto_change_pct: 5
ebay_fee_assumption_pct: 0         # fill in from your eBay fee statement
EOF

cat > catalogue/suppliers/approved-suppliers.yml <<'EOF'
# Orders to suppliers listed here need no extra approval (they still count against stock_purchases_monthly_cap).
# Add a supplier only after you have checked it yourself.
approved: []
# Example:
# - {name: Example Supplier Ltd, platform: wholesaler, max_delivery_days: 5, notes: ""}
EOF
# ---------------------------------------------------------------- channels

cat > channels/_shared/adapter-interface.md <<'EOF'
# Channel adapter interface
Agents talk to this interface, never to eBay or Shopify directly. Each channel implements:
list_products, publish_listing, update_price, update_stock, get_orders, mark_shipped, get_messages.
Adding a channel = a new folder in channels/ plus config.yml with enabled: true.
Single source of truth for products and stock is catalogue/.
EOF
cat > channels/_shared/order.schema.yml <<'EOF'
order:
  order_id: string
  channel: string
  items: [{sku: string, qty: integer, price_gbp: number}]
  status: string
  # no customer personal data is stored here
EOF
cat > channels/ebay-uk/config.yml <<'EOF'
channel: ebay-uk
enabled: true
marketplace: EBAY_GB
currency: GBP
ships_to: [GB]
api:
  mode: manual                     # manual | api (api needs an eBay developer account and OAuth tokens in GitHub Secrets)
  secrets: [EBAY_CLIENT_ID, EBAY_CLIENT_SECRET, EBAY_REFRESH_TOKEN]
EOF
cat > channels/ebay-uk/mapping.yml <<'EOF'
# Map catalogue fields to eBay listing fields
title: title
description: description
price: price_gbp
quantity: stock
condition: condition
EOF
cat > channels/ebay-uk/rules.md <<'EOF'
# eBay UK rules
Use official eBay APIs only. No scraping. Record fee assumptions and category rules here.
EOF
: > channels/ebay-uk/templates/.gitkeep
: > channels/ebay-uk/business-policies/.gitkeep
cat > channels/shopify/config.yml <<'EOF'
channel: shopify
enabled: false                     # do not enable until docs/shopify-expansion.md is complete and approved
region: GB
currency: GBP
api:
  mode: manual
  secrets: [SHOPIFY_STORE_DOMAIN, SHOPIFY_ADMIN_TOKEN]
launch_requires: [owner approval, accountant approval, checklist complete]
EOF
cat > channels/shopify/mapping.yml <<'EOF'
title: title
body_html: description
price: price_gbp
inventory_quantity: stock
EOF
cat > channels/shopify/rules.md <<'EOF'
# Shopify rules (placeholder)
Fill in when the channel is planned. See docs/shopify-expansion.md.
EOF

cat > channels/social/config.yml <<'EOF'
channel: social
enabled: false                     # switch on when the social accounts are linked and the playbooks are written
currency: GBP
platforms: []                      # add the platforms you use, one playbook each in channels/social/playbooks/
api:
  mode: manual
EOF
cat > channels/social/playbooks/README.md <<'EOF'
One playbook per platform: posting style, hashtags, reply rules and what needs approval. Marketing and Customer Care read these.
EOF
# ---------------------------------------------------------------- integrations, operations, logs, reports

cat > integrations/README.md <<'EOF'
One subfolder per external service (shipping, accounting, helpdesk, payments, suppliers). Add them when needed.
EOF
cat > operations/sops/README.md <<'EOF'
Standard operating procedures: packing, returns, escalation. Write them as short checklists.
EOF
cat > operations/incident-response.md <<'EOF'
# Incident response
1. Run the Kill switch workflow (paused: true).
2. Revoke any exposed key at the provider.
3. Open an issue using the Incident template.
4. Review logs/ to see what ran. Fix by pull request. Unpause only after review.
EOF
cat > operations/contacts.md <<'EOF'
Roles only, no personal details: owner, accountant, supplier contacts (company names only).
EOF
echo "date,agent,provider,model,input_tokens,output_tokens,cost_gbp,note" > logs/costs.csv
for d in logs/actions logs/decisions logs/audits reports/weekly reports/monthly reports/accountant-pack inbox; do : > $d/.gitkeep; done
cat > outbox/README.md <<'EOF'
Prompts prepared for you to paste into claude.ai (free mode). Save each reply in inbox/ with the same file name.
EOF
cat > dashboard/README.md <<'EOF'
Dashboard front end goes here later. It will read reports/ and logs/ (no customer data). Start with the weekly report issue.
EOF
cat > tests/evals/README.md <<'EOF'
Evals: for each agent, add input examples and what a good answer must include. Add them as you learn.
EOF
cat > tests/simulations/README.md <<'EOF'
Simulations: replay realistic scenarios (late delivery, refund request) in dry-run before enabling an agent.
EOF
echo '{"order_id": "TEST-0001", "items": [{"sku": "SKU-001", "qty": 1, "price_gbp": 9.99}], "status": "paid"}' > tests/fixtures/sample_order.json

# ---------------------------------------------------------------- scripts

cat > scripts/pii_guard.py <<'EOF'
"""Simple check that blocks obvious personal data from going into prompts."""
import re

PATTERNS = {
    "email address": re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),
    "UK phone number": re.compile(r"(?<!\d)(?:\+44\s?|0)\d{3,4}[\s-]?\d{3}[\s-]?\d{3,4}(?!\d)"),
    "UK postcode": re.compile(r"\b[A-Za-z]{1,2}\d[A-Za-z\d]?\s*\d[A-Za-z]{2}\b"),
}


def find_pii(text):
    return [name for name, rx in PATTERNS.items() if rx.search(text)]
EOF

cat > scripts/check_budget.py <<'EOF'
#!/usr/bin/env python3
"""Fails if this month's AI spend is over the caps in governance/budgets.yml."""
import csv
import datetime
import pathlib
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent


def load_yaml(rel):
    return yaml.safe_load((ROOT / rel).read_text()) or {}


def month_totals(month=None):
    month = month or datetime.date.today().strftime("%Y-%m")
    total, per_agent = 0.0, {}
    path = ROOT / "logs" / "costs.csv"
    if path.exists():
        with path.open(newline="") as f:
            for row in csv.DictReader(f):
                if not row.get("date", "").startswith(month):
                    continue
                cost = float(row.get("cost_gbp") or 0)
                total += cost
                per_agent[row["agent"]] = per_agent.get(row["agent"], 0.0) + cost
    return total, per_agent


def check():
    caps = load_yaml("governance/budgets.yml")["ai_costs"]
    total, per_agent = month_totals()
    problems = []
    if total > caps["total_monthly_cap"]:
        problems.append(f"total {total:.2f} GBP is over cap {caps['total_monthly_cap']}")
    for agent, cost in per_agent.items():
        cap = caps["per_agent_monthly_cap"].get(agent, 0)
        if cost > cap:
            problems.append(f"{agent} {cost:.2f} GBP is over cap {cap}")
    return total, problems


if __name__ == "__main__":
    total, problems = check()
    print(f"AI spend this month: {total:.2f} GBP")
    for p in problems:
        print("OVER BUDGET:", p)
    sys.exit(1 if problems else 0)
EOF

cat > scripts/validate_config.py <<'EOF'
#!/usr/bin/env python3
"""Checks that the YAML config files are valid and consistent."""
import pathlib
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
errors, warnings = [], []


def load(rel):
    try:
        return yaml.safe_load((ROOT / rel).read_text()) or {}
    except Exception as exc:
        errors.append(f"{rel}: cannot parse ({exc})")
        return {}


for f in ROOT.rglob("*.yml"):
    if ".git" in f.parts or ".migration-backup" in f.parts:
        continue
    load(f.relative_to(ROOT))

status = load("governance/status.yml")
routing = load("models/routing.yml")
budgets = load("governance/budgets.yml")
models = routing.get("models") or {}

if not isinstance(status.get("paused"), bool):
    errors.append("status.yml: paused must be true or false")
if status.get("provider") not in ("manual", "api"):
    errors.append("status.yml: provider must be manual or api")

caps = (budgets.get("ai_costs") or {})
per_agent = caps.get("per_agent_monthly_cap") or {}
for name, cfg in (status.get("agents") or {}).items():
    base = ROOT / "agents" / name
    for needed in ("prompt.md", "permissions.yml", "tools.yml"):
        if not (base / needed).exists():
            errors.append(f"agents/{name}/{needed} is missing")
    if not (ROOT / "memory" / "brain" / "sops" / f"{name}.md").exists():
        errors.append(f"memory/brain/sops/{name}.md is missing")
    r = (routing.get("agents") or {}).get(name)
    if r is None:
        errors.append(f"models/routing.yml has no entry for agent {name}")
    else:
        for key in ("tier", "escalate"):
            if key in r and r[key] not in models:
                errors.append(f"routing.yml: {name} uses unknown model tier {r[key]}")
    if name not in per_agent:
        errors.append(f"budgets.yml has no AI cap for agent {name}")
    perms = load(f"agents/{name}/permissions.yml")
    if perms.get("execute_live_actions") is not False:
        errors.append(f"agents/{name}/permissions.yml: execute_live_actions must be false")

for name in per_agent:
    if name not in (status.get("agents") or {}):
        errors.append(f"budgets.yml has a cap for unknown agent {name}")
if sum(per_agent.values()) > (caps.get("total_monthly_cap") or 0) + 0.1:
    errors.append("budgets.yml: per-agent AI caps add up to more than total_monthly_cap")

for ch in ("ebay-uk", "shopify", "social"):
    cfg = load(f"channels/{ch}/config.yml")
    if not isinstance(cfg.get("enabled"), bool):
        errors.append(f"channels/{ch}/config.yml: enabled must be true or false")

if "YOUR-GITHUB-USERNAME" in (ROOT / "CODEOWNERS").read_text():
    warnings.append("CODEOWNERS still has the placeholder username")

for w in warnings:
    print("WARNING:", w)
for e in errors:
    print("ERROR:", e)
print("Config OK" if not errors else f"{len(errors)} error(s)")
sys.exit(1 if errors else 0)
EOF

cat > scripts/check_secrets.py <<'EOF'
#!/usr/bin/env python3
"""Basic scan of tracked files for things that look like API keys."""
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PATTERNS = [
    re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}"),
    re.compile(r"AIza[0-9A-Za-z_-]{35}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}"),
    re.compile(r"shpat_[0-9a-f]{20,}"),
    re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"][A-Za-z0-9_\-/+=]{20,}['\"]"),
]
SKIP = {"scripts/check_secrets.py", ".env.example"}

files = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True).stdout.split()
hits = []
for rel in files:
    if rel in SKIP:
        continue
    try:
        text = (ROOT / rel).read_text(errors="ignore")
    except Exception:
        continue
    for rx in PATTERNS:
        if rx.search(text):
            hits.append(rel)
            break
for h in hits:
    print("POSSIBLE SECRET in", h)
print("No secrets found" if not hits else f"{len(hits)} file(s) flagged")
sys.exit(1 if hits else 0)
EOF

cat > scripts/run_agent.py <<'EOF'
#!/usr/bin/env python3
"""Run one agent with Claude.
Free mode (manual): writes a ready-to-paste prompt to outbox/ for claude.ai.
API mode: calls the Claude API, but only if budgets, rates and the key are set. Output is always a proposal.
Usage: python scripts/run_agent.py --agent sourcing --task "Scan 20 products for ..."
"""
import argparse
import datetime
import json
import os
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_budget import ROOT, load_yaml, month_totals  # noqa: E402
from pii_guard import find_pii  # noqa: E402


def read(rel):
    p = ROOT / rel
    return p.read_text() if p.exists() else ""


def call_claude(model_cfg, key, prompt):
    body = {"model": model_cfg["model"], "max_tokens": model_cfg.get("max_tokens", 1500),
            "messages": [{"role": "user", "content": prompt}]}
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages", data=json.dumps(body).encode(),
        headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            d = json.load(resp)
    except urllib.error.HTTPError as exc:
        sys.exit(f"API error {exc.code}: {exc.read().decode()[:500]}")
    text = "".join(b.get("text", "") for b in d["content"] if b.get("type") == "text")
    return text, d["usage"]["input_tokens"], d["usage"]["output_tokens"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", required=True)
    ap.add_argument("--task", required=True)
    ap.add_argument("--tier", help="haiku, sonnet or opus (only the agent's own tier or its escalation tier)")
    ap.add_argument("--input-file")
    ap.add_argument("--skip-pii-check", action="store_true", help="manual mode only")
    a = ap.parse_args()

    status = load_yaml("governance/status.yml")
    if status.get("paused"):
        print("PAUSED: governance/status.yml has paused: true. Nothing was run.")
        return 0
    cfg = (status.get("agents") or {}).get(a.agent)
    if cfg is None or not (ROOT / "agents" / a.agent).exists():
        print(f"Unknown agent: {a.agent}")
        return 2
    if not cfg.get("enabled"):
        print(f"Agent {a.agent} is disabled in governance/status.yml")
        return 0

    routing = load_yaml("models/routing.yml")
    route = (routing.get("agents") or {}).get(a.agent)
    if not route:
        print(f"models/routing.yml has no entry for {a.agent}")
        return 2
    allowed = [t for t in (route.get("tier"), route.get("escalate")) if t]
    tier = a.tier or route["tier"]
    if tier not in allowed:
        print(f"Refused: {a.agent} may only use {', '.join(allowed)}")
        return 7
    model_cfg = routing["models"][tier]

    extra = ""
    if a.input_file:
        path = ROOT / a.input_file
        extra = path.read_text() if path.exists() else open(a.input_file).read()
    mode = cfg.get("provider", status.get("provider", "manual"))
    pii = find_pii(a.task + "\n" + extra)
    if pii and not (a.skip_pii_check and mode == "manual"):
        print("Refused: the task looks like it contains personal data (" + ", ".join(pii) + "). Use order IDs instead.")
        return 3

    dry = cfg.get("dry_run", status.get("default_dry_run", True))
    sop = read(f"memory/brain/sops/{a.agent}.md")
    prompt = "\n\n".join(x for x in [
        read("agents/_shared/company-rules.md"), read(f"agents/{a.agent}/prompt.md"),
        ("## Your SOP\n" + sop) if sop else "", read("agents/_shared/output-schema.md"),
        "## Task\n" + a.task, ("## Extra input\n" + extra) if extra else ""] if x.strip())

    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S")
    name = f"{stamp}-{a.agent}.md"
    banner = f"DRY RUN: proposal only. Live actions are not implemented. Dry-run flag: {dry}\n"

    if mode == "manual":
        out = ROOT / "outbox" / name
        out.write_text(
            f"# Prepared prompt for {a.agent}\n{banner}\n"
            f"Open {model_cfg['paste_into']}, choose {model_cfg['label']}, and paste everything below the line.\n"
            f"Save the reply as inbox/{name}\n\n---\n\n{prompt}\n")
        print(f"Prompt written to {out.relative_to(ROOT)} (use {model_cfg['label']})")
        return 0

    costs = load_yaml("models/costs.yml").get(tier, {})
    rin, rout = costs.get("input_per_mtok_gbp", 0), costs.get("output_per_mtok_gbp", 0)
    if not (rin or rout):
        print(f"Refused: fill in the {tier} rates in models/costs.yml first.")
        return 4
    caps = load_yaml("governance/budgets.yml")["ai_costs"]
    total, per_agent = month_totals()
    if total >= caps["total_monthly_cap"] or per_agent.get(a.agent, 0) >= caps["per_agent_monthly_cap"].get(a.agent, 0):
        print("Refused: AI budget cap reached (or still 0) in governance/budgets.yml.")
        return 5
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        print("Refused: ANTHROPIC_API_KEY is not set.")
        return 6

    text, tin, tout = call_claude(model_cfg, key, prompt)
    cost = tin / 1e6 * rin + tout / 1e6 * rout
    with (ROOT / "logs" / "costs.csv").open("a") as f:
        f.write(f"{datetime.date.today()},{a.agent},anthropic,{model_cfg['model']},{tin},{tout},{cost:.4f},\n")
    out = ROOT / "logs" / "actions" / name
    out.write_text(f"# Proposal from {a.agent} ({model_cfg['model']})\n{banner}\n{text}\n")
    print(f"Proposal written to {out.relative_to(ROOT)} (cost {cost:.4f} GBP)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
EOF

cat > scripts/weekly_report.py <<'EOF'
#!/usr/bin/env python3
"""Builds the weekly summary (no AI needed). Usage: python scripts/weekly_report.py [--out file.md]"""
import argparse
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_budget import ROOT, load_yaml, month_totals  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--out")
args = ap.parse_args()

status = load_yaml("governance/status.yml")
caps = load_yaml("governance/budgets.yml")["ai_costs"]
total, per_agent = month_totals()
enabled = [n for n, c in (status.get("agents") or {}).items() if c.get("enabled")]
outbox = {p.name for p in (ROOT / "outbox").glob("*.md") if p.name != "README.md"}
inbox = {p.name for p in (ROOT / "inbox").glob("*.md")}
actions = [p for p in (ROOT / "logs" / "actions").glob("*.md")]

lines = [
    f"# Weekly report {datetime.date.today()}",
    f"- Paused: {status.get('paused')} | Provider: {status.get('provider')}",
    f"- Enabled agents: {', '.join(enabled)}",
    f"- AI spend this month: {total:.2f} GBP of cap {caps['total_monthly_cap']} GBP",
    f"- Prompts waiting for a reply in inbox/: {len(outbox - inbox)}",
    f"- Proposals logged: {len(actions)}",
    "",
    "## Decisions waiting on the owner",
    "- Review open pull requests and proposals above.",
]
text = "\n".join(lines) + "\n"
print(text)
if args.out:
    open(args.out, "w").write(text)
else:
    (ROOT / "reports" / "weekly" / f"{datetime.date.today()}.md").write_text(text)
EOF

cat > scripts/new_accountant_pack.py <<'EOF'
#!/usr/bin/env python3
"""Creates reports/accountant-pack/YYYY-MM/ with a checklist for the month."""
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_budget import ROOT  # noqa: E402

month = datetime.date.today().strftime("%Y-%m")
d = ROOT / "reports" / "accountant-pack" / month
d.mkdir(parents=True, exist_ok=True)
(d / "CHECKLIST.md").write_text(
    f"# Accountant pack {month}\n- [ ] eBay payout and fee reports exported\n- [ ] Refunds listed\n"
    "- [ ] Postage and stock purchase receipts\n- [ ] Questions for the accountant (VAT, tax)\n"
    "- [ ] No customer personal data included\n")
print("Created", d.relative_to(ROOT))
EOF

cat > scripts/monitor.py <<'EOF'
#!/usr/bin/env python3
"""Free watcher for Tech Support. Runs the config, budget and secret checks and looks for stuck work.
Prints a short report and exits 1 if anything needs attention. No AI is used."""
import datetime
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
problems = []

for script in ("validate_config.py", "check_budget.py", "check_secrets.py"):
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / script)], cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        out = (r.stdout + r.stderr).strip().splitlines()
        problems.append(f"{script} failed: " + (out[-1] if out else "no output"))

today = datetime.date.today()
inbox = {p.name for p in (ROOT / "inbox").glob("*.md")}
for p in sorted((ROOT / "outbox").glob("*.md")):
    if p.name == "README.md" or p.name in inbox:
        continue
    try:
        made = datetime.datetime.strptime(p.name[:8], "%Y%m%d").date()
    except ValueError:
        continue
    if (today - made).days > 3:
        problems.append(f"prompt waiting more than 3 days for a reply: outbox/{p.name}")

lines = [f"# Monitor report {today}"]
lines += [f"- PROBLEM: {x}" for x in problems] or ["- All checks passed"]
text = "\n".join(lines) + "\n"
print(text)
(ROOT / "logs" / "audits").mkdir(parents=True, exist_ok=True)
(ROOT / "logs" / "audits" / f"monitor-{today}.md").write_text(text)
sys.exit(1 if problems else 0)
EOF
# ---------------------------------------------------------------- tests

cat > tests/test_basics.py <<'EOF'
import pathlib
import subprocess
import sys
import unittest

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from pii_guard import find_pii  # noqa: E402


def load(rel):
    return yaml.safe_load((ROOT / rel).read_text())


class Basics(unittest.TestCase):
    def test_pii_email_caught(self):
        self.assertTrue(find_pii("contact bob@example.com"))

    def test_order_id_is_fine(self):
        self.assertEqual(find_pii("Order TEST-12345 is delayed"), [])

    def test_config_valid(self):
        r = subprocess.run([sys.executable, "scripts/validate_config.py"], cwd=ROOT)
        self.assertEqual(r.returncode, 0)

    def test_budget_ok(self):
        r = subprocess.run([sys.executable, "scripts/check_budget.py"], cwd=ROOT)
        self.assertEqual(r.returncode, 0)

    def test_routing_uses_known_tiers(self):
        routing = load("models/routing.yml")
        for name, cfg in routing["agents"].items():
            self.assertIn(cfg["tier"], routing["models"], name)

    def test_every_agent_has_a_sop(self):
        for name in load("governance/status.yml")["agents"]:
            self.assertTrue((ROOT / "memory" / "brain" / "sops" / f"{name}.md").exists(), name)

    def test_ai_caps_add_up(self):
        caps = load("governance/budgets.yml")["ai_costs"]
        self.assertLessEqual(sum(caps["per_agent_monthly_cap"].values()), caps["total_monthly_cap"] + 0.1)


if __name__ == "__main__":
    unittest.main()
EOF

# ---------------------------------------------------------------- GitHub workflows and templates

cat > .github/workflows/config-lint.yml <<'EOF'
name: Config lint
on: [pull_request, push]
permissions: {contents: read}
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install pyyaml
      - run: python scripts/validate_config.py
EOF

cat > .github/workflows/budget-check.yml <<'EOF'
name: Budget check
on: [pull_request, push]
permissions: {contents: read}
jobs:
  budget:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install pyyaml
      - run: python scripts/check_budget.py
EOF

cat > .github/workflows/secret-scan.yml <<'EOF'
name: Secret scan
on: [pull_request, push]
permissions: {contents: read}
jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: python scripts/check_secrets.py
EOF

cat > .github/workflows/evals.yml <<'EOF'
name: Evals and tests
on: [pull_request, push]
permissions: {contents: read}
jobs:
  tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install pyyaml
      - run: python -m unittest discover tests
EOF

cat > .github/workflows/approval-gate.yml <<'EOF'
name: Approval gate
on: pull_request
permissions:
  contents: read
  pull-requests: write
jobs:
  gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: {fetch-depth: 0}
      - name: Label by risk
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          BASE: ${{ github.base_ref }}
          PR: ${{ github.event.pull_request.number }}
        run: |
          files=$(git diff --name-only "origin/$BASE"...HEAD)
          labels=""
          echo "$files" | grep -qE '^(governance/|CODEOWNERS|\.github/|models/|agents/[^/]+/permissions\.yml)' && labels="$labels needs-owner" || true
          echo "$files" | grep -qE '^(governance/policies/vat-and-tax\.md|agents/finance-insights/)' && labels="$labels needs-accountant" || true
          echo "$files" | grep -qE '^channels/[^/]+/config\.yml' && labels="$labels new-channel" || true
          for l in needs-owner needs-accountant new-channel; do gh label create "$l" --force >/dev/null 2>&1 || true; done
          for l in $labels; do gh pr edit "$PR" --add-label "$l"; done
          echo "Labels applied: ${labels:-none}"
EOF

cat > .github/workflows/agent-run.yml <<'EOF'
name: Agent run
# Manual trigger. Add a schedule later once you trust the agents.
on:
  workflow_dispatch:
    inputs:
      agent: {description: "Agent name, e.g. listings", required: true}
      task: {description: "What should it do? (no personal data)", required: true}
  # schedule:
  #   - cron: "0 7 * * 1-5"
permissions:
  contents: write
  pull-requests: write
jobs:
  run:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install pyyaml
      - name: Run agent
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: python scripts/run_agent.py --agent "${{ inputs.agent }}" --task "${{ inputs.task }}"
      - name: Open a pull request with the output
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          if [ -z "$(git status --porcelain)" ]; then echo "Nothing to commit"; exit 0; fi
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          branch="agent/${{ github.run_id }}"
          git checkout -b "$branch"
          git add -A
          git commit -m "Agent output: ${{ inputs.agent }}"
          git push origin "$branch"
          gh pr create --title "Agent output: ${{ inputs.agent }}" --body "Proposal for owner review. Dry run only." --base "${{ github.event.repository.default_branch }}"
EOF

cat > .github/workflows/weekly-report.yml <<'EOF'
name: Weekly report
on:
  schedule:
    - cron: "0 8 * * 1"
  workflow_dispatch:
permissions:
  contents: read
  issues: write
jobs:
  report:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install pyyaml
      - run: python scripts/weekly_report.py --out /tmp/report.md
      - env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: gh issue create --title "Weekly report $(date +%F)" --body-file /tmp/report.md
EOF

cat > .github/workflows/kill-switch.yml <<'EOF'
name: Kill switch
on:
  workflow_dispatch:
    inputs:
      pause: {description: "true = stop all agents, false = resume", required: true, default: "true"}
permissions:
  contents: write
jobs:
  switch:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set paused flag
        run: |
          sed -i "s/^paused: .*/paused: ${{ inputs.pause }}/" governance/status.yml
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add governance/status.yml
          git commit -m "Kill switch: paused=${{ inputs.pause }}" || echo "No change"
          git push
EOF

cat > .github/dependabot.yml <<'EOF'
version: 2
updates:
  - package-ecosystem: github-actions
    directory: "/"
    schedule: {interval: monthly}
EOF

cat > .github/pull_request_template.md <<'EOF'
## What and why

## Approval tier (see governance/approval-tiers.yml)
- [ ] auto  - [ ] needs_approval  - [ ] needs_owner_and_accountant

## Checks
- [ ] Dry run only
- [ ] Within budget (AI cost and spend)
- [ ] Follows the relevant policy in governance/policies/
- [ ] No secrets and no customer personal data
EOF

mk_issue() {  # file | name | about | extra line
cat > ".github/ISSUE_TEMPLATE/$1.md" <<EOF
---
name: $2
about: $3
---
**What is needed and why**

**Cost or amount (GBP)**

**$4**
EOF
}
mk_issue spend-request "Spend request" "Ask to spend money (ads, stock, tools)" "Expected return"
mk_issue price-change "Price change" "Propose a price change" "Old price, new price, margin after fees"
mk_issue new-supplier "New supplier" "Propose a new supplier" "Terms, delivery times, returns"
mk_issue new-channel "New channel" "Propose a new sales channel (e.g. Shopify)" "Checklist from docs/shopify-expansion.md"
mk_issue incident "Incident" "Report something that went wrong" "What happened and what was affected (no personal data)"

cat > .github/workflows/monitor.yml <<'EOF'
name: Monitor
on:
  schedule:
    - cron: "0 7 * * *"
  workflow_dispatch:
permissions:
  contents: read
  issues: write
jobs:
  watch:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install pyyaml
      - id: run
        run: |
          set +e
          python scripts/monitor.py > /tmp/monitor.md
          echo "code=$?" >> "$GITHUB_OUTPUT"
          cat /tmp/monitor.md
      - name: Open an issue if there are problems
        if: steps.run.outputs.code != '0'
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          gh label create monitor --force >/dev/null 2>&1 || true
          open=$(gh issue list --label monitor --state open --json number -q length)
          if [ "$open" = "0" ]; then gh issue create --title "Monitor: problems found" --label monitor --body-file /tmp/monitor.md; fi
EOF
# ---------------------------------------------------------------- docs

cat > docs/architecture.md <<'EOF'
# Architecture
Human owner (and accountant) -> GitHub approval gate -> Chief of Staff (Claude Sonnet) -> two groups of agents:
- Product research pipeline: Sourcing -> Merchandiser -> Finance and Insights -> Compliance -> Reviewer -> owner Approve or Deny.
- Operations: Fulfilment, Customer Care, Marketing, Tech Support.
Shared layer: GBrain memory (SOPs in memory/brain/sops/) and channel adapters (eBay now, Shopify and social later).
Agents only write proposals; the owner approves. All agents are Claude models (Haiku, Sonnet or Opus by task).
EOF
cat > docs/runbook.md <<'EOF'
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
EOF
cat > docs/onboarding.md <<'EOF'
# Onboarding
1. Create a private repo, clone it, run bootstrap.sh with your GitHub username.
2. Settings > Actions > General: allow read and write, and allow Actions to create pull requests.
3. In your Claude account settings, check that "help improve Claude" is switched off.
4. Fill in governance/policies/, governance/budgets.yml and the SOPs in memory/brain/sops/.
5. Add your first products to catalogue/products/ or run the product research pipeline.
EOF
cat > docs/shopify-expansion.md <<'EOF'
# Shopify expansion checklist (to confirm with your accountant)
- [ ] Decide whether the catalogue stays the single source of truth for stock and prices (recommended)
- [ ] Store set up, UK shipping rates and delivery times
- [ ] Payments provider chosen and set up
- [ ] VAT display and invoicing agreed with the accountant
- [ ] Policy pages: privacy, terms, returns, cookies (check UK requirements)
- [ ] Fill in channels/shopify/mapping.yml and rules.md
- [ ] Add Shopify lines to governance/budgets.yml
- [ ] New-channel approval from owner and accountant
- [ ] Run in dry-run first, then set channels/shopify/config.yml enabled: true
EOF
cat > docs/glossary.md <<'EOF'
Dry run: agent proposes only. Provider manual: you paste prompts into claude.ai yourself (free). Provider api: the script calls the Claude API.
Tier: which Claude model (haiku, sonnet, opus) an agent uses. Approval tier: how much sign-off an action needs. SOP: the written instructions an agent reads before each run.
EOF
cat > docs/decisions/0001-free-first-manual-mode.md <<'EOF'
# 0001: Free-first with manual mode
Decision: start with provider: manual so no paid API is needed. Upgrade agent by agent when the value is clear.
Why: avoid cost and risk while the policies and approvals are being tested.
EOF

cat > docs/roster.md <<'EOF'
# Agent roster (10 agents, all Claude)

| Agent | Replaces | Model tier | Role |
|---|---|---|---|
| chief-of-staff | orchestrator | sonnet | Plans each run (max 3 delegated tasks), writes the single digest, keeps the SOPs up to date |
| sourcing | inventory | haiku | Scans about 20 eBay UK products, finds wholesale or manufacturer costs and delivery times, keeps the approved supplier list |
| merchandiser | listings, pricing | haiku | Writes listings and proposes prices through the channel adapter |
| finance-insights | finance, analytics | haiku | Margins (30 percent minimum), spend vs earnings, profit and loss, engagement, accountant pack |
| compliance | compliance | sonnet | eBay rules, UK consumer-law notes, advertising and data protection |
| reviewer | reviewer | sonnet (opus for high risk) | Independent second opinion in a fresh context |
| fulfilment | orders | haiku | Orders, supplier orders, parcel checks and courier tracking |
| customer-care | messages, returns | haiku (sonnet to escalate) | eBay and social messages, returns, disputes |
| marketing | (new) | haiku | Social posts and replies per platform, ad budget, email follow-ups |
| tech-support | monitor | opus | Fixes problems flagged by the free monitoring scripts |

Stage 1 (switched on): chief-of-staff, sourcing, merchandiser, finance-insights, compliance, reviewer, tech-support.
Stage 2 (switch on once selling): fulfilment, customer-care, marketing.
Product research order: sourcing -> merchandiser -> finance-insights -> compliance -> reviewer -> owner Approve or Deny.
EOF
cat > docs/decisions/0002-claude-only.md <<'EOF'
# 0002: Claude for every agent
Decision: all agents use Claude (Haiku for volume, Sonnet for planning and checking, Opus for fixes). Gemini is dropped.
Why: keep business data away from a free tier that may be used to improve another company's products; simpler setup.
Trade-offs: the Reviewer shares blind spots with the agents it checks, and the Claude API costs money.
Mitigations: fresh-context adversarial Reviewer, scripts (not AI) for margin and budget maths, owner approval, manual mode on a Claude plan until the API is worth it.
EOF
cat > docs/decisions/0003-no-marketplace-dropshipping.md <<'EOF'
# 0003: No retailer or marketplace dropshipping
Decision: Sourcing only proposes wholesale or manufacturer suppliers you have an agreement with, or stock you hold.
Why: eBay does not allow listing an item and then buying it from another retailer or marketplace (AliExpress, Amazon) that ships straight to the buyer.
Open question: which fulfilment model to use (hold stock, or a wholesale supplier). Decide it before the first real listing.
EOF

}

if [ "$MIGRATE" = 1 ]; then
  if [ ! -f governance/status.yml ]; then
    echo "Run --migrate from the root of a repo made with the earlier bootstrap."
    exit 1
  fi
  BK=".migration-backup/$(date +%Y%m%d-%H%M%S)"
  mkdir -p "$BK"
  for p in agents governance models scripts tests .github catalogue docs CODEOWNERS README.md CLAUDE.md; do
    if [ -e "$p" ]; then cp -R "$p" "$BK/"; fi
  done
  mvagent() { if [ -d "agents/$1" ] && [ ! -e "agents/$2" ]; then mv "agents/$1" "agents/$2"; echo "renamed agents/$1 -> agents/$2"; fi; }
  mvagent orchestrator chief-of-staff
  mvagent inventory sourcing
  mvagent listings merchandiser
  mvagent orders fulfilment
  mvagent messages customer-care
  mvagent finance finance-insights
  mvagent monitor tech-support
  for gone in pricing returns analytics; do
    if [ -d "agents/$gone" ]; then rm -rf "agents/$gone"; echo "merged away agents/$gone (copy kept in $BK)"; fi
  done
  for gone in marketing shopify content-seo insights; do rm -rf "agents/_future/$gone"; done
  STAGE="$(mktemp -d)"
  ( cd "$STAGE" && generate )
  python3 - "$STAGE" "$BK" "$GH_USER" <<'PY'
import fnmatch
import pathlib
import shutil
import sys

import yaml

stage = pathlib.Path(sys.argv[1])
backup = sys.argv[2]
user = sys.argv[3]
root = pathlib.Path(".")

OVERWRITE = ["scripts/*", "tests/test_basics.py", ".github/workflows/*",
             "agents/*/prompt.md", "agents/*/permissions.yml", "agents/*/tools.yml",
             "models/routing.yml", "models/costs.yml",
             "docs/roster.md", "docs/architecture.md", "docs/runbook.md"]
MERGE = {"governance/status.yml", "governance/budgets.yml"}
MAP = {"orchestrator": "chief-of-staff", "inventory": "sourcing", "listings": "merchandiser",
       "pricing": "merchandiser", "orders": "fulfilment", "messages": "customer-care",
       "returns": "customer-care", "finance": "finance-insights", "analytics": "finance-insights",
       "monitor": "tech-support", "compliance": "compliance", "reviewer": "reviewer"}

added, replaced, kept = [], [], []
for src in sorted(p for p in stage.rglob("*") if p.is_file()):
    rel = src.relative_to(stage).as_posix()
    if rel in MERGE:
        continue
    dst = root / rel
    if not dst.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        added.append(rel)
    elif rel in ("models/routing.yml", "models/costs.yml") and "haiku" in dst.read_text():
        kept.append(rel)
    elif any(fnmatch.fnmatch(rel, pat) for pat in OVERWRITE):
        shutil.copy2(src, dst)
        replaced.append(rel)
    else:
        kept.append(rel)


def load(p):
    return yaml.safe_load(p.read_text()) or {}


def b(v):
    return str(bool(v)).lower()


# status.yml: keep the owner's global settings, carry enabled/provider across renames
new = load(stage / "governance/status.yml")
old = load(root / "governance/status.yml")
agents = {n: dict(c) for n, c in new["agents"].items()}
for oname, ocfg in (old.get("agents") or {}).items():
    n = MAP.get(oname)
    if n in agents:
        if ocfg.get("enabled"):
            agents[n]["enabled"] = True
        if "provider" in ocfg:
            agents[n]["provider"] = ocfg["provider"]
lines = ["paused: " + b(old.get("paused", False)) + "              # true stops every agent run (use the Kill switch workflow)",
         "provider: " + str(old.get("provider", "manual")) + "           # manual = free copy/paste mode | api = call the Claude API",
         "default_dry_run: " + b(old.get("default_dry_run", True)),
         "agents:"]
for n, c in agents.items():
    extra = (", provider: " + c["provider"]) if "provider" in c else ""
    lines.append("  %s: {enabled: %s, dry_run: true%s}" % (n, b(c["enabled"]), extra))
(root / "governance/status.yml").write_text("\n".join(lines) + "\n")

# budgets.yml: keep the owner's total and any non-zero spend limits, rescale per-agent caps
nb = load(stage / "governance/budgets.yml")
ob = load(root / "governance/budgets.yml")
new_total = nb["ai_costs"]["total_monthly_cap"]
old_total = (ob.get("ai_costs") or {}).get("total_monthly_cap") or 0
total = old_total if old_total > 0 else new_total
scale = total / new_total
per = {k: round(v * scale, 2) for k, v in nb["ai_costs"]["per_agent_monthly_cap"].items()}
spend = dict(nb["spend"])
for k, v in (ob.get("spend") or {}).items():
    if v:
        spend[k] = v
bl = ["currency: GBP", "ai_costs:                  # per-agent caps must add up to no more than the total",
      "  total_monthly_cap: %s" % total, "  per_agent_monthly_cap:"]
bl += ["    %s: %s" % (k, v) for k, v in per.items()]
bl += ["spend:                     # real-money limits that need your approval to use"]
bl += ["  %s: %s" % (k, v) for k, v in spend.items()]
(root / "governance/budgets.yml").write_text("\n".join(bl) + "\n")

# small in-place updates to files the owner may have edited
p = root / "catalogue/pricing-rules.yml"
if p.exists() and "min_margin_pct: 20" in p.read_text():
    p.write_text(p.read_text().replace("min_margin_pct: 20", "min_margin_pct: 30"))
    print("pricing-rules.yml: min_margin_pct 20 -> 30")
p = root / "governance/approval-tiers.yml"
if p.exists():
    t = p.read_text()
    t2 = t.replace(", reorder stock]", ", social ad spend, publishing social posts]")
    t2 = t2.replace("[draft listing text,", "[orders to approved suppliers inside the stock budget, draft listing text,")
    if t2 != t:
        p.write_text(t2)
        print("approval-tiers.yml: updated examples")
for rel in ("memory/brain/sops/sourcing.md", "governance/pipelines/product-research.yml"):
    p = root / rel
    if p.exists():
        t = p.read_text()
        t2 = t.replace("AliExpress cost, shipping cost and delivery time", "wholesale or manufacturer cost, shipping cost and delivery time")
        t2 = t2.replace("the AliExpress item cost, shipping cost and delivery time", "the wholesale or manufacturer item cost, shipping cost and delivery time")
        if t2 != t:
            p.write_text(t2)
            print(rel + ": AliExpress wording replaced (eBay does not allow retailer-to-buyer dropshipping)")
for rel in ("CODEOWNERS", "governance/approvers.yml"):
    p = root / rel
    if p.exists() and "YOUR-GITHUB-USERNAME" in p.read_text():
        p.write_text(p.read_text().replace("YOUR-GITHUB-USERNAME", user))
        print(rel + ": placeholder replaced with " + user)
g = root / ".gitignore"
if g.exists() and ".migration-backup/" not in g.read_text():
    g.write_text(g.read_text().rstrip("\n") + "\n.migration-backup/\n")

print("")
print("Migration summary")
print("  new files added:       %d" % len(added))
print("  files replaced:        %d (originals backed up in %s)" % (len(replaced), backup))
print("  files left untouched:  %d" % len(kept))
print("  status.yml and budgets.yml were rewritten for the new agent names")
PY
  rm -rf "$STAGE"
  echo ""
  echo "Migration done. Next steps:"
  echo "  pip install pyyaml"
  echo "  python scripts/validate_config.py && python -m unittest discover tests"
  echo "  git add -A && git commit -m 'Move to the 10-agent Claude roster' && git push"
  echo "Before using API mode, check models/costs.yml has your Claude rates filled in."
else
  if [ -f governance/status.yml ]; then
    echo "governance/status.yml already exists. For a repo made with the earlier bootstrap run:"
    echo "  bash bootstrap.sh --migrate"
    exit 1
  fi
  generate
  echo ""
  echo "Done. Next steps:"
  echo "  pip install pyyaml"
  echo "  python scripts/validate_config.py"
  echo "  python -m unittest discover tests"
  echo "  git add -A && git commit -m 'Bootstrap AI commerce repo' && git push"
fi
