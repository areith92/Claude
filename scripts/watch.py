#!/usr/bin/env python3
"""The daily watch: parcels, supplier prices, profit and loss, social and shop figures, and the alerts that need you.
Data is kept by scripts/store.py (local files, or your private Supabase when its keys are set). No customer personal data: order IDs only.

  python3 scripts/watch.py scan [--alert-file F]       check every parcel and price now (this is what runs daily on GitHub)
  python3 scripts/watch.py order add|import|update|list
  python3 scripts/watch.py ship add|import|update|list
  python3 scripts/watch.py listing add|import|list     what you currently sell, and what you assumed it costs
  python3 scripts/watch.py price import FILE           new supplier prices (product_id,cost_gbp,shipping_gbp,source,checked_date)
  python3 scripts/watch.py pnl [--days 14]             daily and weekly profit and loss
  python3 scripts/watch.py metrics import FILE | shop import FILE | spend add --date D --platform P --amount N
  python3 scripts/watch.py alerts [list|ack ID|close ID] | status
"""
import argparse
import csv
import datetime as dt
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import yaml  # noqa: E402
import margin as mg  # noqa: E402
from check_budget import ROOT, load_yaml  # noqa: E402
from pii_guard import find_pii  # noqa: E402
from store import StoreError, open_store, put  # noqa: E402

FEE_CHANNEL = {"ebay-uk": "ebay-uk", "social": "social", "shopify": "social"}


def cfg():
    p = ROOT / "governance" / "watch.yml"
    base = {"ship": {"default_promised_days": 5, "critical_after_days_late": 3, "no_tracking_after_days": 2, "stale_after_days": 3},
            "price": {"rise_alert_pct": 5}, "metrics": {"window_days": 7}}
    got = (yaml.safe_load(p.read_text()) or {}) if p.exists() else {}
    return {k: {**base[k], **(got.get(k) or {})} for k in base}


def day(s):
    return dt.date.fromisoformat(str(s)[:10])


