# Memory
`brain/` holds plain markdown notes (suppliers, decisions, lessons). It works as ordinary files now.
Connect GBrain to this folder when you are ready (check its docs for setup). Read memory/memory-policy.md first.
`brain/sops/` holds one SOP per agent. scripts/run_agent.py adds the agent's SOP and up to two related notes (keyword search, scripts/brain_search.py) to every prompt.
