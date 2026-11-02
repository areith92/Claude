#!/usr/bin/env python3
"""Tech Support. The monitor flags a problem, Claude proposes a fix, the fix is tested in a scratch copy,
applied on a branch, checked again in your working tree and handed to you to push. Nothing is pushed or merged here.

  python scripts/techsupport.py detect                run the health checks and raise incidents
  python scripts/techsupport.py raise --title "..." --details "..."
  python scripts/techsupport.py run INC-...           diagnose, test, implement and verify in one go
  python scripts/techsupport.py ingest INC-... FILE   use a reply you pasted back (manual mode)
  python scripts/techsupport.py test INC-...          test the proposed fix in a scratch copy
  python scripts/techsupport.py implement INC-... [--include-owner-files]
  python scripts/techsupport.py resolve INC-...       after you merged and pulled: verify and close
  python scripts/techsupport.py status | abandon INC-... --reason "..."
"""
import argparse
import datetime
import json
import os
import pathlib
import posixpath
import re
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import yaml  # noqa: E402
import monitor_checks as mc  # noqa: E402
from check_budget import ROOT, load_yaml  # noqa: E402
from pii_guard import find_pii  # noqa: E402

QUEUE = ROOT / "operations" / "incidents" / "queue.yml"
FIXES = ROOT / "operations" / "incidents" / "fixes"
FENCE = "`" * 3
CLOSED = ("resolved", "abandoned")
REFUSE = re.compile(r"^(\.git/|\.env|logs/|inbox/|outbox/|reports/|operations/|memory/|dashboard/status\.|.*\.(pem|key)$)")
OWNER = re.compile(r"^(governance/|\.github/|CODEOWNERS$|models/|channels/|CLAUDE\.md$|SECURITY\.md$|agents/[^/]+/(permissions|tools)\.yml$|"
                   r"scripts/(budget_guard|pii_guard|check_secrets|check_budget|validate_config|run_agent|techsupport|monitor_checks)\.py$)")
ALLOWED = re.compile(r"^(scripts/|tests/|docs/|dashboard/|agents/[^/]+/prompt\.md$)")
SECRET = re.compile(r"sk-ant-[A-Za-z0-9_-]{10,}|AIza[0-9A-Za-z_-]{30,}|gh[pousr]_[A-Za-z0-9]{20,}")
IGNORED_DIRTY = ("operations/incidents/", "outbox/", "inbox/", "logs/", "reports/", "dashboard/status.")
TASK = (
    "Diagnose incident {id}: {title}. Find the root cause and propose the smallest safe fix, using the evidence and files below.\n"
    "In the Proposal section include exactly one fenced json block shaped like this:\n"
    '{"diagnosis": "what is wrong", "root_cause": "why", "risk": "low or medium or high", "changes": '
    '[{"path": "scripts/example.py", "op": "replace", "old": "exact text that appears once", "new": "replacement"}], '
    '"verify": "which check should pass"}\n'
    "Follow your rules: at most 4 files, no weakening of tests or safety checks, no personal data or keys. "
    "If you cannot fix it safely, return an empty changes list and explain."
)


def today():
    return datetime.date.today().isoformat()


def settings():
    p = ROOT / "agents" / "techsupport" / "settings.yml"
    s = (yaml.safe_load(p.read_text()) or {}) if p.exists() else {}
    return {"max_attempts": 2, "max_files": 4, "max_file_bytes": 40000, "evidence_lines": 40, **s}


def load():
    q = (yaml.safe_load(QUEUE.read_text()) or {}) if QUEUE.exists() else {}
    q.setdefault("incidents", [])
    return q


def save(q):
    QUEUE.parent.mkdir(parents=True, exist_ok=True)
    QUEUE.write_text("# Tech Support incident queue. Edited by scripts/techsupport.py. No personal data.\n"
                     + yaml.safe_dump(q, sort_keys=False, allow_unicode=True))


def get(q, iid):
    inc = next((i for i in q["incidents"] if i["id"] == iid), None)
    if not inc:
        sys.exit(f"No incident {iid}. Run: python3 scripts/techsupport.py status")
    return inc


