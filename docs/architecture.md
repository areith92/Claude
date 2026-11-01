# Architecture
Human owner (and accountant) -> GitHub approval gate -> Claude orchestrator -> department agents -> shared layer
(GBrain memory, channel adapters). Agents only write proposals; the owner merges. Channels plug in via channels/_shared.
