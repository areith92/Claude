# Architecture
Human owner (and accountant) -> GitHub approval gate -> Claude orchestrator -> department agents -> shared layer
(GBrain memory, channel adapters). Agents only write proposals; the owner merges. Channels plug in via channels/_shared.

Orchestrator flow: plan -> queue -> delegate (via scripts/run_agent.py) -> review -> digest -> owner decision. State lives in
operations/tasks/queue.yml, digests in reports/digests/, decisions in logs/decisions/.
