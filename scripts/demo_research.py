#!/usr/bin/env python3
"""Fills the research pipeline with clearly labelled DEMO products so you can see the whole workflow on the dashboard.
Free: no AI calls and no network. The agent replies are simulated, and every title starts with "DEMO - ".
  python3 scripts/demo_research.py            create the demo products
  python3 scripts/demo_research.py --clean    remove them again (real products are never touched)"""
import argparse
import json
import shutil
import struct
import sys
import tempfile
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import research as rs  # noqa: E402
from check_budget import ROOT, load_yaml  # noqa: E402

PREFIX = "DEMO - "
FENCE = "`" * 3


def png(path, rgb, size=96):
    raw = b"".join(b"\x00" + bytes(rgb) * size for _ in range(size))
    chunk = lambda t, d: struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)  # noqa: E731
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def row(keyword, title, category, channel, model, price, cost, ship, days, postage="0", themes="", notes=""):
    return {"keyword": keyword, "title": PREFIX + title, "category": category, "brand": "", "channel": channel, "fulfilment_model": model,
            "ebay_url": "https://www.ebay.co.uk/itm/DEMO", "market_price_gbp": price, "sold_30d": "180", "active_listings": "260", "supplier_platform": "wholesaler (demo)",
            "supplier_url": "https://supplier.example/demo", "supplier_cost_gbp": cost, "supplier_shipping_gbp": ship, "delivery_days_max": days, "supplier_rating": "4.7",
            "ships_from": "GB", "postage_gbp": postage, "image_urls": "", "bad_review_themes": themes, "listing_notes": "demo data", "data_date": ""}


def replies(title, price):
    return {
        "listings": {"verdict": "pass", "improved_title": title.replace(PREFIX, "") + ", easy to clean", "improved_description":
                     "A well-made, practical product. This text is a DEMO written for the dashboard.", "key_points": ["Easy to clean", "Built to last", "Sensible size"], "notes": "demo"},
        "pricing": {"verdict": "pass", "suggested_price_gbp": price, "reasoning": "DEMO: sits in the middle of the competing range."},
        "compliance": {"verdict": "flag", "issues": ["Check product safety marking"], "notes": "demo"},
        "finance": {"verdict": "flag", "issues": ["Fee figures are placeholders"], "notes": "demo"},
    }


def attach(pid, agent, body, tmp):
    f = tmp / f"{pid}-{agent}.md"
    f.write_text("Proposal:\n" + FENCE + "json\n" + json.dumps(body) + "\n" + FENCE + "\n")
    class A:  # the same path as: research.py attach P-... AGENT FILE
        pass
    a = A()
    a.id, a.agent, a.file = pid, agent, str(f)
    rs.cmd_attach(a)


def demo_dossiers():
    return [d for d in rs.all_dossiers() if d["title"].startswith(PREFIX)]


def create():
    if demo_dossiers():
        print("Demo products already exist. Run with --clean first.")
        return 1
    cfg = load_yaml("catalogue/research.yml")
    rows = [
        row("pet grooming glove", "Pet grooming glove pair", "Pets", "ebay-uk", "wholesale_dropship", "14.99", "1.60", "0.80", "4", themes="hair sticks to the glove|seams split"),
        row("bamboo cutting board", "Bamboo cutting board set", "Kitchen", "ebay-uk", "hold_stock", "19.99", "3.20", "1.00", "3", postage="3.20", themes="warps after washing"),
        row("silicone food bags", "Reusable silicone food bags", "Kitchen", "social", "marketplace_dropship", "12.99", "1.80", "0.90", "4", themes="zip splits|hard to wash"),
        row("cotton napkins", "Cotton napkin set", "Home", "ebay-uk", "wholesale_dropship", "16.99", "2.20", "0.90", "4", themes="colour runs"),
        row("car phone holder", "Car phone holder", "Auto", "ebay-uk", "hold_stock", "14.99", "3.00", "1.00", "3", postage="2.85"),
        row("desk organiser", "Bamboo desk organiser", "Office", "ebay-uk", "marketplace_dropship", "19.99", "4.00", "0", "4"),
        row("yoga strap", "Cotton yoga strap", "Sport", "ebay-uk", "wholesale_dropship", "9.99", "2.00", "0.50", "9"),
        row("kitchen mat", "Thin margin kitchen mat", "Kitchen", "ebay-uk", "wholesale_dropship", "6.00", "3.00", "1.00", "4"),
    ]
    made = {}
    for r in rows:
        d = rs.build(r, cfg)
        rs.analyse(d, cfg)
        rs.save(d)
        made[r["title"]] = d
        print(f"{d['id']} [{d['stage']}] {d['title']}")
    colours = [(52, 168, 150), (240, 160, 70), (120, 130, 230), (230, 90, 110)]
    for i, name in enumerate(["Pet grooming glove pair", "Bamboo cutting board set", "Reusable silicone food bags"]):
        d = made[PREFIX + name]
        d["market"]["images"] = [{"url": "demo://image", "rights": "unverified", "path": None} for _ in range(2)]
        for n, img in enumerate(d["market"]["images"], 1):
            p = rs.IMAGES / d["id"] / f"{n:02d}.png"
            png(p, colours[(i + n) % 4])
            img["path"] = p.relative_to(ROOT).as_posix()
        rs.save(d)
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        for name, price in (("Pet grooming glove pair", 14.49), ("Reusable silicone food bags", 12.49), ("Bamboo cutting board set", 14.49)):
            d = made[PREFIX + name]
            for ag, body in replies(d["title"], price).items():
                attach(d["id"], ag, body, tmp)
    rs.cmd_export(argparse.Namespace())
    print("\nDemo ready: 2 products awaiting your decision, 1 blocked (the price suggestion breaks the margin), 1 in progress, 4 rejected by the rules.")
    print("Open it:  python3 scripts/dashboard_server.py   then the Approvals page.   Tidy up:  python3 scripts/demo_research.py --clean")
    return 0


def clean():
    n = 0
    for d in demo_dossiers():
        pid = d["id"]
        for p in (rs.DOSSIERS / f"{pid}.json", rs.DOSSIERS / f"{pid}.md", ROOT / "memory" / "brain" / "research" / f"lesson-{pid}.md"):
            p.unlink(missing_ok=True)
        shutil.rmtree(rs.IMAGES / pid, ignore_errors=True)
        shutil.rmtree(rs.APPROVED / pid, ignore_errors=True)
        n += 1
    lessons = ROOT / "memory" / "brain" / "research"
    if lessons.exists() and not any(lessons.iterdir()):
        lessons.rmdir()
    rs.cmd_export(argparse.Namespace())
    print(f"Removed {n} demo product(s). Real products were not touched.")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--clean", action="store_true")
    return clean() if ap.parse_args().clean else create()


if __name__ == "__main__":
    sys.exit(main())
