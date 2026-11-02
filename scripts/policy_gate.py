#!/usr/bin/env python3
"""Runs a product dossier against the compliance rules for its channel and says pass, flag or block for each rule.
Usage: python scripts/policy_gate.py research/dossiers/P-....json"""
import datetime
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_budget import ROOT, load_yaml  # noqa: E402

RULE_FILES = {"ebay-uk": "governance/policies/ebay-uk-compliance.yml", "social": "governance/policies/social-selling-compliance.yml"}


def get(d, path, default=None):
    cur = d
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur


def keyword_hits(text, words):
    low = " " + re.sub(r"[^a-z0-9]+", " ", str(text).lower()) + " "
    return [w for w in words if " " + re.sub(r"[^a-z0-9]+", " ", w.lower()).strip() + " " in low]


def load_rules(channel):
    rel = RULE_FILES.get(channel)
    return (load_yaml(rel), rel) if rel else ({}, None)


def check(rule, d, cfg, today=None):
    c, kind = rule["check"], rule["check"]["type"]
    if kind == "field_not_in":
        bad = get(d, c["field"]) in c["values"]
        return not bad, f"{c['field']} is {get(d, c['field'])}" if bad else ""
    if kind == "keywords_absent":
        text = " ".join(str(get(d, f, "")) for f in c["fields"])
        hits = keyword_hits(text, cfg.get(c["list"]) or [])
        return not hits, "matched: " + ", ".join(hits) if hits else ""
    if kind == "field_true":
        return bool(get(d, c["field"])), f"{c['field']} is not confirmed yet"
    if kind == "field_true_if":
        if get(d, c["when_field"]) != c["when_value"]:
            return True, ""
        return bool(get(d, c["field"])), f"{c['field']} is not confirmed yet"
    if kind == "field_empty_or_true":
        if not get(d, c["empty_field"]):
            return True, ""
        return bool(get(d, c["field"])), f"brand '{get(d, c['empty_field'])}' has no proof you may sell it"
    if kind == "images_rights":
        bad = [i for i in (get(d, "market.images", []) or []) + (get(d, "supplier.images", []) or []) if i.get("rights") != "licensed"]
        return not bad, f"{len(bad)} image(s) have unverified rights: do not publish them" if bad else ""
    if kind == "fees_confirmed":
        return bool(get(d, "margin.fees_confirmed")), "fee figures are placeholders"
    if kind == "stress_margin_ok":
        s, m = get(d, "margin.stress_margin_pct"), cfg.get("min_margin_pct", 30)
        return (s is None or s >= m), f"margin would be {s} percent if costs rose {get(d, 'margin.stress_cost_increase_pct')} percent"
    if kind == "fresh":
        stamp = get(d, "data_date")
        if not stamp:
            return False, "no data date recorded"
        age = ((today or datetime.date.today()) - datetime.date.fromisoformat(stamp)).days
        return age <= cfg.get("research_freshness_days", 7), f"data is {age} days old"
    return False, f"unknown check type {kind}"


def evaluate(d, today=None):
    rules, rel = load_rules(d.get("channel"))
    cfg = load_yaml("catalogue/research.yml")
    results, stale = [], None
    if not rules:
        return {"overall": "block", "results": [{"id": "GATE-0", "title": "No rules for this channel", "status": "block", "detail": f"channel {d.get('channel')}"}], "stale": None}
    for r in rules.get("rules", []):
        ok, detail = check(r, d, cfg, today)
        results.append({"id": r["id"], "title": r["title"], "status": "pass" if ok else r["severity"], "detail": "" if ok else detail, "why": r.get("why", "")})
    try:
        age = ((today or datetime.date.today()) - datetime.date.fromisoformat(str(rules["reviewed"]))).days
        if age > rules.get("review_every_days", 90):
            stale = f"{rel} was last reviewed {age} days ago. Re-check it against the current policy pages."
    except (KeyError, ValueError):
        stale = f"{rel} has no valid reviewed date"
    states = {r["status"] for r in results}
    return {"overall": "block" if "block" in states else "flag" if "flag" in states else "pass", "results": results, "stale": stale,
            "rules_confirmed_by_owner": bool(rules.get("confirmed_by_owner"))}


def main():
    d = json.loads(open(sys.argv[1]).read())
    out = evaluate(d)
    for r in out["results"]:
        print(f"{r['status'].upper():5} {r['id']} {r['title']}" + (f" ({r['detail']})" if r["detail"] else ""))
    print("OVERALL:", out["overall"])
    if out["stale"]:
        print("WARNING:", out["stale"])
    return 0 if out["overall"] != "block" else 1


if __name__ == "__main__":
    sys.exit(main())
