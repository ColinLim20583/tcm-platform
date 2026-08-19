"""
product_catalog.py — finished Chemigran products for ChemSync™ step 4.

Reads products.csv. If that file is empty or absent, ChemSync simply always
generates a bespoke blend instead of matching — the flow still works, it just
never returns a stocked SKU. Nothing here invents products.

products.csv columns
--------------------
sku              Your internal product code
name_en          Consumer-facing English name
name_zh          Chinese name (optional)
price_sgd        Retail price, numbers only
pack_size        e.g. "30 sachets" / "60 capsules"
indications      Pipe-separated, using the same vocabulary as herbs.csv
                 indications, e.g. "poor sleep|anxiety|Shen disturbance"
tcm_patterns     Pipe-separated patterns this product addresses
key_ingredients  Pipe-separated Chinese herb names, matching herbs.csv
contraindications Free text
description      One or two sentences for the product card
image_url        Optional
"""

import csv
from functools import lru_cache
from pathlib import Path

CSV_PATH = Path(__file__).parent / "products.csv"

FIELDS = [
    "sku", "name_en", "name_zh", "price_sgd", "pack_size",
    "indications", "tcm_patterns", "key_ingredients",
    "contraindications", "description", "image_url",
]

# A product must clear this share of the user's indications to be offered.
# Below it, a bespoke blend is the more honest answer than a loose match.
MIN_MATCH = 0.34


@lru_cache(maxsize=1)
def load_products() -> list:
    if not CSV_PATH.exists():
        return []
    out = []
    with CSV_PATH.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            if not (row.get("sku") or "").strip():
                continue
            row["indications"] = [i.strip() for i in (row.get("indications") or "").split("|") if i.strip()]
            row["tcm_patterns"] = [i.strip() for i in (row.get("tcm_patterns") or "").split("|") if i.strip()]
            row["key_ingredients"] = [i.strip() for i in (row.get("key_ingredients") or "").split("|") if i.strip()]
            out.append(row)
    return out


def catalogue_status() -> dict:
    products = load_products()
    return {
        "available": bool(products),
        "count": len(products),
        "path": str(CSV_PATH),
    }


def _norm(s: str) -> set:
    stop = {"the", "and", "of", "a", "to", "in", "with", "patterns", "pattern"}
    return {
        w for w in "".join(c if c.isalnum() or c.isspace() else " " for c in s.lower()).split()
        if w and w not in stop and len(w) > 2
    }


def match_products(user_indications: list, tcm_pattern: str = "", top_n: int = 3) -> list:
    """
    Score catalogue products against what the scan found.

    Returns products above MIN_MATCH, best first, each with 'match_score' and
    'matched_on' so the UI can show WHY something was recommended rather than
    presenting an opaque suggestion.
    """
    products = load_products()
    if not products:
        return []

    want = set()
    for ind in user_indications:
        want |= _norm(ind)
    pattern_words = _norm(tcm_pattern)

    scored = []
    for p in products:
        have = set()
        for ind in p["indications"]:
            have |= _norm(ind)

        overlap = want & have
        score = len(overlap) / len(want) if want else 0.0

        # A direct pattern hit is worth more than loose indication overlap
        matched_patterns = [
            tp for tp in p["tcm_patterns"] if pattern_words & _norm(tp)
        ]
        if matched_patterns:
            score = min(1.0, score + 0.25)

        if score >= MIN_MATCH:
            q = dict(p)
            q["match_score"] = round(score, 2)
            q["matched_on"] = sorted(overlap)
            q["matched_patterns"] = matched_patterns
            scored.append(q)

    scored.sort(key=lambda x: -x["match_score"])
    return scored[:top_n]


def ensure_template():
    """Create an empty products.csv with the right header if none exists."""
    if CSV_PATH.exists():
        return False
    with CSV_PATH.open("w", newline="", encoding="utf-8-sig") as f:
        csv.DictWriter(f, fieldnames=FIELDS).writeheader()
    return True
