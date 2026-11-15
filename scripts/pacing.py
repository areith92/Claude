"""AI spend pacing: spreads the monthly AI budget across the month so none of it is used up early.

Allowance so far = monthly cap x (day of month / days in month). If this month's spend is already
above that allowance, API calls are deferred until the next day. run_agent.py checks this in API mode.

Commands:
  python scripts/pacing.py status
"""
import calendar
import datetime
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from check_budget import load_yaml, month_totals  # noqa: E402


def allowance(cap, today=None):
    today = today or datetime.date.today()
    days = calendar.monthrange(today.year, today.month)[1]
    return float(cap) * today.day / days


def check(today=None):
    """Returns (on_pace, spent, allowed). on_pace is False when spend is ahead of the allowance."""
    today = today or datetime.date.today()
    cap = load_yaml("governance/budgets.yml")["ai_costs"]["total_monthly_cap"]
    spent, _ = month_totals(today.strftime("%Y-%m"))
    allowed = allowance(cap, today)
    return spent <= allowed, spent, allowed


def main(argv):
    on_pace, spent, allowed = check()
    state = "on pace" if on_pace else "AHEAD of pace: API calls are deferred until tomorrow"
    print(f"AI spend this month: {spent:.2f} GBP. Pacing allowance so far: {allowed:.2f} GBP. {state}.")
    return 0 if on_pace else 7


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
