#!/usr/bin/env python3
"""Run one agent. Free mode (manual) prepares a prompt for you to paste into Claude or Gemini.
API mode calls the provider, but only if budgets, rates and keys are set. Output is always a proposal.
Usage: python scripts/run_agent.py --agent listings --task "Draft a listing for SKU-001"
"""
import argparse
import datetime
import json
import os
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_budget import ROOT, load_yaml, month_totals  # noqa: E402
from pii_guard import find_pii  # noqa: E402


def read(rel):
    p = ROOT / rel
    return p.read_text() if p.exists() else ""


def post_json(url, headers, body):
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(),
        headers={**headers, "content-type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as exc:
        sys.exit(f"API error {exc.code}: {exc.read().decode()[:500]}")


def call_api(model_cfg, key, prompt):
    if model_cfg["provider"] == "anthropic":
        d = post_json("https://api.anthropic.com/v1/messages",
                      {"x-api-key": key, "anthropic-version": "2023-06-01"},
                      {"model": model_cfg["model"], "max_tokens": model_cfg.get("max_tokens", 1500),
                       "messages": [{"role": "user", "content": prompt}]})
        text = "".join(b.get("text", "") for b in d["content"])
        return text, d["usage"]["input_tokens"], d["usage"]["output_tokens"]
    d = post_json(f"https://generativelanguage.googleapis.com/v1beta/models/{model_cfg['model']}:generateContent",
                  {"x-goog-api-key": key},
                  {"contents": [{"parts": [{"text": prompt}]}],
                   "generationConfig": {"maxOutputTokens": model_cfg.get("max_tokens", 1500)}})
    text = "".join(p.get("text", "") for p in d["candidates"][0]["content"]["parts"])
    u = d.get("usageMetadata", {})
    return text, u.get("promptTokenCount", 0), u.get("candidatesTokenCount", 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", required=True)
    ap.add_argument("--task", required=True)
    ap.add_argument("--input-file")
    ap.add_argument("--skip-pii-check", action="store_true", help="manual mode only")
    a = ap.parse_args()

    status = load_yaml("governance/status.yml")
    if status.get("paused"):
        print("PAUSED: governance/status.yml has paused: true. Nothing was run.")
        return 0
    cfg = (status.get("agents") or {}).get(a.agent)
    if cfg is None or not (ROOT / "agents" / a.agent).exists():
        print(f"Unknown agent: {a.agent}")
        return 2
    if not cfg.get("enabled"):
        print(f"Agent {a.agent} is disabled in governance/status.yml")
        return 0

    extra = ""
    if a.input_file:
        extra = (ROOT / a.input_file).read_text() if (ROOT / a.input_file).exists() else open(a.input_file).read()
    mode = cfg.get("provider", status.get("provider", "manual"))
    pii = find_pii(a.task + "\n" + extra)
    if pii and not (a.skip_pii_check and mode == "manual"):
        print("Refused: the task looks like it contains personal data (" + ", ".join(pii) + "). Use order IDs instead.")
        return 3

    dry = cfg.get("dry_run", status.get("default_dry_run", True))
    prompt = "\n\n".join(x for x in [
        read("agents/_shared/company-rules.md"), read(f"agents/{a.agent}/prompt.md"),
        read("agents/_shared/output-schema.md"), "## Task\n" + a.task,
        ("## Extra input\n" + extra) if extra else ""] if x.strip())

    routing = load_yaml("models/routing.yml")
    pref = routing["agents"].get(a.agent, {}).get("preferred", "claude")
    model_cfg = routing["models"][pref]
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S")
    name = f"{stamp}-{a.agent}.md"
    banner = f"DRY RUN: proposal only. Live actions are not implemented. Dry-run flag: {dry}\n"

    if mode == "manual":
        out = ROOT / "outbox" / name
        out.write_text(
            f"# Prepared prompt for {a.agent}\n{banner}\n"
            f"Paste everything below the line into {pref.title()} ({model_cfg['paste_into']}).\n"
            f"Save the reply as inbox/{name}\n\n---\n\n{prompt}\n")
        print(f"Prompt written to {out.relative_to(ROOT)}")
        return 0

    costs = load_yaml("models/costs.yml")[pref]
    free = bool(costs.get("free_tier"))
    rin, rout = costs.get("input_per_mtok_gbp", 0), costs.get("output_per_mtok_gbp", 0)
    if not free and not (rin or rout):
        print(f"Refused: fill in the rates for {pref} in models/costs.yml first.")
        return 4
    caps = load_yaml("governance/budgets.yml")["ai_costs"]
    total, per_agent = month_totals()
    if not free and (total >= caps["total_monthly_cap"]
                     or per_agent.get(a.agent, 0) >= caps["per_agent_monthly_cap"].get(a.agent, 0)):
        print("Refused: AI budget cap reached (or still 0) in governance/budgets.yml.")
        return 5
    key_name = "ANTHROPIC_API_KEY" if model_cfg["provider"] == "anthropic" else "GEMINI_API_KEY"
    key = os.environ.get(key_name)
    if not key:
        print(f"Refused: {key_name} is not set.")
        return 6

    text, tin, tout = call_api(model_cfg, key, prompt)
    cost = 0.0 if free else tin / 1e6 * rin + tout / 1e6 * rout
    with (ROOT / "logs" / "costs.csv").open("a") as f:
        f.write(f"{datetime.date.today()},{a.agent},{model_cfg['provider']},{model_cfg['model']},{tin},{tout},{cost:.4f},\n")
    out = ROOT / "logs" / "actions" / name
    out.write_text(f"# Proposal from {a.agent} ({model_cfg['model']})\n{banner}\n{text}\n")
    print(f"Proposal written to {out.relative_to(ROOT)} (cost {cost:.4f} GBP)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
