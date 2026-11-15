import datetime
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import pacing  # noqa: E402


class Pacing(unittest.TestCase):
    def test_allowance_grows_through_the_month(self):
        self.assertAlmostEqual(pacing.allowance(5, datetime.date(2026, 11, 15)), 5 * 15 / 30)
        self.assertAlmostEqual(pacing.allowance(5, datetime.date(2026, 11, 30)), 5.0)

    def test_spend_ahead_of_pace_is_flagged(self):
        original = pacing.month_totals
        pacing.month_totals = lambda month=None: (4.0, {})
        try:
            on_pace, spent, allowed = pacing.check(datetime.date(2026, 11, 3))
        finally:
            pacing.month_totals = original
        self.assertFalse(on_pace)

    def test_spend_on_pace_is_allowed(self):
        original = pacing.month_totals
        pacing.month_totals = lambda month=None: (0.1, {})
        try:
            on_pace, _, _ = pacing.check(datetime.date(2026, 11, 15))
        finally:
            pacing.month_totals = original
        self.assertTrue(on_pace)


if __name__ == "__main__":
    unittest.main()
