# 0005: SOPs live in the brain
Decision: one SOP per agent in memory/brain/sops/. run_agent.py adds the agent's SOP and up to two related notes (keyword search) to every prompt, only if the agent's permissions allow reading memory/brain/.
Why: one place for instructions that agents and people can read, search and change by pull request. The model cannot browse the repo itself, so the script does the search.
GBrain is not connected. The files are plain markdown, so GBrain can be pointed at memory/brain/ later without changing them.
