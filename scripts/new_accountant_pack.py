#!/usr/bin/env python3
"""Creates reports/accountant-pack/YYYY-MM/ with a checklist for the month."""
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_budget import ROOT  # noqa: E402

month = datetime.date.today().strftime("%Y-%m")
d = ROOT / "reports" / "accountant-pack" / month
d.mkdir(parents=True, exist_ok=True)
(d / "CHECKLIST.md").write_text(
    f"# Accountant pack {month}\n- [ ] eBay payout and fee reports exported\n- [ ] Refunds listed\n"
    "- [ ] Postage and stock purchase receipts\n- [ ] Questions for the accountant (VAT, tax)\n"
    "- [ ] No customer personal data included\n")
print("Created", d.relative_to(ROOT))
