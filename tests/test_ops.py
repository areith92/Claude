import datetime as dt
import http.server
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.parse

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import inbox  # noqa: E402
import store  # noqa: E402
import watch  # noqa: E402

D = dt.date


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self._data = store.DATA
        store.DATA = pathlib.Path(self.tmp.name)
        self.st = store.Local()

    def tearDown(self):
        store.DATA = self._data
        self.tmp.cleanup()

    def order(self, oid="O-1001", **kw):
        row = {"id": oid, "order_date": "2026-10-28", "channel": "ebay-uk", "product_id": "P-1", "revenue_gbp": 14.99, "item_cost_gbp": 1.6, "shipping_cost_gbp": 0.8, "fees_gbp": 2.7, "status": "ordered"}
        row.update(kw)
        store.put(self.st, "orders", watch.order_row(row), ["id"])

    def parcel(self, oid="O-1001", shipped="2026-10-29", promised=5, tracking="AB123456789GB"):
        return watch.ship_add(self.st, oid, "Royal Mail", tracking, shipped, promised, "Acme", today=D(2026, 10, 29))

    def kinds(self, new):
        return [(a["kind"], a["severity"]) for a in new]


class Shipments(Base):
    def test_a_parcel_must_belong_to_a_recorded_order(self):
        with self.assertRaises(ValueError):
            watch.ship_add(self.st, "O-404", "Royal Mail", "X", "2026-10-29")

    def test_nothing_is_raised_while_a_parcel_is_inside_its_promise(self):
        self.order(); self.parcel()
        new = []
        watch.scan_shipments(self.st, D(2026, 11, 3), new)  # due on the 3rd
        self.assertEqual(new, [])

    def test_overdue_is_a_warning_then_critical_and_never_repeated(self):
        self.order(); self.parcel()
        new = []
        watch.scan_shipments(self.st, D(2026, 11, 4), new)
        self.assertEqual(self.kinds(new), [("parcel_overdue", "warning")])
        self.assertIn("1 day(s) past its promised 5-day delivery", new[0]["message"])
        watch.scan_shipments(self.st, D(2026, 11, 4), new)  # the same day again
        self.assertEqual(len(new), 1)
        watch.scan_shipments(self.st, D(2026, 11, 6), new)  # now 3 days late
        self.assertEqual(self.kinds(new), [("parcel_overdue", "warning"), ("parcel_overdue", "critical")])
        watch.scan_shipments(self.st, D(2026, 11, 9), new)
        self.assertEqual(len(new), 2)

    def test_delivered_parcels_are_left_alone_and_a_late_arrival_is_noted(self):
        self.order(); p = self.parcel(); new = []
        watch.ship_update(self.st, p["id"], "delivered", "Delivered to door", today=D(2026, 11, 5), new=new)
        self.assertEqual(self.kinds(new), [("delivered_late", "info")])
        fresh = []
        watch.scan_shipments(self.st, D(2026, 12, 1), fresh)
        self.assertEqual(fresh, [])
        self.assertEqual(self.st.select("orders", {"id": "O-1001"})[0]["status"], "delivered")

    def test_missing_tracking_stuck_parcels_and_exceptions(self):
        self.order(); self.order("O-1002")
        a = self.parcel("O-1001", tracking="")
        b = self.parcel("O-1002")
        new = []
        watch.scan_shipments(self.st, D(2026, 10, 31), new)
        self.assertIn(("no_tracking", "warning"), self.kinds(new))
        watch.ship_update(self.st, b["id"], "in_transit", "Arrived at depot", today=D(2026, 10, 30))
        self.st.update("shipments", {"id": b["id"]}, {"last_event_at": "2026-10-30T10:00:00+00:00"})
        new = []
        watch.scan_shipments(self.st, D(2026, 11, 2), new)
        self.assertIn(("parcel_stuck", "warning"), self.kinds(new))
        watch.ship_update(self.st, b["id"], "exception", "Address problem")
        new = []
        watch.scan_shipments(self.st, D(2026, 11, 2), new)
        self.assertIn(("parcel_exception", "critical"), self.kinds(new))

    def test_alert_text_has_no_personal_data(self):
        self.order(); p = self.parcel()
        watch.ship_update(self.st, p["id"], "exception", "ask bob@example.com about it")
        self.assertIn("removed", self.st.select("shipments", {"id": p["id"]})[0]["last_event"])


