import csv
import datetime
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import margin as mg  # noqa: E402
import policy_gate as pg  # noqa: E402
from check_budget import load_yaml  # noqa: E402

TODAY = str(datetime.date.today())
COLS = ["keyword", "title", "category", "brand", "channel", "fulfilment_model", "ebay_url", "market_price_gbp", "sold_30d", "active_listings",
        "supplier_platform", "supplier_url", "supplier_cost_gbp", "supplier_shipping_gbp", "delivery_days_max", "supplier_rating", "ships_from",
        "postage_gbp", "image_urls", "bad_review_themes", "listing_notes", "data_date"]


def row(keyword, title, model="wholesale_dropship", price="14.99", cost="1.60", ship="0.80", days="4", channel="ebay-uk", notes="", date=TODAY, brand="", postage="0"):
    return [keyword, title, "Home", brand, channel, model, "https://ebay.example/1", price, "100", "200", "wholesaler", "https://s.example/1", cost, ship, days, "4.7", "GB",
            postage, "", "seams split", notes, date]


def dossier(**kw):
    d = {"channel": "ebay-uk", "keyword": "glove", "title": "Pet glove", "category": "Pets", "brand": "", "fulfilment_model": "hold_stock", "data_date": TODAY,
         "margin": {"fees_confirmed": True, "stress_margin_pct": 40, "stress_cost_increase_pct": 10}, "market": {"images": []}, "supplier": {"images": []},
         "stock_in_hand": True, "safety_docs_ok": True, "delivery_promise_checked": True}
    d.update(kw)
    return d


class Margin(unittest.TestCase):
    def test_known_numbers(self):
        fees = load_yaml("catalogue/fees.yml")
        r = mg.with_stress({"channel": "ebay-uk", "sale_price_gbp": 24.99, "supplier_cost_gbp": 6.5, "supplier_shipping_gbp": 1.2, "postage_gbp": 2.85,
                            "fulfilment_model": "hold_stock"}, fees, 10)
        self.assertEqual((r["margin_pct"], r["stress_margin_pct"], r["fees_confirmed"]), (31.2, 28.6, False))

    def test_dropship_has_no_postage_or_packaging(self):
        fees = load_yaml("catalogue/fees.yml")
        r = mg.compute({"channel": "ebay-uk", "sale_price_gbp": 20, "supplier_cost_gbp": 5, "supplier_shipping_gbp": 1, "postage_gbp": 3, "fulfilment_model": "wholesale_dropship"}, fees)
        self.assertEqual((r["postage_gbp"], r["packaging_gbp"]), (0, 0))

    def test_vat_registered_lowers_the_margin_and_social_uses_its_own_fees(self):
        fees = load_yaml("catalogue/fees.yml")
        d = {"channel": "social", "sale_price_gbp": 20, "supplier_cost_gbp": 5, "supplier_shipping_gbp": 1, "fulfilment_model": "wholesale_dropship"}
        plain = mg.compute(d, fees)["margin_pct"]
        fees["common"]["vat_registered"] = True
        self.assertLess(mg.compute(d, fees)["margin_pct"], plain)


