# 0006: Research pipeline and compliance model
Decision: products are researched from official exports or APIs (no scraping). Code, not an AI, applies the hard rules: banned keywords, fulfilment model, delivery limit, margin of at least 30 percent.
Compliance is layered: machine-readable rules per channel (governance/policies/), a gate that blocks or flags (scripts/policy_gate.py), AI review by compliance and finance, owner checks, a freshness check, and a review date that warns when the rules file is more than 90 days old.
eBay: buying from another retailer or marketplace that ships straight to the buyer is blocked. Allowed models are stock you hold and a real wholesaler.
Social selling is a separate channel with its own rules (UK consumer law, the CAP Code and platform shop policies). It is not rule-free.
Approve never buys or lists anything. Saved images are for analysis only. Placeholders in catalogue/fees.yml raise a flag until the owner confirms them.