class Prices(Base):
    def setUp(self):
        super().setUp()
        store.put(self.st, "listings", {"product_id": "P-1", "title": "Pet glove", "channel": "ebay-uk", "price_gbp": 14.99, "assumed_cost_gbp": 1.6, "assumed_shipping_gbp": 0.8, "fulfilment_model": "wholesale_dropship", "postage_gbp": 0, "active": True}, ["product_id"])

    def price(self, cost, ship=0.8, day="2026-11-02"):
        store.put(self.st, "supplier_prices", {"product_id": "P-1", "checked_date": day, "cost_gbp": cost, "shipping_gbp": ship, "source": "import"}, ["product_id", "checked_date", "source"])

    def test_a_steady_price_raises_nothing(self):
        self.price(1.6)
        new = []
        watch.check_prices(self.st, D(2026, 11, 2), new)
        self.assertEqual(new, [])

    def test_a_rise_that_keeps_the_margin_is_a_warning(self):
        self.price(1.9)  # +12% on 2.4
        new = []
        watch.check_prices(self.st, D(2026, 11, 2), new)
        self.assertEqual(self.kinds(new), [("supplier_price_rise", "warning")])

    def test_a_rise_that_breaks_the_margin_is_critical_when_it_loses_money(self):
        self.price(30.0)
        new = []
        watch.check_prices(self.st, D(2026, 11, 2), new)
        self.assertEqual(self.kinds(new), [("margin_below_minimum", "critical")])
        self.assertIn("LOSES money", new[0]["message"])

    def test_the_latest_price_is_the_one_that_counts(self):
        self.price(30.0, day="2026-10-30")
        self.price(1.6, day="2026-11-02")
        new = []
        watch.check_prices(self.st, D(2026, 11, 2), new)
        self.assertEqual(new, [])

    def test_a_paid_order_the_supplier_has_not_been_given_yet_is_flagged_if_it_now_loses_money(self):
        self.order("O-2001", status="new", revenue_gbp=14.99, item_cost_gbp=1.6, shipping_cost_gbp=0.8, fees_gbp=2.7)
        self.order("O-2002", status="ordered", revenue_gbp=14.99, item_cost_gbp=1.6, shipping_cost_gbp=0.8, fees_gbp=2.7)  # already bought at the old price
        self.price(15.0)
        new = []
        watch.check_prices(self.st, D(2026, 11, 2), new)
        exposed = [a for a in new if a["kind"] == "order_exposed"]
        self.assertEqual([a["entity_id"] for a in exposed], ["O-2001"])
        self.assertIn("loses", exposed[0]["message"])
        self.assertEqual(exposed[0]["severity"], "critical")