def note(inc, status, text):
    inc["status"] = status
    inc.setdefault("history", []).append({"date": today(), "status": status, "note": text[:200]})


def redact(text):
    return "\n".join("[line removed: looks like personal data]" if find_pii(line) else line for line in text.splitlines())


def extract_json(text):
    cands = []
    m = re.search(FENCE + r"(?:json)?\s*(\{.*?\})\s*" + FENCE, text, re.S)
    if m:
        cands.append(m.group(1))
    if "{" in text and "}" in text:
        cands.append(text[text.find("{"):text.rfind("}") + 1])
    for c in cands:
        try:
            return json.loads(c)
        except ValueError:
            continue
    return None


def classify(path):
    if REFUSE.match(path):
        return "refuse"
    if OWNER.match(path):
        return "owner"
    return "apply" if ALLOWED.match(path) else "refuse"


def validate_fix(plan, cfg):
    if not isinstance(plan, dict) or not isinstance(plan.get("changes"), list):
        return [], ["No usable fix found (expected json with a 'changes' list)."]
    problems, changes, raw = [], [], plan["changes"]
    if len(raw) > cfg["max_files"]:
        problems.append(f"The fix touched {len(raw)} files; only the first {cfg['max_files']} were kept.")
        raw = raw[:cfg["max_files"]]
    for c in raw:
        if not isinstance(c, dict):
            problems.append("Skipped a change that was not an object.")
            continue
        path = posixpath.normpath(str(c.get("path", "")).strip().replace("\\", "/"))
        if path in ("", ".") or path.startswith("/") or ".." in path.split("/"):
            problems.append(f"Refused an unsafe path: {c.get('path')!r}.")
            continue
        kind = classify(path)
        if kind == "refuse":
            problems.append(f"Refused {path}: Tech Support may not change that file.")
            continue
        op = c.get("op")
        if op == "replace" and isinstance(c.get("old"), str) and c["old"] and isinstance(c.get("new"), str):
            item, text = {"path": path, "op": op, "old": c["old"], "new": c["new"]}, c["new"]
            if path.startswith("tests/") and c["new"].count("assert") < c["old"].count("assert"):
                kind = "owner"
                item["note"] = "removes assertions from a test"
        elif op == "write" and isinstance(c.get("content"), str):
            item, text = {"path": path, "op": op, "content": c["content"]}, c["content"]
        else:
            problems.append(f"Skipped a change to {path}: it needs op replace (old and new) or write (content).")
            continue
        if len(text.encode()) > cfg["max_file_bytes"]:
            problems.append(f"Refused {path}: the change is too large.")
        elif SECRET.search(text):
            problems.append(f"Refused {path}: the change looks like it contains a key or secret.")
        elif find_pii(text):
            problems.append(f"Refused {path}: the change looks like it contains personal data.")
        else:
            item["kind"] = kind
            changes.append(item)
    return changes, problems


def apply_changes(root, changes):
    for c in changes:
        f = (root / c["path"]).resolve()
        if root.resolve() not in f.parents:
            raise ValueError(f"{c['path']} is outside the repo")
        if c["op"] == "replace":
            if not f.exists():
                raise ValueError(f"{c['path']} does not exist")
            t = f.read_text()
            if t.count(c["old"]) != 1:
                raise ValueError(f"{c['path']}: the text to replace must appear exactly once (found {t.count(c['old'])})")
            f.write_text(t.replace(c["old"], c["new"]))
        else:
            if f.exists() and c["path"].startswith("tests/"):
                raise ValueError(f"{c['path']} already exists: change tests with replace, not write")
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(c["content"])


def save_fix(inc, changes, plan):
    FIXES.mkdir(parents=True, exist_ok=True)
    (FIXES / f"{inc['id']}.json").write_text(json.dumps({"changes": changes, "verify": plan.get("verify", "")}, indent=2) + "\n")
    inc["fix"] = {"files": [{"path": c["path"], "op": c["op"], "kind": c["kind"], "note": c.get("note", "")} for c in changes]}


def load_fix(inc):
    p = FIXES / f"{inc['id']}.json"
    return json.loads(p.read_text())["changes"] if p.exists() else []


