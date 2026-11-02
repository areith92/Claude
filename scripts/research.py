#!/usr/bin/env python3
"""Product research pipeline. Data comes in from a CSV (Terapeak or eBay API exports plus supplier quotes; API providers come later).
Code checks the rules, calculates the margin and runs the compliance gate. AI agents review the listing, price, compliance and finance.
You approve or deny on the dashboard. Nothing is bought, listed or published here.

  python scripts/research.py template                 write research/templates/products.csv
  python scripts/research.py keywords                 prepare the research agent's prompt (picks up to 20 keywords)
  python scripts/research.py import FILE.csv          create dossiers; rules reject what does not qualify
  python scripts/research.py images P-...             save the image links as files for analysis (rights stay unverified)
  python scripts/research.py prepare P-...            prepare prompts for listings, pricing, compliance and finance
  python scripts/research.py attach P-... AGENT FILE  attach an agent's reply (JSON block with a verdict)
  python scripts/research.py confirm P-... FIELD      tick an owner check (stock_in_hand, safety_docs_ok, ...)
  python scripts/research.py decide P-... approved|denied --reason "..." [--acknowledge-flags]
  python scripts/research.py list | export
"""
import argparse
import csv
import datetime
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import yaml  # noqa: E402
import margin as mg  # noqa: E402
import policy_gate as pg  # noqa: E402
from check_budget import ROOT, load_yaml  # noqa: E402
from pii_guard import find_pii  # noqa: E402

RES = ROOT / "research"
DOSSIERS, IMAGES, APPROVED, EXPORTS = RES / "dossiers", RES / "images", RES / "approved", RES / "exports"
REQUIRED = ("listings", "pricing", "compliance", "finance")
CONFIRMABLE = ("stock_in_hand", "supplier_agreement", "brand_authorised", "safety_docs_ok", "delivery_promise_checked",
               "pre_contract_info_ok", "returns_process_ok", "ad_claims_checked", "platform_policy_checked")
COLUMNS = ["keyword", "title", "category", "brand", "channel", "fulfilment_model", "ebay_url", "market_price_gbp", "sold_30d", "active_listings",
           "supplier_platform", "supplier_url", "supplier_cost_gbp", "supplier_shipping_gbp", "delivery_days_max", "supplier_rating", "ships_from",
           "postage_gbp", "image_urls", "bad_review_themes", "listing_notes", "data_date"]
FENCE = "`" * 3
TASKS = {
    "listings": "Improve the listing for this product so it reads naturally and honestly, as a person would write it. Write it in your own words from the facts in the dossier. "
                "Do not copy competitor wording. Use the bad-review themes to answer likely concerns truthfully. Never invent features.",
    "pricing": "Recommend the price to list at. Use the market price, the number of competing listings and the margin breakdown. Show your reasoning. "
               "The price must still clear the minimum margin in the dossier.",
    "compliance": "Check this product against the compliance rules for its channel. The automatic gate results are in the dossier. Add anything it cannot see "
                  "(product safety, brand or IP risk, claims in the listing). Do not invent rules; name what is missing.",
    "finance": "Check the costs, fees and margin. Say which figures are placeholders or unconfirmed and what would change the result. Flag anything for the accountant. No tax advice.",
}
SHAPES = {
    "listings": '{"verdict": "pass or flag or block", "improved_title": "...", "improved_description": "...", "key_points": ["..."], "notes": "..."}',
    "pricing": '{"verdict": "pass or flag or block", "suggested_price_gbp": 0.0, "reasoning": "..."}',
    "compliance": '{"verdict": "pass or flag or block", "issues": ["..."], "notes": "..."}',
    "finance": '{"verdict": "pass or flag or block", "issues": ["..."], "notes": "..."}',
}


def today():
    return datetime.date.today().isoformat()


def clean(text):
    text = str(text or "").strip()
    return "[removed: looked like personal data]" if find_pii(text) else text


def num(x):
    try:
        return float(str(x).replace("£", "").replace(",", "").strip())
    except ValueError:
        return None


def extract_json(text):
    cands = []
    m = re.search(FENCE + r"(?:json)?\s*(\{.*?\})\s*" + FENCE, text, re.S)
    if m:
        cands.append(m.group(1))
    if "{" in text and "}" in text:
        cands.append(text[text.find("{"):text.rfind("}") + 1])
    for c in cands:
        try:
            return json.loads(c)
        except ValueError:
            continue
    return None


