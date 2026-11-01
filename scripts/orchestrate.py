#!/usr/bin/env python3
"""Orchestrator helper: plan, queue, review, digest and record decisions. Proposals only.

Free (manual) flow:
  python scripts/orchestrate.py plan --goal "Draft the first three listings"
  python scripts/orchestrate.py ingest inbox/<plan reply>.md --delegate
  python scripts/orchestrate.py review            (optional)
  python scripts/orchestrate.py digest
  python scripts/orchestrate.py decide T-YYYYMMDD-001 approved --reason "why"
  python scripts/orchestrate.py complete T-YYYYMMDD-001
  python scripts/orchestrate.py status
Every model call goes through scripts/run_agent.py, so pause, enabled flags, PII and budget checks still apply.
"""
import argparse
import datetime
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import yaml  # noqa: E402
from check_budget import ROOT, load_yaml, month_totals  # noqa: E402
from pii_guard import find_pii  # noqa: E402

QUEUE = ROOT / "operations" / "tasks" / "queue.yml"
TIERS = ("auto", "needs_approval", "needs_owner_and_accountant")  # 'never' tasks are refused
SEVERITY = {t: i for i, t in enumerate(TIERS)}
FENCE = "`" * 3

PLAN_TASK = (
    "Plan the next piece of work. Owner's goal: {goal}\n"
    "Choose at most {n} tasks. Only use agents marked enabled in the context. Never delegate to the orchestrator.\n"
    "Prefer cheap, high-volume work for gemini agents. Do not repeat rejected or deferred work.\n"
    "In the Proposal section include exactly one fenced json block shaped like this:\n"
    '{"tasks": [{"agent": "listings", "objective": "what to do", "why": "one line", '
    '"approval_tier": "auto or needs_approval or needs_owner_and_accountant"}], "notes_for_next_run": "short note"}\n'
    "Use order IDs only. No personal data. If nothing useful can be planned, return an empty tasks list and say why."
)
REVIEW_TASK = (
    "Review the proposals below as the orchestrator, using your review rubric. For each task give a verdict "
    "(ready_for_owner, rework or reject), the approval tier you think is correct under governance/approval-tiers.yml, "
    "policy conflicts, risks and a one-line recommendation. Finish with a ranked list of what the owner should read first. "
    "No personal data."
)


def now():
    return datetime.datetime.now(datetime.timezone.utc)


def settings():
    p = ROOT / "agents" / "orchestrator" / "settings.yml"
    s = (yaml.safe_load(p.read_text()) or {}) if p.exists() else {}
    return {"max_tasks_per_run": 3, "max_review_chars_per_reply": 6000, **s}


def load_queue():
    q = (yaml.safe_load(QUEUE.read_text()) or {}) if QUEUE.exists() else {}
    q.setdefault("tasks", [])
    return q


def save_queue(q):
    QUEUE.parent.mkdir(parents=True, exist_ok=True)
    QUEUE.write_text("# Orchestrator task queue. Edited by scripts/orchestrate.py. No personal data.\n"
                     + yaml.safe_dump(q, sort_keys=False, allow_unicode=True))


def extract_json(text):
    """Finds the plan: a fenced json block first, then the widest {...} in the text."""
    candidates = []
    m = re.search(FENCE + r"(?:json)?\s*(\{.*?\})\s*" + FENCE, text, re.S)
    if m:
        candidates.append(m.group(1))
    if "{" in text and "}" in text:
        candidates.append(text[text.find("{"):text.rfind("}") + 1])
    for c in candidates:
        try:
            return json.loads(c)
        except ValueError:
            continue
    return None


def validate_plan(plan, agents_cfg, max_tasks, existing_ids, today=None):
    today = today or now().date()
    if not isinstance(plan, dict) or not isinstance(plan.get("tasks"), list):
        return [], ["No usable plan found (expected a json object with a 'tasks' list)."]
    problems, tasks = [], []
    raw_tasks = plan["tasks"]
    if len(raw_tasks) > max_tasks:
        problems.append(f"Plan had {len(raw_tasks)} tasks; only the first {max_tasks} were kept.")
    prefix = f"T-{today:%Y%m%d}-"
    n = sum(1 for i in existing_ids if str(i).startswith(prefix))
    for raw in raw_tasks[:max_tasks]:
        if not isinstance(raw, dict):
            problems.append("Skipped a task that was not an object.")
            continue
        agent = str(raw.get("agent", "")).strip()
        objective = str(raw.get("objective", "")).strip()
        why = str(raw.get("why", "")).strip()
        if agent == "orchestrator" or agent not in agents_cfg:
            problems.append(f"Skipped a task for unknown or not-allowed agent '{agent}'.")
            continue
        if not objective:
            problems.append(f"Skipped a {agent} task with no objective.")
            continue
        pii = find_pii(objective + " " + why)
        if pii:
            problems.append(f"Skipped a {agent} task: looks like personal data ({', '.join(pii)}).")
            continue
        tier = str(raw.get("approval_tier", "")).strip()
        if tier == "never":
            problems.append(f"Skipped a {agent} task: tier 'never' is not allowed.")
            continue
        if tier not in TIERS:
            tier = "needs_approval"  # unknown tier: be strict
        enabled = bool((agents_cfg.get(agent) or {}).get("enabled"))
        n += 1
        tasks.append({
            "id": f"{prefix}{n:03d}", "created": today.isoformat(), "agent": agent, "objective": objective,
            "why": why, "tier": tier, "status": "queued" if enabled else "blocked",
            "note": "" if enabled else f"{agent} is disabled in governance/status.yml; the owner can enable it by pull request.",
            "prompt_file": "", "reply_file": "", "flags": [],
        })
    return tasks, problems