def git(*args, cwd=None):
    return subprocess.run(["git", *args], cwd=str(cwd or ROOT), capture_output=True, text=True)


def dirty():
    out = git("status", "--porcelain").stdout.splitlines()
    return [ln for ln in out if not ln[3:].startswith(IGNORED_DIRTY)]


def run_pass(results, before, key):
    after = {r["key"]: r for r in results}
    regress = [k for k, r in after.items() if not r["ok"] and before.get(k)]
    own_ok = after[key]["ok"] if key in after else True
    return own_ok and not regress, own_ok, regress, after


def summary_line(results):
    return ", ".join(f"{r['key']} {'ok' if r['ok'] else 'FAILED'}" for r in results)


def next_ids(q):
    n = sum(1 for i in q["incidents"] if i["id"].startswith(f"INC-{today().replace('-', '')}-"))
    return f"INC-{today().replace('-', '')}-{n + 1:03d}"


def raise_incident(q, check, title, severity, evidence, source):
    inc = {"id": next_ids(q), "created": today(), "source": source, "check": check, "title": title, "severity": severity,
           "evidence": redact(evidence)[-3000:], "status": "raised", "attempts": 0, "occurrences": 1, "history": []}
    note(inc, "raised", f"Raised by {source}")
    q["incidents"].append(inc)
    return inc


def cmd_detect(a):
    q, cfg = load(), settings()
    results = mc.run_checks(ROOT, evidence_lines=cfg["evidence_lines"])
    for r in results:
        print(("PASS " if r["ok"] else "FAIL ") + r["key"] + ": " + r["title"])
        if r["ok"]:
            continue
        open_inc = next((i for i in q["incidents"] if i["check"] == r["key"] and i["status"] not in CLOSED), None)
        if open_inc:
            open_inc["occurrences"] += 1
            open_inc["evidence"] = redact(r["evidence"])[-3000:]
            print(f"     still open as {open_inc['id']} ({open_inc['status']})")
        else:
            inc = raise_incident(q, r["key"], "Check failing: " + r["title"], r["severity"], r["evidence"], "monitor")
            print(f"     RAISED {inc['id']}. Next: python3 scripts/techsupport.py run {inc['id']}")
    save(q)
    return 0


def cmd_raise(a):
    q = load()
    if find_pii(a.title + " " + a.details):
        print("Refused: that looks like personal data.")
        return 3
    inc = raise_incident(q, "manual", a.title, a.severity, a.details, "owner")
    save(q)
    print(f"RAISED {inc['id']}. Next: python3 scripts/techsupport.py run {inc['id']}")
    return 0


def candidate_files(evidence, limit=4):
    seen, out = set(), []
    for m in re.findall(r"[\w./-]+\.(?:py|yml|yaml|md|js|json|html|css)", evidence):
        m = m.lstrip("./")
        if m in seen or classify(m) == "refuse" or not (ROOT / m).is_file():
            continue
        seen.add(m)
        out.append(m)
    return out[:limit]


def build_context(inc):
    lines = [f"# Incident {inc['id']}", f"Failing check: {inc['check']} ({inc['title']})", f"Severity: {inc['severity']}", "",
             "## Evidence (last lines of the failing output)", redact(inc["evidence"])]
    if inc.get("last_failure"):
        lines += ["", "## Your previous attempt failed", inc.get("diagnosis", ""), "Why it failed:", redact(inc["last_failure"])]
    files = candidate_files(inc["evidence"] + " " + inc.get("last_failure", ""))
    if files:
        lines += ["", "## Relevant files (current contents)"]
        for f in files:
            lines += [f"### {f}", redact((ROOT / f).read_text()[:12000])]
    return "\n".join(lines) + "\n"


def call_techsupport(inc, manual):
    task = TASK.replace("{id}", inc["id"]).replace("{title}", inc["title"])
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
        f.write(build_context(inc))
        path = f.name
    try:
        cmd = [sys.executable, str(ROOT / "scripts" / "run_agent.py"), "--agent", "techsupport", "--task", task, "--input-file", path]
        r = subprocess.run(cmd + (["--manual"] if manual else []), capture_output=True, text=True, cwd=ROOT)
    finally:
        os.unlink(path)
    out = (r.stdout + r.stderr).strip()
    m = re.search(r"(?:Prompt|Proposal) written to (\S+)", out)
    return r.returncode, out, (m.group(1) if m else "")


