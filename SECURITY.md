# Security
- Secrets live in GitHub Settings > Secrets and variables > Actions. Never in files, issues or PRs.
- If a key is ever committed: revoke it at the provider first, then clean the repo.
- Emergency stop: run the "Kill switch" workflow (sets paused: true in governance/status.yml).
- No customer personal data in the repo, logs, memory or AI prompts.
