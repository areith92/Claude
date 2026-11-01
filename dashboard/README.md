# Dashboard (Commerce OS)
A static page: no server, no build step, no customer data. Open dashboard/index.html or serve the folder.
Pages: Home, Tasks (decisions with copyable commands), Finances (AI spend and caps), Agents, Org Chart, Knowledge Core (radial map and department
drill-downs), Health, Connections, Roadmap.
Data comes from scripts/build_dashboard.py, which writes status.json and status.js from governance/, models/, operations/tasks/, logs/ and
memory/brain/. The Budget alert workflow rebuilds them when logs/costs.csv changes and once a day.
Layout of departments and tools is in dashboard/departments.yml. Every agent in governance/status.yml must appear there once.
View in a Codespace: python3 scripts/build_dashboard.py, then python3 -m http.server 8000 --directory dashboard, and open the forwarded port.