def new_id():
    DOSSIERS.mkdir(parents=True, exist_ok=True)
    prefix = f"P-{today().replace('-', '')}-"
    return f"{prefix}{sum(1 for p in DOSSIERS.glob(prefix + '*.json')) + 1:03d}"


def path(pid):
    return DOSSIERS / f"{pid}.json"


def load(pid):
    p = path(pid)
    if not p.exists():
        sys.exit(f"No dossier {pid}. Run: python3 scripts/research.py list")
    return json.loads(p.read_text())


def save(d):
    DOSSIERS.mkdir(parents=True, exist_ok=True)
    path(d["id"]).write_text(json.dumps(d, indent=2) + "\n")
    (DOSSIERS / f"{d['id']}.md").write_text(document(d))


def note(d, stage, text):
    d["stage"] = stage
    d.setdefault("history", []).append({"date": today(), "stage": stage, "note": text[:200]})


def all_dossiers():
    return [json.loads(p.read_text()) for p in sorted(DOSSIERS.glob("P-*.json"))] if DOSSIERS.exists() else []


def margin_for(d, price=None):
    fees = load_yaml("catalogue/fees.yml")
    cfg = load_yaml("catalogue/research.yml")
    return mg.with_stress({"channel": d["channel"], "sale_price_gbp": price or d["market"]["price_gbp"], "supplier_cost_gbp": d["supplier"]["cost_gbp"],
                           "supplier_shipping_gbp": d["supplier"]["shipping_gbp"], "postage_gbp": d.get("postage_gbp", 0),
                           "fulfilment_model": d["fulfilment_model"]}, fees, cfg["stress_cost_increase_pct"])


def build(row, cfg):
    imgs = [{"url": u.strip(), "rights": "unverified", "path": None} for u in str(row.get("image_urls", "")).split("|") if u.strip().startswith("http")]
    d = {"id": new_id(), "created": today(), "data_date": row.get("data_date") or today(), "channel": (row.get("channel") or "ebay-uk").strip(),
         "keyword": clean(row.get("keyword")), "title": clean(row.get("title")), "category": clean(row.get("category")), "brand": clean(row.get("brand")),
         "fulfilment_model": (row.get("fulfilment_model") or "hold_stock").strip(), "stage": "new", "history": [], "agent_notes": {}, "decisions": [],
         "postage_gbp": num(row.get("postage_gbp")) or 0.0,
         "market": {"url": row.get("ebay_url", "").strip(), "price_gbp": num(row.get("market_price_gbp")) or 0.0, "sold_30d": num(row.get("sold_30d")),
                    "active_listings": num(row.get("active_listings")), "sold_signal": "import",
                    "review_themes": [clean(t) for t in str(row.get("bad_review_themes", "")).split("|") if t.strip()],
                    "listing_notes": clean(row.get("listing_notes")), "images": imgs},
         "supplier": {"platform": clean(row.get("supplier_platform")), "url": row.get("supplier_url", "").strip(), "cost_gbp": num(row.get("supplier_cost_gbp")) or 0.0,
                      "shipping_gbp": num(row.get("supplier_shipping_gbp")) or 0.0, "delivery_days_max": num(row.get("delivery_days_max")),
                      "rating": clean(row.get("supplier_rating")), "ships_from": clean(row.get("ships_from")), "images": []}}
    for f in CONFIRMABLE:
        d[f] = False
    return d


def analyse(d, cfg):
    d["margin"] = margin_for(d)
    d["policy"] = pg.evaluate(d)
    reasons = []
    days = d["supplier"]["delivery_days_max"]
    if days is None or days > cfg["max_supplier_delivery_days"]:
        reasons.append(f"supplier delivery is {days} days; the limit is {cfg['max_supplier_delivery_days']}")
    if d["margin"]["margin_pct"] < cfg["min_margin_pct"]:
        reasons.append(f"margin is {d['margin']['margin_pct']} percent; the minimum is {cfg['min_margin_pct']}")
    reasons += [f"{r['id']}: {r['title']} ({r['detail']})" for r in d["policy"]["results"] if r["status"] == "block"]
    if reasons:
        d["reject_reason"] = "; ".join(reasons)
        note(d, "rejected", d["reject_reason"])
    else:
        note(d, "analysed", f"margin {d['margin']['margin_pct']} percent, gate {d['policy']['overall']}")