def ingest_reply(inc, path, cfg):
    plan = extract_json(path.read_text())
    changes, problems = validate_fix(plan, cfg)
    for p in problems:
        print("NOTE:", p)
    if isinstance(plan, dict):
        inc["diagnosis"] = str(plan.get("diagnosis", ""))[:600]
        inc["root_cause"] = str(plan.get("root_cause", ""))[:600]
        inc["risk"] = str(plan.get("risk", ""))[:20]
    if not changes:
        note(inc, "needs_owner", "No safe fix was proposed. " + (inc.get("diagnosis") or "; ".join(problems))[:150])
        return False
    save_fix(inc, changes, plan)
    note(inc, "fix_proposed", f"Fix proposed: {len(changes)} file(s)")
    return True


def cmd_ingest(a):
    q, cfg = load(), settings()
    inc = get(q, a.id)
    path = pathlib.Path(a.file)
    ok = ingest_reply(inc, path if path.is_absolute() else ROOT / path, cfg)
    inc["reply_file"] = a.file
    save(q)
    print(f"{inc['id']}: {inc['status']}" + (f". Next: python3 scripts/techsupport.py test {inc['id']}" if ok else ""))
    return 0


def do_test(inc):
    changes = load_fix(inc)
    cfg = settings()
    before = {r["key"]: r["ok"] for r in mc.run_checks(ROOT, evidence_lines=cfg["evidence_lines"])}
    tmp = tempfile.mkdtemp(prefix="techsupport-")
    repo = pathlib.Path(tmp) / "repo"
    try:
        shutil.copytree(ROOT, repo, ignore=shutil.ignore_patterns(".git", "__pycache__", "node_modules"))
        subprocess.run(["git", "init", "-q"], cwd=repo)
        subprocess.run(["git", "add", "-A"], cwd=repo, capture_output=True)
        try:
            apply_changes(repo, changes)
        except ValueError as exc:
            inc["test"] = {"passed": False, "summary": f"The fix could not be applied: {exc}", "before": before}
            inc["last_failure"] = inc["test"]["summary"]
            return False
        results = mc.run_checks(repo, evidence_lines=cfg["evidence_lines"])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    passed, own_ok, regress, after = run_pass(results, before, inc["check"])
    inc["test"] = {"passed": passed, "before": before, "summary": "Scratch copy: " + summary_line(results)}
    if not passed:
        bad = [r for r in results if not r["ok"]]
        inc["last_failure"] = "\n".join(f"{r['key']}:\n{r['evidence']}" for r in bad)[-2500:]
    return passed


def cmd_test(a):
    q = load()
    inc = get(q, a.id)
    if not load_fix(inc):
        sys.exit("No proposed fix to test. Run: python3 scripts/techsupport.py run " + inc["id"])
    passed = do_test(inc)
    owner_only = bool(inc["fix"]["files"]) and all(f["kind"] == "owner" for f in inc["fix"]["files"])
    if passed:
        note(inc, "needs_owner" if owner_only else "fix_tested", inc["test"]["summary"])
    else:
        inc["attempts"] += 1
        note(inc, "fix_failed", inc["test"]["summary"])
    save(q)
    print(f"{inc['id']}: {inc['status']}. {inc['test']['summary']}")
    return 0 if passed else 1


def finish_message(inc):
    b = inc["branch"]
    print(f"\nFIX READY: {inc['id']} {inc['title']}\n  Branch: {b} ({len(inc['fix']['files'])} file(s) changed)\n  {inc['test']['summary']}\n  "
          f"{inc['live']['summary']}\n\nTo ship it:\n  git push -u origin {b}\n  gh pr create --base main --head {b} --title \"Fix {inc['id']}: {inc['title']}\" "
          f"--body \"Tech Support fix for {inc['id']}. Tested in a scratch copy and verified in the working tree.\"\n"
          f"Merge the pull request on GitHub, then:\n  git checkout main && git pull\n  python3 scripts/techsupport.py resolve {inc['id']}")


