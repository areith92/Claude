#!/usr/bin/env python3
"""Builds dashboard/status.json and dashboard/status.js from the repo's own files. No customer data, no timestamps.
Usage: python scripts/build_dashboard.py [--alert-file /tmp/alert.md]
With --alert-file, an alert message is written there when AI spend needs attention (the file is empty otherwise)."""
import argparse
import csv
import datetime
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import yaml  # noqa: E402
from budget_guard import read_stop_marker, spend_state  # noqa: E402
from check_budget import ROOT, load_yaml, month_totals  # noqa: E402

PHASES = [
    {"n": 1, "name": "Draft only", "text": "Agents write proposals. You approve and act by hand."},
    {"n": 2, "name": "Read-only eBay API", "text": "Agents read orders, listings and traffic. Nothing is changed on eBay."},
    {"n": 3, "name": "Limited live actions", "text": "Chosen actions run behind the approval tiers, one at a time, by pull request."},
    {"n": 4, "name": "Shopify channel", "text": "A second sales channel, after owner and accountant approval."},
]
TASK_FIELDS = ("id", "created", "agent", "objective", "why", "tier", "tier_effective", "status", "note",
               "prompt_file", "reply_file", "flags", "decided")


def safe_yaml(rel):
    p = ROOT / rel
    try:
        return yaml.safe_load(p.read_text()) or {}
    except (OSError, yaml.YAMLError):
        return {}


def role_of(agent):
    p = ROOT / "agents" / agent / "prompt.md"
    m = re.search(r"## Role\n(.+?)(?:\n\s*\n|\Z)", p.read_text(), re.S) if p.exists() else None
    return " ".join(m.group(1).split()) if m else ""


def sop_view(agent):
    p = ROOT / "memory" / "brain" / "sops" / f"{agent}.md"
    path = f"memory/brain/sops/{agent}.md"
    if not p.exists():
        return {"exists": False, "path": path}
    secs = dict(re.findall(r"^## (.+?)\n(.*?)(?=^## |\Z)", p.read_text(), re.S | re.M))

    def lines(k):
        return [re.sub(r"^(\d+\.|-)\s*", "", ln).strip() for ln in secs.get(k, "").splitlines() if ln.strip()]

    def para(k):
        return " ".join(secs.get(k, "").split())
    return {"exists": True, "path": path, "purpose": para("Purpose"), "steps": lines("Steps"), "tier": para("Approval tier"),
            "escalate": lines("Escalate to the owner"), "never": para("Never")}


STAGE_DONE = {"raised": 2, "diagnosing": 2, "fix_proposed": 3, "fix_failed": 3, "fix_tested": 4, "needs_owner": 4,
              "ready_to_ship": 6, "resolved": 7, "abandoned": 2}


def incident_next(i):
    iid, s, b, ts = i["id"], i["status"], i.get("branch", ""), "python3 scripts/techsupport.py"
    if s == "raised" or (s == "needs_owner" and not i.get("fix")):
        return [{"label": "Let Tech Support fix it (uses your Claude key)", "cmd": f"{ts} run {iid}"},
                {"label": "Or the free route: prepare a prompt to paste into Claude", "cmd": f"{ts} run {iid} --manual"},
                {"label": "Or give up on it", "cmd": f'{ts} abandon {iid} --reason "why"'}]
    if s == "diagnosing":
        return [{"label": "After saving Claude's reply in inbox/", "cmd": f"{ts} ingest {iid} inbox/<file name>"}]
    if s == "fix_proposed":
        return [{"label": "Test the fix in a scratch copy", "cmd": f"{ts} test {iid}"}]
    if s == "fix_failed":
        return [{"label": "Try again", "cmd": f"{ts} run {iid}"}, {"label": "Or give up on it", "cmd": f'{ts} abandon {iid} --reason "why"'}]
    if s == "fix_tested":
        return [{"label": "Apply it on a branch and verify it in your working tree", "cmd": f"{ts} implement {iid}"}]
    if s == "needs_owner":
        return [{"label": "Review the change, then apply it on a branch", "cmd": f"{ts} implement {iid} --include-owner-files"}]
    if s == "ready_to_ship":
        return [{"label": "1. Push the branch", "cmd": f"git push -u origin {b}"},
                {"label": "2. Open the pull request", "cmd": f'gh pr create --base main --head {b} --title "Fix {iid}" --body "Tech Support fix"'},
                {"label": "3. After you merge it on GitHub: pull it down and verify", "cmd": f"git checkout main && git pull && {ts} resolve {iid}"}]
    return []


