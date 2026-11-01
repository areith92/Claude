#!/usr/bin/env python3
"""Basic scan of tracked files for things that look like API keys."""
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PATTERNS = [
    re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}"),
    re.compile(r"AIza[0-9A-Za-z_-]{35}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}"),
    re.compile(r"shpat_[0-9a-f]{20,}"),
    re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"][A-Za-z0-9_\-/+=]{20,}['\"]"),
]
SKIP = {"scripts/check_secrets.py", ".env.example"}

files = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True).stdout.split()
hits = []
for rel in files:
    if rel in SKIP:
        continue
    try:
        text = (ROOT / rel).read_text(errors="ignore")
    except Exception:
        continue
    for rx in PATTERNS:
        if rx.search(text):
            hits.append(rel)
            break
for h in hits:
    print("POSSIBLE SECRET in", h)
print("No secrets found" if not hits else f"{len(hits)} file(s) flagged")
sys.exit(1 if hits else 0)