def do_implement(inc, include_owner):
    if git("rev-parse", "--is-inside-work-tree").stdout.strip() != "true":
        sys.exit("This is not a git working tree.")
    if dirty():
        sys.exit("You have uncommitted changes. Commit or stash them first:\n" + "\n".join(dirty()[:8]))
    base = git("branch", "--show-current").stdout.strip()
    branch = "fix/" + inc["id"].lower()
    r = git("checkout", "-b", branch)
    if r.returncode:
        sys.exit("Could not create the branch: " + r.stderr.strip())
    changes = [c for c in load_fix(inc) if c["kind"] == "apply" or (include_owner and c["kind"] == "owner")]
    existed = {c["path"]: (ROOT / c["path"]).exists() for c in changes}
    try:
        apply_changes(ROOT, changes)
        results = mc.run_checks(ROOT, evidence_lines=settings()["evidence_lines"])
        passed, own_ok, regress, after = run_pass(results, inc["test"]["before"], inc["check"])
    except ValueError as exc:
        results, passed = [], False
        inc["last_failure"] = str(exc)
        after = {}
    if not passed:
        for path, was_there in existed.items():  # undo only the files this fix touched
            if was_there:
                git("checkout", "--", path)
            else:
                (ROOT / path).unlink(missing_ok=True)
        git("checkout", base)
        git("branch", "-D", branch)
        inc["live"] = {"passed": False, "summary": "Working tree check FAILED, so the branch was removed: " + (summary_line(results) or inc.get("last_failure", ""))}
        if results:
            inc["last_failure"] = "\n".join(f"{r['key']}:\n{r['evidence']}" for r in results if not r["ok"])[-2500:]
        return False
    paths = [c["path"] for c in changes]
    git("add", "--", *paths)
    ident = [] if git("config", "user.email").stdout.strip() else ["-c", "user.name=Tech Support", "-c", "user.email=techsupport@users.noreply.github.com"]
    git(*ident, "commit", "-q", "-m", f"Fix {inc['id']}: {inc['title']}")
    git("checkout", base)
    inc["branch"] = branch
    inc["live"] = {"passed": True, "summary": "Verified again in your working tree on the branch: " + summary_line(results)}
    return True


def cmd_implement(a):
    q = load()
    inc = get(q, a.id)
    if inc["status"] not in ("fix_tested", "needs_owner"):
        sys.exit(f"{inc['id']} is '{inc['status']}'. A fix must pass its scratch test first (python3 scripts/techsupport.py test {inc['id']}).")
    only_owner = all(f["kind"] == "owner" for f in inc["fix"]["files"])
    if (only_owner or inc["status"] == "needs_owner") and not a.include_owner_files:
        sys.exit("This fix changes owner-only files (governance, models, workflows, safety scripts). Review it, then run again with --include-owner-files.")
    if do_implement(inc, a.include_owner_files):
        note(inc, "ready_to_ship", f"Branch {inc['branch']} verified")
        save(q)
        finish_message(inc)
        return 0
    inc["attempts"] += 1
    note(inc, "fix_failed", inc["live"]["summary"])
    save(q)
    print(inc["live"]["summary"])
    return 1


