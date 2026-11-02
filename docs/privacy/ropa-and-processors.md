# Record of processing and processors
A simple record of what personal data is used for and who handles it. Update it when something changes. Draft: check against the ICO guidance.

## What is processed
| Purpose | Data | Reason | Kept |
|---|---|---|---|
| Fulfil an order | Name, delivery address, email, order ID | Contract | Until the order is done, then per governance/privacy.yml |
| Tax and accounting | Order amounts, dates, order ID (no contact details needed) | Legal obligation | The retention period in governance/privacy.yml |
| Answer messages | Redacted message text, customer reference | Needed to answer the person | messages_months |
| Marketing emails | Email, consent record | Consent | Until consent is withdrawn |
| Deal with requests and breaches | Request log, breach log | Legal obligation | Per governance/privacy.yml |

## Who handles it (processors) and what to check
| Provider | What it does | Personal data? | Check |
|---|---|---|---|
| Supabase | Holds the private database | Yes | Project region, data processing agreement, two-factor authentication |
| GitHub | Holds code, settings and alerts | No | Never put personal data in issues or commits |
| Anthropic and Google (AI) | Write text from prompts | No | The system removes personal data first |
| Shopify and the payment provider | Checkout and card payments | Yes | Their agreements; you never see card numbers |
| Mailchimp or similar | Marketing email | Yes (consented only) | A data processing agreement; sync only people with current consent |
| Couriers and suppliers | Deliver parcels | Name and address for each delivery | Share only what each delivery needs |

## International transfers
Some providers store or process data outside the UK. Check each provider's terms for how they protect transfers.
