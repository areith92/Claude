import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import techsupport as ts  # noqa: E402

CFG = {"max_attempts": 2, "max_files": 4, "max_file_bytes": 40000, "evidence_lines": 40}
BROKEN = "a: [1, 2\n"
GOOD_FIX = {"diagnosis": "Unclosed list.", "root_cause": "Missing bracket.", "risk": "low", "verify": "config",
            "changes": [{"path": "docs/example.yml", "op": "replace", "old": "a: [1, 2\n", "new": "a: [1, 2]\n"}]}


class Rules(unittest.TestCase):
    def test_classify(self):
        self.assertEqual(ts.classify("scripts/foo.py"), "apply")
        self.assertEqual(ts.classify("docs/x.md"), "apply")
        self.assertEqual(ts.classify("agents/listings/prompt.md"), "apply")
        self.assertEqual(ts.classify("governance/status.yml"), "owner")
        self.assertEqual(ts.classify(".github/workflows/a.yml"), "owner")
        self.assertEqual(ts.classify("agents/listings/permissions.yml"), "owner")
        self.assertEqual(ts.classify("scripts/budget_guard.py"), "owner")
        self.assertEqual(ts.classify("logs/costs.csv"), "refuse")
        self.assertEqual(ts.classify("operations/incidents/queue.yml"), "refuse")
        self.assertEqual(ts.classify(".env"), "refuse")
        self.assertEqual(ts.classify("random/file.txt"), "refuse")

    def test_validate_refuses_unsafe(self):
        plan = {"changes": [
            {"path": "../evil.py", "op": "write", "content": "x"},
            {"path": "/etc/passwd", "op": "write", "content": "x"},
            {"path": "logs/costs.csv", "op": "write", "content": "x"},
            {"path": "scripts/a.py", "op": "write", "content": "key = '" + "sk-ant-" + "abcdefghijklmnop12345" + "'"},
            {"path": "scripts/b.py", "op": "write", "content": "# contact bob@example.com"},
            {"path": "scripts/c.py", "op": "delete"}]}
        changes, problems = ts.validate_fix(plan, dict(CFG, max_files=10))
        self.assertEqual(changes, [])
        self.assertEqual(len(problems), 6)

    def test_validate_limits_and_kinds(self):
        many = {"changes": [{"path": f"docs/f{i}.md", "op": "write", "content": "ok"} for i in range(6)]}
        changes, problems = ts.validate_fix(many, CFG)
        self.assertEqual(len(changes), 4)
        self.assertTrue(problems)
        gov = {"changes": [{"path": "governance/budgets.yml", "op": "replace", "old": "a", "new": "b"}]}
        self.assertEqual(ts.validate_fix(gov, CFG)[0][0]["kind"], "owner")
        weak = {"changes": [{"path": "tests/test_x.py", "op": "replace", "old": "self.assertTrue(x)", "new": "pass"}]}
        self.assertEqual(ts.validate_fix(weak, CFG)[0][0]["kind"], "owner")
        self.assertEqual(ts.validate_fix(None, CFG)[0], [])

    def test_apply_exactly_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "docs").mkdir()
            (root / "docs/a.md").write_text("x x")
            with self.assertRaises(ValueError):
                ts.apply_changes(root, [{"path": "docs/a.md", "op": "replace", "old": "x", "new": "y"}])
            ts.apply_changes(root, [{"path": "docs/a.md", "op": "replace", "old": "x x", "new": "y"}])
            self.assertEqual((root / "docs/a.md").read_text(), "y")

    def test_extract_json(self):
        text = "Proposal:\n" + ts.FENCE + "json\n" + json.dumps(GOOD_FIX) + "\n" + ts.FENCE
        self.assertEqual(ts.extract_json(text)["root_cause"], "Missing bracket.")
        self.assertIsNone(ts.extract_json("nothing here"))


