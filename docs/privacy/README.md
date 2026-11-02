# Customer data plan
Status: a plan and a checklist. Nothing stores real customer data yet. Not legal advice: check it with the ICO guidance and your accountant.

## What and why
Store only what you need to fulfil orders, handle returns, meet tax record rules and (with consent) send marketing emails: a customer reference, name, delivery address, email, phone if needed, order IDs and consent records.
Never store card numbers (the payment provider does), never special-category data, and never collect data from children.

## Where it lives
- In one private place: the Supabase database, in a separate private area that the normal data API does not expose. Only your scripts reach it, through a small set of audited functions, with your secret key.
- Never in git (the repo is public), never in local files, logs, memory notes, GitHub issues or AI prompts.
- Everywhere else in the system a customer is only a reference such as C-1042, and an order is an order ID. Agents see references and order IDs, never names, emails or addresses.
- Showing someone's details (to post a parcel, or answer a request) is a deliberate act that asks for a reason and is written to an access log.

## Lawful reasons (confirm with the ICO guidance)
- Fulfilling an order: it is needed for the contract.
- Tax and accounting records: a legal obligation, kept for the retention period in governance/privacy.yml.
- Marketing emails and texts: consent, recorded with the wording, the date and the source, and easy to withdraw. Abandoned-cart reminders count as marketing unless they are a plain reminder, so use a clear opt-in at checkout.

## How long
The settings are in governance/privacy.yml. Contact details are anonymised a set time after the last order; the financial order record stays for the legal period.

## People's rights and breaches
Follow the customer-data-request and data-breach procedures in memory/brain/sops/procedures/. Requests normally have one month to be answered. A breach that puts people at risk must be reported to the ICO within 72 hours of becoming aware of it.

## Other people who handle the data (processors)
Listed in docs/privacy/ropa-and-processors.md. For each one, check it has a data processing agreement and where it stores data. No AI provider receives personal data.

## Before you store real customer data: checklist
- [ ] Run the ICO data protection fee self-assessment (ico.org.uk) and pay if it applies.
- [ ] Publish a privacy notice (start from docs/privacy/privacy-notice-draft.md and have it checked).
- [ ] Confirm your Supabase project region and accept its data processing terms. Turn on two-factor authentication for Supabase, GitHub and your email.
- [ ] Decide the marketing consent wording and where it appears at checkout.
- [ ] Confirm the retention figures in governance/privacy.yml with your accountant.
- [ ] Make sure you can export and delete one customer's data (the system will provide this).
- [ ] Delete any test or demo data first.

## How it plugs into the system (next build)
A private schema with customers, addresses, consents, requests and an access log. Orders and messages carry only a customer reference. Functions to add a customer, record or withdraw consent, list people who have consented, show details with a reason, export everything about one person, and anonymise them. The daily watch warns you before a request is due.