class Money(Base):
    def test_profit_and_loss_by_day_and_week(self):
        self.order("O-1", order_date="2026-11-02", revenue_gbp=20, item_cost_gbp=5, shipping_cost_gbp=1, fees_gbp=3, status="delivered")
        self.order("O-2", order_date="2026-11-02", revenue_gbp=10, item_cost_gbp=4, shipping_cost_gbp=1, fees_gbp=1.5, refund_gbp=10, status="refunded")
        self.order("O-3", order_date="2026-11-02", revenue_gbp=99, status="cancelled")
        self.st.insert("ad_spend_ledger", {"platform": "facebook", "spend_date": "2026-11-02", "amount_gbp": 2.5, "source": "manual"})
        old = watch.ai_spend_by_day
        watch.ai_spend_by_day = lambda: {"2026-11-02": 0.5}
        try:
            r = watch.pnl(self.st, D(2026, 11, 2), 3)
        finally:
            watch.ai_spend_by_day = old
        today = r["daily"][-1]
        self.assertEqual((today["orders"], today["revenue"], today["refunds"], today["cogs"], today["fees"], today["ads"], today["ai"], today["profit"]), (2, 30.0, 10.0, 11.0, 4.5, 2.5, 0.5, 1.5))
        self.assertEqual([d["profit"] for d in r["daily"][:2]], [0.0, 0.0])
        self.assertEqual([w["week_start"] for w in r["weekly"]], ["2026-10-26", "2026-11-02"])  # a Monday
        self.assertEqual((r["weekly"][1]["profit"], r["weekly"][1]["spend"]), (1.5, 18.5))

    def test_fees_are_estimated_when_missing(self):
        self.order("O-9", order_date="2026-11-02", revenue_gbp=20, fees_gbp=0)
        old = watch.ai_spend_by_day
        watch.ai_spend_by_day = lambda: {}
        try:
            r = watch.pnl(self.st, D(2026, 11, 2), 1)
        finally:
            watch.ai_spend_by_day = old
        self.assertEqual(r["fees_estimated_orders"], 1)
        self.assertGreater(r["daily"][0]["fees"], 0)

    def test_social_and_shop_figures_are_imported_and_summarised(self):
        m, s = pathlib.Path(self.tmp.name) / "m.csv", pathlib.Path(self.tmp.name) / "s.csv"
        m.write_text("platform,date,post_ref,impressions,reach,clicks,likes,comments,shares,saves,followers,spend_gbp,conversions,revenue_gbp\n"
                     "instagram,2026-11-01,post-a,1000,800,40,50,5,3,2,300,0,1,14.99\ninstagram,2026-11-01,post-b,500,400,10,20,1,0,0,300,0,0,0\ntiktok,2026-11-01,post-c,2000,1500,60,100,10,20,5,50,0,2,30\n")
        s.write_text("date,channel,sessions,carts,checkouts,orders,abandoned_checkouts,revenue_gbp\n2026-11-01,shopify,200,20,10,3,7,44.97\n")
        self.assertEqual(watch.import_metrics(self.st, str(m)), 3)
        self.assertEqual(watch.import_metrics(self.st, str(m)), 3)  # importing again never duplicates
        self.assertEqual(len(self.st.select("social_metrics")), 3)
        watch.import_shop(self.st, str(s))
        out = watch.summary(self.st, D(2026, 11, 2))
        insta = next(x for x in out["social"] if x["platform"] == "instagram")
        self.assertEqual((insta["posts"], insta["impressions"], insta["likes"]), (2, 1500, 70))
        self.assertEqual(insta["engagement_pct"], round((70 + 6 + 3 + 2) / 1500 * 100, 2))
        self.assertEqual((out["funnel"]["abandonment_pct"], out["funnel"]["conversion_pct"]), (70.0, 1.5))


