import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent


class DashboardData(unittest.TestCase):
    def build(self):
        tmp = tempfile.TemporaryDirectory()
        repo = pathlib.Path(tmp.name) / "repo"
        shutil.copytree(ROOT, repo, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        r = subprocess.run([sys.executable, "scripts/build_dashboard.py"], cwd=repo, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return tmp, repo, json.loads((repo / "dashboard/status.json").read_text())

    def test_every_agent_is_placed_in_a_department(self):
        tmp, repo, d = self.build()
        with tmp:
            self.assertEqual([a["name"] for a in d["agents"] if a["dept"] == "unassigned"], [],
                             "Add the agent to dashboard/departments.yml")
            known = {x["id"] for x in d["departments"]} | {"conductor"}
            self.assertTrue(all(a["dept"] in known for a in d["agents"]))
            self.assertNotIn("unassigned", {x["id"] for x in d["departments"]})

    def test_data_shape(self):
        tmp, repo, d = self.build()
        with tmp:
            self.assertEqual(d["conductor"], "orchestrator")
            self.assertGreaterEqual(len(d["departments"]), 6)
            self.assertTrue(all(a["role"] for a in d["agents"]))
            self.assertEqual([c["id"] for c in d["connections"]], ["claude", "gemini", "ebay", "shopify"])
            self.assertEqual(d["phases"]["current"], 1)
            js = (repo / "dashboard/status.js").read_text()
            self.assertEqual(json.loads(js[len("window.DASHBOARD = "):].rstrip().rstrip(";")), d)

    def test_page_script_has_valid_syntax(self):
        if not shutil.which("node"):
            self.skipTest("node is not installed")
        r = subprocess.run(["node", "--check", "dashboard/app.js"], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)


if __name__ == "__main__":
    unittest.main()
