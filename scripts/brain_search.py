#!/usr/bin/env python3
"""Searches memory/brain/ (the GBrain folder of markdown notes). run_agent.py uses it so every agent gets its own SOP
and up to two related notes in its prompt. Usage: python scripts/brain_search.py "question" [--agent listings]"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import yaml  # noqa: E402
from check_budget import ROOT  # noqa: E402

BRAIN = "memory/brain"
STOP = set("the and for with that this from are was were has have had not but you your our can will into about what when how why who".split())


def words(text):
    return [w for w in re.findall(r"[a-z0-9]{4,}", text.lower()) if w not in STOP]


def split_note(text):
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not m:
        return {}, text
    try:
        return (yaml.safe_load(m.group(1)) or {}), m.group(2)
    except yaml.YAMLError:
        return {}, text


def notes(root=ROOT):
    out = []
    base = root / BRAIN
    for p in sorted(base.rglob("*.md")) if base.exists() else []:
        rel = p.relative_to(root).as_posix()
        meta, body = split_note(p.read_text())
        out.append({"path": rel, "meta": meta, "body": body, "title": str(meta.get("title") or p.stem),
                    "tags": [str(t) for t in (meta.get("tags") or [])]})
    return out


def search(query, root=ROOT, limit=2, skip_sops=True):
    q = set(words(query))
    scored = []
    for n in notes(root):
        if n["path"].endswith("README.md") or (skip_sops and "/sops/" in n["path"]):
            continue
        body = words(n["body"])
        score = 3 * len(q & set(words(n["title"]))) + 2 * len(q & set(words(" ".join(n["tags"])))) + min(5, sum(1 for w in body if w in q))
        if score >= 3:
            scored.append((score, n))
    scored.sort(key=lambda s: (-s[0], s[1]["path"]))
    return [n for _, n in scored[:limit]]


def sop_text(agent, root=ROOT):
    p = root / BRAIN / "sops" / f"{agent}.md"
    return split_note(p.read_text())[1].strip() if p.exists() else None


def can_read_brain(agent, root=ROOT):
    p = root / "agents" / agent / "permissions.yml"
    try:
        perms = yaml.safe_load(p.read_text()) or {}
    except (OSError, yaml.YAMLError):
        return False
    return any(str(x).rstrip("/") in (BRAIN, "memory") for x in (perms.get("can_read") or []))


def brain_context(agent, text, root=ROOT):
    """The block run_agent.py adds to every prompt: the agent's SOP and related notes."""
    if not can_read_brain(agent, root):
        return f"## Standing procedure (SOP)\nNot loaded: agents/{agent}/permissions.yml does not allow reading {BRAIN}/."
    sop = sop_text(agent, root)
    parts = [f"## Your standing procedure (SOP), from {BRAIN}/sops/{agent}.md\n" + sop[:6000]] if sop else \
            [f"## Standing procedure (SOP)\nNo SOP found at {BRAIN}/sops/{agent}.md. Say so and ask the owner to add one."]
    found = search(text, root)
    if found:
        parts.append(f"## Related notes from {BRAIN}/ (found by keyword search)\n" + "\n\n".join(
            f"### {n['path']}\n{n['body'].strip()[:900]}" for n in found))
    return "\n\n".join(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("--agent")
    a = ap.parse_args()
    if a.agent:
        print(brain_context(a.agent, a.query))
        return 0
    hits = search(a.query, limit=5, skip_sops=False)
    for n in hits:
        print(f"{n['path']}  ({n['title']})")
    if not hits:
        print("Nothing found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
