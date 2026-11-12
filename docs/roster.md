# Agent roster (10 agents, all Claude), niche edition
Niche: UK new-baby and expectant-parent gifting. Channels: eBay UK and Etsy UK. Sourcing: Route A (decision 0010).

| Agent | Department | Model tier | Role |
|---|---|---|---|
| chief-of-staff | company (conductor) | sonnet | Plans each run (max 3 delegated tasks), writes the single digest and the approval queue, keeps the SOP library current, holds the Stage 2 switch closed |
| sourcing | research | haiku (escalate sonnet) | Finds and vets UK wholesalers, brands and the production partner; builds the supplier paperwork pack; keeps the approved supplier list; costs the first 300 GBP order |
| merchandiser | sales | haiku | Designs gift boxes and bundles, writes eBay and Etsy listings in the right lane with the right disclosures, proposes cost-plus prices |
| finance-insights | finance | haiku | Margin per product after the real eBay and Etsy fee stacks, stock budget, weekly profit and loss, AI spend, accountant pack |
| compliance | compliance | sonnet | Children's product checklist (toys, nightwear, textiles, cosmetics as a distributor), Etsy creativity and medical-claims rules, eBay policy and API licence, CAP Code for ads |
| reviewer | compliance | sonnet (opus for safety) | Independent second opinion in a fresh context; must disagree with at least one thing or say why not |
| fulfilment | operations | haiku | Stock in hand, gift box assembly runs, production partner orders, Royal Mail Tracked 48 dispatch, courier tracking, late and stuck orders |
| customer-care | customer care | haiku (escalate sonnet) | eBay, Etsy and social messages: personalisation details, gift messages, delivery, returns, safety complaints |
| marketing | marketing | haiku | Content for parents and gift buyers on Instagram, Facebook, Pinterest and TikTok within 100 GBP a month; every post approved before it is published |
| tech-support | tech support | opus | Fixes problems flagged by the free monitoring scripts, in a branch, with tests |

Stage 1 (switched on): chief-of-staff, sourcing, merchandiser, finance-insights, compliance, reviewer, tech-support.
Stage 2 (switch on once selling): fulfilment, customer-care, marketing.
Product research order: sourcing -> merchandiser -> finance-insights -> compliance -> reviewer -> owner Approve or Deny.
Monitoring is done by scripts (monitor.py, budget_guard.py, kill-switch workflow), not by an AI agent; tech-support picks up what they flag.
