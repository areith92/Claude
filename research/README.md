# Research
Local working folder for the product research pipeline (scripts/research.py). Dossiers, images, launch packs and exports are created here and are NOT committed
(see .gitignore): saved images may belong to other people, and shared storage (Supabase) comes later.
See it with demo data: python3 scripts/demo_research.py (remove with --clean).
Start: python3 scripts/research.py template, fill in the CSV, then python3 scripts/research.py import <file>.
Approve or deny on the dashboard: python3 scripts/dashboard_server.py, then open Approvals.