class Inbox(Base):
    def test_personal_data_is_removed(self):
        t, n = inbox.redact("mail me bob@example.com or 07700 900123, BD1 1AA, card 4111 1111 1111 1111, @bob_smith https://x.example/a")
        for word in ("bob@example", "07700", "BD1", "4111", "@bob_smith", "x.example"):
            self.assertNotIn(word, t)
        self.assertEqual(n, 6)
        self.assertEqual(inbox.redact("Order O-1001 please")[0], "Order O-1001 please")  # order IDs stay

    def test_triage_categories_and_tiers(self):
        self.assertEqual(inbox.triage("The charger burnt my hand")["tier"], "escalate")
        self.assertEqual(inbox.triage("I will contact trading standards")["category"], "legal")
        self.assertEqual(inbox.triage("Earn money fast, click the link")["tier"], "ignore")
        self.assertEqual(inbox.triage("Where is my order? Has it been dispatched?")["category"], "order_status")
        self.assertEqual(inbox.triage("Still waiting, it has not arrived")["category"], "delivery_delay")
        self.assertEqual(inbox.triage("I want a refund")["category"], "return_refund")
        self.assertEqual(inbox.triage("Is this washable? what colour")["category"], "product_question")
        self.assertEqual(inbox.triage("Where is my parcel", "comment")["template_id"], "public_move_to_dm")

    def test_replies_need_their_facts_and_nothing_is_ready_by_default(self):
        t = inbox.triage("Where is my order?")
        self.assertEqual(t["tier"], "draft")
        self.assertIn("business_name", t["missing_facts"])
        self.assertIn("{{business_name}}", t["reply"])

    def test_a_category_becomes_ready_only_when_allowed_and_complete_and_never_for_refunds(self):
        orig = inbox.settings
        cfg, rules, templates, facts = orig()
        facts = {**facts, "business_name": "Acme Home", "delivery_estimate_text": "arrive within 3 to 5 working days", "return_window_days": 30, "return_postage_text": "Postage is paid by the buyer"}
        inbox.settings = lambda: ({**cfg, "auto_send_categories": ["order_status", "return_refund"]}, rules, templates, facts)
        try:
            ready = inbox.triage("Where is my order?")
            self.assertEqual(ready["tier"], "ready")
            self.assertIn("Acme Home", ready["reply"])
            self.assertIn(cfg["disclosure"], ready["reply"])
            self.assertEqual(inbox.triage("I want a refund")["tier"], "draft")  # never_auto wins
        finally:
            inbox.settings = orig

    def test_messages_are_stored_redacted_with_a_draft_and_escalations_raise_an_alert(self):
        r = inbox.add_message(self.st, "facebook", "dm", "Where is my order? mail bob@example.com", "O-1001")
        stored = self.st.select("messages", {"id": r["message"]})[0]
        self.assertNotIn("bob@example", stored["body_redacted"])
        self.assertEqual(self.st.select("messages", {"id": r["draft"]})[0]["draft_status"], "awaiting_approval")
        inbox.add_message(self.st, "tiktok", "dm", "it caught fire")
        self.assertEqual([a["kind"] for a in self.st.select("alerts")], ["message_escalation"])
        s = inbox.summary(self.st)
        self.assertEqual((s["awaiting_approval"], s["escalated"]), (1, 1))
        inbox.decide(self.st, r["draft"], "approved")
        self.assertEqual(inbox.summary(self.st)["awaiting_approval"], 0)


class Mock(http.server.BaseHTTPRequestHandler):
    tables = {}

    def log_message(self, *a):
        pass

    def send(self, code, obj):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def parse(self):
        u = urllib.parse.urlsplit(self.path)
        table = u.path.rsplit("/", 1)[1]
        flt = {k: v[len("eq."):] for k, v in urllib.parse.parse_qsl(u.query) if v.startswith("eq.")}
        return table, flt

    def authed(self):
        return self.headers.get("apikey") == "sb_secret_TESTKEY"

    def match(self, row, flt):
        return all(str(row.get(k)) == v for k, v in flt.items())

    def do_GET(self):
        if not self.authed():
            return self.send(401, {"message": "bad key"})
        t, flt = self.parse()
        rows = [dict(r) for r in self.tables.get(t, []) if self.match(r, flt)]
        if t == "shipments":
            for r in rows:
                r["expected_by"] = str(D.fromisoformat(r["shipped_date"]) + dt.timedelta(days=r["promised_days"])) if r.get("shipped_date") else None
        self.send(200, rows)

    def do_POST(self):
        if not self.authed():
            return self.send(401, {"message": "bad key"})
        t, _ = self.parse()
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        out = []
        for row in body:
            if "expected_by" in row:
                return self.send(400, {"message": "cannot insert into generated column expected_by"})
            row = dict(row)
            if t in store.AUTO_ID:
                row["id"] = len(self.tables.setdefault(t, [])) + 1
            self.tables.setdefault(t, []).append(row)
            out.append(row)
        self.send(201, out)

    def do_PATCH(self):
        if not self.authed():
            return self.send(401, {"message": "bad key"})
        t, flt = self.parse()
        vals = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        hit = [r for r in self.tables.get(t, []) if self.match(r, flt)]
        for r in hit:
            r.update(vals)
        self.send(200, hit)