def document(d):
    m, s, mk = d.get("margin", {}), d["supplier"], d["market"]
    L = [f"# {d['title']} ({d['id']})", f"Channel: {d['channel']} | Fulfilment: {d['fulfilment_model']} | Stage: {d['stage']} | Data date: {d['data_date']}", "",
         "## Links", f"- eBay listing: {mk['url'] or 'none'}", f"- Supplier ({s['platform']}): {s['url'] or 'none'}", "",
         "## Market", f"- Price: {mk['price_gbp']} GBP | Sold in 30 days: {mk['sold_30d']} | Active listings: {mk['active_listings']} (source: {mk['sold_signal']})",
         f"- Listing notes: {mk['listing_notes'] or 'none'}", "- Bad-review themes: " + ("; ".join(mk["review_themes"]) or "none recorded"), "",
         "## Supplier", f"- Cost {s['cost_gbp']} GBP | Shipping {s['shipping_gbp']} GBP | Delivery up to {s['delivery_days_max']} days | Rating {s['rating']} | Ships from {s['ships_from']}", ""]
    if m:
        L += ["## Margin", f"- Margin {m['margin_pct']} percent (profit {m['profit_gbp']} GBP on {m['net_price_gbp']} GBP). If costs rose {m['stress_cost_increase_pct']} percent: {m['stress_margin_pct']} percent.",
              f"- Costs: item {m['cost_gbp']}, supplier shipping {m['shipping_gbp']}, duty {m['duty_gbp']}, postage {m['postage_gbp']}, packaging {m['packaging_gbp']}, "
              f"fees {m['channel_fees_gbp']}, returns allowance {m['returns_allowance_gbp']}", f"- Fees confirmed: {m['fees_confirmed']}", ""]
    if d.get("policy"):
        L += ["## Compliance gate: " + d["policy"]["overall"]] + [f"- {r['status'].upper()} {r['id']} {r['title']}" + (f": {r['detail']}" if r["detail"] else "")
                                                                  for r in d["policy"]["results"] if r["status"] != "pass"] + [""]
    if d.get("reject_reason"):
        L += ["## Rejected", d["reject_reason"], ""]
    for a, n in d.get("agent_notes", {}).items():
        L += [f"## {a} ({n.get('verdict')})", n.get("text", "")[:3000], ""]
    L += ["## Images (rights unverified: do not publish)"] + [f"- {i['url']}" + (f" saved as {i['path']}" if i.get("path") else "") for i in mk["images"] + s["images"]]
    return "\n".join(L) + "\n"


def cmd_template(a):
    p = RES / "templates" / "products.csv"
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(COLUMNS)
        w.writerow(["silicone baking mat", "Silicone baking mat set", "Home and Garden", "", "ebay-uk", "hold_stock", "https://www.ebay.co.uk/itm/EXAMPLE", "12.99", "180", "260",
                    "wholesaler", "https://supplier.example/item/123", "2.80", "0.60", "4", "4.8", "GB", "2.85", "https://img.example/1.jpg|https://img.example/2.jpg",
                    "slips on hot trays|edges curl", "set of 3, plain photos", today()])
    print("Wrote", p.relative_to(ROOT))
    return 0


def cmd_import(a):
    cfg = load_yaml("catalogue/research.yml")
    rows = list(csv.DictReader(open(a.file, newline="")))
    made = []
    for row in rows[:cfg["max_products_per_run"]]:
        d = build(row, cfg)
        analyse(d, cfg)
        save(d)
        made.append(d)
        print(f"{d['id']} [{d['stage']}] {d['title']}" + (f"  REJECTED: {d['reject_reason']}" if d["stage"] == "rejected" else f"  margin {d['margin']['margin_pct']}%"))
    if len(rows) > cfg["max_products_per_run"]:
        print(f"NOTE: only the first {cfg['max_products_per_run']} rows were used (max_products_per_run).")
    cmd_export(a)
    return 0


