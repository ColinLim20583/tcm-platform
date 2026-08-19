"""
inventory_data.py — Chemigran 551-Herb Granule Inventory

The inventory now lives in herbs.csv beside this file, one row per product, so a
ratio can be corrected in Excel without a code change or redeploy.

Manufacturing figures (net content, raw-herb equivalents, extract ratio) come
directly from the Chemigran product list and are authoritative.

Knowledge fields carry a data_source flag:
    curated            — hand-written, reviewed
    curated+processed  — curated base, processing modifier applied
    derived            — generated from standard references, NOT practitioner-reviewed

Contraindications on 'derived' rows in particular should be reviewed before
being relied upon clinically.
"""

import csv
from functools import lru_cache
from pathlib import Path

CSV_PATH = Path(__file__).parent / "herbs.csv"


@lru_cache(maxsize=1)
def _load() -> list:
    herbs = []
    with CSV_PATH.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            herbs.append({
                "id": int(row["id"]),
                "chinese": row["chinese"],
                "pinyin": row["pinyin"],
                "english": row["english"],
                "base_herb": row["base_herb"],
                "processing": row["processing"],
                "botanical_source": row["botanical_source"],
                "net_content_g": float(row["net_content_g"]),
                "extract_ratio": row["extract_ratio"],
                "raw_per_g": float(row["raw_per_g"]),
                "raw_per_bag": float(row["raw_per_bag"]),
                "categories": [c for c in row["categories"].split("|") if c],
                "tcm_functions": row["tcm_functions"],
                "contraindications": row["contraindications"],
                "data_source": row["data_source"],
            })
    if not herbs:
        raise RuntimeError(f"No herbs loaded from {CSV_PATH}")
    return herbs


HERBS = _load()


# ── Category keyword mapping ───────────────────────────────────────────────────

CONDITION_CATEGORY_MAP = {
    "sleep": ["sleep", "shen", "heart", "anxiety"],
    "insomnia": ["sleep", "shen", "heart", "anxiety", "liver_qi"],
    "stress": ["stress", "liver_qi", "shen", "anxiety", "qi_tonic"],
    "anxiety": ["anxiety", "shen", "heart", "sleep", "liver_qi"],
    "depression": ["depression", "liver_qi", "shen", "qi_tonic"],
    "fatigue": ["fatigue", "qi_tonic", "spleen", "yang_tonic", "blood_tonic"],
    "thyroid": ["thyroid", "nodule", "phlegm", "liver", "heat"],
    "nodule": ["nodule", "thyroid", "phlegm", "lymph"],
    "menopause": ["menopause", "women", "heat", "yin_tonic", "kidney", "sweating"],
    "women": ["women", "menstrual", "blood_tonic", "liver_qi"],
    "menstrual": ["menstrual", "women", "blood_stasis", "blood_tonic"],
    "aging": ["aging", "kidney", "yin_tonic", "yang_tonic", "qi_tonic", "blood_tonic"],
    "gut": ["gut", "spleen", "damp", "qi_stagnation"],
    "digestion": ["gut", "spleen", "damp", "phlegm"],
    "kidney": ["kidney", "yang_tonic", "yin_tonic", "jing"],
    "liver": ["liver", "liver_qi", "blood_stasis"],
    "blood": ["blood_tonic", "blood_stasis", "women"],
    "qi": ["qi_tonic", "spleen", "fatigue"],
    "phlegm": ["phlegm", "damp", "nodule", "thyroid"],
    "damp": ["damp", "spleen", "gut", "phlegm"],
    "heat": ["heat", "yin_tonic", "damp_heat", "blood_cooling"],
    "men": ["men", "yang_tonic", "kidney", "jing"],
    "immune": ["immune", "qi_tonic", "lung"],
    "head": ["head", "liver", "wind", "blood_pressure"],
    "brain": ["brain", "memory", "aging", "liver"],
    "memory": ["brain", "memory", "kidney", "heart"],
    "bone": ["bone", "yang_tonic", "kidney", "aging"],
    "joint": ["joint", "yang_tonic", "wind", "bone"],
    "blood_pressure": ["blood_pressure", "liver", "liver_yang", "wind"],
    "heart": ["heart", "shen", "blood_tonic", "qi_tonic"],
}

def get_all_herbs():
    return HERBS


def filter_herbs_by_condition(condition_text: str, max_herbs: int = 80):
    text = condition_text.lower()
    scored = []
    for herb in HERBS:
        score = 0
        cats = herb.get("categories", [])
        for keyword, mapped_cats in CONDITION_CATEGORY_MAP.items():
            if keyword in text:
                for mc in mapped_cats:
                    if mc in cats:
                        score += 2
        for cat in cats:
            if cat in text:
                score += 3
        for cat in cats:
            if any(word in cat for word in text.split()):
                score += 1
        if score > 0:
            scored.append((score, herb))
    scored.sort(key=lambda x: -x[0])
    result = [h for _, h in scored[:max_herbs]]
    if len(result) < 20:
        result = HERBS[:max_herbs]
    return result


def format_herb_list_for_prompt(herbs: list) -> str:
    lines = ["No. | Chinese | Pinyin | English | Extract Ratio | TCM Functions | Contraindications"]
    lines.append("-" * 100)
    for i, h in enumerate(herbs, 1):
        line = (f"{i:3}. | {h['chinese']:10} | {h['pinyin']:20} | {h['english']:30} | "
                f"{h['extract_ratio']:6} | {h['tcm_functions'][:60]:60} | {h['contraindications'][:40]}")
        lines.append(line)
    return "\n".join(lines)


# Names a practitioner may use that differ from the product-list name.
# Left side: common or classical synonym. Right side: the stocked base herb.
ALIASES = {
    "山茱萸": "山萸肉",     # Cornus — stocked as the deseeded flesh
    "旱莲草": "墨旱莲",     # Eclipta
    "仙灵脾": "淫羊藿",     # Epimedium
    "元胡": "延胡索",
    "生地": "生地黄",
    "苡仁": "薏苡仁",
    "云苓": "茯苓",
    "潞党参": "党参",
    "杭白芍": "白芍",
    "怀牛膝": "牛膝",
    "川牛膝": "牛膝",
    "北沙参": "南沙参",     # only the southern species is stocked
}

# Herbs a practitioner may ask for that Chemigran does NOT stock. Named
# explicitly so the caller gets None rather than a silent near-match.
NOT_STOCKED = {"昆布", "鹿茸", "海藻"}


def get_herb_by_chinese(chinese_name: str):
    """
    Resolve a herb name to a stocked product.

    Order: exact product name, alias, base-herb name, then a contains match.
    Returns None for herbs known not to be stocked, so the formulator cannot
    quietly substitute something similar.
    """
    name = (chinese_name or "").strip()
    if not name or name in NOT_STOCKED:
        return None

    for h in HERBS:
        if h["chinese"] == name:
            return h

    name = ALIASES.get(name, name)

    for h in HERBS:
        if h["chinese"] == name or h["base_herb"] == name:
            return h
    for h in HERBS:
        if name in h["chinese"]:
            return h
    return None
