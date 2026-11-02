import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import brain_search as bs  # noqa: E402
import yaml  # noqa: E402
from pii_guard import find_pii  # noqa: E402

HEADINGS = ["Purpose", "When to use", "Inputs", "Steps", "Output", "Approval tier", "Escalate to the owner", "Never", "Done when"]
AGENTS = list((yaml.safe_load((ROOT / "governance/status.yml").read_text()).get("agents") or {}))


def copy_repo(tmp):
    repo = pathlib.Path(tmp) / "repo"
    shutil.copytree(ROOT, repo, ignore=shutil.ignore_patterns(".git", "__pycache__"))
    return repo


class Sops(unittest.TestCase):
    def test_every_agent_has_a_complete_sop(self):
        for a in AGENTS:
            p = ROOT / "memory/brain/sops" / f"{a}.md"
            self.assertTrue(p.exists(), f"{a} has no SOP at memory/brain/sops/{a}.md")
            meta, body = bs.split_note(p.read_text())
            self.assertEqual(meta.get("agent"), a)
            self.assertEqual(meta.get("type"), "sop")
            for h in HEADINGS:
                self.assertIn(f"## {h}\n", body, f"{a}: missing section {h}")
            self.assertGreaterEqual(len(re.findall(r"^\d+\. ", body, re.M)), 5, f"{a}: too few numbered steps")
            self.assertEqual(find_pii(p.read_text()), [], f"{a}: SOP looks like it contains personal data")
            self.assertTrue(re.search(r"auto|needs_approval|needs_owner_and_accountant", body), f"{a}: no approval tier named")

    def test_index_lists_every_agent(self):
        index = (ROOT / "memory/brain/sops/README.md").read_text()
        for a in AGENTS:
            self.assertIn(f"| {a} |", index)

    def test_every_agent_brief_points_at_its_sop(self):
        for a in AGENTS:
            self.assertIn(f"memory/brain/sops/{a}.md", (ROOT / "agents" / a / "prompt.md").read_text())

    def test_every_agent_may_read_the_brain(self):
        for a in AGENTS:
            self.assertTrue(bs.can_read_brain(a), f"agents/{a}/permissions.yml must allow memory/brain/")


class Search(unittest.TestCase):
    def test_sop_text_and_context(self):
        self.assertIn("Write the title within eBay", bs.sop_text("listings"))
        self.assertIsNone(bs.sop_text("nobody"))
        ctx = bs.brain_context("listings", "Draft a listing")
        self.assertIn("Your standing procedure (SOP), from memory/brain/sops/listings.md", ctx)

    def test_related_notes_are_found_and_sops_are_not_repeated(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = copy_repo(tmp)
            (repo / "memory/brain/suppliers").mkdir(parents=True, exist_ok=True)
            (repo / "memory/brain/suppliers/acme.md").write_text(
                "---\ntitle: Acme Widgets supplier lead times\ntags: [suppliers, acme]\n---\nAcme ships in 5 working days and charges 4 GBP postage.\n")
            found = bs.search("what is the Acme lead time", repo)
            self.assertEqual([n["path"] for n in found], ["memory/brain/suppliers/acme.md"])
            self.assertIn("5 working days", bs.brain_context("inventory", "Acme lead time", repo))
            self.assertEqual(bs.search("how do I draft a listing title", repo), [])  # SOPs come in through the agent's own slot

    def test_permission_is_respected(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = copy_repo(tmp)
            perms = repo / "agents/listings/permissions.yml"
            perms.write_text(perms.read_text().replace("memory/brain/, ", ""))
            self.assertIn("Not loaded", bs.brain_context("listings", "x", repo))

    def test_run_agent_puts_the_sop_in_the_prompt(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = copy_repo(tmp)
            r = subprocess.run([sys.executable, "scripts/run_agent.py", "--agent", "listings", "--task", "Draft a listing for SKU-001", "--manual"],
                               cwd=repo, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            name = re.search(r"outbox/(\S+)", r.stdout).group(1)
            prompt = (repo / "outbox" / name).read_text()
            self.assertIn("Your standing procedure (SOP)", prompt)
            self.assertIn("Write the title within eBay's 80-character limit", prompt)

    def test_dashboard_data_has_sops(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = copy_repo(tmp)
            r = subprocess.run([sys.executable, "scripts/build_dashboard.py"], cwd=repo, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            data = json.loads((repo / "dashboard/status.json").read_text())
            self.assertTrue(all(a["sop"]["exists"] for a in data["agents"]))
            ts = next(a for a in data["agents"] if a["name"] == "techsupport")
            self.assertGreaterEqual(len(ts["sop"]["steps"]), 5)
            self.assertGreaterEqual(data["brain"]["count"], len(AGENTS))


if __name__ == "__main__":
    unittest.main()