def cmd_images(a):
    d = load(a.id)
    folder = IMAGES / d["id"]
    folder.mkdir(parents=True, exist_ok=True)
    n = 0
    for img in d["market"]["images"] + d["supplier"]["images"]:
        if img.get("path") or not img["url"].startswith(("http://", "https://")):
            continue
        try:
            req = urllib.request.Request(img["url"], headers={"User-Agent": "Mozilla/5.0 (research; saves images for analysis)"})
            with urllib.request.urlopen(req, timeout=20) as r:
                ctype = r.headers.get("Content-Type", "")
                data = r.read(5_000_001)
            if not ctype.startswith("image/") or len(data) > 5_000_000:
                print("Skipped (not an image or over 5 MB):", img["url"])
                continue
            ext = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif"}.get(ctype.split(";")[0], ".img")
            n += 1
            f = folder / f"{n:02d}{ext}"
            f.write_bytes(data)
            img["path"] = f.relative_to(ROOT).as_posix()
        except Exception as exc:  # network errors are reported, not fatal
            print("Could not fetch", img["url"], "-", exc)
    save(d)
    print(f"{d['id']}: saved {n} image(s) in {folder.relative_to(ROOT)}. Rights are unverified: use them for analysis only, not in a listing.")
    return 0


def run_agent(agent, task, text, manual=False):
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
        f.write(text)
        p = f.name
    try:
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "run_agent.py"), "--agent", agent, "--task", task, "--input-file", p] + (["--manual"] if manual else []),
                           capture_output=True, text=True, cwd=ROOT)
    finally:
        os.unlink(p)
    return (r.stdout + r.stderr).strip()


def cmd_keywords(a):
    cfg = load_yaml("catalogue/research.yml")
    task = (f"Choose up to {cfg['max_products_per_run']} search keywords for UK product research. Never pick cars, car parts or anything matching the banned list. "
            "Prefer small, light, durable items with steady demand, few safety rules and room for a margin of at least "
            f"{cfg['min_margin_pct']} percent. For each keyword say why, what to look for, and the risk. Learn from the denied lessons in the notes below. "
            "Reply in the shared output format.")
    text = "Banned keywords: " + ", ".join(cfg["banned_keywords"]) + "\nRestricted (flagged): " + ", ".join(cfg["restricted_keywords"]) + "\n"
    print(run_agent("research", task, text, a.manual))
    return 0


def cmd_prepare(a):
    d = load(a.id)
    if d["stage"] in ("rejected", "approved", "denied"):
        sys.exit(f"{d['id']} is {d['stage']}.")
    text = document(d) + "\nOwner checks so far: " + ", ".join(f"{k}={d.get(k)}" for k in CONFIRMABLE) + "\n"
    for ag in REQUIRED:
        task = TASKS[ag] + f" Reply in the shared output format. In the Proposal section include exactly one fenced json block shaped like: {SHAPES[ag]}"
        print(f"--- {ag}\n" + run_agent(ag, task, text, a.manual))
        time.sleep(1.1)  # prompt file names use whole seconds
    print(f"\nWhen each reply is saved in inbox/, run: python3 scripts/research.py attach {d['id']} <agent> inbox/<file>")
    return 0


def recompute_stage(d, cfg):
    d["policy"] = pg.evaluate(d)
    d["margin"] = margin_for(d, d.get("suggested_price_gbp"))
    verdicts = [d["agent_notes"].get(a, {}).get("verdict") for a in REQUIRED]
    problems = []
    if d["margin"]["margin_pct"] < cfg["min_margin_pct"]:
        problems.append(f"margin at the suggested price is {d['margin']['margin_pct']} percent")
    problems += [f"{r['id']} blocks" for r in d["policy"]["results"] if r["status"] == "block"]
    problems += [f"{a} says block" for a in REQUIRED if d["agent_notes"].get(a, {}).get("verdict") == "block"]
    if problems:
        note(d, "blocked", "; ".join(problems))
    elif all(verdicts):
        note(d, "awaiting_approval", "all four reviews attached")
    else:
        d["stage"] = "analysed"


def cmd_attach(a):
    cfg = load_yaml("catalogue/research.yml")
    d = load(a.id)
    if a.agent not in REQUIRED + ("sourcing", "research"):
        sys.exit("Agent must be one of: " + ", ".join(REQUIRED))
    p = ROOT / a.file if not os.path.isabs(a.file) else __import__("pathlib").Path(a.file)
    text = p.read_text()
    j = extract_json(text) or {}
    verdict = j.get("verdict") if j.get("verdict") in ("pass", "flag", "block") else "flag"
    d["agent_notes"][a.agent] = {"verdict": verdict, "text": clean(text)[:6000], "data": {k: v for k, v in j.items() if k != "verdict"}, "date": today()}
    if a.agent == "pricing" and num(j.get("suggested_price_gbp")):
        d["suggested_price_gbp"] = num(j["suggested_price_gbp"])
    recompute_stage(d, cfg)
    save(d)
    print(f"{d['id']}: {a.agent} verdict {verdict}. Stage: {d['stage']}")
    return 0


