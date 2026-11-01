# 0002: Orchestrator design
Decision: the orchestrator plans, delegates, reviews and produces one owner digest per run, driven by scripts/orchestrate.py.
It reuses scripts/run_agent.py for every model call, so pause, enabled flags, personal-data checks, budgets and manual mode all still apply.
Why: one ranked list of decisions for the owner, no live actions, and no paid API needed to start.
Limits: at most 3 tasks per plan; tasks tagged never are refused; accountant-tier approvals need an explicit flag.
