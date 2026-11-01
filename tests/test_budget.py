import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import budget_guard as bg  # noqa: E402

BUDGETS = """currency: GBP
ai_costs:
  total_monthly_cap: {total}
  alert_at_percent: 80
  per_agent_monthly_cap:
    orchestrator: 2
    listings: {listings}
    orders: 0
    messages: 0
    finance: 0
    compliance: 1
    reviewer: 0
    monitor: 0
    pricing: 0
    inventory: 0
    returns: 0
    analytics: 0
spend: {{promoted_listings_monthly_cap: 0, stock_purchases_monthly_cap: 0, other_monthly_cap: 0}}
"""
COSTS = "claude:\n  input_per_mtok_gbp: 1.6\n  output_per_mtok_gbp: 8\ngemini:\n  free_tier: true\n  input_per_mtok_gbp: 0\n  output_per_mtok_gbp: 0\n"


class Logic(unittest.TestCase):
    def test_worst_case(self):
        self.assertAlmostEqual(bg.worst_case_cost(4000, 1500, 1.6, 8), 0.0136, places=6)

    def test_would_exceed(self):
        self.assertEqual(bg.would_exceed(4.99, 0, 0.02, 5, 2), "total")
        self.assertEqual(bg.would_exceed(1, 1.99, 0.02, 5, 2), "agent")
        self.assertIsNone(bg.would_exceed(1, 0, 0.02, 5, 2))
        self.assertEqual(bg.would_exceed(0, 0, 0.01, 0, 0), "total")

    def test_state(self):
        self.assertEqual(bg.spend_state(0, 0), "off")
        self.assertEqual(bg.spend_state(1, 5), "ok")
        self.assertEqual(bg.spend_state(4, 5), "warning")
        self.assertEqual(bg.spend_state(5, 5), "stopped")
        self.assertEqual(bg.spend_state(1, 5, stop_marker=True), "stopped")


class Integration(unittest.TestCase):
    def repo(self, tmp, total, listings=1.5):
        repo = pathlib.Path(tmp) / "repo"
        shutil.copytree(ROOT, repo, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        (repo / "governance/budgets.yml").write_text(BUDGETS.format(total=total, listings=listings))
        (repo / "models/costs.yml").write_text(COSTS)
        s = repo / "governance/status.yml"
        s.write_text(s.read_text().replace("  listings:     {enabled: true,  dry_run: true}",
                                           "  listings:     {enabled: true,  dry_run: true, provider: api}"))
        (repo / "logs/costs.csv").write_text("date,agent,provider,model,input_tokens,output_tokens,cost_gbp,note\n")
        for f in ("logs/budget-stop.json",):
            (repo / f).unlink(missing_ok=True)
        return repo

    def run_py(self, repo, *args):
        env = {"PATH": "/usr/bin:/bin:/usr/local/bin", "ANTHROPIC_API_KEY": "dummy-not-a-real-key"}
        return subprocess.run([sys.executable, *args], cwd=repo, capture_output=True, text=True, env=env)

    def test_cap_blocks_call_and_raises_alert(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = self.repo(tmp, total=0.001)
            r = self.run_py(repo, "scripts/run_agent.py", "--agent", "listings", "--task", "Draft a listing for SKU-001")
            self.assertEqual(r.returncode, 5, r.stdout + r.stderr)
            self.assertIn("STOPPED", r.stdout)
            self.assertEqual(json.loads((repo / "logs/budget-stop.json").read_text())["scope"], "total")
            r = self.run_py(repo, "scripts/build_dashboard.py", "--alert-file", str(repo / "alert.md"))
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertEqual(json.loads((repo / "dashboard/status.json").read_text())["spend"]["state"], "stopped")
            self.assertTrue((repo / "alert.md").read_text().startswith("# AI budget STOPPED"))
            self.assertTrue((repo / "dashboard/status.js").read_text().startswith("window.DASHBOARD = "))

    def test_zero_cap_blocks_without_alert(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = self.repo(tmp, total=0, listings=0)
            r = self.run_py(repo, "scripts/run_agent.py", "--agent", "listings", "--task", "Draft a listing for SKU-001")
            self.assertEqual(r.returncode, 5, r.stdout + r.stderr)
            self.assertFalse((repo / "logs/budget-stop.json").exists())

    def test_ok_state_has_no_alert(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = self.repo(tmp, total=5)
            self.run_py(repo, "scripts/build_dashboard.py", "--alert-file", str(repo / "alert.md"))
            self.assertEqual((repo / "alert.md").read_text(), "")
            self.assertEqual(json.loads((repo / "dashboard/status.json").read_text())["spend"]["state"], "ok")

    def test_warning_at_80_percent(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = self.repo(tmp, total=5)
            (repo / "logs/costs.csv").write_text(
                "date,agent,provider,model,input_tokens,output_tokens,cost_gbp,note\n"
                f"{__import__('datetime').date.today()},orchestrator,anthropic,claude-sonnet-5-5,1000,1000,4.2,\n")
            self.run_py(repo, "scripts/build_dashboard.py", "--alert-file", str(repo / "alert.md"))
            self.assertTrue((repo / "alert.md").read_text().startswith("# AI budget warning"))


if __name__ == "__main__":
    unittest.main()