class Gate(unittest.TestCase):
    def status(self, d, rule):
        return next(r["status"] for r in pg.evaluate(d)["results"] if r["id"] == rule)

    def test_marketplace_dropship_is_blocked_on_ebay_but_not_on_social(self):
        self.assertEqual(self.status(dossier(fulfilment_model="marketplace_dropship"), "EBAY-DS-1"), "block")
        self.assertNotEqual(pg.evaluate(dossier(channel="social", fulfilment_model="marketplace_dropship"))["overall"], "block")

    def test_cars_are_blocked_with_whole_word_matching(self):
        self.assertEqual(self.status(dossier(title="Car phone holder"), "EBAY-ITEM-1"), "block")
        self.assertEqual(self.status(dossier(title="Birthday card holder", keyword="card holder"), "EBAY-ITEM-1"), "pass")
        self.assertEqual(self.status(dossier(title="Alloy wheel cleaner"), "EBAY-ITEM-1"), "block")

    def test_restricted_images_and_brand_flags(self):
        self.assertEqual(self.status(dossier(title="LED desk lamp"), "EBAY-ITEM-2"), "flag")
        d = dossier(market={"images": [{"url": "x", "rights": "unverified"}]})
        self.assertEqual(self.status(d, "EBAY-IMG-1"), "flag")
        d["market"]["images"][0]["rights"] = "licensed"
        self.assertEqual(self.status(d, "EBAY-IMG-1"), "pass")
        self.assertEqual(self.status(dossier(brand="Acme"), "EBAY-IP-1"), "flag")
        self.assertEqual(self.status(dossier(brand="Acme", brand_authorised=True), "EBAY-IP-1"), "pass")

    def test_stock_in_hand_and_stale_data(self):
        self.assertEqual(self.status(dossier(stock_in_hand=False), "EBAY-DS-2"), "flag")
        self.assertEqual(self.status(dossier(data_date=str(datetime.date.today() - datetime.timedelta(days=30))), "EBAY-DATA-1"), "block")

    def test_old_rules_file_raises_a_warning(self):
        far = datetime.date.today() + datetime.timedelta(days=400)
        self.assertIn("last reviewed", pg.evaluate(dossier(), today=far)["stale"])
        self.assertIsNone(pg.evaluate(dossier())["stale"])

    def test_unknown_channel_blocks(self):
        self.assertEqual(pg.evaluate(dossier(channel="nowhere"))["overall"], "block")