class Flow(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = pathlib.Path(self.tmp.name) / "repo"
        shutil.copytree(ROOT, self.repo, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        (self.repo / "operations/incidents/queue.yml").write_text("incidents: []\n")
        (self.repo / "docs/example.yml").write_text(BROKEN)
        self.env = {**os.environ, "MONITOR_SKIP": "tests,secrets,budget,dashboard"}
        self.env.pop("ANTHROPIC_API_KEY", None)
        for cmd in (["init", "-q", "-b", "main"], ["config", "user.email", "t@example.com"], ["config", "user.name", "t"],
                    ["add", "-A"], ["commit", "-q", "-m", "base"]):
            subprocess.run(["git", *cmd], cwd=self.repo, capture_output=True)

    def tearDown(self):
        self.tmp.cleanup()

    def cli(self, *args):
        return subprocess.run([sys.executable, "scripts/techsupport.py", *args], cwd=self.repo, capture_output=True, text=True, env=self.env)

    def queue(self):
        return ts.yaml.safe_load((self.repo / "operations/incidents/queue.yml").read_text())["incidents"]

    def reply(self, plan, name="reply.md"):
        (self.repo / "inbox").mkdir(exist_ok=True)
        (self.repo / "inbox" / name).write_text("Summary: x\nProposal:\n" + ts.FENCE + "json\n" + json.dumps(plan) + "\n" + ts.FENCE + "\n")
        return "inbox/" + name

    def raised(self):
        r = self.cli("detect")
        self.assertIn("RAISED", r.stdout, r.stdout + r.stderr)
        return self.queue()[0]["id"]

    def test_full_pipeline(self):
        iid = self.raised()
        inc = self.queue()[0]
        self.assertEqual((inc["check"], inc["status"]), ("config", "raised"))
        self.assertIn("example.yml", inc["evidence"])
        self.assertEqual(self.cli("detect").stdout.count("RAISED"), 0)  # no duplicate while open
        self.assertEqual(self.cli("ingest", iid, self.reply(GOOD_FIX)).returncode, 0)
        self.assertEqual(self.queue()[0]["status"], "fix_proposed")
        r = self.cli("test", iid)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.queue()[0]["status"], "fix_tested")
        r = self.cli("implement", iid)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("FIX READY", r.stdout)
        inc = self.queue()[0]
        self.assertEqual(inc["status"], "ready_to_ship")
        branch = inc["branch"]
        shown = subprocess.run(["git", "show", f"{branch}:docs/example.yml"], cwd=self.repo, capture_output=True, text=True).stdout
        self.assertEqual(shown, "a: [1, 2]\n")
        self.assertEqual((self.repo / "docs/example.yml").read_text(), BROKEN)  # main is untouched until the owner merges
        self.assertEqual(subprocess.run(["git", "branch", "--show-current"], cwd=self.repo, capture_output=True, text=True).stdout.strip(), "main")
        self.assertEqual(self.cli("resolve", iid).returncode, 1)  # not merged yet, so still failing
        self.assertEqual(self.queue()[0]["status"], "raised")
        subprocess.run(["git", "merge", "-q", branch], cwd=self.repo, capture_output=True)
        r = self.cli("resolve", iid)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.queue()[0]["status"], "resolved")

    def test_failing_fix_is_not_applied(self):
        iid = self.raised()
        bad = {"diagnosis": "x", "changes": [{"path": "docs/example.yml", "op": "replace", "old": "a: [1, 2\n", "new": "a: [1, 3\n"}]}
        self.cli("ingest", iid, self.reply(bad))
        r = self.cli("test", iid)
        self.assertEqual(r.returncode, 1)
        inc = self.queue()[0]
        self.assertEqual((inc["status"], inc["attempts"]), ("fix_failed", 1))
        self.assertIn("example.yml", inc["last_failure"])
        self.assertNotEqual(self.cli("implement", iid).returncode, 0)

    def test_owner_files_need_the_flag(self):
        routing = (self.repo / "models/routing.yml").read_text()
        line = "  techsupport:  {preferred: claude, max_tokens: 3000}\n"
        self.assertIn(line, routing)
        (self.repo / "models/routing.yml").write_text(routing.replace(line, ""))
        (self.repo / "docs/example.yml").write_text("a: [1, 2]\n")
        subprocess.run(["git", "commit", "-qam", "break routing"], cwd=self.repo, capture_output=True)
        iid = self.raised()
        plan = {"diagnosis": "routing entry missing", "changes": [{"path": "models/routing.yml", "op": "replace",
                "old": "  monitor:      {preferred: claude}\n", "new": "  monitor:      {preferred: claude}\n" + line}]}
        self.cli("ingest", iid, self.reply(plan))
        self.assertEqual(self.queue()[0]["fix"]["files"][0]["kind"], "owner")
        self.assertEqual(self.cli("test", iid).returncode, 0)
        self.assertEqual(self.queue()[0]["status"], "needs_owner")
        r = self.cli("implement", iid)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("--include-owner-files", r.stdout + r.stderr)
        r = self.cli("implement", iid, "--include-owner-files")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        branch = self.queue()[0]["branch"]
        shown = subprocess.run(["git", "show", f"{branch}:models/routing.yml"], cwd=self.repo, capture_output=True, text=True).stdout
        self.assertIn(line, shown)

    def test_run_without_key_and_manual_route(self):
        iid = self.raised()
        r = self.cli("run", iid)
        self.assertEqual(r.returncode, 1)
        self.assertIn("ANTHROPIC_API_KEY", r.stdout + r.stderr)
        r = self.cli("run", iid, "--manual")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        inc = self.queue()[0]
        self.assertEqual(inc["status"], "diagnosing")
        prompt = (self.repo / inc["prompt_file"]).read_text()
        self.assertIn("example.yml", prompt)
        self.assertIn("a: [1, 2", prompt)

    def test_dashboard_shows_incidents(self):
        iid = self.raised()
        self.cli("ingest", iid, self.reply(GOOD_FIX))
        self.cli("test", iid)
        self.cli("implement", iid)
        r = subprocess.run([sys.executable, "scripts/build_dashboard.py"], cwd=self.repo, capture_output=True, text=True, env=self.env)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        data = json.loads((self.repo / "dashboard/status.json").read_text())
        inc = data["incidents"][0]
        self.assertEqual((inc["status"], inc["stage"]), ("ready_to_ship", 6))
        self.assertTrue(any(n["cmd"].startswith("git push -u origin fix/") for n in inc["next"]))
        self.assertTrue(any("fix ready" in a for a in data["alerts"]))
        self.assertIn("techsupport", [a["name"] for a in data["agents"]])

    def test_files_with_personal_data_are_redacted_in_the_prompt(self):
        (self.repo / "docs/contact.md").write_text("Notes\nEmail bob@example.com for help\nThe bug is here: broken\n")
        subprocess.run(["git", "add", "-A"], cwd=self.repo, capture_output=True)
        subprocess.run(["git", "commit", "-qm", "add notes"], cwd=self.repo, capture_output=True)
        r = self.cli("raise", "--title", "Problem in a doc", "--details", "see docs/contact.md")
        iid = self.queue()[0]["id"]
        r = self.cli("run", iid, "--manual")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)  # the personal-data guard must not refuse the prompt
        prompt = (self.repo / self.queue()[0]["prompt_file"]).read_text()
        self.assertNotIn("bob@example.com", prompt)
        self.assertIn("[line removed: looks like personal data]", prompt)
        self.assertIn("The bug is here: broken", prompt)

    def test_health_checks_run(self):
        self.assertEqual(subprocess.run([sys.executable, "scripts/monitor_checks.py"], cwd=self.repo, capture_output=True, text=True, env=self.env).returncode, 1)
        (self.repo / "docs/example.yml").write_text("a: [1, 2]\n")
        self.assertEqual(subprocess.run([sys.executable, "scripts/monitor_checks.py"], cwd=self.repo, capture_output=True, text=True, env=self.env).returncode, 0)


if __name__ == "__main__":
    unittest.main()