def read_csv(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def now_iso():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def num(x, default=0.0):
    try:
        return float(str(x).replace("£", "").replace(",", "").strip())
    except ValueError:
        return default


def clean_text(s):
    return "[removed: looked like personal data]" if find_pii(str(s or "")) else str(s or "").strip()


def raise_alert(st, new, kind, severity, entity, entity_id, message, key):
    if st.select("alerts", {"dedupe_key": key}):
        return False
    row = {"created_at": now_iso(), "kind": kind, "severity": severity, "entity": entity, "entity_id": entity_id, "message": message[:500], "status": "open", "dedupe_key": key}
    st.insert("alerts", row)
    new.append(row)
    return True


# ------------------------------------------------------------------ orders and shipments
def expected_by(s):
    return day(s["shipped_date"]) + dt.timedelta(days=int(s.get("promised_days") or 5)) if s.get("shipped_date") else None


def order_row(r):
    return {"id": r["id"], "order_date": str(r.get("order_date") or dt.date.today()), "channel": r.get("channel") or "ebay-uk", "product_id": r.get("product_id") or None,
            "title": clean_text(r.get("title")), "qty": int(num(r.get("qty"), 1)) or 1, "revenue_gbp": num(r.get("revenue_gbp")), "item_cost_gbp": num(r.get("item_cost_gbp")),
            "shipping_cost_gbp": num(r.get("shipping_cost_gbp")), "fees_gbp": num(r.get("fees_gbp")), "refund_gbp": num(r.get("refund_gbp")), "status": r.get("status") or "new"}


def ship_add(st, order_id, carrier="", tracking_no="", shipped_date=None, promised_days=None, supplier="", status=None, today=None):
    if not st.select("orders", {"id": order_id}):
        raise ValueError(f"Order {order_id} is not recorded yet. Add it first: python3 scripts/watch.py order add --id {order_id} ...")
    today = today or dt.date.today()
    n = sum(1 for s in st.select("shipments") if s["id"].startswith(f"S-{today:%Y%m%d}")) + 1
    row = {"id": f"S-{today:%Y%m%d}-{n:03d}", "order_id": order_id, "supplier": clean_text(supplier), "carrier": clean_text(carrier), "tracking_no": "".join(str(tracking_no).split()),
           "shipped_date": str(shipped_date) if shipped_date else None, "promised_days": int(promised_days or cfg()["ship"]["default_promised_days"]),
           "status": status or ("in_transit" if tracking_no and shipped_date else "pending"), "last_event": "", "last_event_at": None, "last_checked_at": None, "delivered_date": None}
    st.insert("shipments", row)
    if shipped_date:
        st.update("orders", {"id": order_id}, {"status": "shipped"})
    return row


def ship_update(st, sid, status=None, event="", today=None, new=None):
    rows = st.select("shipments", {"id": sid})
    if not rows:
        raise ValueError(f"No shipment {sid}")
    s, today = rows[0], today or dt.date.today()
    vals = {"last_event": clean_text(event) if event else s.get("last_event", ""), "last_event_at": now_iso() if (event or status) else s.get("last_event_at")}
    if status:
        vals["status"] = status
    if status == "delivered":
        vals["delivered_date"] = str(today)
        due = expected_by(s)
        if due and today > due and new is not None:
            raise_alert(st, new, "delivered_late", "info", "shipment", sid, f"Parcel {sid} (order {s['order_id']}) arrived {(today - due).days} day(s) late. Worth noting for supplier {s.get('supplier') or '?'}.", f"late-done:{sid}")
        st.update("orders", {"id": s["order_id"]}, {"status": "delivered"})
    st.update("shipments", {"id": sid}, vals)
    return {**s, **vals}


def scan_shipments(st, today, new):
    c = cfg()["ship"]
    for s in st.select("shipments"):
        if s["status"] in ("delivered", "returned"):
            continue
        sid, due = s["id"], expected_by(s)
        who = f"Parcel {sid} (order {s['order_id']}, {s.get('carrier') or 'carrier not set'}, tracking {s.get('tracking_no') or 'none'})"
        if s["status"] == "exception":
            raise_alert(st, new, "parcel_exception", "critical", "shipment", sid, f"{who} has a delivery problem: {s.get('last_event') or 'no detail'}.", f"exception:{sid}:{s.get('last_event', '')[:20]}")
        if due and today > due:
            late = (today - due).days
            crit = late >= c["critical_after_days_late"]
            raise_alert(st, new, "parcel_overdue", "critical" if crit else "warning", "shipment", sid,
                        f"{who} is {late} day(s) past its promised {s['promised_days']}-day delivery (due {due}). Last update: {s.get('last_event') or 'none'}.", f"overdue:{sid}:{'c' if crit else 'w'}")
        shipped = day(s["shipped_date"]) if s.get("shipped_date") else None
        if shipped and not s.get("tracking_no") and (today - shipped).days >= c["no_tracking_after_days"]:
            raise_alert(st, new, "no_tracking", "warning", "shipment", sid, f"{who} shipped {(today - shipped).days} days ago and still has no tracking number.", f"notrack:{sid}")
        last = day(s["last_event_at"]) if s.get("last_event_at") else None
        if last and s["status"] != "pending" and (today - last).days >= c["stale_after_days"]:
            raise_alert(st, new, "parcel_stuck", "warning", "shipment", sid, f"{who} has had no update for {(today - last).days} days. It may be stuck.", f"stuck:{sid}:{last}")
        st.update("shipments", {"id": sid}, {"last_checked_at": now_iso()})


# ------------------------------------------------------------------ listings and supplier prices
def latest_price(st, product_id):
    rows = sorted(st.select("supplier_prices", {"product_id": product_id}), key=lambda r: (str(r["checked_date"]), r.get("id", 0)), reverse=True)
    return rows[0] if rows else None


def margin_at(listing, cost, shipping):
    fees = load_yaml("catalogue/fees.yml")
    return mg.compute({"channel": FEE_CHANNEL.get(listing["channel"], "social"), "sale_price_gbp": float(listing["price_gbp"]), "supplier_cost_gbp": cost, "supplier_shipping_gbp": shipping,
                       "postage_gbp": float(listing.get("postage_gbp") or 0), "fulfilment_model": listing.get("fulfilment_model", "hold_stock")}, fees)


def check_prices(st, today, new):
    minimum, rise = load_yaml("catalogue/research.yml")["min_margin_pct"], cfg()["price"]["rise_alert_pct"]
    for l in st.select("listings"):
        if not l.get("active", True):
            continue
        p = latest_price(st, l["product_id"])
        if not p:
            continue
        cost, ship = float(p["cost_gbp"]), float(p.get("shipping_gbp") or 0)
        was = float(l["assumed_cost_gbp"]) + float(l.get("assumed_shipping_gbp") or 0)
        pct = ((cost + ship) / was - 1) * 100 if was else 0
        m = margin_at(l, cost, ship)
        name = l.get("title") or l["product_id"]
        if m["margin_pct"] < minimum:
            loss = m["profit_gbp"] < 0
            raise_alert(st, new, "margin_below_minimum", "critical" if loss else "warning", "listing", l["product_id"],
                        f"{name}: the supplier now charges {cost:.2f} + {ship:.2f} shipping (was {was:.2f} together). Margin is {m['margin_pct']}% against your {minimum}% minimum" + (" and every sale now LOSES money. Pause the listing." if loss else ". Reprice or pause it."),
                        f"margin:{l['product_id']}:{cost:.2f}:{ship:.2f}")
        elif pct >= rise:
            raise_alert(st, new, "supplier_price_rise", "warning", "listing", l["product_id"], f"{name}: supplier cost up {pct:.0f}% (now {cost + ship:.2f}, was {was:.2f}). Margin is still {m['margin_pct']}%.", f"rise:{l['product_id']}:{cost:.2f}:{ship:.2f}")
        for o in st.select("orders", {"product_id": l["product_id"]}):
            if o["status"] != "new":
                continue  # already bought from the supplier at the old price
            unit_now, qty = cost, int(o.get("qty") or 1)
            profit = float(o["revenue_gbp"]) - (unit_now * qty + ship) - float(o.get("fees_gbp") or 0)
            old_total = float(o["item_cost_gbp"]) + float(o["shipping_cost_gbp"])
            if profit < 0 and unit_now * qty + ship > old_total:
                raise_alert(st, new, "order_exposed", "critical", "order", o["id"],
                            f"Order {o['id']} sold for {float(o['revenue_gbp']):.2f} but the supplier now charges {unit_now * qty + ship:.2f} (cost when sold: {old_total:.2f}). Fulfilling it loses {abs(profit):.2f}. Decide: fulfil anyway, ask the supplier, or cancel and refund.",
                            f"exposed:{o['id']}:{unit_now:.2f}")


# ------------------------------------------------------------------ profit and loss
def ai_spend_by_day():
    out, p = {}, ROOT / "logs" / "costs.csv"
    if p.exists():
        with p.open(newline="") as f:
            for r in csv.DictReader(f):
                if r.get("date"):
                    out[r["date"]] = out.get(r["date"], 0.0) + num(r.get("cost_gbp"))
    return out


def estimate_fees(channel, revenue):
    return mg.compute({"channel": FEE_CHANNEL.get(channel, "social"), "sale_price_gbp": revenue, "supplier_cost_gbp": 0, "supplier_shipping_gbp": 0, "fulfilment_model": "wholesale_dropship"}, load_yaml("catalogue/fees.yml"))["channel_fees_gbp"]


def pnl(st, today, days=14):
    orders = [o for o in st.select("orders") if o["status"] != "cancelled"]
    ads, ai = {}, ai_spend_by_day()
    for r in st.select("ad_spend_ledger"):
        ads[str(r["spend_date"])] = ads.get(str(r["spend_date"]), 0.0) + float(r["amount_gbp"])
    rows, estimated = [], 0
    for i in range(days - 1, -1, -1):
        d = today - dt.timedelta(days=i)
        todays = [o for o in orders if str(o["order_date"]) == str(d)]
        fees = 0.0
        for o in todays:
            if float(o.get("fees_gbp") or 0) > 0:
                fees += float(o["fees_gbp"])
            else:
                fees += estimate_fees(o["channel"], float(o["revenue_gbp"]))
                estimated += 1
        rev, ref = sum(float(o["revenue_gbp"]) for o in todays), sum(float(o.get("refund_gbp") or 0) for o in todays)
        cogs = sum(float(o["item_cost_gbp"]) + float(o["shipping_cost_gbp"]) for o in todays)
        a, k = ads.get(str(d), 0.0), ai.get(str(d), 0.0)
        profit = rev - ref - cogs - fees - a - k
        rows.append({"date": str(d), "orders": len(todays), "revenue": round(rev, 2), "refunds": round(ref, 2), "cogs": round(cogs, 2), "fees": round(fees, 2), "ads": round(a, 2), "ai": round(k, 4), "profit": round(profit, 2)})
    weeks = {}
    for r in rows:
        monday = day(r["date"]) - dt.timedelta(days=day(r["date"]).weekday())
        w = weeks.setdefault(str(monday), {"week_start": str(monday), "orders": 0, "revenue": 0.0, "refunds": 0.0, "cogs": 0.0, "fees": 0.0, "ads": 0.0, "ai": 0.0, "profit": 0.0, "days": 0})
        for k in ("orders", "revenue", "refunds", "cogs", "fees", "ads", "ai", "profit"):
            w[k] += r[k]
        w["days"] += 1
    weekly = [{**w, **{k: round(w[k], 2) for k in ("revenue", "refunds", "cogs", "fees", "ads", "ai", "profit")}, "spend": round(w["cogs"] + w["fees"] + w["ads"] + w["ai"], 2)} for w in weeks.values()]
    return {"daily": rows, "weekly": weekly, "fees_estimated_orders": estimated}


# ------------------------------------------------------------------ social metrics and shop figures
def import_metrics(st, path):
    n = 0
    for r in read_csv(path):
        row = {"platform": r["platform"].strip().lower(), "post_ref": clean_text(r.get("post_ref")), "metric_date": r["date"].strip(), "captured_at": now_iso(), "source": "import",
               **{k: int(num(r.get(k))) for k in ("impressions", "reach", "clicks", "likes", "comments", "shares", "saves", "followers", "conversions")},
               "spend_gbp": num(r.get("spend_gbp")), "revenue_gbp": num(r.get("revenue_gbp"))}
        put(st, "social_metrics", row, ["platform", "post_ref", "metric_date", "source"])
        n += 1
    return n


def import_shop(st, path):
    n = 0
    for r in read_csv(path):
        row = {"day": r["date"].strip(), "channel": (r.get("channel") or "shopify").strip(), "sessions": int(num(r.get("sessions"))), "carts": int(num(r.get("carts"))), "checkouts": int(num(r.get("checkouts"))),
               "orders": int(num(r.get("orders"))), "abandoned_checkouts": int(num(r.get("abandoned_checkouts"))), "revenue_gbp": num(r.get("revenue_gbp"))}
        put(st, "shop_daily", row, ["day", "channel"])
        n += 1
    return n


def summary(st=None, today=None):
    st, today = st or open_store(), today or dt.date.today()
    window = cfg()["metrics"]["window_days"]
    since = str(today - dt.timedelta(days=window - 1))
    alerts = sorted([a for a in st.select("alerts") if a["status"] != "closed"], key=lambda a: ({"critical": 0, "warning": 1, "info": 2}[a["severity"]], -a.get("id", 0)))
    ships = []
    for s in sorted(st.select("shipments"), key=lambda s: str(s.get("shipped_date") or "")):
        due = expected_by(s)
        ships.append({"id": s["id"], "order_id": s["order_id"], "carrier": s.get("carrier", ""), "tracking_no": s.get("tracking_no", ""), "supplier": s.get("supplier", ""), "status": s["status"],
                      "shipped_date": s.get("shipped_date"), "due": str(due) if due else None, "days_late": (today - due).days if due and s["status"] not in ("delivered", "returned") and today > due else 0,
                      "last_event": s.get("last_event", "")})
    minimum, listings = load_yaml("catalogue/research.yml")["min_margin_pct"], []
    for l in st.select("listings"):
        p = latest_price(st, l["product_id"])
        cost, ship = (float(p["cost_gbp"]), float(p.get("shipping_gbp") or 0)) if p else (float(l["assumed_cost_gbp"]), float(l.get("assumed_shipping_gbp") or 0))
        m = margin_at(l, cost, ship)
        listings.append({"product_id": l["product_id"], "title": l.get("title", ""), "channel": l["channel"], "price_gbp": float(l["price_gbp"]), "cost_now_gbp": round(cost + ship, 2),
                         "cost_assumed_gbp": round(float(l["assumed_cost_gbp"]) + float(l.get("assumed_shipping_gbp") or 0), 2), "margin_pct": m["margin_pct"], "ok": m["margin_pct"] >= minimum, "price_checked": bool(p)})
    social = {}
    for r in st.select("social_metrics"):
        if str(r["metric_date"]) >= since:
            s = social.setdefault(r["platform"], {"platform": r["platform"], "posts": set(), **{k: 0 for k in ("impressions", "reach", "clicks", "likes", "comments", "shares", "saves", "conversions")}})
            s["posts"].add(r.get("post_ref", ""))
            for k in ("impressions", "reach", "clicks", "likes", "comments", "shares", "saves", "conversions"):
                s[k] += int(r.get(k) or 0)
    social = [{**{k: v for k, v in s.items() if k != "posts"}, "posts": len(s["posts"]), "engagement_pct": round((s["likes"] + s["comments"] + s["shares"] + s["saves"]) / s["impressions"] * 100, 2) if s["impressions"] else 0.0} for s in social.values()]
    f = {k: 0 for k in ("sessions", "carts", "checkouts", "orders", "abandoned_checkouts")}
    revenue = 0.0
    for r in st.select("shop_daily"):
        if str(r["day"]) >= since:
            for k in f:
                f[k] += int(r.get(k) or 0)
            revenue += float(r.get("revenue_gbp") or 0)
    f["revenue_gbp"] = round(revenue, 2)
    f["abandonment_pct"] = round(f["abandoned_checkouts"] / (f["checkouts"] or 1) * 100, 1) if f["checkouts"] else 0.0
    f["conversion_pct"] = round(f["orders"] / f["sessions"] * 100, 2) if f["sessions"] else 0.0
    try:
        import inbox
        inbox_state = inbox.summary(st)
    except Exception:  # the inbox is optional
        inbox_state = {"open": 0, "awaiting_approval": 0, "escalated": 0, "items": []}
    return {"store": st.kind, "alerts": alerts, "shipments": ships, "listings": listings, "pnl": pnl(st, today), "social": sorted(social, key=lambda s: s["platform"]), "funnel": f, "inbox": inbox_state,
            "window_days": window, "min_margin_pct": minimum}


# ------------------------------------------------------------------ command line
def cmd_order(a, st):
    if a.sub == "add":
        row = order_row({"id": a.id, "order_date": a.date, "channel": a.channel, "product_id": a.product, "title": a.title, "qty": a.qty, "revenue_gbp": a.revenue, "item_cost_gbp": a.cost,
                         "shipping_cost_gbp": a.shipping, "fees_gbp": a.fees, "refund_gbp": a.refund, "status": a.status})
        put(st, "orders", row, ["id"])
        print(f"ORDER {row['id']} saved ({row['status']}).")
    elif a.sub == "import":
        rows = [order_row({"id": r["order_id"], **r}) for r in read_csv(a.file)]
        for row in rows:
            put(st, "orders", row, ["id"])
        print(f"{len(rows)} order(s) imported.")
    elif a.sub == "update":
        vals = {k: v for k, v in (("status", a.status), ("refund_gbp", a.refund)) if v is not None}
        print(f"{st.update('orders', {'id': a.id}, vals)} order(s) updated.")
    else:
        for o in sorted(st.select("orders"), key=lambda o: str(o["order_date"])):
            print(f"{o['id']} {o['order_date']} {o['channel']} [{o['status']}] revenue {float(o['revenue_gbp']):.2f} cost {float(o['item_cost_gbp']) + float(o['shipping_cost_gbp']):.2f}")
    return 0


def cmd_ship(a, st):
    new = []
    if a.sub == "add":
        row = ship_add(st, a.order, a.carrier, a.tracking, a.shipped, a.promised_days, a.supplier)
        print(f"SHIPMENT {row['id']} added. Due {expected_by(row) or 'when it ships'}.")
    elif a.sub == "import":
        for r in read_csv(a.file):
            ship_add(st, r["order_id"], r.get("carrier", ""), r.get("tracking_no", ""), r.get("shipped_date") or None, r.get("promised_days") or None, r.get("supplier", ""))
        print("Shipments imported.")
    elif a.sub == "update":
        ship_update(st, a.id, a.status, a.event or "", new=new)
        print(f"{a.id} updated." + (f" {len(new)} note(s) raised." if new else ""))
    else:
        for s in summary(st)["shipments"]:
            print(f"{s['id']} order {s['order_id']} [{s['status']}] {s['carrier'] or '-'} {s['tracking_no'] or 'no tracking'} due {s['due'] or '-'}" + (f"  LATE {s['days_late']}d" if s["days_late"] else ""))
    return 0


def cmd_listing(a, st):
    if a.sub == "add":
        rows = [{"product_id": a.product, "title": clean_text(a.title), "channel": a.channel, "price_gbp": a.price, "assumed_cost_gbp": a.cost, "assumed_shipping_gbp": a.shipping, "fulfilment_model": a.model, "postage_gbp": a.postage}]
    elif a.sub == "import":
        rows = [{"product_id": r["product_id"], "title": clean_text(r.get("title")), "channel": r.get("channel") or "ebay-uk", "price_gbp": num(r["price_gbp"]), "assumed_cost_gbp": num(r["assumed_cost_gbp"]),
                 "assumed_shipping_gbp": num(r.get("assumed_shipping_gbp")), "fulfilment_model": r.get("fulfilment_model") or "hold_stock", "postage_gbp": num(r.get("postage_gbp"))} for r in read_csv(a.file)]
    else:
        for l in summary(st)["listings"]:
            print(f"{l['product_id']} {l['channel']} price {l['price_gbp']:.2f} cost now {l['cost_now_gbp']:.2f} margin {l['margin_pct']}% {'OK' if l['ok'] else 'BELOW MINIMUM'}")
        return 0
    for r in rows:
        put(st, "listings", {**r, "active": True}, ["product_id"])
    print(f"{len(rows)} listing(s) saved.")
    return 0


def cmd_price(a, st):
    n = 0
    for r in read_csv(a.file):
        put(st, "supplier_prices", {"product_id": r["product_id"], "checked_date": r.get("checked_date") or str(dt.date.today()), "cost_gbp": num(r["cost_gbp"]), "shipping_gbp": num(r.get("shipping_gbp")), "source": r.get("source") or "import"},
            ["product_id", "checked_date", "source"])
        n += 1
    print(f"{n} supplier price(s) recorded. Run: python3 scripts/watch.py scan")
    return 0


def cmd_scan(a, st):
    today, new = dt.date.fromisoformat(a.today) if a.today else dt.date.today(), []
    scan_shipments(st, today, new)
    check_prices(st, today, new)
    open_n = len([x for x in st.select("alerts") if x["status"] == "open"])
    print(f"Scanned parcels and supplier prices ({st.describe()}). {len(new)} new alert(s), {open_n} open in total.")
    for n in new:
        print(f"  {n['severity'].upper():8} {n['message']}")
    if a.alert_file:
        with open(a.alert_file, "w") as f:
            if new:
                f.write(f"# Daily watch {today}: {len(new)} new alert(s)\n\n" + "\n".join(f"- **{n['severity'].upper()}** {n['message']}" for n in new) + "\n\nSee the Operations page on the dashboard. Acknowledge with: python3 scripts/watch.py alerts ack ID\n")
    return 0


def cmd_pnl(a, st):
    r = pnl(st, dt.date.today(), a.days)
    print("WEEKLY (Monday to Sunday, inside the window)")
    for w in r["weekly"]:
        print(f"  from {w['week_start']}: spent {w['spend']:>8.2f}  earned {w['revenue'] - w['refunds']:>8.2f}  profit {w['profit']:>8.2f}   (orders {w['orders']}, ads {w['ads']:.2f}, AI {w['ai']:.2f})")
    print("DAILY")
    for d in r["daily"]:
        print(f"  {d['date']}  orders {d['orders']:>3}  revenue {d['revenue']:>8.2f}  costs {d['cogs'] + d['fees'] + d['ads'] + d['ai']:>8.2f}  profit {d['profit']:>8.2f}")
    if r["fees_estimated_orders"]:
        print(f"NOTE: fees were estimated for {r['fees_estimated_orders']} order(s) from catalogue/fees.yml (placeholders). Put the real fee on each order for exact profit.")
    return 0


def cmd_alerts(a, st):
    if a.sub in ("ack", "close"):
        print(f"{st.update('alerts', {'id': int(a.id)}, {'status': 'acknowledged' if a.sub == 'ack' else 'closed'})} alert(s) updated.")
    else:
        al = [x for x in st.select("alerts") if x["status"] != "closed"]
        for x in sorted(al, key=lambda x: x.get("id", 0)):
            print(f"#{x.get('id')} [{x['status']}] {x['severity'].upper()} {x['message']}")
        print(f"{len(al)} alert(s) open or acknowledged." if al else "No alerts.")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--local", action="store_true", help="use local files even if Supabase keys are set")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("scan")
    p.add_argument("--alert-file"), p.add_argument("--today"), p.add_argument("--require-supabase", action="store_true")
    sub.add_parser("status")
    p = sub.add_parser("pnl")
    p.add_argument("--days", type=int, default=14)
    p = sub.add_parser("order").add_subparsers(dest="sub", required=True)
    q = p.add_parser("add")
    q.add_argument("--id", required=True), q.add_argument("--date"), q.add_argument("--channel", default="ebay-uk"), q.add_argument("--product"), q.add_argument("--title", default="")
    q.add_argument("--qty", type=int, default=1), q.add_argument("--revenue", type=float, default=0), q.add_argument("--cost", type=float, default=0), q.add_argument("--shipping", type=float, default=0)
    q.add_argument("--fees", type=float, default=0), q.add_argument("--refund", type=float, default=0), q.add_argument("--status", default="new")
    p.add_parser("import").add_argument("file")
    q = p.add_parser("update")
    q.add_argument("id"), q.add_argument("--status"), q.add_argument("--refund", type=float)
    p.add_parser("list")
    p = sub.add_parser("ship").add_subparsers(dest="sub", required=True)
    q = p.add_parser("add")
    q.add_argument("--order", required=True), q.add_argument("--carrier", default=""), q.add_argument("--tracking", default=""), q.add_argument("--shipped"), q.add_argument("--promised-days", type=int)
    q.add_argument("--supplier", default="")
    p.add_parser("import").add_argument("file")
    q = p.add_parser("update")
    q.add_argument("id"), q.add_argument("--status", choices=["pending", "in_transit", "out_for_delivery", "delivered", "exception", "returned"]), q.add_argument("--event")
    p.add_parser("list")
    p = sub.add_parser("listing").add_subparsers(dest="sub", required=True)
    q = p.add_parser("add")
    q.add_argument("--product", required=True), q.add_argument("--title", default=""), q.add_argument("--channel", default="ebay-uk"), q.add_argument("--price", type=float, required=True)
    q.add_argument("--cost", type=float, required=True), q.add_argument("--shipping", type=float, default=0), q.add_argument("--model", default="hold_stock"), q.add_argument("--postage", type=float, default=0)
    p.add_parser("import").add_argument("file")
    p.add_parser("list")
    sub.add_parser("price").add_subparsers(dest="sub", required=True).add_parser("import").add_argument("file")
    sub.add_parser("metrics").add_subparsers(dest="sub", required=True).add_parser("import").add_argument("file")
    sub.add_parser("shop").add_subparsers(dest="sub", required=True).add_parser("import").add_argument("file")
    p = sub.add_parser("spend").add_subparsers(dest="sub", required=True).add_parser("add")
    p.add_argument("--date", required=True), p.add_argument("--platform", required=True), p.add_argument("--amount", type=float, required=True)
    p = sub.add_parser("alerts")
    p.add_argument("sub", nargs="?", default="list", choices=["list", "ack", "close"]), p.add_argument("id", nargs="?")
    a = ap.parse_args()
    if a.cmd == "scan" and a.require_supabase and not (os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_SECRET_KEY")):
        print("NOT RUN: add SUPABASE_URL and SUPABASE_SECRET_KEY as repository secrets (Settings, Secrets and variables, Actions). The daily watch needs your private database.")
        return 1
    try:
        st = open_store(a.local)
        if a.cmd == "scan":
            return cmd_scan(a, st)
        if a.cmd == "status":
            s = summary(st)
            print(f"Data: {st.describe()}. Open alerts: {len([x for x in s['alerts'] if x['status'] == 'open'])}. Parcels: {len(s['shipments'])} ({sum(1 for x in s['shipments'] if x['days_late'])} late). Listings: {len(s['listings'])} ({sum(1 for x in s['listings'] if not x['ok'])} below minimum margin).")
            return 0
        if a.cmd == "pnl":
            return cmd_pnl(a, st)
        if a.cmd == "metrics":
            print(f"{import_metrics(st, a.file)} metric row(s) imported.")
            return 0
        if a.cmd == "shop":
            print(f"{import_shop(st, a.file)} day(s) of shop figures imported.")
            return 0
        if a.cmd == "spend":
            st.insert("ad_spend_ledger", {"platform": a.platform, "spend_date": a.date, "amount_gbp": a.amount, "source": "manual"})
            print("Ad spend recorded.")
            return 0
        return {"order": cmd_order, "ship": cmd_ship, "listing": cmd_listing, "price": cmd_price, "alerts": cmd_alerts}[a.cmd](a, st)
    except (ValueError, StoreError) as exc:
        print(f"Refused: {exc}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
