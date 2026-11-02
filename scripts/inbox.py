#!/usr/bin/env python3
"""Incoming customer messages and comments from every platform: remove personal data, sort them, and prepare a reply.
Nothing is ever sent from here. Every reply is a draft that waits for you, unless governance/inbox.yml lists its category as auto-send
AND its template has every fact filled in AND a platform connection exists (none does yet).
  python3 scripts/inbox.py add --platform facebook --kind dm|comment --text "..." [--order-id O-1001]
  python3 scripts/inbox.py import FILE.csv         columns: platform,kind,text,order_id
  python3 scripts/inbox.py list                    what is waiting
  python3 scripts/inbox.py approve|deny|sent ID    the decision on a draft (sent = you sent it by hand)
  python3 scripts/inbox.py prompt ID               prepare a prompt for the platform agent when no template fits
"""
import argparse
import csv
import datetime as dt
import os
import re
import subprocess
import sys
import tempfile
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import yaml  # noqa: E402
import watch  # noqa: E402
from check_budget import ROOT, load_yaml  # noqa: E402
from store import StoreError, open_store  # noqa: E402

PATTERNS = [("EMAIL", r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), ("LINK", r"https?://\S+|www\.\S+"), ("CARD", r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)"),
            ("PHONE", r"(?<!\d)(?:\+44\s?\(?0?\)?|0)\s?\d{2,4}[\s-]?\d{3,4}[\s-]?\d{3,4}(?!\d)"), ("POSTCODE", r"\b[A-Za-z]{1,2}\d[A-Za-z\d]?\s?\d[A-Za-z]{2}\b"),
            ("HANDLE", r"(?<!\w)@[A-Za-z0-9_.]{2,}")]
AGENT_FOR = {"facebook": "facebook", "instagram": "instagram", "tiktok": "tiktok", "pinterest": "pinterest"}


def redact(text):
    """Returns (clean_text, number_of_removals). Names are NOT detected: the text is only stored in your private data store."""
    n = 0
    for label, rx in PATTERNS:
        text, k = re.subn(rx, f"[{label}]", text)
        n += k
    return text, n


def settings():
    return load_yaml("governance/inbox.yml"), load_yaml("catalogue/support/rules.yml"), load_yaml("catalogue/support/templates.yml")["templates"], load_yaml("catalogue/support/facts.yml")


def triage(text, kind="dm"):
    inbox_cfg, rules, templates, facts = settings()
    low = " " + re.sub(r"\s+", " ", text.lower()) + " "
    scores = {c: sum(1 for kw in kws if kw in low) for c, kws in rules["categories"].items()}
    category = next((c for c in rules["order"] if scores.get(c)), "other")
    flags = [c for c in inbox_cfg["escalate_categories"] if scores.get(c)]
    out = {"category": category, "flags": flags, "template_id": None, "missing_facts": [], "reply": "", "tier": "draft", "reason": ""}
    if flags:
        out.update(category=flags[0], tier="escalate", reason=f"{flags[0]} words found: this needs you, not a template")
        return out
    if category == "spam":
        out.update(tier="ignore", reason="looks like spam: do not reply; hide or report it in the platform")
        return out
    pick = None
    for t in templates:
        cat = t["category"]
        match = category in rules["order_specific"] if cat == "order_specific" else category == cat
        if match and kind in t.get("for", ["dm", "comment"]):
            if cat == "order_specific" and kind != "comment":
                continue
            pick = t
            break
    if kind == "comment" and category in rules["order_specific"] and not pick:
        pick = next((t for t in templates if t["id"] == "public_move_to_dm"), None)
    if not pick:
        out["reason"] = "no template fits: ask the platform agent (python3 scripts/inbox.py prompt ID)"
        return out
    missing = [k for k in pick.get("needs", []) if facts.get(k) in (None, "")]
    reply = pick["reply"]
    for k, v in facts.items():
        reply = reply.replace("{{" + k + "}}", str(v) if v not in (None, "") else "{{" + k + "}}")
    out.update(template_id=pick["id"], missing_facts=missing, reply=reply)
    if missing:
        out["reason"] = "needs these facts filled in catalogue/support/facts.yml: " + ", ".join(missing)
    elif category in inbox_cfg["auto_send_categories"] and category not in inbox_cfg["never_auto"]:
        out.update(tier="ready", reply=reply + "\n\n" + inbox_cfg["disclosure"], reason="template complete and category allowed to auto-send once a platform connection exists")
    else:
        out["reason"] = "draft for your approval"
    return out