def stated_tier(text):
    found = [t for t in TIERS if re.search(r"\b" + t + r"\b", text)]
    return max(found, key=SEVERITY.get) if found else None


def effective_tier(planned, stated):
    return max([planned] + ([stated] if stated else []), key=lambda t: SEVERITY.get(t, 1))


def can_decide(task, decision, accountant_ok=False):
    if task["status"] != "replied":
        return False, f"{task['id']} is '{task['status']}'. Only tasks with a reply waiting ('replied') can be decided. Run digest first."
    if decision == "approved" and "pii" in task.get("flags", []):
        return False, "The reply looks like it contains personal data. Remove it, then run digest again before approving."
    if decision == "approved" and task.get("tier_effective", task["tier"]) == "needs_owner_and_accountant" and not accountant_ok:
        return False, "This needs accountant sign-off. Get their OK (record it in the pull request), then add --accountant-ok."
    return True, ""


def run_agent(agent, task, input_file=None):
    cmd = [sys.executable, str(ROOT / "scripts" / "run_agent.py"), "--agent", agent, "--task", task]
    if input_file:
        cmd += ["--input-file", input_file]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    out = (r.stdout + r.stderr).strip()
    m = re.search(r"(?:Prompt|Proposal) written to (\S+)", out)
    return r.returncode, out, (m.group(1) if m else "")


def locate_reply(file_str):
    if not file_str:
        return None
    p = pathlib.Path(file_str)
    cand = ROOT / "inbox" / p.name if file_str.startswith("outbox/") else ROOT / file_str
    return cand if cand.exists() else None


def paused():
    return bool(load_yaml("governance/status.yml").get("paused"))


def build_context():
    status, routing = load_yaml("governance/status.yml"), load_yaml("models/routing.yml")["agents"]
    tiers, budgets = load_yaml("governance/approval-tiers.yml"), load_yaml("governance/budgets.yml")
    total, _ = month_totals()
    q = load_queue()
    lines = [
        "# Context for the orchestrator (no personal data)", "",
        f"Mode: {status.get('provider')}. Paused: {status.get('paused')}. Default dry run: {status.get('default_dry_run')}.",
        f"AI spend this month: {total:.2f} GBP. Total monthly cap: {budgets['ai_costs']['total_monthly_cap']} GBP (0 means no paid API use).",
        f"Thresholds: {tiers.get('thresholds')}", "", "## Agents (only enabled ones may be given tasks)"]
    for name, cfg in (status.get("agents") or {}).items():
        lines.append(f"- {name}: {'enabled' if cfg.get('enabled') else 'DISABLED'}, model {routing.get(name, {}).get('preferred', 'claude')}")
    open_tasks = [t for t in q["tasks"] if t["status"] in ("queued", "delegated", "replied", "blocked", "approved")]
    lines += ["", "## Open tasks"] + ([f"- {t['id']} {t['agent']} [{t['status']}] {t['objective']}" for t in open_tasks] or ["- none"])
    decisions = sorted((ROOT / "logs" / "decisions").glob("*.md"))[-10:]
    lines += ["", "## Recent decisions (do not repeat rejected or deferred work unless things changed)"]
    lines += [f"- {p.name}: " + " ".join(p.read_text().split())[:250] for p in decisions] or ["- none yet"]
    brain = sorted(p.name for p in (ROOT / "memory" / "brain").glob("*.md"))
    lines += ["", "## Memory notes available", ", ".join(brain) or "none yet"]
    if q.get("notes_for_next_run"):
        lines += ["", "## Your notes from the last run", str(q["notes_for_next_run"])]
    return "\n".join(lines) + "\n"


def with_tempfile(text, fn):
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
        f.write(text)
        path = f.name
    try:
        return fn(path)
    finally:
        os.unlink(path)


