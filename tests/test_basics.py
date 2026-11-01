import pathlib
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from pii_guard import find_pii  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()