def add_message(st, platform, kind, text, order_id=None):
    clean, removed = redact(text)
    t = triage(clean, kind)
    cid, now = str(uuid.uuid4()), dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    channel = platform if platform in ("ebay", "facebook", "instagram", "tiktok", "whatsapp", "youtube", "x", "pinterest") else "other"
    st.insert("conversations", {"id": cid, "channel": channel, "public_comment": kind == "comment", "order_ref": order_id or None, "category": t["category"] if t["category"] in ("question", "delivery", "return", "damage", "dispute", "complaint", "other") else {
        "order_status": "delivery", "delivery_delay": "delivery", "return_refund": "return", "product_question": "question", "payment": "other", "price_discount": "question", "praise": "other", "safety": "complaint", "legal": "dispute", "abuse": "complaint", "spam": "other"}.get(t["category"], "other"),
        "status": "open", "escalated": t["tier"] == "escalate", "created_at": now, "last_message_at": now})
    mid = str(uuid.uuid4())
    st.insert("messages", {"id": mid, "conversation_id": cid, "direction": "in", "body_redacted": clean, "redactions": removed, "draft_status": None, "created_at": now,
                           "meta": {"platform": platform, "kind": kind, "category": t["category"], "tier": t["tier"], "flags": t["flags"]}})
    draft_id = None
    if t["tier"] in ("draft", "ready") and t["reply"]:
        draft_id = str(uuid.uuid4())
        st.insert("messages", {"id": draft_id, "conversation_id": cid, "direction": "draft_out", "body_redacted": t["reply"], "redactions": 0, "draft_status": "awaiting_approval", "created_at": now,
                               "meta": {"platform": platform, "kind": kind, "category": t["category"], "tier": t["tier"], "template_id": t["template_id"], "missing_facts": t["missing_facts"], "reason": t["reason"]}})
    if t["tier"] == "escalate":
        new = []
        watch.raise_alert(st, new, "message_escalation", "critical" if t["category"] in ("safety", "legal") else "warning", "conversation", cid[:8],
                          f"{platform} {kind} needs you now ({t['category']}): \"{clean[:140]}\"", f"msg:{cid}")
    return {"conversation": cid, "message": mid, "draft": draft_id, **t, "redactions": removed, "text": clean}


def summary(st):
    convs = {c["id"]: c for c in st.select("conversations")}
    msgs = st.select("messages")
    inbound = {m["conversation_id"]: m for m in msgs if m["direction"] == "in"}
    items = []
    for m in msgs:
        if m["direction"] == "draft_out" and m.get("draft_status") == "awaiting_approval":
            c, i = convs.get(m["conversation_id"], {}), inbound.get(m["conversation_id"], {})
            meta = m.get("meta") or {}
            items.append({"id": m["id"], "platform": (i.get("meta") or {}).get("platform", c.get("channel", "")), "kind": (i.get("meta") or {}).get("kind", ""), "category": meta.get("category", ""), "tier": meta.get("tier", ""),
                          "message": i.get("body_redacted", ""), "draft": m["body_redacted"], "missing_facts": meta.get("missing_facts", []), "reason": meta.get("reason", ""), "created_at": m.get("created_at", "")})
    drafted = {m["conversation_id"] for m in msgs if m["direction"] == "draft_out"}
    waiting = [{"id": m["id"], "platform": (m.get("meta") or {}).get("platform", ""), "kind": (m.get("meta") or {}).get("kind", ""), "category": (m.get("meta") or {}).get("category", ""), "tier": "draft", "message": m["body_redacted"],
                "draft": "", "missing_facts": [], "reason": "no template fits: run python3 scripts/inbox.py prompt " + m["id"], "created_at": m.get("created_at", "")}
               for m in msgs if m["direction"] == "in" and (m.get("meta") or {}).get("tier") == "draft" and m["conversation_id"] not in drafted and convs.get(m["conversation_id"], {}).get("status") == "open"]
    return {"open": sum(1 for c in convs.values() if c["status"] == "open"), "awaiting_approval": len(items), "needs_reply": len(waiting), "escalated": sum(1 for c in convs.values() if c.get("escalated") and c["status"] == "open"), "items": (items + waiting)[-20:]}


