window.DASHBOARD = {
  "month": "2026-11",
  "as_of": null,
  "mode": {
    "provider": "manual",
    "paused": false,
    "dry_run_default": true
  },
  "spend": {
    "spent_gbp": 0.0,
    "cap_gbp": 5,
    "remaining_gbp": 5.0,
    "percent": 0.0,
    "state": "ok",
    "alert_at_percent": 80
  },
  "per_agent": [
    {
      "agent": "orchestrator",
      "spent_gbp": 0,
      "cap_gbp": 2
    },
    {
      "agent": "listings",
      "spent_gbp": 0,
      "cap_gbp": 1.5
    },
    {
      "agent": "finance",
      "spent_gbp": 0,
      "cap_gbp": 0.5
    },
    {
      "agent": "compliance",
      "spent_gbp": 0,
      "cap_gbp": 1
    },
    {
      "agent": "techsupport",
      "spent_gbp": 0,
      "cap_gbp": 1
    }
  ],
  "alerts": [
    "Tech Support: 1 open incident(s)."
  ],
  "queue": {},
  "latest_digest": null,
  "recent_costs": [],
  "conductor": "orchestrator",
  "agents": [
    {
      "name": "orchestrator",
      "role": "Plans the work, delegates tasks to department agents, reviews their proposals and prepares one digest for the owner. The owner decides. In free (manual) mode the owner pastes each prompt into the AI named in it.",
      "sop": {
        "exists": true,
        "path": "memory/brain/sops/orchestrator.md",
        "purpose": "Turn the owner's goal into a few tasks, send each to the right agent, review the replies and give the owner one ranked digest.",
        "steps": [
          "Run: python3 scripts/orchestrate.py plan --goal \"<goal>\". Paste the prepared prompt into Claude and save the reply in inbox/.",
          "Choose at most 3 tasks. Only use enabled agents. Give each task a one-line reason and an approval tier. Pick the stricter tier if unsure.",
          "Run: python3 scripts/orchestrate.py ingest inbox/<file> --delegate. This prepares one prompt per agent.",
          "Review each reply: did it do the task, with numbers and assumptions? Is the tier right? Does it conflict with governance/policies/? Any personal data, invented facts or claims that something was done?",
          "Give a verdict per task: ready_for_owner, rework or reject. Ask for a second opinion from the reviewer or compliance agent on anything risky.",
          "Run: python3 scripts/orchestrate.py digest. The owner decides with decide, does approved work by hand, then runs complete.",
          "Write a short note for the next run in notes_for_next_run, including what changed since anything the owner rejected."
        ],
        "tier": "Planning is auto. Anything involving spend, suppliers, new channels, refunds over 20 GBP or VAT or tax is escalated.",
        "escalate": [
          "eBay policy warnings or account health problems",
          "Product safety or legal questions",
          "VAT or tax (needs the accountant)",
          "Refunds over 20 GBP, any spend, new suppliers, new channels",
          "Anything involving customer personal data"
        ],
        "never": "Edit governance/, agents/*/permissions.yml, CODEOWNERS or .github/. Perform live actions. Message buyers. Handle bank or card details. Plan work for a disabled agent. Propose spending when the cap is 0."
      },
      "enabled": true,
      "dept": "conductor",
      "model": "claude-sonnet-5-5",
      "provider": "claude",
      "mode": "api",
      "dry_run": true,
      "spent_gbp": 0,
      "cap_gbp": 2
    },
    {
      "name": "listings",
      "role": "Drafts eBay UK titles, descriptions and item specifics from catalogue data, following governance/policies/listing-rules.md.",
      "sop": {
        "exists": true,
        "path": "memory/brain/sops/listings.md",
        "purpose": "Write a clear, accurate eBay UK listing draft from catalogue data.",
        "steps": [
          "Read the product data. List any required field that is missing instead of guessing it.",
          "Write the title within eBay's 80-character limit. Lead with brand and product, then key details. No keyword stuffing or capitals for emphasis.",
          "Write the description from the data only: condition, what is included, size and weight, delivery and returns as set in channels/ebay-uk/.",
          "Fill item specifics (brand, condition, and anything in the schema). Suggest a category and say if you are unsure.",
          "Use the catalogue price. If none is set, ask for the pricing agent. Never set your own.",
          "List the image file names to use. Do not describe images you have not been given.",
          "Check your draft against listing-rules.md and channels/ebay-uk/rules.md. Note any rule you needed that is not written down."
        ],
        "tier": "Drafting is auto. Publishing or revising a live listing needs_approval from the owner.",
        "escalate": [
          "listing-rules.md is incomplete and a rule you need is missing",
          "The product might be restricted or unsafe",
          "Brand or authenticity claims you cannot check from the data"
        ],
        "never": "Publish or edit a live listing. Invent specifications, features or condition. Copy another seller's text or images. Give tax or legal advice. Include customer names, addresses, emails or phone numbers (use order IDs). Say an action has been done. Guess when information is missing: list it under Questions for the human."
      },
      "enabled": true,
      "dept": "sales",
      "model": "claude-sonnet-5-5",
      "provider": "claude",
      "mode": "api",
      "dry_run": true,
      "spent_gbp": 0,
      "cap_gbp": 1.5
    },
    {
      "name": "orders",
      "role": "Reviews new orders by order ID, proposes shipping choices and flags delivery problems.",
      "sop": {
        "exists": true,
        "path": "memory/brain/sops/orders.md",
        "purpose": "Review new orders by order ID, propose how to ship them and flag delivery problems early.",
        "steps": [
          "List the orders by order ID with SKU, quantity and the handling-time deadline.",
          "Check stock for each SKU. Flag any order you cannot fulfil from stock.",
          "Propose the carrier and service per the business policies, with the reason (weight, value, speed promised).",
          "Flag risks: tight handling deadline, heavy or large item, high value needing tracking or insurance, signs of a delivery problem.",
          "For a delivery problem, propose the next step (check tracking, contact the carrier, hand over to the returns agent) without contacting anyone yourself.",
          "Summarise what needs doing today, in priority order."
        ],
        "tier": "Triage and proposals are auto. Any refund, compensation or goodwill credit over 20 GBP needs_approval.",
        "escalate": [
          "Missing stock for an order",
          "Possible fraud signs",
          "Delivery claims or disputes (hand to returns)"
        ],
        "never": "Buy postage or book collections. Contact buyers or carriers. Give tax or legal advice. Include customer names, addresses, emails or phone numbers (use order IDs). Say an action has been done. Guess when information is missing: list it under Questions for the human."
      },
      "enabled": true,
      "dept": "operations",
      "model": "claude-sonnet-5-5",
      "provider": "claude",
      "mode": "manual",
      "dry_run": true,
      "spent_gbp": 0,
      "cap_gbp": 0
    },
    {
      "name": "messages",
      "role": "Triages buyer messages and drafts replies. Escalates refunds, disputes and complaints to the owner.",
      "sop": {
        "exists": true,
        "path": "memory/brain/sops/messages.md",
        "purpose": "Sort buyer messages, draft polite accurate replies and escalate anything sensitive.",
        "steps": [
          "Remove or ignore any personal data. Refer to the buyer by order ID only.",
          "Classify the message: question, delivery, return, damage, dispute, complaint or other.",
          "Draft a reply in friendly UK English: acknowledge, answer from the business policies, say what happens next. Keep it short.",
          "Do not promise refunds, replacements or compensation. If one may be needed, escalate.",
          "Escalate refunds, disputes, complaints, safety issues and legal threats to the owner with a one-line summary.",
          "Keep every reply inside eBay messaging."
        ],
        "tier": "Triage and drafts are auto. Replying to a buyer needs_approval, and anything touching a refund is escalated.",
        "escalate": [
          "Refund, dispute or complaint",
          "Safety issue or legal threat",
          "A buyer asks to move the conversation off eBay"
        ],
        "never": "Send messages. Message buyers outside eBay. Promise refunds or compensation. Give tax or legal advice. Include customer names, addresses, emails or phone numbers (use order IDs). Say an action has been done. Guess when information is missing: list it under Questions for the human."
      },
      "enabled": true,
      "dept": "customer",
      "model": "gemini-3.8-flash",
      "provider": "gemini",
      "mode": "manual",
      "dry_run": true,
      "spent_gbp": 0,
      "cap_gbp": 0
    },
    {
      "name": "finance",
      "role": "Reconciles payouts, fees and refunds and prepares the monthly accountant pack. Never gives tax advice.",
      "sop": {
        "exists": true,
        "path": "memory/brain/sops/finance.md",
        "purpose": "Keep the numbers straight and prepare the monthly pack for the accountant. Never give tax advice.",
        "steps": [
          "Run: python3 scripts/new_accountant_pack.py. It creates reports/accountant-pack/<month>/CHECKLIST.md.",
          "Reconcile payouts against sales, fees and refunds. Show the working and any difference.",
          "Total the costs: postage, stock, eBay fees, AI spend from logs/costs.csv.",
          "List every question about VAT or tax separately for the accountant. Do not answer them.",
          "Tick the checklist items you could complete and list those you could not.",
          "Confirm the pack has no customer personal data."
        ],
        "tier": "Reconciliation and reports are auto. Anything on VAT or tax treatment, or changing bookkeeping categories, is needs_owner_and_accountant.",
        "escalate": [
          "Any VAT or tax question",
          "A difference you cannot explain",
          "A change to bookkeeping categories"
        ],
        "never": "Move money or touch bank or card details. Decide tax treatment. Give tax or legal advice. Include customer names, addresses, emails or phone numbers (use order IDs). Say an action has been done. Guess when information is missing: list it under Questions for the human."
      },
      "enabled": true,
      "dept": "finance",
      "model": "claude-sonnet-5-5",
      "provider": "claude",
      "mode": "manual",
      "dry_run": true,
      "spent_gbp": 0,
      "cap_gbp": 0.5
    },
    {
      "name": "compliance",
      "role": "Checks proposed listings and actions against eBay rules, company policies and UK consumer-law notes in governance/policies/.",
      "sop": {
        "exists": true,
        "path": "memory/brain/sops/compliance.md",
        "purpose": "Check proposed listings and actions against eBay rules, company policy and the UK consumer-law notes, and say clearly what passes and what does not.",
        "steps": [
          "Read the proposal and the rules that apply to it.",
          "Check it against each rule. For each, say pass, flag or block and give the reason.",
          "Where a policy file is a draft or silent, say exactly which rule is missing and what you assumed. Do not invent rules.",
          "Check the approval tier is right under governance/approval-tiers.yml.",
          "Note anything that touches consumer rights, product safety or data protection for the owner to look at.",
          "Give an overall result: pass, pass with flags, or block."
        ],
        "tier": "Checking is auto. A block always goes to the owner.",
        "escalate": [
          "Possible breach of eBay rules or consumer law",
          "Product safety concerns",
          "Data protection issues"
        ],
        "never": "Give final legal rulings. You are not a lawyer: say when professional advice is needed. Give tax or legal advice. Include customer names, addresses, emails or phone numbers (use order IDs). Say an action has been done. Guess when information is missing: list it under Questions for the human."
      },
      "enabled": true,
      "dept": "compliance",
      "model": "claude-sonnet-5-5",
      "provider": "claude",
      "mode": "api",
      "dry_run": true,
      "spent_gbp": 0,
      "cap_gbp": 1
    },
    {
      "name": "reviewer",
      "role": "Gives an independent second opinion on high-risk proposals before they reach the owner.",
      "sop": {
        "exists": true,
        "path": "memory/brain/sops/reviewer.md",
        "purpose": "Give an independent second opinion on high-risk proposals before they reach the owner.",
        "steps": [
          "Read the task first, then the proposal. Do not rely on the author's summary.",
          "Check the numbers and assumptions yourself and show your working.",
          "Check the approval tier against governance/approval-tiers.yml and its thresholds.",
          "Check for policy conflicts, personal data, invented facts and claims that something was done.",
          "Say what you checked and what you could not check.",
          "Give a verdict: ready_for_owner, rework or reject, with the main reason."
        ],
        "tier": "Reviews are auto. The proposal keeps its own tier.",
        "escalate": [
          "Anything you think is unsafe or against policy",
          "A proposal you cannot assess from what you were given"
        ],
        "never": "Approve or publish anything. Change the proposal yourself. Give tax or legal advice. Include customer names, addresses, emails or phone numbers (use order IDs). Say an action has been done. Guess when information is missing: list it under Questions for the human."
      },
      "enabled": true,
      "dept": "compliance",
      "model": "gemini-3.8-flash",
      "provider": "gemini",
      "mode": "api",
      "dry_run": true,
      "spent_gbp": 0,
      "cap_gbp": 0
    },
    {
      "name": "monitor",
      "role": "Watches AI spend, budgets, errors and account health signals. Mostly done by scripts.",
      "sop": {
        "exists": true,
        "path": "memory/brain/sops/monitor.md",
        "purpose": "Watch AI spend, budgets, errors and account health signals. Most of this is done by scripts. Raise problems so Tech Support can fix them.",
        "steps": [
          "Run: python3 scripts/techsupport.py detect. It runs the five health checks and raises an incident for each failure.",
          "Check AI spend against the caps. At 80 percent, tell the owner. At the cap, calls stop and an alert is raised.",
          "Read the dashboard alerts and the Budget alert and Monitor issues on GitHub.",
          "For a problem the checks miss, describe it and give the owner the command: python3 scripts/techsupport.py raise --title \"...\" --details \"...\".",
          "For a security problem (a key exposed, something running that should not), tell the owner to run the Kill switch workflow, then follow operations/incident-response.md.",
          "Report what you checked, what is healthy and what needs attention."
        ],
        "tier": "Monitoring and reports are auto. Raising spend caps is a pull request the owner approves.",
        "escalate": [
          "Any exposed key",
          "Spend at or near a cap",
          "eBay account health warnings",
          "Repeated failures"
        ],
        "never": "Raise or remove a cap yourself. Run live actions. Give tax or legal advice. Include customer names, addresses, emails or phone numbers (use order IDs). Say an action has been done. Guess when information is missing: list it under Questions for the human."
      },
      "enabled": true,
      "dept": "monitoring",
      "model": "claude-sonnet-5-5",
      "provider": "claude",
      "mode": "manual",
      "dry_run": true,
      "spent_gbp": 0,
      "cap_gbp": 0
    },
    {
      "name": "techsupport",
      "role": "Fixes problems in this repo's own systems (scripts, tests, dashboard, docs, agent briefs) when the monitor raises an incident. Finds the root cause, proposes the smallest safe fix as exact file changes, and learns from failed attempts. It never touches eBay, money or customers.",
      "sop": {
        "exists": true,
        "path": "memory/brain/sops/techsupport.md",
        "purpose": "Fix problems in this repo's own systems when the monitor raises an incident: find the cause, propose the smallest safe fix, and let the scripts test and verify it.",
        "steps": [
          "Read the evidence and the supplied files. Find the root cause before proposing anything.",
          "Propose the smallest fix as exact file changes: replace (old text must appear once) or write for a new file. Maximum 4 files.",
          "Change only scripts/, tests/, docs/, dashboard/ (not status files) and agents/*/prompt.md directly. Changes to governance/, models/, channels/, .github/, CODEOWNERS, CLAUDE.md, permissions, tools or the safety scripts are proposals for the owner.",
          "Never weaken a test or a safety check to make something pass.",
          "Reply with one fenced json block: diagnosis, root_cause, risk, changes, verify.",
          "The script tests your fix in a scratch copy, applies it on a branch fix/inc-..., and checks it again in the real working tree.",
          "If an attempt fails, read the failure output and take a different approach. After 2 attempts, explain what the owner needs to decide.",
          "The owner pushes the branch and merges it. After they pull, the script runs resolve to verify the fix once more."
        ],
        "tier": "A fix to scripts, tests, docs or dashboard is needs_approval (the owner merges). Owner-only files are applied only if the owner passes --include-owner-files.",
        "escalate": [
          "A fix needs governance, models, workflow, permission or safety-script changes",
          "You cannot find a safe fix",
          "The same incident keeps coming back"
        ],
        "never": "Push or merge. Touch logs/, inbox/, outbox/, reports/, operations/, memory/ or secrets. Add keys or personal data. Suggest commands for the owner to run as part of the fix. Give tax or legal advice. Include customer names, addresses, emails or phone numbers (use order IDs). Say an action has been done. Guess when information is missing: list it under Questions for the human."
      },
      "enabled": true,
      "dept": "support",
      "model": "claude-sonnet-5-5",
      "provider": "claude",
      "mode": "api",
      "dry_run": true,
      "spent_gbp": 0,
      "cap_gbp": 1
    },
    {
      "name": "pricing",
      "role": "Proposes price changes within catalogue/pricing-rules.yml.",
      "sop": {
        "exists": true,
        "path": "memory/brain/sops/pricing.md",
        "purpose": "Propose prices that respect the pricing rules and show the working.",
        "steps": [
          "Read pricing-rules.yml: minimum margin 20 percent, never below cost, round to .99, automatic change limit 5 percent.",
          "Work out margin: (price - cost - eBay fees - postage) / price. Flag that the eBay fee assumption is still 0 and the result may be overstated.",
          "Propose the new price rounded to .99. Show the working.",
          "If the change is more than 5 percent from the current price, mark it needs_approval.",
          "If the price would breach the minimum margin or fall below cost, do not propose it. Explain and suggest alternatives.",
          "Summarise the effect on margin."
        ],
        "tier": "A change of 5 percent or less is auto. A larger change needs_approval.",
        "escalate": [
          "Margin below 20 percent",
          "Missing cost data",
          "A request to price below cost"
        ],
        "never": "Change prices directly. Propose a price below cost. Give tax or legal advice. Include customer names, addresses, emails or phone numbers (use order IDs). Say an action has been done. Guess when information is missing: list it under Questions for the human."
      },
      "enabled": false,
      "dept": "sales",
      "model": "gemini-3.8-flash",
      "provider": "gemini",
      "mode": "manual",
      "dry_run": true,
      "spent_gbp": 0,
      "cap_gbp": 0
    },
    {
      "name": "inventory",
      "role": "Tracks stock, proposes reorders and compares suppliers.",
      "sop": {
        "exists": true,
        "path": "memory/brain/sops/inventory.md",
        "purpose": "Track stock, propose reorders and compare suppliers.",
        "steps": [
          "List products with low stock or slow sales, with the numbers.",
          "Estimate the reorder quantity from sales rate and supplier lead time. State the assumptions.",
          "Compare suppliers from catalogue/suppliers/ on price, lead time and reliability if known.",
          "Write the reorder proposal with total cost. Any reorder needs_approval; flag if a single spend is over 25 GBP.",
          "A supplier not in the catalogue is a new supplier: needs_approval.",
          "List slow movers and suggest what the owner might do."
        ],
        "tier": "Analysis is auto. Reordering stock and any new supplier is needs_approval.",
        "escalate": [
          "Any spend",
          "A new supplier",
          "Stock-outs on best sellers"
        ],
        "never": "Place orders or pay suppliers. Contact suppliers. Give tax or legal advice. Include customer names, addresses, emails or phone numbers (use order IDs). Say an action has been done. Guess when information is missing: list it under Questions for the human."
      },
      "enabled": false,
      "dept": "operations",
      "model": "gemini-3.8-flash",
      "provider": "gemini",
      "mode": "manual",
      "dry_run": true,
      "spent_gbp": 0,
      "cap_gbp": 0
    },
    {
      "name": "returns",
      "role": "Handles return requests and cases within governance/policies/refunds.md.",
      "sop": {
        "exists": true,
        "path": "memory/brain/sops/returns.md",
        "purpose": "Handle return requests and cases within the refunds policy, and escalate what needs the owner.",
        "steps": [
          "Identify the reason: changed mind, not as described, damaged, wrong item, not received.",
          "Check the case against the returns terms in the business policies and refunds.md. If refunds.md is silent, say so.",
          "Propose an outcome (accept return, partial refund, replacement, decline with reason) and the cost.",
          "Any refund over 20 GBP, or any goodwill credit, needs_approval. Disputes and complaints go to the owner.",
          "Draft a neutral message for the owner to approve. Do not promise anything.",
          "Record the lesson for the brain notes if the case shows a pattern (no personal data)."
        ],
        "tier": "Triage is auto. Refunds over 20 GBP and goodwill credits are needs_approval.",
        "escalate": [
          "Refund over 20 GBP",
          "Dispute, complaint or safety issue",
          "Possible fraud"
        ],
        "never": "Issue refunds or reply to buyers. Give tax or legal advice. Include customer names, addresses, emails or phone numbers (use order IDs). Say an action has been done. Guess when information is missing: list it under Questions for the human."
      },
      "enabled": false,
      "dept": "operations",
      "model": "claude-sonnet-5-5",
      "provider": "claude",
      "mode": "manual",
      "dry_run": true,
      "spent_gbp": 0,
      "cap_gbp": 0
    },
    {
      "name": "analytics",
      "role": "Calculates margin per product and prepares dashboard data.",
      "sop": {
        "exists": true,
        "path": "memory/brain/sops/analytics.md",
        "purpose": "Calculate margin per product and prepare data for reports and the dashboard.",
        "steps": [
          "Collect price, cost, eBay fees and postage for each product.",
          "Work out margin per product: (price - cost - fees - postage) / price. Show the working.",
          "Flag products below the 20 percent minimum margin and any with missing data.",
          "Flag that the eBay fee assumption is still 0 if it has not been filled in.",
          "Produce a table sorted by margin and a three-line summary of what stands out.",
          "Note what data you need to be more accurate."
        ],
        "tier": "All reporting is auto.",
        "escalate": [
          "Products losing money",
          "Missing or inconsistent data"
        ],
        "never": "Change catalogue data or prices. Give tax or legal advice. Include customer names, addresses, emails or phone numbers (use order IDs). Say an action has been done. Guess when information is missing: list it under Questions for the human."
      },
      "enabled": false,
      "dept": "finance",
      "model": "gemini-3.8-flash",
      "provider": "gemini",
      "mode": "manual",
      "dry_run": true,
      "spent_gbp": 0,
      "cap_gbp": 0
    }
  ],
  "departments": [
    {
      "id": "sales",
      "label": "Sales",
      "color": "#ff4d6d",
      "agents": [
        "listings",
        "pricing"
      ],
      "tools": [
        "eBay UK listings",
        "Catalogue"
      ]
    },
    {
      "id": "operations",
      "label": "Operations",
      "color": "#22d3ee",
      "agents": [
        "orders",
        "inventory",
        "returns"
      ],
      "tools": [
        "eBay UK orders",
        "Stock sheet"
      ]
    },
    {
      "id": "customer",
      "label": "Customer care",
      "color": "#3b82f6",
      "agents": [
        "messages"
      ],
      "tools": [
        "eBay messages"
      ]
    },
    {
      "id": "finance",
      "label": "Finance",
      "color": "#34d399",
      "agents": [
        "finance",
        "analytics"
      ],
      "tools": [
        "Cost log",
        "Accountant pack"
      ]
    },
    {
      "id": "compliance",
      "label": "Compliance",
      "color": "#a78bfa",
      "agents": [
        "compliance",
        "reviewer"
      ],
      "tools": [
        "Policies",
        "Approval tiers"
      ]
    },
    {
      "id": "monitoring",
      "label": "Monitoring",
      "color": "#fbbf24",
      "agents": [
        "monitor"
      ],
      "tools": [
        "Health checks",
        "Budget guard",
        "Kill switch"
      ]
    },
    {
      "id": "support",
      "label": "Tech Support",
      "color": "#fb923c",
      "agents": [
        "techsupport"
      ],
      "tools": [
        "Incident queue",
        "Test sandbox"
      ]
    }
  ],
  "tasks": [],
  "approvals": [],
  "connections": [
    {
      "id": "claude",
      "name": "Claude API",
      "status": "in use",
      "detail": "Agents on the API: orchestrator, listings, compliance, techsupport. Key lives in GitHub secrets, never in the repo."
    },
    {
      "id": "gemini",
      "name": "Gemini API",
      "status": "in use",
      "detail": "Agents on the API: reviewer. Free tier."
    },
    {
      "id": "ebay",
      "name": "eBay UK",
      "status": "manual mode",
      "detail": "Draft only. Needs EBAY_CLIENT_ID, EBAY_CLIENT_SECRET, EBAY_REFRESH_TOKEN as GitHub secrets for Phase 2."
    },
    {
      "id": "shopify",
      "name": "Shopify",
      "status": "not enabled",
      "detail": "Reserved for Phase 4. Needs owner and accountant approval."
    }
  ],
  "phases": {
    "current": 1,
    "list": [
      {
        "n": 1,
        "name": "Draft only",
        "text": "Agents write proposals. You approve and act by hand."
      },
      {
        "n": 2,
        "name": "Read-only eBay API",
        "text": "Agents read orders, listings and traffic. Nothing is changed on eBay."
      },
      {
        "n": 3,
        "name": "Limited live actions",
        "text": "Chosen actions run behind the approval tiers, one at a time, by pull request."
      },
      {
        "n": 4,
        "name": "Shopify channel",
        "text": "A second sales channel, after owner and accountant approval."
      }
    ]
  },
  "brain": {
    "count": 13,
    "notes": [
      "sops/analytics.md",
      "sops/compliance.md",
      "sops/finance.md",
      "sops/inventory.md",
      "sops/listings.md",
      "sops/messages.md",
      "sops/monitor.md",
      "sops/orchestrator.md",
      "sops/orders.md",
      "sops/pricing.md",
      "sops/returns.md",
      "sops/reviewer.md",
      "sops/techsupport.md"
    ]
  },
  "incidents": [
    {
      "id": "INC-20261102-001",
      "created": "2026-11-02",
      "title": "Check failing: No secrets in tracked files",
      "severity": "high",
      "check": "secrets",
      "status": "raised",
      "stage": 2,
      "evidence": "POSSIBLE SECRET in tests/test_techsupport.py\n1 file(s) flagged",
      "diagnosis": "",
      "root_cause": "",
      "fix": null,
      "test": null,
      "live": null,
      "branch": "",
      "attempts": 0,
      "history": [
        {
          "date": "2026-11-02",
          "status": "raised",
          "note": "Raised by monitor"
        }
      ],
      "next": [
        {
          "label": "Let Tech Support fix it (uses your Claude key)",
          "cmd": "python3 scripts/techsupport.py run INC-20261102-001"
        },
        {
          "label": "Or the free route: prepare a prompt to paste into Claude",
          "cmd": "python3 scripts/techsupport.py run INC-20261102-001 --manual"
        },
        {
          "label": "Or give up on it",
          "cmd": "python3 scripts/techsupport.py abandon INC-20261102-001 --reason \"why\""
        }
      ]
    }
  ]
};
