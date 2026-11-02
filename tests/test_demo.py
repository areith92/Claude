import csv
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent


class Demo(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = pathlib.Path(self.tmp.name) / "repo"
        shutil.copytree(ROOT, self.repo, ignore=shutil.ignore_patterns(".git", "__pycache__", "dossiers", "images", "approved", "exports"))
        self.env = {k: v for k, v in os.environ.items() if "API_KEY" not in k}

    def tearDown(self):
        self.tmp.cleanup()

    def run_py(self, *args):
        return subprocess.run([sys.executable, *args], cwd=self.repo, capture_output=True, text=True, env=self.env)

    def state(self):
        out = self.run_py("-c", "import sys, json; sys.path.insert(0, 'scripts'); import research; print(json.dumps(research.api_state()))")
        return json.loads(out.stdout)

    def test_demo_fills_every_part_of_the_dashboard_and_cleans_up(self):
        r = self.run_py("scripts/demo_research.py")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        s = self.state()
        self.assertEqual({k: s["counts"][k] for k in ("awaiting_approval", "blocked", "analysed", "rejected")}, {"awaiting_approval": 2, "blocked": 1, "analysed": 1, "rejected": 4})
        awaiting = [i for i in s["items"] if i["stage"] == "awaiting_approval"]
        self.assertTrue(all(i["title"].startswith("DEMO - ") for i in s["items"]))
        self.assertTrue(all(any(img["url_local"] for img in i["market"]["images"]) for i in awaiting))
        self.assertTrue((self.repo / awaiting[0]["market"]["images"][0]["path"]).exists())
        reasons = " ".join(i["reject_reason"] or "" for i in s["items"])
        self.assertIn("EBAY-ITEM-1", reasons)
        self.assertIn("EBAY-DS-1", reasons)
        self.assertEqual(self.run_py("scripts/demo_research.py").returncode, 1)  # not twice

        pid = next(i["id"] for i in awaiting if i["channel"] == "ebay-uk")
        self.assertEqual(self.run_py("scripts/research.py", "decide", pid, "approved", "--reason", "demo").returncode, 1)  # flags first
        self.assertEqual(self.run_py("scripts/research.py", "decide", pid, "approved", "--reason", "demo", "--acknowledge-flags").returncode, 0)
        self.assertTrue((self.repo / "research/approved" / pid / "listing-draft.md").exists())
        other = next(i["id"] for i in awaiting if i["id"] != pid)
        self.assertEqual(self.run_py("scripts/research.py", "decide", other, "denied", "--reason", "demo denial").returncode, 0)
        self.assertTrue((self.repo / "memory/brain/research" / f"lesson-{other}.md").exists())

        r = self.run_py("scripts/demo_research.py", "--clean")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.state()["items"], [])
        self.assertFalse((self.repo / "research/approved" / pid).exists())
        self.assertFalse((self.repo / "memory/brain/research").exists())

    def test_clean_never_touches_real_products(self):
        p = self.repo / "real.csv"
        cols = ["keyword", "title", "category", "brand", "channel", "fulfilment_model", "ebay_url", "market_price_gbp", "sold_30d", "active_listings", "supplier_platform",
                "supplier_url", "supplier_cost_gbp", "supplier_shipping_gbp", "delivery_days_max", "supplier_rating", "ships_from", "postage_gbp", "image_urls",
                "bad_review_themes", "listing_notes", "data_date"]
        with p.open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(cols)
            w.writerow(["pet glove", "Real pet glove", "Pets", "", "ebay-uk", "wholesale_dropship", "u", "14.99", "1", "1", "w", "u", "1.6", "0.8", "4", "4", "GB", "0", "", "", "", ""])
        self.run_py("scripts/research.py", "import", str(p))
        self.run_py("scripts/demo_research.py")
        self.run_py("scripts/demo_research.py", "--clean")
        titles = [i["title"] for i in self.state()["items"]]
        self.assertEqual(titles, ["Real pet glove"])


if __name__ == "__main__":
    unittest.main()
