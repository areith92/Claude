import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import orchestrate as orc  # noqa: E402

AGENTS = {"listings": {"enabled": True}, "compliance": {"enabled": True}, "pricing": {"enabled": False},
          "orchestrator": {"enabled": True}}


def task(agent, tier="needs_approval", obj="Do a thing for SKU-001"):
    return {"agent": agent, "objective": obj, "why": "because", "approval_tier": tier}


class Parsing(unittest.TestCase):
    def test_fenced_json(self):
        text = "Proposal:\n" + orc.FENCE + "json\n" + json.dumps({"tasks": []}) + "\n" + orc.FENCE + "\nthanks"
        self.assertEqual(orc.extract_json(text), {"tasks": []})

    def test_bare_json(self):
        self.assertEqual(orc.extract_json('Plan: {"tasks": [{"agent": "x"}]} done'), {"tasks": [{"agent": "x"}]})

    def test_garbage(self):
        self.assertIsNone(orc.extract_json("no json here"))
        self.assertIsNone(orc.extract_json("{ not json }"))


class Validation(unittest.TestCase):
    def check(self, tasks, max_tasks=5, existing=()):
        return orc.validate_plan({"tasks": tasks}, AGENTS, max_tasks, list(existing))

    def test_good_and_blocked(self):
        tasks, problems = self.check([task("listings"), task("pricing")])
        self.assertEqual([t["status"] for t in tasks], ["queued", "blocked"])
        self.assertEqual(problems, [])

    def test_rejects_unknown_self_never_and_pii(self):
        tasks, problems = self.check([task("marketing"), task("orchestrator"), task("listings", "never"),
                                      task("listings", obj="Email bob@example.com about it")])
        self.assertEqual(tasks, [])
        self.assertEqual(len(problems), 4)

    def test_cap_and_ids(self):
        tasks, problems = self.check([task("listings")] * 4, max_tasks=3, existing=["T-20990101-001"])
        self.assertEqual(len(tasks), 3)
        self.assertTrue(problems)
        self.assertEqual(len({t["id"] for t in tasks}), 3)

    def test_unknown_tier_becomes_strict(self):
        tasks, _ = self.check([task("listings", "whatever")])
        self.assertEqual(tasks[0]["tier"], "needs_approval")

    def test_no_plan(self):
        self.assertEqual(orc.validate_plan(None, AGENTS, 3, [])[0], [])


class Decisions(unittest.TestCase):
    def test_tier_logic(self):
        self.assertEqual(orc.stated_tier("Approval tier: needs_approval"), "needs_approval")
        self.assertIsNone(orc.stated_tier("nothing here"))
        self.assertEqual(orc.effective_tier("auto", "needs_owner_and_accountant"), "needs_owner_and_accountant")
        self.assertEqual(orc.effective_tier("needs_approval", "auto"), "needs_approval")

    def test_can_decide_guards(self):
        t = {"id": "T-1", "status": "replied", "tier": "needs_approval", "flags": []}
        self.assertTrue(orc.can_decide(t, "approved")[0])
        self.assertFalse(orc.can_decide({**t, "status": "delegated"}, "approved")[0])
        self.assertFalse(orc.can_decide({**t, "flags": ["pii"]}, "approved")[0])
        self.assertTrue(orc.can_decide({**t, "flags": ["pii"]}, "rejected")[0])
        acc = {**t, "tier": "needs_owner_and_accountant"}
        self.assertFalse(orc.can_decide(acc, "approved")[0])
        self.assertTrue(orc.can_decide(acc, "approved", accountant_ok=True)[0])


class EndToEnd(unittest.TestCase):
    """Runs the whole manual flow in a throwaway copy of the repo."""

    def run_cli(self, cwd, *args):
        return subprocess.run([sys.executable, "scripts/orchestrate.py", *args], cwd=cwd, capture_output=True, text=True)

    def test_flow(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = pathlib.Path(tmp) / "repo"
            shutil.copytree(ROOT, repo, ignore=shutil.ignore_patterns(".git", "__pycache__"))
            (repo / "operations/tasks/queue.yml").write_text("tasks: []\n")
            st = repo / "governance/status.yml"
            st.write_text(st.read_text().replace(", provider: api", ""))  # these tests run in manual mode

            r = self.run_cli(repo, "plan", "--goal", "Draft the first listing")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("Prompt written to outbox/", r.stdout)

            r = self.run_cli(repo, "ingest", "tests/fixtures/sample_plan_reply.md", "--delegate")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            q = orc.yaml.safe_load((repo / "operations/tasks/queue.yml").read_text())
            by_agent = {t["agent"]: t for t in q["tasks"]}
            self.assertEqual(by_agent["listings"]["status"], "delegated")
            self.assertEqual(by_agent["compliance"]["status"], "delegated")
            self.assertEqual(by_agent["inventory"]["status"], "blocked")

            (repo / "inbox").mkdir(exist_ok=True)
            for agent, tier in (("listings", "needs_approval"), ("compliance", "auto")):
                name = pathlib.Path(by_agent[agent]["prompt_file"]).name
                (repo / "inbox" / name).write_text(f"Summary: ok.\nApproval tier: {tier}\n")

            r = self.run_cli(repo, "digest")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            digest = next((repo / "reports/digests").glob("*.md")).read_text()
            self.assertIn(by_agent["listings"]["id"], digest)
            q = orc.yaml.safe_load((repo / "operations/tasks/queue.yml").read_text())
            by_agent = {t["agent"]: t for t in q["tasks"]}
            self.assertEqual(by_agent["listings"]["status"], "replied")
            self.assertEqual(by_agent["compliance"]["status"], "done")

            lid = by_agent["listings"]["id"]
            r = self.run_cli(repo, "decide", lid, "approved", "--reason", "Looks good")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertTrue(list((repo / "logs/decisions").glob(f"*{lid}.md")))
            self.assertNotEqual(self.run_cli(repo, "decide", by_agent["compliance"]["id"], "approved").returncode, 0)
            self.assertEqual(self.run_cli(repo, "complete", lid).returncode, 0)

    def test_paused_blocks_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = pathlib.Path(tmp) / "repo"
            shutil.copytree(ROOT, repo, ignore=shutil.ignore_patterns(".git", "__pycache__"))
            s = repo / "governance/status.yml"
            s.write_text(s.read_text().replace("paused: false", "paused: true"))
            r = self.run_cli(repo, "plan", "--goal", "anything")
            self.assertIn("PAUSED", r.stdout)
            self.assertFalse(list((repo / "outbox").glob("*orchestrator.md")))


if __name__ == "__main__":
    unittest.main()
