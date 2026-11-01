"""Spend-cap logic shared by run_agent.py, build_dashboard.py, orchestrate.py and the tests (GBP, estimates)."""
import datetime
import json


def worst_case_cost(prompt_chars, max_tokens, rate_in, rate_out):
    """Upper estimate for one call: about 4 characters per token in, the full max_tokens out."""
    return (prompt_chars / 4) / 1e6 * rate_in + max_tokens / 1e6 * rate_out


def would_exceed(total, agent_spent, worst, total_cap, agent_cap):
    """Returns 'total', 'agent' or None. A cap of 0 always blocks."""
    if total + worst > total_cap:
        return "total"
    if agent_spent + worst > agent_cap:
        return "agent"
    return None


def spend_state(spent, cap, alert_pct=80, stop_marker=False):
    """off = paid API not enabled (cap 0), ok, warning, or stopped."""
    if cap <= 0:
        return "off"
    if spent >= cap or stop_marker:
        return "stopped"
    return "warning" if spent / cap * 100 >= alert_pct else "ok"


def _marker_path(root):
    return root / "logs" / "budget-stop.json"


def write_stop_marker(root, agent, scope, spent, cap):
    today = datetime.date.today()
    _marker_path(root).write_text(json.dumps(
        {"month": today.strftime("%Y-%m"), "date": str(today), "agent": agent, "scope": scope,
         "spent_gbp": round(spent, 4), "cap_gbp": cap}, indent=2) + "\n")


def read_stop_marker(root):
    """The most recent cap stop, but only if it happened this month (caps reset monthly)."""
    try:
        d = json.loads(_marker_path(root).read_text())
    except (OSError, ValueError):
        return None
    return d if d.get("month") == datetime.date.today().strftime("%Y-%m") else None
