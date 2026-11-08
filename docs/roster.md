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
