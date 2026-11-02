#!/usr/bin/env python3
"""Profit and margin for one product, calculated by code (never by an AI). Fees come from catalogue/fees.yml.
Usage: python scripts/margin.py --channel ebay-uk --price 24.99 --cost 6.5 --shipping 1.2 [--postage 2.85]"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_budget import load_yaml  # noqa: E402


def _n(x, default=0.0):
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def compute(d, fees, cost_uplift_pct=0.0):
    """d needs: channel, sale_price_gbp, supplier_cost_gbp, supplier_shipping_gbp, fulfilment_model; optional postage_gbp."""
    ch = (fees.get("channels") or {}).get(d["channel"]) or {}
    com = fees.get("common") or {}
    price = _n(d["sale_price_gbp"])
    uplift = 1 + cost_uplift_pct / 100
    cost = _n(d["supplier_cost_gbp"]) * uplift
    shipping = _n(d["supplier_shipping_gbp"])
    duty = cost * _n(com.get("import_duty_pct")) / 100
    held = d.get("fulfilment_model") == "hold_stock"
    postage = _n(d.get("postage_gbp")) if held else 0.0
    packaging = _n(com.get("packaging_gbp")) if held else 0.0
    if d["channel"] == "ebay-uk":
        fees_gbp = price * (_n(ch.get("final_value_fee_pct")) + _n(ch.get("promoted_listing_pct"))) / 100 + _n(ch.get("fixed_fee_gbp"))
    else:
        fees_gbp = price * (_n(ch.get("platform_commission_pct")) + _n(ch.get("payment_fee_pct"))) / 100 + _n(ch.get("payment_fixed_gbp"))
    returns = price * _n(com.get("returns_allowance_pct")) / 100
    net_price = price / (1 + _n(com.get("vat_rate_pct"), 20) / 100) if com.get("vat_registered") else price
    total = cost + shipping + duty + postage + packaging + fees_gbp + returns
    profit = net_price - total
    margin = profit / net_price * 100 if net_price > 0 else -100.0
    return {"sale_price_gbp": round(price, 2), "net_price_gbp": round(net_price, 2), "cost_gbp": round(cost, 2),
            "shipping_gbp": round(shipping, 2), "duty_gbp": round(duty, 2), "postage_gbp": round(postage, 2),
            "packaging_gbp": round(packaging, 2), "channel_fees_gbp": round(fees_gbp, 2), "returns_allowance_gbp": round(returns, 2),
            "total_cost_gbp": round(total, 2), "profit_gbp": round(profit, 2), "margin_pct": round(margin, 1),
            "fees_confirmed": bool(ch.get("confirmed"))}


def with_stress(d, fees, stress_pct):
    base = compute(d, fees)
    base["stress_margin_pct"] = compute(d, fees, stress_pct)["margin_pct"]
    base["stress_cost_increase_pct"] = stress_pct
    return base


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--channel", default="ebay-uk")
    ap.add_argument("--price", type=float, required=True)
    ap.add_argument("--cost", type=float, required=True)
    ap.add_argument("--shipping", type=float, default=0)
    ap.add_argument("--postage", type=float, default=0)
    ap.add_argument("--model", default="hold_stock")
    a = ap.parse_args()
    cfg = load_yaml("catalogue/research.yml")
    r = with_stress({"channel": a.channel, "sale_price_gbp": a.price, "supplier_cost_gbp": a.cost, "supplier_shipping_gbp": a.shipping,
                     "postage_gbp": a.postage, "fulfilment_model": a.model}, load_yaml("catalogue/fees.yml"), cfg["stress_cost_increase_pct"])
    for k, v in r.items():
        print(f"{k}: {v}")
    print("PASS" if r["margin_pct"] >= cfg["min_margin_pct"] else f"REJECT: below {cfg['min_margin_pct']} percent")
    if not r["fees_confirmed"]:
        print("NOTE: the fee figures in catalogue/fees.yml are placeholders. Confirm them from your fee statement.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