def cmd_confirm(a):
    if a.field not in CONFIRMABLE:
        sys.exit("Field must be one of: " + ", ".join(CONFIRMABLE))
    d = load(a.id)
    d[a.field] = not a.off
    d["policy"] = pg.evaluate(d)
    save(d)
    print(f"{d['id']}: {a.field} = {d[a.field]}")
    return 0


def set_confirm(pid, field, value):
    if field not in CONFIRMABLE:
        raise ValueError("unknown field")
    d = load(pid)
    d[field] = bool(value)
    d["policy"] = pg.evaluate(d)
    save(d)
    return d


def decide(pid, decision, reason, acknowledge=False):
    """Returns (ok, message). Used by the CLI and the dashboard server."""
    cfg = load_yaml("catalogue/research.yml")
    d = load(pid)
    if find_pii(reason or ""):
        return False, "The reason looks like it contains personal data."
    if d["stage"] != "awaiting_approval":
        return False, f"{pid} is '{d['stage']}', not awaiting approval."
    if decision == "denied":
        note(d, "denied", reason or "denied")
        d["decisions"].append({"date": today(), "decision": "denied", "reason": reason})
        save(d)
        lesson = ROOT / "memory" / "brain" / "research" / f"lesson-{pid}.md"
        lesson.parent.mkdir(parents=True, exist_ok=True)
        lesson.write_text(f"---\ntype: lesson\ntitle: \"Denied: {d['title']}\"\ntags: [research, denied, {d['keyword']}]\n---\n"
                          f"Product '{d['title']}' (keyword {d['keyword']}, channel {d['channel']}) was denied on {today()}. Reason: {reason or 'none given'}.\n"
                          "Do not propose the same product again unless the reason no longer applies.\n")
        return True, "Denied. The reason was saved as a lesson for the research agent."
    d["policy"] = pg.evaluate(d)
    stamp_age = (datetime.date.today() - datetime.date.fromisoformat(d["data_date"])).days
    if d["policy"]["overall"] == "block" or stamp_age > cfg["research_freshness_days"]:
        return False, "Blocked by the compliance gate or stale data: " + "; ".join(f"{r['id']}" for r in d["policy"]["results"] if r["status"] == "block")
    flags = [r for r in d["policy"]["results"] if r["status"] == "flag"]
    if flags and not acknowledge:
        return False, f"{len(flags)} flag(s) need to be acknowledged first: " + ", ".join(r["id"] for r in flags)
    note(d, "approved", reason or "approved")
    d["decisions"].append({"date": today(), "decision": "approved", "reason": reason, "flags_acknowledged": [r["id"] for r in flags]})
    save(d)
    launch_pack(d)
    return True, f"Approved. Launch pack written to research/approved/{pid}/. Nothing was bought or listed."


def launch_pack(d):
    out = APPROVED / d["id"]
    out.mkdir(parents=True, exist_ok=True)
    ln = d["agent_notes"].get("listings", {}).get("data", {})
    price = d.get("suggested_price_gbp") or d["market"]["price_gbp"]
    (out / "listing-draft.md").write_text(
        f"# Listing draft for {d['id']} ({d['channel']})\n\nTitle: {ln.get('improved_title') or d['title']}\n\nPrice: {price} GBP\n\n"
        f"Description:\n{ln.get('improved_description') or '(none yet)'}\n\nKey points:\n" + "\n".join(f"- {k}" for k in ln.get("key_points", [])) +
        "\n\nUse your own photos. The saved supplier and competitor images are for analysis only.\n")
    (out / "catalogue-entry.yml").write_text(yaml.safe_dump({"sku": d["id"], "title": ln.get("improved_title") or d["title"], "description": ln.get("improved_description", ""),
                                                           "brand": d["brand"], "condition": "new", "cost_gbp": d["supplier"]["cost_gbp"], "price_gbp": price, "stock": 0,
                                                           "category": d["category"], "supplier": d["supplier"]["url"], "images": [],
                                                           "channel_overrides": {d["channel"]: {}}}, sort_keys=False))
    (out / "sample-order-checklist.md").write_text(
        f"# Sample order checklist for {d['id']}\n- [ ] Order 1 to 2 samples from the supplier ({d['supplier']['url']})\n- [ ] Note the real delivery time\n"
        "- [ ] Check quality against the bad-review themes\n- [ ] Take your own photos\n- [ ] Check safety marking and documents (then: research.py confirm safety_docs_ok)\n"
        "- [ ] Mark stock_in_hand when it arrives\n- [ ] Re-run the margin with real costs\n- [ ] Only then list it, by hand\n")


