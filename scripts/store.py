#!/usr/bin/env python3
"""Where operations data lives. Two places, same functions:
  local    JSON files in operations/data/ (never committed, see .gitignore). Used when no Supabase keys are set, and in tests.
  supabase your private database (SUPABASE_URL and SUPABASE_SECRET_KEY). Used automatically when both are set.
Set OPS_STORE=local to force local files. The secret key is only ever sent to your own Supabase project and is never printed."""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_budget import ROOT  # noqa: E402

DATA = ROOT / "operations" / "data"
AUTO_ID = {"alerts", "supplier_prices", "social_metrics", "ad_spend_ledger"}
GENERATED = {"shipments": {"expected_by"}}   # worked out by the database; never sent


class StoreError(Exception):
    pass


class Local:
    kind = "local"

    def describe(self):
        return "local files in operations/data (not committed)"

    def _path(self, t):
        return DATA / f"{t}.json"

    def _load(self, t):
        p = self._path(t)
        return json.loads(p.read_text()) if p.exists() else []

    def _save(self, t, rows):
        DATA.mkdir(parents=True, exist_ok=True)
        self._path(t).write_text(json.dumps(rows, indent=1, default=str) + "\n")

    def select(self, t, where=None):
        return [dict(r) for r in self._load(t) if all(r.get(k) == v for k, v in (where or {}).items())]

    def insert(self, t, row):
        rows, row = self._load(t), {k: v for k, v in row.items() if k not in GENERATED.get(t, ())}
        if t in AUTO_ID and "id" not in row:
            row["id"] = max([r.get("id", 0) for r in rows] + [0]) + 1
        rows.append(row)
        self._save(t, rows)
        return row

    def update(self, t, where, values):
        rows, n = self._load(t), 0
        for r in rows:
            if all(r.get(k) == v for k, v in where.items()):
                r.update({k: v for k, v in values.items() if k not in GENERATED.get(t, ())})
                n += 1
        self._save(t, rows)
        return n


class Supabase:
    kind = "supabase"

    def __init__(self, url, key):
        p = urllib.parse.urlsplit(url.strip())
        self.base, self.key = f"{p.scheme}://{p.netloc}", key.strip()

    def describe(self):
        return "your private Supabase database"

    def _req(self, method, path, body=None, prefer=None, extra=None):
        h = {"apikey": self.key, "Accept": "application/json", "Content-Type": "application/json"}
        if self.key.startswith("eyJ"):
            h["Authorization"] = "Bearer " + self.key
        if prefer:
            h["Prefer"] = prefer
        h.update(extra or {})
        req = urllib.request.Request(self.base + path, data=json.dumps(body, default=str).encode() if body is not None else None, headers=h, method=method)
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                raw = r.read()
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as e:
            try:
                msg = json.loads(e.read() or b"{}").get("message", "")
            except ValueError:
                msg = ""
            raise StoreError(f"Supabase said HTTP {e.code} for {method} {path.split('?')[0]}: {msg[:200]}")
        except (urllib.error.URLError, OSError) as e:
            raise StoreError(f"Could not reach Supabase: {e}")

    @staticmethod
    def _filters(where):
        return "".join(f"&{k}=eq.{urllib.parse.quote(str(v), safe='')}" for k, v in (where or {}).items())

    def select(self, t, where=None):
        out, start = [], 0
        while True:
            page = self._req("GET", f"/rest/v1/{t}?select=*{self._filters(where)}", extra={"Range-Unit": "items", "Range": f"{start}-{start + 999}"}) or []
            out += page
            if len(page) < 1000:
                return out
            start += 1000

    def insert(self, t, row):
        row = {k: v for k, v in row.items() if k not in GENERATED.get(t, ())}
        res = self._req("POST", f"/rest/v1/{t}", [row], prefer="return=representation")
        return res[0] if res else row

    def update(self, t, where, values):
        values = {k: v for k, v in values.items() if k not in GENERATED.get(t, ())}
        res = self._req("PATCH", f"/rest/v1/{t}?{self._filters(where).lstrip('&')}", values, prefer="return=representation")
        return len(res or [])


def open_store(force_local=False):
    url, key = os.environ.get("SUPABASE_URL", ""), os.environ.get("SUPABASE_SECRET_KEY", "")
    if not force_local and os.environ.get("OPS_STORE") != "local" and url and key:
        return Supabase(url, key)
    return Local()


def put(st, table, row, keys):
    """Insert the row, or update it if a row with the same key columns already exists."""
    where = {k: row[k] for k in keys}
    if st.select(table, where):
        st.update(table, where, {k: v for k, v in row.items() if k not in keys})
    else:
        st.insert(table, row)
    return row
