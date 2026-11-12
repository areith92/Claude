# eBay UK channel rules (plain-English companion to governance/policies/ebay-uk-compliance.yml)
Checked 2026-11-12 against eBay's drop-shipping policy, the business seller fee pages and the API License Agreement dated 3 September 2025. Not legal advice; the owner confirms the policy file.

## Fulfilment
- Stock you hold (hold_stock) and items made and shipped by a genuine production partner (production_partner) are allowed.
- Buying from another retailer or marketplace that ships straight to the buyer is not allowed and is blocked by the gate.

## Fees (business seller, excluding VAT, which is added at 20 percent)
- Final value fee by category, 12.9 percent in most categories, on item price plus postage. Confirm the Baby category rate on your fee page.
- Per-order fee 0.30 GBP up to 10 GBP, 0.40 GBP above (since 12 February 2026). Regulatory operating fee 0.35 percent.

## Listings
- Title within eBay's 80-character limit. Item specifics filled in. Own photos. Honest delivery time.
- Nightwear and babies' garments show the flammability wording next to the item. Toys show the age grading and warnings from the supplier's label.
- No health or medical claims of our own. Quote only what the brand's own label says.

## API License Agreement (what our code must never do)
- Never use eBay content to suggest or model prices for eBay listings. Prices come from scripts/margin.py (cost plus fees and margin) and the owner's own Seller Hub research.
- Never automate ordering from third-party sites or reprice against them (seller arbitrage).
- Never use eBay data to train or improve any AI, and never put Restricted API data (Marketplace Insights and similar) into any third-party AI without eBay's written consent.
- Displayed listing data is refreshed within 6 hours and deleted when no longer needed. Browse API default limit: 5,000 calls a day.
