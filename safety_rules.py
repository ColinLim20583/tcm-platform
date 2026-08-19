"""
safety_rules.py — hard safety checks on a generated formulation.

Two layers:

1. Classical incompatibilities (十八反 / 十九畏). These are absolute pairings
   recorded in the Chinese Pharmacopoeia and taught as non-negotiable. They are
   checked deterministically after generation rather than left to the model —
   a language model that has just written a plausible formula is exactly the
   wrong thing to ask whether that formula is safe.

2. Structured flags extracted from each herb's contraindication text, so
   toxic / restricted / pregnancy-unsafe herbs can be surfaced or filtered
   before they reach the patient-facing output.

Only pairs where BOTH sides exist in the Chemigran catalogue are listed; the
rest are noise. Re-check this file if the inventory changes.
"""

from inventory_data import get_herb_by_chinese


# ── 十八反 / 十九畏 — restricted to pairs both stocked ────────────────────────

INCOMPATIBLE_GROUPS = [
    {
        "rule": "十八反 — 乌头反半夏、瓜蒌、贝母、白蔹、白及",
        "severity": "absolute",
        "note": "Classical absolute incompatibility. Aconite-type herbs must never "
                "be combined with this group.",
        "side_a": ["附片", "制川乌", "川乌", "草乌", "附子"],
        "side_b": ["半夏", "清半夏", "姜半夏", "法半夏",
                   "瓜蒌", "瓜蒌子", "瓜蒌皮",
                   "浙贝母", "川贝母", "土贝母", "平贝母",
                   "白蔹", "白及"],
    },
    {
        "rule": "十九畏 — 丁香畏郁金",
        "severity": "avoid",
        "note": "Traditionally antagonistic; combination is avoided in practice.",
        "side_a": ["丁香", "母丁香"],
        "side_b": ["郁金"],
    },
    {
        "rule": "十九畏 — 人参畏五灵脂",
        "severity": "avoid",
        "note": "Traditionally antagonistic; the pairing is held to negate the "
                "tonifying action.",
        "side_a": ["人参", "红参", "人参叶"],
        "side_b": ["五灵脂"],
    },
    {
        "rule": "十八反 — 甘草反甘遂、大戟、芫花、海藻",
        "severity": "absolute",
        "note": "Neither counterpart is currently stocked; retained so the rule "
                "still fires if the inventory expands.",
        "side_a": ["甘草", "炙甘草"],
        "side_b": ["甘遂", "大戟", "芫花", "海藻"],
    },
    {
        "rule": "十八反 — 藜芦反人参、沙参、丹参、玄参、细辛、芍药",
        "severity": "absolute",
        "note": "藜芦 is not stocked; retained in case it is added.",
        "side_a": ["藜芦"],
        "side_b": ["人参", "红参", "南沙参", "北沙参", "丹参",
                   "玄参", "细辛", "白芍", "赤芍"],
    },
]


def _base_of(name: str) -> str:
    """Resolve a name the model produced to its stocked base herb."""
    h = get_herb_by_chinese(name)
    return h["base_herb"] if h else (name or "").strip()


def check_incompatibilities(herb_names: list) -> list:
    """
    Return a list of violations found in a proposed formula.

    Each violation: {rule, severity, note, herbs}
    An empty list means no classical incompatibility was found.
    """
    bases = {}
    for n in herb_names:
        bases.setdefault(_base_of(n), []).append(n)

    violations = []
    for grp in INCOMPATIBLE_GROUPS:
        a = [orig for b in grp["side_a"] if b in bases for orig in bases[b]]
        b = [orig for x in grp["side_b"] if x in bases for orig in bases[x]]
        if a and b:
            violations.append({
                "rule": grp["rule"],
                "severity": grp["severity"],
                "note": grp["note"],
                "herbs": sorted(set(a + b)),
            })
    return violations


# ── Structured flags from contraindication text ──────────────────────────────

def herb_flags(herb: dict) -> list:
    """Machine-readable safety flags for a single herb record."""
    text = (herb.get("contraindications") or "")
    low = text.lower()
    flags = []
    if "toxic" in low:
        flags.append("TOXIC")
    if "restricted" in low or "hsa status" in low:
        flags.append("REGULATED")
    if "aristolochic" in low:
        flags.append("ARISTOLOCHIC_ACID")
    if "hepatotox" in low or "liver" in low and "monitor" in low:
        flags.append("HEPATOTOXIC_RISK")
    if "pregnan" in low:
        flags.append("PREGNANCY")
    if "incompatible" in low or "never combine" in low or "never with" in low:
        flags.append("INCOMPATIBILITY")
    if "dose limit" in low or "dose-limited" in low or "strict dose" in low:
        flags.append("DOSE_LIMITED")
    return flags


def summarise_formula_safety(herb_names: list) -> dict:
    """Everything the UI needs to decide whether to show or block a formula."""
    resolved, unknown = [], []
    for n in herb_names:
        h = get_herb_by_chinese(n)
        (resolved if h else unknown).append(h or n)

    flagged = {}
    for h in resolved:
        f = herb_flags(h)
        if f:
            flagged[h["chinese"]] = f

    violations = check_incompatibilities(herb_names)
    blocking = [v for v in violations if v["severity"] == "absolute"]

    return {
        "violations": violations,
        "blocking": blocking,
        "safe": not blocking,
        "flagged_herbs": flagged,
        "not_in_inventory": unknown,
        "derived_knowledge_count": sum(
            1 for h in resolved if h.get("data_source", "").startswith("derived")
        ),
    }
