# Risk register
| Risk | Likelihood | Impact | Control |
|---|---|---|---|
| Agent publishes a wrong or non-compliant listing | Medium | Medium | Dry-run, Compliance and Reviewer agents, owner approval |
| Runaway AI cost | Low | Medium | Caps in budgets.yml, cost log, check_budget.py |
| Customer data leaks into prompts or the repo | Medium | High | pii_guard.py, memory-policy.md, no personal data in logs |
| eBay account action from bad automation | Low | High | Official APIs only, no scraping, human approval for live actions |
| Wrong VAT or tax handling | Medium | High | Accountant sign-off tier |
