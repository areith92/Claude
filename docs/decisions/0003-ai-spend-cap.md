# 0003: AI spend cap
Decision: AI spend is capped at 5 GBP a month (per-agent caps inside that). run_agent.py refuses any call whose worst-case cost would pass a cap.
Alerts: warning at 80 percent and a stop alert at the cap, shown on the dashboard and raised as a GitHub issue.
Why: the owner wants a hard limit with an alert. Costs are estimates, so the Anthropic Console spend limit is the independent backstop.