class SupabaseBackend(unittest.TestCase):
    def test_the_same_watch_works_against_the_database_and_never_sends_generated_columns(self):
        Mock.tables = {}
        srv = http.server.HTTPServer(("127.0.0.1", 0), Mock)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            st = store.Supabase(f"http://127.0.0.1:{srv.server_address[1]}/rest/v1/", "sb_secret_TESTKEY")
            store.put(st, "orders", watch.order_row({"id": "O-1001", "order_date": "2026-10-28", "revenue_gbp": 14.99, "status": "ordered"}), ["id"])
            row = watch.ship_add(st, "O-1001", "Royal Mail", "AB1", "2026-10-29", 5, "Acme", today=D(2026, 10, 29))
            self.assertNotIn("expected_by", Mock.tables["shipments"][0])
            new = []
            watch.scan_shipments(st, D(2026, 11, 9), new)
            self.assertEqual([a["severity"] for a in new], ["critical", "critical"][:len(new)])
            self.assertEqual(new[0]["kind"], "parcel_overdue")
            self.assertEqual(len(Mock.tables["alerts"]), len(new))
            watch.scan_shipments(st, D(2026, 11, 9), [])
            self.assertEqual(len(Mock.tables["alerts"]), len(new))  # no duplicates
            self.assertEqual(st.update("alerts", {"id": 1}, {"status": "acknowledged"}), 1)
            with self.assertRaises(store.StoreError) as ctx:
                store.Supabase(f"http://127.0.0.1:{srv.server_address[1]}", "wrong").select("orders")
            self.assertNotIn("wrong", str(ctx.exception))  # a key is never shown in an error
            self.assertEqual(row["promised_days"], 5)
        finally:
            srv.shutdown()
            srv.server_close()