def cmd_plan(a):
    if paused():
        print("PAUSED: governance/status.yml has paused: true. Nothing was run.")
        return 0
    task = PLAN_TASK.replace("{goal}", a.goal).replace("{n}", str(settings()["max_tasks_per_run"]))
    rc, out, _ = with_tempfile(build_context(), lambda p: run_agent("orchestrator", task, p))
    print(out)
    return rc


def cmd_ingest(a):
    path = pathlib.Path(a.file)
    path = path if path.is_absolute() else ROOT / path
    plan = extract_json(path.read_text())
    status = load_yaml("governance/status.yml")
    q = load_queue()
    tasks, problems = validate_plan(plan, status.get("agents") or {}, settings()["max_tasks_per_run"], [t["id"] for t in q["tasks"]])
    q["tasks"] += tasks
    if isinstance(plan, dict):
        notes = str(plan.get("notes_for_next_run", ""))[:500]
        q["notes_for_next_run"] = "" if find_pii(notes) else notes
    if a.delegate and paused():
        problems.append("PAUSED: tasks were queued but not delegated.")
    elif a.delegate:
        for i, t in enumerate([t for t in tasks if t["status"] == "queued"]):
            if i:
                time.sleep(1.1)  # run_agent file names use whole seconds
            rc, out, f = run_agent(t["agent"], t["objective"] + (f"\nReason: {t['why']}" if t["why"] else ""))
            if rc != 0:
                t["status"], t["note"] = "failed", out[:200]
            elif not f:
                t["status"], t["note"] = "blocked", out[:200]
            elif f.startswith("outbox/"):
                t["status"], t["prompt_file"] = "delegated", f
            else:
                t["status"], t["reply_file"] = "replied", f
    save_queue(q)
    for t in tasks:
        print(f"{t['id']} {t['agent']} [{t['status']}, {t['tier']}] {t['objective']}" + (f"\n   -> {t['prompt_file']}" if t["prompt_file"] else ""))
    for p in problems:
        print("NOTE:", p)
    if not tasks:
        print("No tasks were added.")
    return 0


def cmd_review(a):
    if paused():
        print("PAUSED: governance/status.yml has paused: true. Nothing was run.")
        return 0
    q = load_queue()
    cap = settings()["max_review_chars_per_reply"]
    parts, ids = [], []
    for t in q["tasks"]:
        reply = locate_reply(t.get("prompt_file") or t.get("reply_file"))
        if t["status"] in ("delegated", "replied") and reply and not find_pii(reply.read_text()):
            parts.append(f"### {t['id']} ({t['agent']}, planned tier {t['tier']})\nTask: {t['objective']}\nReply:\n{reply.read_text()[:cap]}")
            ids.append(t["id"])
    if not ids:
        print("Nothing to review yet: no replies saved in inbox/ (or they contain personal data).")
        return 0
    rc, out, f = with_tempfile("\n\n".join(parts) + "\n", lambda p: run_agent("orchestrator", REVIEW_TASK, p))
    print(out)
    if rc == 0 and f:
        q["review"] = {"prompt_file": f, "task_ids": ids}
        save_queue(q)
    return rc


