"""Simple check that blocks obvious personal data from going into prompts."""
import re

PATTERNS = {
    "email address": re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),
    "UK phone number": re.compile(r"(?<!\d)(?:\+44\s?|0)\d{3,4}[\s-]?\d{3}[\s-]?\d{3,4}(?!\d)"),
    "UK postcode": re.compile(r"\b[A-Za-z]{1,2}\d[A-Za-z\d]?\s*\d[A-Za-z]{2}\b"),
}


def find_pii(text):
    return [name for name, rx in PATTERNS.items() if rx.search(text)]
