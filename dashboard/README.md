# Dashboard
dashboard/index.html shows AI spend against the monthly cap, alerts, spend by agent, task counts and recent AI calls.
Data comes from scripts/build_dashboard.py (files status.json and status.js; no customer data). The Budget alert workflow rebuilds them
when logs/costs.csv changes and once a day.
To view it in a Codespace: python3 scripts/build_dashboard.py, then python3 -m http.server 8000 --directory dashboard and open the forwarded port.
