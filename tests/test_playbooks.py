import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import brain_search as bs  # noqa: E402
import yaml  # noqa: E402
from pii_guard import find_pii  # noqa: E402

SOPS = ROOT / "memory/brain/sops"
PLAYBOOK_HEADINGS = ["Purpose", "Who", "Daily routine", "Weekly routine", "Monthly routine", "Systems and commands", "Handoffs", "Escalate to the owner", "Measures", "Never"]
PROCEDURE_HEADINGS = ["Purpose", "Trigger", "Roles", "Steps", "Records", "Escalate to the owner", "Done when"]
DEPARTMENTS = (yaml.safe_load((ROOT / "dashboard/departments.yml").read_text()) or {}).get("departments") or {}
SLUG = {"customer": "customer-care", "support": "tech-support"}
AGENTS = list((yaml.safe_load((ROOT / "governance/status.yml").read_text()).get("agents") or {}))


class Playbooks(unittest.TestCase):
    def test_every_department_and_the_company_have_a_complete_playbook(self):
        for slug in [SLUG.get(k, k) for k in DEPARTMENTS] + ["company"]:
            p = SOPS / "departments" / f"{slug}.md"
            self.assertTrue(p.exists(), f"no playbook for {slug}")
            meta, body = bs.split_note(p.read_text())
            self.assertEqual((meta.get("type"), meta.get("department")), ("department-playbook", slug))
            for h in PLAYBOOK_HEADINGS:
                self.assertIn(f"## {h}\n", body, f"{slug}: missing {h}")
            for h in ("Daily routine", "Weekly routine", "Monthly routine"):
                section = body.split(f"## {h}\n")[1].split("\n## ")[0]
                self.assertGreaterEqual(len(re.findall(r"^\d+\. ", section, re.M)), 1, f"{slug}: {h} has no steps")
            self.assertEqual(find_pii(p.read_text()), [], f"{slug}: looks like personal data")

    def test_every_procedure_is_complete(self):
        files = sorted((SOPS / "procedures").glob("*.md"))
        self.assertGreaterEqual(len(files), 11)
        for p in files:
            meta, body = bs.split_note(p.read_text())
            self.assertEqual(meta.get("type"), "procedure")
            for h in PROCEDURE_HEADINGS:
                self.assertIn(f"## {h}\n", body, f"{p.stem}: missing {h}")
            self.assertGreaterEqual(len(re.findall(r"^\d+\. ", body, re.M)), 5, f"{p.stem}: too few steps")
            self.assertEqual(find_pii(p.read_text()), [], f"{p.stem}: looks like personal data")

    def test_every_agent_sop_points_at_its_department_and_real_procedures(self):
        for a in AGENTS:
            meta, body = bs.split_note((SOPS / f"{a}.md").read_text())
            self.assertEqual(meta.get("department"), bs.department_slug(a), a)
            self.assertIn("## Department and procedures\n", body, a)
            self.assertTrue((SOPS / "departments" / f"{meta['department']}.md").exists(), a)
            for slug in re.findall(r"sops/procedures/([a-z0-9-]+)\.md", body):
                self.assertTrue((SOPS / "procedures" / f"{slug}.md").exists(), f"{a} lists a missing procedure {slug}")

    def test_the_index_lists_every_playbook_and_procedure(self):
        index = (SOPS / "README.md").read_text()
        for p in (SOPS / "departments").glob("*.md"):
            self.assertIn(f"- {p.stem}:", index)
        for p in (SOPS / "procedures").glob("*.md"):
            self.assertIn(f"- {p.stem}:", index)

    def test_an_agent_prompt_gets_its_playbook_and_the_procedure_that_matches_the_task(self):
        ctx = bs.brain_context("orders", "A parcel is late and the customer is asking where it is")
        self.assertIn("Your department playbook, from memory/brain/sops/departments/operations.md", ctx)
        self.assertIn("sops/procedures/late-parcel.md", ctx)
        self.assertNotIn("sops/procedures/data-breach.md", ctx)
        if "research" in AGENTS:
            self.assertIn("departments/research.md", bs.brain_context("research", "Pick keywords"))
        self.assertIn("departments/company.md", bs.brain_context("orchestrator", "Plan the week"))
        if "marketing" in AGENTS:  # present once the social agents are installed
            self.assertIn("procedures/social-post-approval.md", bs.brain_context("marketing", "Approve this post for facebook"))

    def test_the_legal_procedures_state_the_key_deadlines(self):
        self.assertIn("72 hours", (SOPS / "procedures/data-breach.md").read_text())
        self.assertIn("one month", (SOPS / "procedures/customer-data-request.md").read_text())

    def test_the_privacy_pack_exists_and_agents_are_told_never_to_see_personal_data(self):
        for f in ("docs/privacy/README.md", "docs/privacy/ropa-and-processors.md", "docs/privacy/privacy-notice-draft.md", "governance/privacy.yml"):
            self.assertTrue((ROOT / f).exists(), f)
            self.assertEqual(find_pii((ROOT / f).read_text()), [], f)
        cfg = yaml.safe_load((ROOT / "governance/privacy.yml").read_text())
        self.assertFalse(cfg["ai"]["personal_data_to_ai_providers"])
        self.assertEqual(cfg["requests"]["response_days"], 30)
        self.assertIn("customer references", (ROOT / "agents/_shared/company-rules.md").read_text())


if __name__ == "__main__":
    unittest.main()
