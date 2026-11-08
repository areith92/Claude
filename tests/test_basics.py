import pathlib
import subprocess
import sys
import unittest

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from pii_guard import find_pii  # noqa: E402


def load(rel):
    return yaml.safe_load((ROOT / rel).read_text())


class Basics(unittest.TestCase):
    def test_pii_email_caught(self):
        self.assertTrue(find_pii("contact bob@example.com"))

    def test_order_id_is_fine(self):
        self.assertEqual(find_pii("Order TEST-12345 is delayed"), [])

    def test_config_valid(self):
        r = subprocess.run([sys.executable, "scripts/validate_config.py"], cwd=ROOT)
        self.assertEqual(r.returncode, 0)

    def test_budget_ok(self):
        r = subprocess.run([sys.executable, "scripts/check_budget.py"], cwd=ROOT)
        self.assertEqual(r.returncode, 0)

    def test_routing_uses_known_tiers(self):
        routing = load("models/routing.yml")
        for name, cfg in routing["agents"].items():
            self.assertIn(cfg["tier"], routing["models"], name)

    def test_every_agent_has_a_sop(self):
        for name in load("governance/status.yml")["agents"]:
            self.assertTrue((ROOT / "memory" / "brain" / "sops" / f"{name}.md").exists(), name)

    def test_ai_caps_add_up(self):
        caps = load("governance/budgets.yml")["ai_costs"]
        self.assertLessEqual(sum(caps["per_agent_monthly_cap"].values()), caps["total_monthly_cap"] + 0.1)


if __name__ == "__main__":
    unittest.main()