def cmd_digest(a):
    q, status = load_queue(), load_yaml("governance/status.yml")
    fyi = []
    for t in q["tasks"]:
        if t["status"] not in ("delegated", "replied"):
            continue
        reply = locate_reply(t.get("prompt_file") or t.get("reply_file"))
        if not reply:
            continue
        text = reply.read_text()
        stated = stated_tier(text)
        eff = effective_tier(t["tier"], stated)
        flags = (["pii"] if find_pii(text) else []) + ([] if stated else ["no tier stated"]) \
            + ([f"tier mismatch (planned {t['tier']}, reply says {stated})"] if stated and stated != t["tier"] else [])
        t.update(reply_file=str(reply.relative_to(ROOT)), tier_effective=eff, flags=flags, status="replied")
        if eff == "auto" and not flags:
            t["status"] = "done"
            fyi.append(t)
    total, _ = month_totals()
    cap = load_yaml("governance/budgets.yml")["ai_costs"]["total_monthly_cap"]
    L = [f"# Owner digest {now():%Y-%m-%d %H:%M} UTC", "",
         f"Mode: {status.get('provider')} | Paused: {status.get('paused')} | AI spend this month: {total:.2f} GBP of {cap} GBP cap", "",
         "## 1. Decisions needed"]
    need = sorted([t for t in q["tasks"] if t["status"] == "replied"],
                  key=lambda t: (-SEVERITY.get(t.get("tier_effective", t["tier"]), 1), t["id"]))
    for t in need:
        L += [f"### {t['id']} {t['agent']} (tier: {t.get('tier_effective', t['tier'])})", f"Task: {t['objective']}",
              f"Reply: {t['reply_file']}"]
        if t["flags"]:
            L.append("Flags: " + "; ".join(t["flags"]))
        L += [f"Decide: python scripts/orchestrate.py decide {t['id']} approved|rejected|deferred --reason \"why\"", ""]
    if not need:
        L += ["Nothing waiting.", ""]
    L += ["## 2. Approved: carry out by hand, then mark complete"]
    L += [f"- {t['id']} {t['agent']}: {t['objective']}  (python scripts/orchestrate.py complete {t['id']})"
          for t in q["tasks"] if t["status"] == "approved"] or ["- none"]
    L += ["", "## 3. Waiting on you: paste the prompt, save the reply in inbox/ with the same file name"]
    L += [f"- {t['id']}: {t['prompt_file']}" for t in q["tasks"] if t["status"] == "delegated"] or ["- none"]
    L += ["", "## 4. FYI: auto tier, no approval needed"] + ([f"- {t['id']} {t['agent']}: {t['objective']} ({t['reply_file']})" for t in fyi] or ["- none"])
    L += ["", "## 5. Blocked or failed"]
    L += [f"- {t['id']} {t['agent']} [{t['status']}]: {t['note']}" for t in q["tasks"] if t["status"] in ("blocked", "failed")] or ["- none"]
    rv = q.get("review") or {}
    rv_reply = locate_reply(rv.get("prompt_file", ""))
    if rv_reply:
        L += ["", "## 6. Orchestrator review", rv_reply.read_text()[:4000]]
    elif rv:
        L += ["", f"## 6. Orchestrator review: paste {rv['prompt_file']} and save the reply in inbox/ with the same name, then run digest again"]
    L += ["", "## Next", "Open a pull request with this digest and any decision files. Merging it is your sign-off record."]
    out = ROOT / "reports" / "digests" / f"{now():%Y-%m-%d-%H%M}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(L) + "\n")
    save_queue(q)
    print(f"Digest written to {out.relative_to(ROOT)}")
    return 0


def cmd_decide(a):
    q = load_queue()
    t = next((x for x in q["tasks"] if x["id"] == a.task_id), None)
    if not t:
        print(f"No task {a.task_id}")
        return 2
    if find_pii(a.reason or ""):
        print("Refused: the reason looks like it contains personal data.")
        return 3
    ok, msg = can_decide(t, a.decision, a.accountant_ok)
    if not ok:
        print("Refused:", msg)
        return 4
    today = now().date()
    d = ROOT / "logs" / "decisions"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{today}-{t['id']}.md").write_text(
        f"# Decision {t['id']}: {a.decision}\n- Date: {today}\n- Agent: {t['agent']}\n- Task: {t['objective']}\n"
        f"- Tier: {t.get('tier_effective', t['tier'])}\n- Accountant OK: {'yes' if a.accountant_ok else 'no'}\n"
        f"- Reason: {a.reason or 'none given'}\n- Proposal: {t['reply_file']}\n\n"
        "Nothing is done automatically. Carry out approved work by hand.\n")
    t["status"], t["decided"] = a.decision, today.isoformat()
    save_queue(q)
    print(f"Recorded: {t['id']} {a.decision}. Nothing was published or changed on eBay.")
    return 0


def cmd_complete(a):
    q = load_queue()
    t = next((x for x in q["tasks"] if x["id"] == a.task_id), None)
    if not t or t["status"] != "approved":
        print("Only approved tasks can be marked complete.")
        return 2
    t["status"] = "completed"
    save_queue(q)
    print(f"{t['id']} marked completed.")
    return 0


def cmd_status(a):
    q = load_queue()
    counts = {}
    for t in q["tasks"]:
        counts[t["status"]] = counts.get(t["status"], 0) + 1
    print("Queue:", counts or "empty")
    for t in q["tasks"]:
        print(f"{t['id']} {t['agent']} [{t['status']}] {t['objective']}")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan")
    p.add_argument("--goal", required=True)
    p = sub.add_parser("ingest")
    p.add_argument("file")
    p.add_argument("--delegate", action="store_true")
    sub.add_parser("review")
    sub.add_parser("digest")
    p = sub.add_parser("decide")
    p.add_argument("task_id")
    p.add_argument("decision", choices=["approved", "rejected", "deferred"])
    p.add_argument("--reason")
    p.add_argument("--accountant-ok", action="store_true")
    p = sub.add_parser("complete")
    p.add_argument("task_id")
    sub.add_parser("status")
    a = ap.parse_args()
    return {"plan": cmd_plan, "ingest": cmd_ingest, "review": cmd_review, "digest": cmd_digest,
            "decide": cmd_decide, "complete": cmd_complete, "status": cmd_status}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