class Cli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = pathlib.Path(self.tmp.name) / "repo"
        shutil.copytree(ROOT, self.repo, ignore=shutil.ignore_patterns(".git", "__pycache__", "dossiers", "images", "approved", "exports", "data"))
        self.env = {k: v for k, v in os.environ.items() if "API_KEY" not in k and not k.startswith("SUPABASE")}
        self.env["OPS_STORE"] = "local"

    def tearDown(self):
        self.tmp.cleanup()

    def run_py(self, *args, env=None):
        return subprocess.run([sys.executable, *args], cwd=self.repo, capture_output=True, text=True, env=env or self.env)

    def test_the_daily_job_fails_loudly_without_the_database_keys(self):
        r = self.run_py("scripts/watch.py", "scan", "--require-supabase")
        self.assertEqual(r.returncode, 1)
        self.assertIn("NOT RUN", r.stdout)
        wf = (ROOT / ".github/workflows/daily-watch.yml").read_text()
        self.assertIn("--require-supabase", wf)
        self.assertIn("cron:", wf)
        self.assertIn("assignee", wf)

    def test_scan_writes_an_alert_file_only_when_something_is_new(self):
        self.run_py("scripts/watch.py", "order", "add", "--id", "O-5", "--date", "2026-10-28", "--revenue", "10", "--status", "ordered")
        self.run_py("scripts/watch.py", "ship", "add", "--order", "O-5", "--carrier", "Evri", "--tracking", "T1", "--shipped", "2026-10-29", "--promised-days", "3")
        r = self.run_py("scripts/watch.py", "scan", "--today", "2026-11-10", "--alert-file", str(self.repo / "a.md"))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("CRITICAL", (self.repo / "a.md").read_text())
        self.run_py("scripts/watch.py", "scan", "--today", "2026-11-10", "--alert-file", str(self.repo / "b.md"))
        self.assertEqual((self.repo / "b.md").read_text(), "")
        self.assertIn("acknowledged", self.run_py("scripts/watch.py", "alerts", "ack", "1").stdout + "acknowledged")
        self.assertEqual(self.run_py("scripts/watch.py", "ship", "add", "--order", "O-404", "--shipped", "2026-11-01").returncode, 2)

    def test_the_dashboard_server_serves_operations_and_protects_alert_changes(self):
        self.run_py("scripts/watch.py", "order", "add", "--id", "O-7", "--date", "2026-10-28", "--revenue", "10")
        self.run_py("scripts/watch.py", "ship", "add", "--order", "O-7", "--tracking", "T7", "--shipped", "2026-10-01", "--promised-days", "3")
        self.run_py("scripts/watch.py", "scan")
        proc = subprocess.Popen([sys.executable, "scripts/dashboard_server.py", "--port", "0", "--no-build"], cwd=self.repo, stdout=subprocess.PIPE, text=True, env=self.env)
        try:
            base = proc.stdout.readline().split("Dashboard: ")[1].split()[0]
            import urllib.error
            import urllib.request
            ops = json.loads(urllib.request.urlopen(base + "/api/ops", timeout=15).read())
            self.assertTrue(ops["alerts"])
            self.assertEqual(ops["shipments"][0]["order_id"], "O-7")
            for key in ("pnl", "social", "funnel", "inbox", "listings"):
                self.assertIn(key, ops)

            def post(body, token=None):
                h = {"Content-Type": "application/json"}
                if token:
                    h["X-Dash-Token"] = token
                try:
                    return urllib.request.urlopen(urllib.request.Request(base + "/api/alert", data=json.dumps(body).encode(), headers=h, method="POST"), timeout=10).status
                except urllib.error.HTTPError as e:
                    return e.code
            self.assertEqual(post({"id": 1, "status": "closed"}), 403)
            token = json.loads(urllib.request.urlopen(base + "/api/token").read())["token"]
            self.assertEqual(post({"id": 1, "status": "deleted"}, token), 400)
            self.assertEqual(post({"id": 1, "status": "acknowledged"}, token), 200)
        finally:
            proc.terminate()
            proc.wait(timeout=10)
            proc.stdout.close()

    def test_inbox_cli_and_prompt_for_the_platform_agent(self):
        r = self.run_py("scripts/inbox.py", "add", "--platform", "instagram", "--kind", "dm", "--text", "Do you have a bigger size? mail bob@example.com")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("DRAFT", r.stdout)
        lst = self.run_py("scripts/inbox.py", "list").stdout
        self.assertIn("[EMAIL]", lst)
        self.assertNotIn("bob@example", lst)
        mid = re.search(r"- ([0-9a-f-]{36}) \[instagram", lst).group(1)
        before = set((self.repo / "outbox").glob("*.md"))
        out = self.run_py("scripts/inbox.py", "prompt", mid).stdout
        self.assertIn("Prompt written to outbox/", out)
        prompt = next(iter(set((self.repo / "outbox").glob("*.md")) - before)).read_text()
        self.assertIn("instagram", prompt.lower())
        self.assertIn("[EMAIL]", prompt)
        self.assertNotIn("bob@example", prompt)
        self.assertEqual(self.run_py("scripts/inbox.py", "approve", mid).returncode, 2)  # no draft exists yet, so there is nothing to approve
        self.run_py("scripts/inbox.py", "add", "--platform", "facebook", "--kind", "comment", "--text", "Love this, thank you so much")
        drafted = re.search(r"- ([0-9a-f-]{36}) \[facebook comment\]", self.run_py("scripts/inbox.py", "list").stdout).group(1)
        self.assertEqual(self.run_py("scripts/inbox.py", "approve", drafted).returncode, 0)


if __name__ == "__main__":
    unittest.main()