class Pipeline(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = pathlib.Path(self.tmp.name) / "repo"
        shutil.copytree(ROOT, self.repo, ignore=shutil.ignore_patterns(".git", "__pycache__", "dossiers", "images", "approved", "exports"))
        self.env = {k: v for k, v in os.environ.items() if "API_KEY" not in k}

    def tearDown(self):
        self.tmp.cleanup()

    def cli(self, *args):
        return subprocess.run([sys.executable, "scripts/research.py", *args], cwd=self.repo, capture_output=True, text=True, env=self.env)

    def csv(self, rows):
        p = self.repo / "in.csv"
        with p.open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(COLS)
            w.writerows(rows)
        return str(p)

    def dossiers(self):
        return {d["title"]: d for d in (json.loads(p.read_text()) for p in sorted((self.repo / "research/dossiers").glob("P-*.json")))}

    def reply(self, pid, agent, body):
        (self.repo / "inbox").mkdir(exist_ok=True)
        f = self.repo / "inbox" / f"{pid}-{agent}.md"
        f.write_text("Proposal:\n```json\n" + json.dumps(body) + "\n```\n")
        return self.cli("attach", pid, agent, str(f))

    def reviews(self, pid, price=None, verdicts=("pass", "pass", "pass", "pass")):
        for ag, v in zip(("listings", "pricing", "compliance", "finance"), verdicts):
            body = {"verdict": v, "improved_title": "Better title", "improved_description": "Natural text.", "key_points": ["a"]}
            if ag == "pricing" and price:
                body["suggested_price_gbp"] = price
            self.assertEqual(self.reply(pid, ag, body).returncode, 0)

    def test_rules_reject_with_reasons_and_cap_the_run(self):
        rows = [row("pet glove", "Pet glove"), row("car phone holder", "Car phone holder", price="30"), row("desk", "Desk organiser", model="marketplace_dropship"),
                row("strap", "Slow strap", days="9"), row("mat", "Thin margin mat", price="6.00", cost="3.00")]
        r = self.cli("import", self.csv(rows))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        d = self.dossiers()
        self.assertEqual(d["Pet glove"]["stage"], "analysed")
        self.assertIn("EBAY-ITEM-1", d["Car phone holder"]["reject_reason"])
        self.assertIn("EBAY-DS-1", d["Desk organiser"]["reject_reason"])
        self.assertIn("delivery is 9", d["Slow strap"]["reject_reason"])
        self.assertIn("margin is", d["Thin margin mat"]["reject_reason"])
        self.assertTrue((self.repo / "research/exports/summary.csv").exists())
        self.assertTrue((self.repo / "research/dossiers" / f"{d['Pet glove']['id']}.md").exists())
        many = self.csv([row(f"k{i}", f"Product {i}") for i in range(25)])
        self.assertIn("only the first 20", self.cli("import", many).stdout)

    def test_personal_data_in_an_import_is_removed(self):
        self.cli("import", self.csv([row("pet glove", "Pet glove", notes="seller is bob@example.com")]))
        self.assertIn("removed", self.dossiers()["Pet glove"]["market"]["listing_notes"])

    def test_prepare_free_route_writes_four_prompts_with_the_dossier(self):
        self.cli("import", self.csv([row("pet glove", "Pet glove")]))
        pid = self.dossiers()["Pet glove"]["id"]
        before = set((self.repo / "outbox").glob("*.md"))
        r = self.cli("prepare", pid, "--manual")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        prompts = sorted(set((self.repo / "outbox").glob("*.md")) - before)
        self.assertEqual(sorted(p.name.split("-", 2)[2][:-3] for p in prompts), ["compliance", "finance", "listings", "pricing"])
        text = next(p for p in prompts if "listings" in p.name).read_text()
        self.assertIn("Pet glove", text)
        self.assertIn("Do not copy competitor wording", text)

    def test_full_approval_flow(self):
        self.cli("import", self.csv([row("pet glove", "Pet glove")]))
        pid = self.dossiers()["Pet glove"]["id"]
        self.reviews(pid, price=14.49, verdicts=("pass", "pass", "flag", "flag"))
        self.assertEqual(self.dossiers()["Pet glove"]["stage"], "awaiting_approval")
        r = self.cli("decide", pid, "approved", "--reason", "good")
        self.assertEqual(r.returncode, 1)
        self.assertIn("flag(s) need to be acknowledged", r.stdout)
        self.cli("confirm", pid, "safety_docs_ok")
        r = self.cli("decide", pid, "approved", "--reason", "good", "--acknowledge-flags")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        pack = self.repo / "research/approved" / pid
        self.assertEqual(sorted(p.name for p in pack.iterdir()), ["catalogue-entry.yml", "listing-draft.md", "sample-order-checklist.md"])
        self.assertIn("Better title", (pack / "listing-draft.md").read_text())
        self.assertEqual(self.dossiers()["Pet glove"]["stage"], "approved")

    def test_a_price_suggestion_that_breaks_the_margin_blocks_the_product(self):
        self.cli("import", self.csv([row("pet glove", "Pet glove", price="14.99", cost="6.00", ship="1.00")]))
        pid = self.dossiers()["Pet glove"]["id"]
        self.reviews(pid, price=8.99)
        d = self.dossiers()["Pet glove"]
        self.assertEqual(d["stage"], "blocked")
        self.assertIn("margin at the suggested price", d["history"][-1]["note"])
        self.assertEqual(self.cli("decide", pid, "approved", "--acknowledge-flags").returncode, 1)

    def test_an_agent_block_stops_approval(self):
        self.cli("import", self.csv([row("pet glove", "Pet glove")]))
        pid = self.dossiers()["Pet glove"]["id"]
        self.reviews(pid, verdicts=("pass", "pass", "block", "pass"))
        self.assertEqual(self.dossiers()["Pet glove"]["stage"], "blocked")

    def test_stale_data_cannot_be_approved(self):
        self.cli("import", self.csv([row("pet glove", "Pet glove")]))
        pid = self.dossiers()["Pet glove"]["id"]
        self.reviews(pid)
        p = self.repo / "research/dossiers" / f"{pid}.json"
        d = json.loads(p.read_text())
        d["data_date"] = str(datetime.date.today() - datetime.timedelta(days=30))
        p.write_text(json.dumps(d))
        r = self.cli("decide", pid, "approved", "--acknowledge-flags")
        self.assertEqual(r.returncode, 1)
        self.assertIn("stale", r.stdout)

    def test_denial_becomes_a_lesson_the_research_agent_can_find(self):
        self.cli("import", self.csv([row("pet glove", "Pet glove")]))
        pid = self.dossiers()["Pet glove"]["id"]
        self.reviews(pid)
        self.assertEqual(self.cli("decide", pid, "denied", "--reason", "too many sellers already").returncode, 0)
        lesson = (self.repo / "memory/brain/research" / f"lesson-{pid}.md").read_text()
        self.assertIn("too many sellers already", lesson)
        out = subprocess.run([sys.executable, "scripts/brain_search.py", "pet glove ideas", "--agent", "research"], cwd=self.repo, capture_output=True, text=True).stdout
        self.assertIn("too many sellers already", out)

    def test_personal_data_in_a_reason_is_refused(self):
        self.cli("import", self.csv([row("pet glove", "Pet glove")]))
        pid = self.dossiers()["Pet glove"]["id"]
        self.reviews(pid)
        self.assertEqual(self.cli("decide", pid, "denied", "--reason", "ask bob@example.com").returncode, 1)

    def test_template_and_keywords(self):
        self.assertEqual(self.cli("template").returncode, 0)
        self.assertTrue((self.repo / "research/templates/products.csv").exists())
        r = self.cli("keywords", "--manual")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("Prompt written to outbox/", r.stdout)


class Server(unittest.TestCase):
    def test_api_token_and_decision(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = pathlib.Path(tmp) / "repo"
            shutil.copytree(ROOT, repo, ignore=shutil.ignore_patterns(".git", "__pycache__", "dossiers", "images", "approved", "exports"))
            env = {k: v for k, v in os.environ.items() if "API_KEY" not in k}
            p = repo / "in.csv"
            with p.open("w", newline="") as f:
                w = csv.writer(f)
                w.writerow(COLS)
                w.writerow(row("pet glove", "Pet glove"))
            subprocess.run([sys.executable, "scripts/research.py", "import", str(p)], cwd=repo, capture_output=True, env=env)
            proc = subprocess.Popen([sys.executable, "scripts/dashboard_server.py", "--port", "0", "--no-build"], cwd=repo, stdout=subprocess.PIPE, text=True, env=env)
            try:
                base = proc.stdout.readline().split("Dashboard: ")[1].split()[0]
                get = lambda path: json.loads(urllib.request.urlopen(base + path, timeout=10).read())  # noqa: E731
                state = get("/api/research")
                self.assertEqual(state["counts"]["analysed"], 1)
                pid = state["items"][0]["id"]

                def post(body, token=None, origin=None):
                    h = {"Content-Type": "application/json"}
                    if token:
                        h["X-Dash-Token"] = token
                    if origin:
                        h["Origin"] = origin
                    req = urllib.request.Request(base + "/api/decision", data=json.dumps(body).encode(), headers=h, method="POST")
                    try:
                        return urllib.request.urlopen(req, timeout=10).status
                    except urllib.error.HTTPError as e:
                        return e.code
                self.assertEqual(post({"id": pid, "decision": "denied"}), 403)  # no token
                token = get("/api/token")["token"]
                self.assertEqual(post({"id": pid, "decision": "denied"}, token, origin="http://evil.example"), 403)  # other site
                self.assertEqual(post({"id": pid, "decision": "maybe"}, token), 400)
                self.assertEqual(post({"id": pid, "decision": "approved"}, token), 409)  # not awaiting approval yet
                with self.assertRaises(urllib.error.HTTPError) as ctx:
                    urllib.request.urlopen(base + "/research/images/../../governance/status.yml", timeout=10)
                self.assertEqual(ctx.exception.code, 404)
            finally:
                proc.terminate()
                proc.wait(timeout=10)
                proc.stdout.close()


if __name__ == "__main__":
    unittest.main()
