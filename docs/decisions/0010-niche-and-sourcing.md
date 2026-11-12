# 0010: Niche, sourcing route and sales channels
Date: 2026-11-12. Status: accepted. Supersedes the "any product" scope of 0003 and 0006.

## Decision
- Niche: UK new-baby and expectant-parent gifting. Products: newborn clothes, curated gift boxes and bundles, wooden toys, mum-to-be gifts.
- Stage 1 (now): no supplements, no medical devices, no health claims of our own. A gift box may contain an unaltered UK-branded cosmetic (such as a bump balm) that carries its own Responsible Person label.
- Stage 2 (later, eBay only, owner switches it on): a vetted list of UK-branded pregnancy health products, each cleared one at a time by the compliance gate. Until then the health keywords stay blocked in catalogue/research.yml.
- Sourcing: Route A. Stock held in the UK, bought from UK wholesalers and brands that supply safety paperwork, plus one UK production partner for buyer-personalised and original-design items. No AliExpress, no overseas marketplaces, no importing.
- Channels: eBay UK (business seller) and Etsy UK. Etsy lanes: curated gift boxes, original designs made by a disclosed production partner, buyer-personalised items made by a production partner.
- Budget: starting stock 250 to 500 GBP (first order capped at 300 GBP in governance/budgets.yml), AI 5 GBP a month, social ads 100 GBP a month, minimum 30 percent margin after fees.

## Why
- Etsy does not allow drop shipping or reselling commercially available items; production partners are allowed only for the seller's own designs or the buyer's personalisation. Curated gift boxes qualify when they contain different item types from more than one brand, personally selected and packaged, with every item listed.
- The eBay API licence (September 2025) bans using eBay content to suggest or model prices, seller arbitrage (automatic ordering from third-party sites, automatic repricing), and using eBay data to train AI. Prices therefore come from cost-plus maths in code and the owner's own Seller Hub research, never from API data fed to an agent.
- Importing children's products makes the importer the responsible party for UKCA or CE marking, labelling, test evidence and nightwear labels. Buying from UK brands keeps those duties with the manufacturer; we check the paperwork as a distributor.
- Worked examples (fees and postage checked 12 November 2026): a 34.99 GBP gift set nets about 32 percent on eBay and about 40 percent on Etsy; a personalised bodysuit needs a price of about 21 GBP or more to clear 30 percent; plain wholesale basics cannot reach 30 percent at marketplace fee levels.

## Consequences
- catalogue/research.yml, catalogue/fees.yml, governance/pipelines/product-research.yml and governance/policies/ now describe the niche, Route A and the two channels.
- Every agent SOP and department playbook in memory/brain/sops/ is rewritten for the niche (Phase 2).
- The dashboard, the live research pipeline, voice calls, the money model and the handbook follow in Phases 3 to 8.
- Legal and policy points above are our reading of the public rules, not legal advice. The owner confirms them when ticking confirmed_by_owner in each policy file.
