"""
TCM Formula Safety Validator
Checks generated formulas against:
  1. Classical TCM incompatibilities (十八反 / 十九畏)
  2. HSA-mandated dosage limits for restricted substances
  3. Heavy-metal-bearing mineral herbs
  4. Pregnancy Category D herbs
  5. Animal-derived herbs (TSE / contamination risk)
  6. General herb-drug interaction flags

Returns a structured dict with a traffic-light score and per-flag detail.
No API call needed — pure rule-based logic.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional

# ─────────────────────────────────────────────────────────────────────────────
# DATA STRUCTURES
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class SafetyFlag:
    level: str          # "RED" | "AMBER" | "INFO"
    category: str       # e.g. "Classical Incompatibility", "Dosage Limit"
    herbs_involved: List[str]
    message: str
    action: str         # What the formulator should do


@dataclass
class SafetyReport:
    overall: str                        # "GREEN" | "AMBER" | "RED"
    score: int                          # 0–100 (100 = fully safe)
    flags: List[SafetyFlag] = field(default_factory=list)
    summary: str = ""
    manufacturer_notes: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "overall": self.overall,
            "score": self.score,
            "summary": self.summary,
            "flags": [
                {
                    "level": f.level,
                    "category": f.category,
                    "herbs_involved": f.herbs_involved,
                    "message": f.message,
                    "action": f.action,
                }
                for f in self.flags
            ],
            "manufacturer_notes": self.manufacturer_notes,
        }


# ─────────────────────────────────────────────────────────────────────────────
# RULE DATABASES
# ─────────────────────────────────────────────────────────────────────────────

# 十八反 — Eighteen Antagonisms
# Each entry: (herb_A, herb_B, note)
# If BOTH appear in a formula → RED flag
EIGHTEEN_ANTAGONISMS = [
    # 甘草 (Gan Cao) antagonises:
    ("甘草", "大戟",   "Gan Cao + Da Ji: classical 十八反 antagonism — toxic combination"),
    ("甘草", "芫花",   "Gan Cao + Yuan Hua: classical 十八反 antagonism — toxic combination"),
    ("甘草", "甘遂",   "Gan Cao + Gan Sui: classical 十八反 antagonism — toxic combination"),
    ("甘草", "海藻",   "Gan Cao + Hai Zao: classical 十八反 antagonism — evidence of interaction"),

    # 乌头 group (川乌, 草乌, 附子, 制附子, 制川乌, 制草乌) antagonises:
    ("川乌",  "贝母",  "Chuan Wu + Bei Mu: 十八反 — do not combine"),
    ("草乌",  "贝母",  "Cao Wu + Bei Mu: 十八反 — do not combine"),
    ("附子",  "贝母",  "Fu Zi + Bei Mu: 十八反 — do not combine"),
    ("制附子","贝母",  "Zhi Fu Zi + Bei Mu: 十八反 — do not combine"),
    ("制川乌","贝母",  "Zhi Chuan Wu + Bei Mu: 十八反 — do not combine"),
    ("制草乌","贝母",  "Zhi Cao Wu + Bei Mu: 十八反 — do not combine"),

    ("川乌",  "瓜蒌",  "Chuan Wu + Gua Lou: 十八反 — do not combine"),
    ("草乌",  "瓜蒌",  "Cao Wu + Gua Lou: 十八反 — do not combine"),
    ("附子",  "瓜蒌",  "Fu Zi + Gua Lou: 十八反 — do not combine"),
    ("制附子","瓜蒌",  "Zhi Fu Zi + Gua Lou: 十八反 — do not combine"),
    ("制川乌","瓜蒌",  "Zhi Chuan Wu + Gua Lou: 十八反 — do not combine"),
    ("制草乌","瓜蒌",  "Zhi Cao Wu + Gua Lou: 十八反 — do not combine"),

    ("川乌",  "半夏",  "Chuan Wu + Ban Xia: 十八反 — do not combine"),
    ("草乌",  "半夏",  "Cao Wu + Ban Xia: 十八反 — do not combine"),
    ("附子",  "半夏",  "Fu Zi + Ban Xia: 十八反 — do not combine"),
    ("制附子","半夏",  "Zhi Fu Zi + Ban Xia: 十八反 — do not combine"),
    ("制川乌","半夏",  "Zhi Chuan Wu + Ban Xia: 十八反 — do not combine"),
    ("制草乌","半夏",  "Zhi Cao Wu + Ban Xia: 十八反 — do not combine"),

    ("川乌",  "白蔹",  "Chuan Wu + Bai Lian: 十八反 — do not combine"),
    ("草乌",  "白蔹",  "Cao Wu + Bai Lian: 十八反 — do not combine"),
    ("附子",  "白蔹",  "Fu Zi + Bai Lian: 十八反 — do not combine"),
    ("制附子","白蔹",  "Zhi Fu Zi + Bai Lian: 十八反 — do not combine"),

    ("川乌",  "白及",  "Chuan Wu + Bai Ji: 十八反 — do not combine"),
    ("草乌",  "白及",  "Cao Wu + Bai Ji: 十八反 — do not combine"),
    ("附子",  "白及",  "Fu Zi + Bai Ji: 十八反 — do not combine"),
    ("制附子","白及",  "Zhi Fu Zi + Bai Ji: 十八反 — do not combine"),

    # 藜芦 (Li Lu) antagonises:
    ("藜芦", "人参",   "Li Lu + Ren Shen: 十八反 — toxic, avoid combination"),
    ("藜芦", "沙参",   "Li Lu + Sha Shen: 十八反 — toxic, avoid combination"),
    ("藜芦", "丹参",   "Li Lu + Dan Shen: 十八反 — toxic, avoid combination"),
    ("藜芦", "玄参",   "Li Lu + Xuan Shen: 十八反 — toxic, avoid combination"),
    ("藜芦", "苦参",   "Li Lu + Ku Shen: 十八反 — toxic, avoid combination"),
    ("藜芦", "细辛",   "Li Lu + Xi Xin: 十八反 — toxic, avoid combination"),
    ("藜芦", "白芍",   "Li Lu + Bai Shao: 十八反 — toxic, avoid combination"),
    ("藜芦", "赤芍",   "Li Lu + Chi Shao: 十八反 — toxic, avoid combination"),
]

# 十九畏 — Nineteen Incompatibilities (mutual inhibition / antagonism)
NINETEEN_INCOMPATIBILITIES = [
    ("硫磺",  "朴硝",   "Liu Huang + Pu Xiao: 十九畏 — mutual inhibition"),
    ("水银",  "砒霜",   "Shui Yin + Pi Shuang: 十九畏 — highly toxic minerals"),
    ("狼毒",  "密陀僧", "Lang Du + Mi Tuo Seng: 十九畏 — do not combine"),
    ("巴豆",  "牵牛子", "Ba Dou + Qian Niu Zi: 十九畏 — toxic purgatives, do not combine"),
    ("丁香",  "郁金",   "Ding Xiang + Yu Jin: 十九畏 — mutual inhibition, avoid if possible"),
    ("川乌",  "犀角",   "Chuan Wu + Xi Jiao: 十九畏 — do not combine"),
    ("草乌",  "犀角",   "Cao Wu + Xi Jiao: 十九畏 — do not combine"),
    ("牙硝",  "三棱",   "Ya Xiao + San Leng: 十九畏 — do not combine"),
    ("官桂",  "赤石脂", "Guan Gui + Chi Shi Zhi: 十九畏 — mutual inhibition"),
    ("肉桂",  "赤石脂", "Rou Gui + Chi Shi Zhi: 十九畏 — mutual inhibition"),
    ("人参",  "五灵脂", "Ren Shen + Wu Ling Zhi: 十九畏 — mutual inhibition, avoid combination"),
    ("党参",  "五灵脂", "Dang Shen + Wu Ling Zhi: 十九畏 — similar to Ren Shen, avoid combination"),
]

# HSA-restricted substances with dosage limits
# Per daily dose — granule formulas: typical total dose 5–10g/day
# We flag at AMBER when herb is present, RED if high percentage
# Keys: Chinese herb name, value: dict with limit and note
RESTRICTED_SUBSTANCES: dict = {
    "制附子": {
        "limit_desc": "Aconite alkaloids ≤ 60 mcg/day (HSA)",
        "high_risk_pct": 15,   # % in formula above which RED is triggered
        "amber_pct": 5,
        "note": "Processed aconite root. Contains aconitine alkaloids. Must not exceed 60 mcg total aconitine alkaloids per daily dose.",
    },
    "制川乌": {
        "limit_desc": "Aconite alkaloids ≤ 60 mcg/day (HSA)",
        "high_risk_pct": 15,
        "amber_pct": 5,
        "note": "Processed Chuan Wu. Same aconitine limit as Fu Zi. Check daily dosage calculation carefully.",
    },
    "制草乌": {
        "limit_desc": "Aconite alkaloids ≤ 60 mcg/day (HSA)",
        "high_risk_pct": 15,
        "amber_pct": 5,
        "note": "Processed Cao Wu. Often higher aconitine content than Chuan Wu. Keep total aconite alkaloids ≤ 60 mcg/day.",
    },
    "川乌": {
        "limit_desc": "Raw Chuan Wu — HSA requires processed form only. Aconitine ≤ 60 mcg/day",
        "high_risk_pct": 1,
        "amber_pct": 0,
        "note": "RAW Chuan Wu is not permitted in CPM. Only the processed (制) form is allowed.",
    },
    "草乌": {
        "limit_desc": "Raw Cao Wu — HSA requires processed form only",
        "high_risk_pct": 1,
        "amber_pct": 0,
        "note": "RAW Cao Wu is not permitted in CPM. Only the processed (制) form is allowed.",
    },
    "附子": {
        "limit_desc": "Raw Fu Zi — HSA requires processed form (制附子) only",
        "high_risk_pct": 1,
        "amber_pct": 0,
        "note": "RAW Fu Zi is not permitted in CPM. Only the processed (制附子) form is allowed.",
    },
    "麻黄": {
        "limit_desc": "Ephedra alkaloids < 1% of product weight (HSA)",
        "high_risk_pct": 20,
        "amber_pct": 10,
        "note": "Ephedrine content must be < 1% of total product weight. Declare on label. Not for use in children's products.",
    },
    "延胡索": {
        "limit_desc": "Tetrahydropalmatine ≤ 19 mg/day (HSA)",
        "high_risk_pct": 25,
        "amber_pct": 10,
        "note": "Contains tetrahydropalmatine (THP). HSA limit: ≤ 19 mg THP per daily dose. Verify with lab test.",
    },
    "马钱子": {
        "limit_desc": "Strychnine ≤ 0.9 mg/day (HSA)",
        "high_risk_pct": 5,
        "amber_pct": 1,
        "note": "Contains strychnine. Strict HSA limit. Must only be used as processed form (炙马钱子). Requires specialist oversight.",
    },
    "细辛": {
        "limit_desc": "Aristolochic acid concern — daily dose ≤ 3g raw herb (WHO guidance)",
        "high_risk_pct": 15,
        "amber_pct": 5,
        "note": "Xi Xin contains safrole and trace aristolochic-like acids. Keep below recommended daily limit. Not for long-term use.",
    },
    "关木通": {
        "limit_desc": "Aristolochic acid — BANNED in many countries",
        "high_risk_pct": 0,
        "amber_pct": 0,
        "note": "Guan Mu Tong contains aristolochic acid and is banned in Singapore CPM. Use Chuan Mu Tong (川木通) or alternatives.",
    },
    "广防己": {
        "limit_desc": "Aristolochic acid — BANNED in Singapore CPM",
        "high_risk_pct": 0,
        "amber_pct": 0,
        "note": "Guang Fang Ji contains aristolochic acid. Banned. Use Han Fang Ji (汉防己) instead.",
    },
    "朱砂": {
        "limit_desc": "Mercury compound — HSA limit Hg ≤ 0.5 ppm in finished product",
        "high_risk_pct": 0,
        "amber_pct": 0,
        "note": "Cinnabar (HgS). Requires heavy metals lab testing. Mercury must be ≤ 0.5 ppm. Not recommended for prolonged use.",
    },
    "雄黄": {
        "limit_desc": "Arsenic compound — HSA limit As ≤ 5 ppm in finished product",
        "high_risk_pct": 0,
        "amber_pct": 0,
        "note": "Realgar (As2S2). Requires heavy metals lab testing. Arsenic must be ≤ 5 ppm. High risk — obtain specialist sign-off.",
    },
    "洋金花": {
        "limit_desc": "Hyoscyamine/scopolamine ≤ 0.3 mg total alkaloids/day (HSA)",
        "high_risk_pct": 3,
        "amber_pct": 1,
        "note": "Datura flower. Contains belladonna alkaloids. Strict HSA limit. Not for OTC sale.",
    },
    "巴豆": {
        "limit_desc": "Extremely toxic purgative — requires specialist supervision",
        "high_risk_pct": 1,
        "amber_pct": 0,
        "note": "Croton seeds are a Poison Act–scheduled substance in Singapore. Not suitable for OTC CPM.",
    },
}

# Pregnancy Category D herbs — HIGH risk
# RED flag if in formula and pregnancy demographic mentioned
PREGNANCY_HIGH_RISK = {
    "麝香", "蟾酥", "三棱", "莪术", "水蛭", "虻虫",
    "巴豆", "牵牛子", "大戟", "商陆", "芫花", "甘遂",
    "斑蝥", "铅丹", "轻粉", "硇砂",
}

# Pregnancy — CAUTION herbs
PREGNANCY_CAUTION = {
    "桃仁", "红花", "大黄", "枳实", "枳壳",
    "制附子", "制川乌", "制草乌", "附子", "干姜",
    "肉桂", "官桂", "半夏", "天南星", "制半夏",
    "番泻叶", "芒硝", "冰片", "薏苡仁",
}

# Animal-derived herbs — flag for TSE undertaking requirement
ANIMAL_DERIVED = {
    "鹿茸": "Deer antler (mammalian)",
    "阿胶": "Donkey hide gelatin (mammalian)",
    "龟甲": "Tortoise plastron (reptile)",
    "鳖甲": "Soft-shell turtle shell (reptile)",
    "牡蛎": "Oyster shell (mollusc) — low TSE risk",
    "穿山甲": "Pangolin scales — CITES Appendix I, banned from trade",
    "五灵脂": "Flying squirrel faeces (mammalian)",
    "蜈蚣": "Centipede (invertebrate)",
    "全蝎": "Scorpion (invertebrate)",
    "地龙": "Earthworm (invertebrate)",
    "水蛭": "Leech (invertebrate)",
    "僵蚕": "Silkworm (insect)",
    "蝉蜕": "Cicada slough (insect)",
    "鸡内金": "Chicken gizzard lining (avian)",
    "蛤蚧": "Tokay gecko (reptile) — CITES listed",
    "海马": "Seahorse (fish) — CITES listed",
    "熊胆": "Bear bile — BANNED, CITES Appendix I",
    "犀角": "Rhinoceros horn — BANNED, CITES Appendix I",
    "虎骨": "Tiger bone — BANNED, CITES Appendix I",
    "麝香": "Musk deer pod — CITES Appendix II",
}

# Known significant herb–drug interactions
DRUG_INTERACTIONS = [
    {
        "herbs": {"丹参"},
        "drug": "Warfarin / anticoagulants",
        "effect": "Potentiates anticoagulant effect — bleeding risk",
        "level": "RED",
    },
    {
        "herbs": {"当归"},
        "drug": "Warfarin",
        "effect": "May enhance anticoagulant effect",
        "level": "AMBER",
    },
    {
        "herbs": {"红花", "桃仁"},
        "drug": "Anticoagulants / antiplatelet drugs",
        "effect": "Additive antiplatelet effect — bleeding risk",
        "level": "AMBER",
    },
    {
        "herbs": {"甘草"},
        "drug": "Antihypertensives / diuretics",
        "effect": "Glycyrrhizin can cause sodium retention, potassium loss, and raise blood pressure with high-dose long-term use",
        "level": "AMBER",
    },
    {
        "herbs": {"人参", "西洋参"},
        "drug": "MAOIs / stimulants",
        "effect": "May cause CNS stimulation and hypertensive crisis with MAOIs",
        "level": "AMBER",
    },
    {
        "herbs": {"大黄"},
        "drug": "Cardiac glycosides (digoxin)",
        "effect": "Hypokalaemia from diarrhoea can increase digoxin toxicity",
        "level": "AMBER",
    },
    {
        "herbs": {"麻黄"},
        "drug": "MAOIs, stimulants, antihypertensives, cardiac drugs",
        "effect": "Ephedrine: hypertensive crisis with MAOIs; reduces effectiveness of antihypertensives; cardiac arrhythmia risk",
        "level": "RED",
    },
    {
        "herbs": {"延胡索"},
        "drug": "CNS depressants / sedatives",
        "effect": "Tetrahydropalmatine has sedative effects — additive with benzodiazepines, opioids",
        "level": "AMBER",
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# MAIN CHECKER
# ─────────────────────────────────────────────────────────────────────────────

def check_formula_safety(
    formula: list[dict],
    demographic: str = "",
    condition: str = "",
    dosage_recommendation: str = "",
) -> SafetyReport:
    """
    Run all safety checks on a formula.

    Parameters
    ----------
    formula : list of herb dicts (from generate_formulation output)
        Each dict must have at least: chinese, percentage
    demographic : str
        e.g. "Pregnant women", "Children", "Seniors"
    condition : str
        Health condition — used for context warnings
    dosage_recommendation : str
        e.g. "5g twice daily" — used for context

    Returns
    -------
    SafetyReport
    """
    flags: list[SafetyFlag] = []
    manufacturer_notes: list[str] = []

    # Build lookup sets
    herb_chinese_set = {h.get("chinese", "").strip() for h in formula if h.get("chinese")}
    herb_pct_map = {h.get("chinese", "").strip(): h.get("percentage", 0) for h in formula}

    is_pregnancy_context = any(
        kw in (demographic + condition).lower()
        for kw in ["pregnan", "母", "孕", "breastfeed", "lactating", "nursing"]
    )
    is_children_context = any(
        kw in (demographic + condition).lower()
        for kw in ["child", "儿", "infant", "paediatric", "pediatric", "kid", "baby", "toddler"]
    )

    # ── 1. CLASSICAL TCM INCOMPATIBILITIES ────────────────────────────────────
    for herb_a, herb_b, note in EIGHTEEN_ANTAGONISMS:
        if herb_a in herb_chinese_set and herb_b in herb_chinese_set:
            flags.append(SafetyFlag(
                level="RED",
                category="Classical Incompatibility — 十八反",
                herbs_involved=[herb_a, herb_b],
                message=note,
                action="Remove one of these herbs from the formula. This is a classical 十八反 antagonism. Do not proceed to manufacturing until resolved.",
            ))

    for herb_a, herb_b, note in NINETEEN_INCOMPATIBILITIES:
        if herb_a in herb_chinese_set and herb_b in herb_chinese_set:
            flags.append(SafetyFlag(
                level="RED",
                category="Classical Incompatibility — 十九畏",
                herbs_involved=[herb_a, herb_b],
                message=note,
                action="Remove one of these herbs from the formula. This is a 十九畏 incompatibility.",
            ))

    # ── 2. RESTRICTED SUBSTANCES / HSA DOSAGE LIMITS ─────────────────────────
    for herb_cn, rules in RESTRICTED_SUBSTANCES.items():
        if herb_cn in herb_chinese_set:
            pct = herb_pct_map.get(herb_cn, 0)
            if pct >= rules["high_risk_pct"] or rules["high_risk_pct"] == 0:
                level = "RED"
                action = f"Critical: {rules['limit_desc']}. Send to lab for quantitative alkaloid/metal analysis before any manufacturing. Do not proceed without test results."
            elif pct >= rules["amber_pct"]:
                level = "AMBER"
                action = f"Required: verify daily dose compliance. {rules['limit_desc']}. Request lab certificate of analysis from granule supplier."
            else:
                level = "AMBER"
                action = f"Low percentage but still requires monitoring: {rules['limit_desc']}"

            flags.append(SafetyFlag(
                level=level,
                category="Restricted Substance — HSA Limit",
                herbs_involved=[herb_cn],
                message=rules["note"],
                action=action,
            ))
            manufacturer_notes.append(
                f"{herb_cn}: {rules['limit_desc']} — lab CoA required from supplier."
            )

    # ── 3. HEAVY METAL RISK ───────────────────────────────────────────────────
    heavy_metal_herbs = {"朱砂", "雄黄", "铅丹", "轻粉", "密陀僧"}
    found_hm = herb_chinese_set & heavy_metal_herbs
    if found_hm:
        for hm in found_hm:
            flags.append(SafetyFlag(
                level="RED",
                category="Heavy Metal Risk",
                herbs_involved=[hm],
                message=f"{hm} is a mineral herb containing toxic metals (Hg, As, or Pb).",
                action="Mandatory heavy metals testing required: As ≤ 5 ppm, Pb ≤ 10 ppm, Hg ≤ 0.5 ppm, Cd ≤ 0.3 ppm. Provide full lab report to HSA.",
            ))
        manufacturer_notes.append(
            "Heavy metal-containing mineral herbs detected. Full heavy metals CoA required per HSA CPM guidelines."
        )

    # ── 4. PREGNANCY SAFETY ───────────────────────────────────────────────────
    if is_pregnancy_context:
        high_risk_found = herb_chinese_set & PREGNANCY_HIGH_RISK
        caution_found = herb_chinese_set & PREGNANCY_CAUTION

        if high_risk_found:
            flags.append(SafetyFlag(
                level="RED",
                category="Pregnancy Safety — Category D",
                herbs_involved=list(high_risk_found),
                message="These herbs are contraindicated in pregnancy and may cause miscarriage or foetal harm.",
                action="REMOVE from formula immediately if targeting pregnant women. Revise formulation.",
            ))

        if caution_found:
            flags.append(SafetyFlag(
                level="AMBER",
                category="Pregnancy Safety — Use with Caution",
                herbs_involved=list(caution_found),
                message="These herbs are cautioned during pregnancy — may stimulate uterine contractions or affect foetal development.",
                action="If product is for pregnant women, consult a registered TCM physician. Consider substitution or add contraindication to label.",
            ))

    # ── 5. CHILDREN'S FORMULA CHECKS ─────────────────────────────────────────
    if is_children_context:
        child_concern_herbs = herb_chinese_set & {"麻黄", "制附子", "川乌", "草乌", "马钱子", "巴豆", "细辛", "朱砂"}
        if child_concern_herbs:
            flags.append(SafetyFlag(
                level="RED",
                category="Paediatric Safety",
                herbs_involved=list(child_concern_herbs),
                message="These herbs are not recommended for children's formulas due to toxicity risk.",
                action="Remove or substitute with safer alternatives. Children's formulas require specialist paediatric TCM review.",
            ))

        # Ephedra special restriction in children
        if "麻黄" in herb_chinese_set:
            flags.append(SafetyFlag(
                level="RED",
                category="Paediatric Safety — Ephedra",
                herbs_involved=["麻黄"],
                message="Ephedrine (Ma Huang) is banned in children's OTC products in Singapore and many other markets.",
                action="Remove 麻黄 from any formula intended for children.",
            ))

    # ── 6. ANIMAL-DERIVED / CITES ─────────────────────────────────────────────
    banned_cites = {"穿山甲", "熊胆", "犀角", "虎骨"}
    found_banned = herb_chinese_set & banned_cites

    if found_banned:
        for h in found_banned:
            flags.append(SafetyFlag(
                level="RED",
                category="CITES — Banned Species",
                herbs_involved=[h],
                message=f"{h}: {ANIMAL_DERIVED.get(h, 'CITES-listed species')} — international trade is banned.",
                action="Remove immediately. This ingredient cannot be sourced legally or included in any registered CPM product.",
            ))

    # TSE / animal-derived flagging
    tse_herbs_found = {h: ANIMAL_DERIVED[h] for h in herb_chinese_set if h in ANIMAL_DERIVED and h not in banned_cites}
    if tse_herbs_found:
        flags.append(SafetyFlag(
            level="AMBER",
            category="Animal-Derived — TSE Undertaking Required",
            herbs_involved=list(tse_herbs_found.keys()),
            message="Formula contains animal-derived ingredients: " + "; ".join(f"{k} ({v})" for k, v in tse_herbs_found.items()),
            action="A TSE (Transmissible Spongiform Encephalopathy) Undertaking must be submitted with CPM listing. Obtain TSE declaration from each animal-ingredient supplier.",
        ))
        manufacturer_notes.append(
            "TSE Undertaking form required for: " + ", ".join(tse_herbs_found.keys())
        )

    # ── 7. HERB–DRUG INTERACTIONS ─────────────────────────────────────────────
    for interaction in DRUG_INTERACTIONS:
        if interaction["herbs"] & herb_chinese_set:
            matched = list(interaction["herbs"] & herb_chinese_set)
            flags.append(SafetyFlag(
                level=interaction["level"],
                category="Herb–Drug Interaction",
                herbs_involved=matched,
                message=f"{', '.join(matched)} — {interaction['drug']}: {interaction['effect']}",
                action="Add to product label under 'Precautions' and 'Drug Interactions'. Advise patients on concurrent medications to consult physician.",
            ))

    # ── 8. ALWAYS-REQUIRED MANUFACTURER NOTES ────────────────────────────────
    manufacturer_notes.extend([
        "Heavy metals test required for all CPM: As ≤ 5 ppm, Cd ≤ 0.3 ppm, Pb ≤ 10 ppm, Hg ≤ 0.5 ppm.",
        "Microbial limits (oral CPM): Total aerobic count < 10⁵ CFU/g, E. coli absent, Salmonella absent.",
        "For granule format: test filling variation, water content (<9%), granule size variation, dispersibility.",
        "GMP certificate from manufacturer required for CPM listing submission.",
        "Keep batch records and full traceability of raw herb sourcing.",
    ])

    # ── COMPUTE OVERALL SCORE ─────────────────────────────────────────────────
    red_flags = [f for f in flags if f.level == "RED"]
    amber_flags = [f for f in flags if f.level == "AMBER"]

    if red_flags:
        overall = "RED"
        score = max(0, 40 - (len(red_flags) * 15))
    elif amber_flags:
        overall = "AMBER"
        score = max(45, 90 - (len(amber_flags) * 10))
    else:
        overall = "GREEN"
        score = 100

    # Build summary
    if overall == "GREEN":
        summary = (
            f"✅ No critical safety issues found. {len(amber_flags)} advisory note(s). "
            "Formula appears safe for consumption — proceed with standard manufacturer QC testing."
        )
    elif overall == "AMBER":
        summary = (
            f"⚠️ {len(amber_flags)} advisory flag(s) require attention before manufacturing. "
            "No classical incompatibilities detected. Address all AMBER items and obtain required lab certificates."
        )
    else:
        summary = (
            f"🚨 {len(red_flags)} critical issue(s) detected. Formula must NOT proceed to manufacturing "
            f"until all RED flags are resolved. {len(amber_flags)} advisory flag(s) also present."
        )

    return SafetyReport(
        overall=overall,
        score=score,
        flags=flags,
        summary=summary,
        manufacturer_notes=manufacturer_notes,
    )