def decide(st, mid, status):
    rows = st.select("messages", {"id": mid})
    if not rows or rows[0]["direction"] != "draft_out":
        raise ValueError(f"No draft {mid}")
    st.update("messages", {"id": mid}, {"draft_status": status, "decided_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")})
    if status in ("sent_manually", "denied"):
        st.update("conversations", {"id": rows[0]["conversation_id"]}, {"status": "waiting" if status == "sent_manually" else "closed"})


def cmd_prompt(st, mid):
    rows = st.select("messages", {"id": mid})
    if not rows:
        raise ValueError(f"No message {mid}")
    m = rows[0]
    inbound = next((x for x in st.select("messages", {"conversation_id": m["conversation_id"]}) if x["direction"] == "in"), m)
    platform = (inbound.get("meta") or {}).get("platform", "")
    agent = AGENT_FOR.get(platform, "messages")
    facts = {k: v for k, v in load_yaml("catalogue/support/facts.yml").items() if v not in (None, "")}
    text = f"Platform: {platform}\nKind: {(inbound.get('meta') or {}).get('kind')}\nCustomer message (personal data removed):\n{inbound['body_redacted']}\n\nFacts you may use:\n{yaml.safe_dump(facts) if facts else '(none filled in yet: do not invent any)'}\n"
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
        f.write(text)
        p = f.name
    try:
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "run_agent.py"), "--agent", agent, "--task", "Draft a reply to this customer message. Use only the facts given. Follow your SOP. If a person is needed, say so.", "--input-file", p, "--manual"],
                           capture_output=True, text=True, cwd=ROOT)
    finally:
        os.unlink(p)
    print((r.stdout + r.stderr).strip())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--local", action="store_true")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("add")
    p.add_argument("--platform", required=True), p.add_argument("--kind", choices=["dm", "comment"], default="dm"), p.add_argument("--text", required=True), p.add_argument("--order-id")
    sub.add_parser("import").add_argument("file")
    sub.add_parser("list")
    for n in ("approve", "deny", "sent", "prompt"):
        sub.add_parser(n).add_argument("id")
    a = ap.parse_args()
    try:
        st = open_store(a.local)
        if a.cmd in ("add", "import"):
            rows = [{"platform": a.platform, "kind": a.kind, "text": a.text, "order_id": a.order_id}] if a.cmd == "add" else list(csv.DictReader(open(a.file, newline="")))
            for r in rows:
                res = add_message(st, r["platform"].strip().lower(), (r.get("kind") or "dm").strip(), r["text"], r.get("order_id") or None)
                print(f"{res['tier'].upper():9} {res['category']:15} {res['redactions']} removed. {res['reason']}")
                if res["draft"]:
                    print(f"  draft {res['draft']}: {res['reply'][:160]}")
        elif a.cmd == "list":
            s = summary(st)
            print(f"{s['awaiting_approval']} draft(s) waiting, {s['needs_reply']} with no template, {s['escalated']} escalated, {s['open']} open conversation(s).")
            for i in s["items"]:
                print(f"- {i['id']} [{i['platform']} {i['kind']}] {i['category']}: \"{i['message'][:80]}\"\n    " + (f"draft: {i['draft'][:120]}" if i["draft"] else i["reason"]) + (f"\n    needs facts: {', '.join(i['missing_facts'])}" if i["missing_facts"] else ""))
        elif a.cmd == "prompt":
            cmd_prompt(st, a.id)
        else:
            decide(st, a.id, {"approve": "approved", "deny": "denied", "sent": "sent_manually"}[a.cmd])
            print(f"Draft {a.id} marked {a.cmd}.")
    except (ValueError, StoreError, KeyError) as exc:
        print(f"Refused: {exc}")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