def cmd_decide(a):
    ok, msg = decide(a.id, a.decision, a.reason, a.acknowledge_flags)
    print(("OK: " if ok else "REFUSED: ") + msg)
    return 0 if ok else 1


def summary_item(d):
    return {k: d.get(k) for k in ("id", "title", "channel", "fulfilment_model", "stage", "data_date", "keyword", "category", "brand", "reject_reason",
                                  "suggested_price_gbp", "margin", "policy", "agent_notes", "decisions", "history", *CONFIRMABLE)} | {
        "market": {**d["market"], "images": [{**i, "url_local": "/" + i["path"] if i.get("path") else None} for i in d["market"]["images"]]},
        "supplier": d["supplier"]}


def api_state():
    ds = all_dossiers()
    cfg = load_yaml("catalogue/research.yml")
    stale = [pg.load_rules(c)[0] and pg.evaluate({"channel": c, "data_date": today()})["stale"] for c in ("ebay-uk", "social")]
    return {"config": {k: cfg[k] for k in ("min_margin_pct", "max_supplier_delivery_days", "research_freshness_days", "max_products_per_run")},
            "counts": {s: sum(1 for d in ds if d["stage"] == s) for s in ("awaiting_approval", "analysed", "blocked", "approved", "denied", "rejected")},
            "stale_rules": [s for s in stale if s], "confirmable": list(CONFIRMABLE), "items": [summary_item(d) for d in ds]}


def cmd_export(a):
    EXPORTS.mkdir(parents=True, exist_ok=True)
    p = EXPORTS / "summary.csv"
    with p.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "title", "channel", "stage", "price_gbp", "cost_gbp", "shipping_gbp", "delivery_days_max", "margin_pct", "ebay_url", "supplier_url", "reject_reason"])
        for d in all_dossiers():
            w.writerow([d["id"], d["title"], d["channel"], d["stage"], d["market"]["price_gbp"], d["supplier"]["cost_gbp"], d["supplier"]["shipping_gbp"],
                        d["supplier"]["delivery_days_max"], d.get("margin", {}).get("margin_pct"), d["market"]["url"], d["supplier"]["url"], d.get("reject_reason", "")])
    print("Summary:", p.relative_to(ROOT))
    return 0


def cmd_list(a):
    ds = all_dossiers()
    for d in ds:
        print(f"{d['id']} [{d['stage']}] {d['channel']} {d['title']}  margin {d.get('margin', {}).get('margin_pct')}")
    print(f"{len(ds)} dossier(s)" if ds else "No dossiers yet. Run: python3 scripts/research.py template")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for n in ("template", "list", "export"):
        sub.add_parser(n)
    sub.add_parser("keywords").add_argument("--manual", action="store_true", help="free route: prepare prompts to paste into Claude or Gemini")
    sub.add_parser("import").add_argument("file")
    sub.add_parser("images").add_argument("id")
    p = sub.add_parser("prepare")
    p.add_argument("id"), p.add_argument("--manual", action="store_true", help="free route: prepare prompts to paste into Claude or Gemini")
    p = sub.add_parser("attach")
    p.add_argument("id"), p.add_argument("agent"), p.add_argument("file")
    p = sub.add_parser("confirm")
    p.add_argument("id"), p.add_argument("field"), p.add_argument("--off", action="store_true")
    p = sub.add_parser("decide")
    p.add_argument("id"), p.add_argument("decision", choices=["approved", "denied"]), p.add_argument("--reason", default="")
    p.add_argument("--acknowledge-flags", action="store_true")
    a = ap.parse_args()
    return {"template": cmd_template, "keywords": cmd_keywords, "import": cmd_import, "images": cmd_images, "prepare": cmd_prepare, "attach": cmd_attach,
            "confirm": cmd_confirm, "decide": cmd_decide, "list": cmd_list, "export": cmd_export}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