def cmd_run(a):
    q, cfg = load(), settings()
    inc = get(q, a.id)
    if inc["status"] in CLOSED:
        sys.exit(f"{inc['id']} is {inc['status']}.")
    while inc["attempts"] < cfg["max_attempts"]:
        rc, out, f = call_techsupport(inc, a.manual)
        if rc != 0 or not f:
            save(q)
            print(out or "Tech Support did not run.")
            print("If the key is missing or a cap was reached, you can use the free route: add --manual and paste the prompt into Claude.")
            return 1
        if f.startswith("outbox/"):
            inc["prompt_file"] = f
            note(inc, "diagnosing", "Prompt prepared: " + f)
            save(q)
            name = pathlib.Path(f).name
            print(f"{inc['id']}: paste {f} into Claude (https://claude.ai), save the reply as inbox/{name}, then run:\n"
                  f"  python3 scripts/techsupport.py ingest {inc['id']} inbox/{name}\n  python3 scripts/techsupport.py test {inc['id']}\n"
                  f"  python3 scripts/techsupport.py implement {inc['id']}")
            return 0
        inc["reply_file"] = f
        if not ingest_reply(inc, ROOT / f, cfg):
            save(q)
            print(f"{inc['id']}: Tech Support could not find a safe fix. {inc.get('diagnosis', '')}\nIt needs you. See the dashboard or the incident notes.")
            return 1
        passed = do_test(inc)
        if not passed:
            inc["attempts"] += 1
            note(inc, "fix_failed", inc["test"]["summary"])
            save(q)
            print(f"Attempt {inc['attempts']} failed its test: {inc['test']['summary']}")
            continue
        owner_only = all(x["kind"] == "owner" for x in inc["fix"]["files"])
        note(inc, "needs_owner" if owner_only else "fix_tested", inc["test"]["summary"])
        if owner_only:
            save(q)
            print(f"{inc['id']}: the fix passed its test but only changes owner-only files. Review it, then:\n"
                  f"  python3 scripts/techsupport.py implement {inc['id']} --include-owner-files")
            return 0
        if do_implement(inc, False):
            note(inc, "ready_to_ship", f"Branch {inc['branch']} verified")
            save(q)
            finish_message(inc)
            return 0
        inc["attempts"] += 1
        note(inc, "fix_failed", inc["live"]["summary"])
        save(q)
        print(inc["live"]["summary"])
    note(inc, "needs_owner", f"{cfg['max_attempts']} attempts did not produce a verified fix")
    save(q)
    print(f"{inc['id']}: {cfg['max_attempts']} attempts did not produce a verified fix. It needs you.")
    return 1


def cmd_resolve(a):
    q = load()
    inc = get(q, a.id)
    only = None if inc["check"] == "manual" else [inc["check"]]
    if only is None and not a.confirm:
        sys.exit("This incident was raised by hand, so there is no automatic check. Confirm it is fixed with --confirm.")
    results = mc.run_checks(ROOT, only=only)
    if only and all(r["ok"] for r in results):
        note(inc, "resolved", "Verified after the fix was pulled: " + summary_line(results))
    elif only is None:
        note(inc, "resolved", "Confirmed by the owner")
    else:
        inc["evidence"] = redact("\n".join(r["evidence"] for r in results if not r["ok"]))[-3000:]
        note(inc, "raised", "Still failing after the fix was pulled")
    save(q)
    print(f"{inc['id']}: {inc['status']}")
    return 0 if inc["status"] == "resolved" else 1


def cmd_abandon(a):
    q = load()
    inc = get(q, a.id)
    note(inc, "abandoned", a.reason or "abandoned by owner")
    save(q)
    print(f"{inc['id']}: abandoned")
    return 0


def cmd_status(a):
    q = load()
    for i in q["incidents"]:
        print(f"{i['id']} [{i['status']}] {i['severity']} {i['title']}" + (f" -> {i['branch']}" if i.get("branch") else ""))
    if not q["incidents"]:
        print("No incidents.")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("detect")
    p = sub.add_parser("raise")
    p.add_argument("--title", required=True)
    p.add_argument("--details", default="")
    p.add_argument("--severity", choices=["low", "medium", "high"], default="medium")
    p = sub.add_parser("run")
    p.add_argument("id")
    p.add_argument("--manual", action="store_true", help="free route: prepare a prompt to paste into Claude")
    p = sub.add_parser("ingest")
    p.add_argument("id")
    p.add_argument("file")
    sub.add_parser("test").add_argument("id")
    p = sub.add_parser("implement")
    p.add_argument("id")
    p.add_argument("--include-owner-files", action="store_true")
    p = sub.add_parser("resolve")
    p.add_argument("id")
    p.add_argument("--confirm", action="store_true")
    p = sub.add_parser("abandon")
    p.add_argument("id")
    p.add_argument("--reason")
    sub.add_parser("status")
    a = ap.parse_args()
    return {"detect": cmd_detect, "raise": cmd_raise, "run": cmd_run, "ingest": cmd_ingest, "test": cmd_test,
            "implement": cmd_implement, "resolve": cmd_resolve, "abandon": cmd_abandon, "status": cmd_status}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