def incident_view(i):
    return {"id": i["id"], "created": i.get("created"), "title": i["title"], "severity": i.get("severity", "medium"),
            "check": i.get("check", ""), "status": i["status"], "stage": STAGE_DONE.get(i["status"], 2),
            "evidence": (i.get("evidence") or "")[-1500:], "diagnosis": i.get("diagnosis", ""), "root_cause": i.get("root_cause", ""),
            "fix": i.get("fix"), "test": i.get("test") and {"passed": i["test"].get("passed"), "summary": i["test"].get("summary", "")},
            "live": i.get("live"), "branch": i.get("branch", ""), "attempts": i.get("attempts", 0),
            "history": (i.get("history") or [])[-6:], "next": incident_next(i)}


def build():
    status = load_yaml("governance/status.yml")
    caps = load_yaml("governance/budgets.yml")["ai_costs"]
    routing = safe_yaml("models/routing.yml")
    layout = safe_yaml("dashboard/departments.yml")
    total, per_agent = month_totals()
    cap = caps["total_monthly_cap"]
    alert_at = caps.get("alert_at_percent", 80)
    marker = read_stop_marker(ROOT)
    state = spend_state(total, cap, alert_at, bool(marker and marker.get("scope") == "total"))
    month = datetime.date.today().strftime("%Y-%m")
    rows = []
    path = ROOT / "logs" / "costs.csv"
    if path.exists():
        with path.open(newline="") as f:
            rows = list(csv.DictReader(f))
    qp = ROOT / "operations" / "tasks" / "queue.yml"
    raw_tasks = ((yaml.safe_load(qp.read_text()) or {}).get("tasks") or []) if qp.exists() else []
    tasks = [{k: t.get(k) for k in TASK_FIELDS if k in t} for t in raw_tasks]
    queue = {}
    for t in tasks:
        queue[t["status"]] = queue.get(t["status"], 0) + 1
    digests = sorted((ROOT / "reports" / "digests").glob("*.md"))
    pct = round(total / cap * 100, 1) if cap > 0 else 0

    # agents and departments
    conductor = layout.get("conductor", "orchestrator")
    agent_cfg = status.get("agents") or {}
    models = routing.get("models") or {}
    dept_of = {a: d for d, v in (layout.get("departments") or {}).items() for a in v.get("agents", [])}
    agents = []
    for name, cfg in agent_cfg.items():
        pref = (routing.get("agents") or {}).get(name, {}).get("preferred", "claude")
        agents.append({
            "name": name, "role": role_of(name), "sop": sop_view(name), "enabled": bool(cfg.get("enabled")),
            "dept": "conductor" if name == conductor else dept_of.get(name, "unassigned"),
            "model": (models.get(pref) or {}).get("model", pref), "provider": pref,
            "mode": cfg.get("provider", status.get("provider", "manual")),
            "dry_run": bool(cfg.get("dry_run", status.get("default_dry_run", True))),
            "spent_gbp": round(per_agent.get(name, 0), 4),
            "cap_gbp": caps["per_agent_monthly_cap"].get(name, 0),
        })
    departments = [{"id": d, "label": v.get("label", d), "color": v.get("color", "#8899aa"),
                    "agents": [a for a in v.get("agents", []) if a in agent_cfg], "tools": v.get("tools", [])}
                   for d, v in (layout.get("departments") or {}).items()]
    if any(a["dept"] == "unassigned" for a in agents):
        departments.append({"id": "unassigned", "label": "Unassigned", "color": "#8899aa",
                            "agents": [a["name"] for a in agents if a["dept"] == "unassigned"], "tools": []})

    approvals = []
    for t in tasks:
        if t["status"] == "replied":
            cmd = f"python3 scripts/orchestrate.py decide {t['id']}"
            approvals.append({"id": t["id"], "agent": t["agent"], "objective": t["objective"],
                              "tier": t.get("tier_effective", t["tier"]), "flags": t.get("flags", []),
                              "reply_file": t.get("reply_file", ""),
                              "approve": cmd + ' approved --reason "why"', "reject": cmd + ' rejected --reason "why"',
                              "defer": cmd + " deferred"})

    ebay, shop = safe_yaml("channels/ebay-uk/config.yml"), safe_yaml("channels/shopify/config.yml")
    used = {p: [a["name"] for a in agents if a["mode"] == "api" and a["provider"] == p] for p in ("claude", "gemini")}
    connections = [
        {"id": "claude", "name": "Claude API", "status": "in use" if used["claude"] else "not in use",
         "detail": "Agents on the API: " + (", ".join(used["claude"]) or "none") + ". Key lives in GitHub secrets, never in the repo."},
        {"id": "gemini", "name": "Gemini API", "status": "in use" if used["gemini"] else "not in use",
         "detail": "Agents on the API: " + (", ".join(used["gemini"]) or "none") + ". Free tier."},
        {"id": "ebay", "name": "eBay UK", "status": (ebay.get("api") or {}).get("mode", "manual") + " mode",
         "detail": "Draft only. Needs " + ", ".join((ebay.get("api") or {}).get("secrets", [])) + " as GitHub secrets for Phase 2."},
        {"id": "shopify", "name": "Shopify", "status": "enabled" if shop.get("enabled") else "not enabled",
         "detail": "Reserved for Phase 4. Needs owner and accountant approval."},
    ]
    bdir = ROOT / "memory" / "brain"
    brain = sorted(p.relative_to(bdir).as_posix() for p in bdir.rglob("*.md") if p.name != "README.md") if bdir.exists() else []

    iq = safe_yaml("operations/incidents/queue.yml")
    incidents = [incident_view(i) for i in (iq.get("incidents") or [])]

    alerts = []
    if state == "stopped":
        alerts.append(f"AI spend stopped: {total:.2f} of {cap} GBP used in {month}. Agents will not call paid models until next month, or until the cap is raised in governance/budgets.yml.")
    elif state == "warning":
        alerts.append(f"AI spend warning: {pct:.0f}% of the {cap} GBP monthly cap is used ({total:.2f} GBP).")
    elif state == "off":
        alerts.append("Paid API use is off: the monthly cap in governance/budgets.yml is 0.")
    if marker and marker.get("scope") == "agent":
        alerts.append(f"{marker['agent']} reached its own monthly cap ({marker['spent_gbp']} of {marker['cap_gbp']} GBP).")
    if status.get("paused"):
        alerts.append("All agents are paused (kill switch).")
    open_inc = [i for i in incidents if i["status"] not in ("resolved", "abandoned")]
    if open_inc:
        alerts.append(f"Tech Support: {len(open_inc)} open incident(s)" +
                      (f", {sum(1 for i in open_inc if i['status'] == 'ready_to_ship')} fix ready to ship." if any(i["status"] == "ready_to_ship" for i in open_inc) else "."))

    title = ""
    if state == "stopped":
        title = f"AI budget STOPPED {month}"
    elif state == "warning":
        title = f"AI budget warning {month}"
    elif marker and marker.get("scope") == "agent":
        title = f"AI agent cap reached {marker['agent']} {month}"

    data = {
        "month": month,
        "as_of": rows[-1]["date"] if rows else None,
        "mode": {"provider": status.get("provider"), "paused": bool(status.get("paused")),
                 "dry_run_default": bool(status.get("default_dry_run"))},
        "spend": {"spent_gbp": round(total, 4), "cap_gbp": cap, "remaining_gbp": round(max(cap - total, 0), 4),
                  "percent": pct, "state": state, "alert_at_percent": alert_at},
        "per_agent": [{"agent": a, "spent_gbp": round(per_agent.get(a, 0), 4), "cap_gbp": c}
                      for a, c in caps["per_agent_monthly_cap"].items() if c or per_agent.get(a)],
        "alerts": alerts,
        "queue": queue,
        "latest_digest": digests[-1].name if digests else None,
        "recent_costs": [{"date": r["date"], "agent": r["agent"], "model": r["model"],
                          "tokens": int(r["input_tokens"] or 0) + int(r["output_tokens"] or 0),
                          "cost_gbp": float(r["cost_gbp"] or 0)} for r in rows[-10:]][::-1],
        "conductor": conductor,
        "agents": agents,
        "departments": departments,
        "tasks": tasks,
        "approvals": approvals,
        "connections": connections,
        "phases": {"current": 1, "list": PHASES},
        "brain": {"count": len(brain), "notes": brain[:40]},
        "incidents": incidents,
    }
    body = "# " + title + "\n\n" + "\n".join("- " + x for x in alerts) + \
           "\n\nTo continue before next month, raise total_monthly_cap in governance/budgets.yml by pull request.\n" if title else ""
    return data, body


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--alert-file")
    a = ap.parse_args()
    data, body = build()
    out = ROOT / "dashboard"
    out.mkdir(exist_ok=True)
    text = json.dumps(data, indent=2) + "\n"
    (out / "status.json").write_text(text)
    (out / "status.js").write_text("window.DASHBOARD = " + text.rstrip() + ";\n")
    if a.alert_file:
        open(a.alert_file, "w").write(body)
    print(f"Dashboard data written. AI spend {data['spend']['spent_gbp']} of {data['spend']['cap_gbp']} GBP ({data['spend']['state']}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
