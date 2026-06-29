"""
TCM Formula Safety Validator
Checks generated formulas against:
  1. Classical TCM incompatibilities (十八反 / 十九畏)
  2. HSA-mandated dosage limits for restricted substances
  3. Heavy-metal-bearing mineral herbs
  4. Pregnancy Category D herbs
  5. Animal-derived herbs (TSE / contamination risk)
  6. General herb-drug interaction flags
  7. Allergen cross-reactivity (tree nuts, shellfish, ragweed/pollen, latex, bee products, sulphites, legumes, ginger family)

Returns a structured dict with a traffic-light score and per-flag detail.
No API call needed — pure rule-based logic.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List

# ─────────────────────────────────────────────────────────────────────────────
# DATA STRUCTURES
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class SafetyFlag:
    level: str          # "RED" | "AMBER" | "INFO"
    category: str
    herbs_involved: List[str]
    message: str
    action: str


@dataclass
class SafetyReport:
    overall: str                        # "GREEN" | "AMBER" | "RED"
    score: int                          # 0–100
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
# 十八反 — EIGHTEEN ANTAGONISMS
# ─────────────────────────────────────────────────────────────────────────────
EIGHTEEN_ANTAGONISMS = [
    ("甘草", "大戟",   "Gan Cao + Da Ji: 十八反 antagonism — toxic combination"),
    ("甘草", "芫花",   "Gan Cao + Yuan Hua: 十八反 antagonism — toxic combination"),
    ("甘草", "甘遂",   "Gan Cao + Gan Sui: 十八反 antagonism — toxic combination"),
    ("甘草", "海藻",   "Gan Cao + Hai Zao: 十八反 antagonism"),
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
    ("藜芦", "人参",   "Li Lu + Ren Shen: 十八反 — toxic, avoid combination"),
    ("藜芦", "沙参",   "Li Lu + Sha Shen: 十八反 — toxic, avoid combination"),
    ("藜芦", "丹参",   "Li Lu + Dan Shen: 十八反 — toxic, avoid combination"),
    ("藜芦", "玄参",   "Li Lu + Xuan Shen: 十八反 — toxic, avoid combination"),
    ("藜芦", "苦参",   "Li Lu + Ku Shen: 十八反 — toxic, avoid combination"),
    ("藜芦", "细辛",   "Li Lu + Xi Xin: 十八反 — toxic, avoid combination"),
    ("藜芦", "白芍",   "Li Lu + Bai Shao: 十八反 — toxic, avoid combination"),
    ("藜芦", "赤芍",   "Li Lu + Chi Shao: 十八反 — toxic, avoid combination"),
]

# ─────────────────────────────────────────────────────────────────────────────
# 十九畏 — NINETEEN INCOMPATIBILITIES
# ─────────────────────────────────────────────────────────────────────────────
NINETEEN_INCOMPATIBILITIES = [
    ("硫磺",  "朴硝",   "Liu Huang + Pu Xiao: 十九畏 — mutual inhibition"),
    ("水银",  "砒霜",   "Shui Yin + Pi Shuang: 十九畏 — highly toxic minerals"),
    ("狼毒",  "密陀僧", "Lang Du + Mi Tuo Seng: 十九畏 — do not combine"),
    ("巴豆",  "牵牛子", "Ba Dou + Qian Niu Zi: 十九畏 — toxic purgatives, do not combine"),
    ("丁香",  "郁金",   "Ding Xiang + Yu Jin: 十九畏 — mutual inhibition"),
    ("川乌",  "犀角",   "Chuan Wu + Xi Jiao: 十九畏 — do not combine"),
    ("草乌",  "犀角",   "Cao Wu + Xi Jiao: 十九畏 — do not combine"),
    ("牙硝",  "三棱",   "Ya Xiao + San Leng: 十九畏 — do not combine"),
    ("官桂",  "赤石脂", "Guan Gui + Chi Shi Zhi: 十九畏 — mutual inhibition"),
    ("肉桂",  "赤石脂", "Rou Gui + Chi Shi Zhi: 十九畏 — mutual inhibition"),
    ("人参",  "五灵脂", "Ren Shen + Wu Ling Zhi: 十九畏 — mutual inhibition"),
    ("党参",  "五灵脂", "Dang Shen + Wu Ling Zhi: 十九畏 — similar to Ren Shen, avoid combination"),
]

# ─────────────────────────────────────────────────────────────────────────────
# HSA RESTRICTED SUBSTANCES
# ─────────────────────────────────────────────────────────────────────────────
RESTRICTED_SUBSTANCES = {
    "制附子": {
        "limit_desc": "Aconite alkaloids ≤ 60 mcg/day (HSA)",
        "high_risk_pct": 15,
        "amber_pct": 5,
        "note": "Processed aconite root. Must not exceed 60 mcg total aconitine alkaloids per daily dose.",
    },
    "制川乌": {
        "limit_desc": "Aconite alkaloids ≤ 60 mcg/day (HSA)",
        "high_risk_pct": 15,
        "amber_pct": 5,
        "note": "Processed Chuan Wu. Same aconitine limit as Fu Zi. Check daily dosage carefully.",
    },
    "制草乌": {
        "limit_desc": "Aconite alkaloids ≤ 60 mcg/day (HSA)",
        "high_risk_pct": 15,
        "amber_pct": 5,
        "note": "Processed Cao Wu. Often higher aconitine content than Chuan Wu. Keep total aconite alkaloids ≤ 60 mcg/day.",
    },
    "川乌": {
        "limit_desc": "Raw Chuan Wu — HSA requires processed form only",
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
        "note": "Ephedrine content must be < 1% of total product weight. Declare on label. Not for children's products.",
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
        "note": "Contains strychnine. Must only be used as processed form (炙马钱子). Requires specialist oversight.",
    },
    "细辛": {
        "limit_desc": "Daily dose ≤ 3g raw herb (WHO guidance)",
        "high_risk_pct": 15,
        "amber_pct": 5,
        "note": "Xi Xin contains safrole and trace aristolochic-like acids. Keep below recommended daily limit.",
    },
    "关木通": {
        "limit_desc": "Aristolochic acid — BANNED in Singapore CPM",
        "high_risk_pct": 0,
        "amber_pct": 0,
        "note": "Guan Mu Tong contains aristolochic acid and is banned. Use Chuan Mu Tong (川木通) instead.",
    },
    "广防己": {
        "limit_desc": "Aristolochic acid — BANNED in Singapore CPM",
        "high_risk_pct": 0,
        "amber_pct": 0,
        "note": "Guang Fang Ji contains aristolochic acid. Banned. Use Han Fang Ji (汉防己) instead.",
    },
    "朱砂": {
        "limit_desc": "Mercury compound — HSA limit Hg ≤ 0.5 ppm",
        "high_risk_pct": 0,
        "amber_pct": 0,
        "note": "Cinnabar (HgS). Requires heavy metals lab testing. Mercury must be ≤ 0.5 ppm.",
    },
    "雄黄": {
        "limit_desc": "Arsenic compound — HSA limit As ≤ 5 ppm",
        "high_risk_pct": 0,
        "amber_pct": 0,
        "note": "Realgar (As2S2). Requires heavy metals lab testing. Arsenic must be ≤ 5 ppm.",
    },
    "洋金花": {
        "limit_desc": "Hyoscyamine/scopolamine ≤ 0.3 mg/day (HSA)",
        "high_risk_pct": 3,
        "amber_pct": 1,
        "note": "Datura flower. Contains belladonna alkaloids. Strict HSA limit. Not for OTC sale.",
    },
    "巴豆": {
        "limit_desc": "Extremely toxic — Poison Act scheduled substance in Singapore",
        "high_risk_pct": 1,
        "amber_pct": 0,
        "note": "Croton seeds. Not suitable for OTC CPM.",
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# PREGNANCY HERBS
# ─────────────────────────────────────────────────────────────────────────────
PREGNANCY_HIGH_RISK = {
    "麝香", "蟾酥", "三棱", "莪术", "水蛭", "虻虫",
    "巴豆", "牵牛子", "大戟", "商陆", "芫花", "甘遂",
    "斑蝥", "铅丹", "轻粉", "硇砂",
}

PREGNANCY_CAUTION = {
    "桃仁", "红花", "大黄", "枳实", "枳壳",
    "制附子", "制川乌", "制草乌", "附子", "干姜",
    "肉桂", "官桂", "半夏", "天南星", "制半夏",
    "番泻叶", "芒硝", "冰片", "薏苡仁",
}

# ─────────────────────────────────────────────────────────────────────────────
# ANIMAL-DERIVED HERBS
# ─────────────────────────────────────────────────────────────────────────────
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

# ─────────────────────────────────────────────────────────────────────────────
# HERB–DRUG INTERACTIONS
# ─────────────────────────────────────────────────────────────────────────────
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
        "effect": "Glycyrrhizin can cause sodium retention and raise blood pressure with high-dose long-term use",
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
# ALLERGEN CROSS-REACTIVITY DATABASE
# ─────────────────────────────────────────────────────────────────────────────
ALLERGEN_GROUPS = [
    {
        "name": "Tree Nut / Stone Fruit Allergy",
        "trigger_keywords": ["tree nut", "nut", "almond", "peach", "apricot", "plum",
                             "walnut", "cashew", "pistachio", "peanut"],
        "herbs": {
            "桃仁": "Peach kernel (Prunus persica) — direct tree nut cross-reactivity",
            "杏仁": "Apricot kernel (Prunus armeniaca) — direct tree nut cross-reactivity",
            "苦杏仁": "Bitter apricot kernel — direct tree nut cross-reactivity",
            "甜杏仁": "Sweet apricot kernel — direct tree nut cross-reactivity",
            "柏子仁": "Arborvitae seed — seed allergen cross-reactivity possible",
            "酸枣仁": "Sour jujube seed — seed allergen, flag for severe nut allergy",
            "火麻仁": "Hemp seed — seed protein allergen cross-reactivity",
            "郁李仁": "Bush cherry seed (Prunus) — stone fruit cross-reactivity",
            "白果": "Ginkgo nut — tree nut cross-reactivity reported",
        },
        "mechanism": "Seed storage proteins (2S albumins, vicilins) shared across Rosaceae and other plant families trigger IgE cross-reactivity in nut-allergic patients.",
        "level": "RED",
        "label_action": "Declare on label: 'Contains [herb] — may cross-react with tree nut allergies. Not suitable for patients with known tree nut or stone fruit allergy.'",
    },
    {
        "name": "Shellfish / Seafood / Marine Allergy",
        "trigger_keywords": ["shellfish", "seafood", "prawn", "shrimp", "crab", "lobster",
                             "oyster", "clam", "mussel", "fish", "marine", "seaweed", "iodine"],
        "herbs": {
            "牡蛎": "Oyster shell — shellfish allergen (tropomyosin) risk",
            "海藻": "Seaweed — iodine content; marine protein allergen cross-reactivity",
            "昆布": "Kelp/Kombu — high iodine; marine allergen cross-reactivity",
            "海马": "Seahorse (fish) — fish allergen",
            "海螵蛸": "Cuttlefish bone — shellfish/mollusc allergen",
            "珍珠": "Pearl (oyster-derived) — mollusc cross-reactivity",
            "珍珠母": "Mother of pearl — mollusc cross-reactivity",
        },
        "mechanism": "Tropomyosin is the major shellfish allergen and is conserved across marine invertebrates. High iodine content in seaweeds can trigger reactions in iodine-sensitive patients.",
        "level": "RED",
        "label_action": "Declare on label: 'Contains marine/shellfish-derived ingredient. Not suitable for patients with shellfish or seafood allergy.'",
    },
    {
        "name": "Ragweed / Pollen / Asteraceae Allergy",
        "trigger_keywords": ["ragweed", "pollen", "hay fever", "seasonal allergy", "flower allergy",
                             "daisy", "chrysanthemum", "asteraceae", "compositae", "chamomile"],
        "herbs": {
            "菊花": "Chrysanthemum (Asteraceae) — primary cross-reactor with ragweed",
            "蒲公英": "Dandelion (Asteraceae) — strong ragweed cross-reactivity",
            "艾叶": "Mugwort/Moxa (Asteraceae) — very common pollen allergen in Asia",
            "茵陈": "Artemisia capillaris (Asteraceae) — mugwort family, high pollen allergen",
            "红花": "Safflower (Asteraceae) — Compositae cross-reactivity",
            "旋覆花": "Inula flower (Asteraceae) — Compositae allergen",
            "蒲黄": "Cattail pollen — direct pollen allergen, HIGH risk",
            "款冬花": "Coltsfoot (Asteraceae) — cross-reacts with ragweed and mugwort",
        },
        "mechanism": "Asteraceae family herbs share pollen proteins that cross-react with ragweed (Ambrosia) and mugwort (Artemisia). Oral consumption can trigger OAS (Oral Allergy Syndrome) or systemic reactions.",
        "level": "AMBER",
        "label_action": "Declare on label: 'Contains herb from Asteraceae (Compositae) family. Patients with hay fever or ragweed allergy should consult physician before use.'",
    },
    {
        "name": "Latex Allergy",
        "trigger_keywords": ["latex", "rubber", "latex allergy"],
        "herbs": {
            "木瓜": "Papaya (papain) — latex-fruit syndrome cross-reactivity",
            "无花果": "Fig — strong latex cross-reactivity (ficin enzyme)",
            "蒲公英": "Dandelion — contains latex-like compounds",
        },
        "mechanism": "Latex-fruit syndrome: Class I chitinases (hevein-like proteins) are shared between rubber latex and certain fruits/plants. Patients with latex allergy may react to these herbs.",
        "level": "AMBER",
        "label_action": "Declare on label: 'May cross-react in patients with latex allergy. Consult physician before use.'",
    },
    {
        "name": "Bee / Honey / Propolis Allergy",
        "trigger_keywords": ["bee", "honey", "propolis", "royal jelly", "beeswax",
                             "bee sting", "bee product"],
        "herbs": {
            "蜂蜜": "Honey — direct bee product allergen",
            "蜂王浆": "Royal jelly — common allergen, anaphylaxis reported",
            "蜂蜡": "Beeswax — bee product allergen",
            "花粉": "Bee pollen — high allergen load, anaphylaxis risk",
            "蒲黄": "Cattail pollen — cross-reacts with bee pollen sensitisation",
        },
        "mechanism": "Bee products contain bee venom proteins, royal jelly proteins, and pollen allergens. IgE-mediated anaphylaxis is well-documented, especially with royal jelly.",
        "level": "RED",
        "label_action": "Declare on label: 'Contains bee-derived product. NOT SUITABLE for patients with bee/honey/royal jelly allergy — risk of anaphylaxis.'",
    },
    {
        "name": "Sulphite / Sulphur Sensitivity",
        "trigger_keywords": ["sulphite", "sulfite", "sulphur", "sulfur", "so2",
                             "wine allergy", "dried fruit allergy", "asthma sulphite"],
        "herbs": {
            "硫磺": "Sulphur mineral — direct sulphite source",
            "白矾": "Alum (aluminium sulphate) — sulphate content",
            "枸杞子": "Wolfberry — often sulphur-fumigated; flag for sulphite sensitivity",
            "百合": "Lily bulb — often sulphur-fumigated during drying",
            "银耳": "White fungus — sulphur fumigation used in processing",
            "山药": "Chinese yam — sulphur fumigation common in drying",
        },
        "mechanism": "Sulphite sensitivity (particularly in asthmatic patients) can be triggered by sulphur-processed herbs. Residual SO2 from fumigation can trigger bronchoconstriction.",
        "level": "AMBER",
        "label_action": "Declare on label: 'May contain sulphite residues from processing. Not recommended for patients with sulphite sensitivity or sulphite-sensitive asthma.' Obtain sulphite-free CoA from supplier.",
    },
    {
        "name": "Legume / Soy / Bean Allergy",
        "trigger_keywords": ["legume", "soy", "soya", "bean", "peanut", "lentil", "pulse"],
        "herbs": {
            "大豆": "Soybean — direct legume allergen",
            "黑豆": "Black soybean — direct soy allergen",
            "赤小豆": "Adzuki bean — legume cross-reactivity",
            "绿豆": "Mung bean — legume cross-reactivity",
            "决明子": "Cassia seed (Leguminosae) — legume cross-reactivity possible",
            "甘草": "Licorice root (Leguminosae) — legume family, cross-reactivity reported",
            "黄芪": "Astragalus (Leguminosae) — legume family",
            "葛根": "Kudzu root (Leguminosae) — legume family",
        },
        "mechanism": "Leguminosae (Fabaceae) is one of the largest plant families in TCM. Patients with soy or legume allergy may cross-react with other Fabaceae members.",
        "level": "AMBER",
        "label_action": "Declare on label: 'Contains herb from the legume family (Leguminosae). Patients with soy or legume allergy should consult physician before use.'",
    },
    {
        "name": "Ginger / Zingiberaceae Family Allergy",
        "trigger_keywords": ["ginger", "turmeric", "cardamom", "zingiberaceae", "spice allergy"],
        "herbs": {
            "生姜": "Fresh ginger — primary Zingiberaceae allergen",
            "干姜": "Dried ginger — concentrated Zingiberaceae allergen",
            "姜黄": "Turmeric — contact allergy well-documented",
            "砂仁": "Cardamom (Zingiberaceae) — cross-reactivity with ginger allergy",
            "草豆蔻": "Katsumada's galangal (Zingiberaceae) — cross-reactivity",
            "高良姜": "Galangal (Zingiberaceae) — cross-reactivity with ginger",
        },
        "mechanism": "Zingiberaceae family shares allergenic proteins across ginger, turmeric, and related spices. Contact allergy and oral allergy syndrome both reported.",
        "level": "AMBER",
        "label_action": "Declare on label: 'Contains herb from the ginger family. Patients with known ginger or turmeric allergy should use with caution.'",
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# MAIN CHECKER
# ─────────────────────────────────────────────────────────────────────────────

def check_formula_safety(
    formula,
    demographic="",
    condition="",
    dosage_recommendation="",
    known_allergies="",
):
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
    known_allergies : str
        Free-text allergy profile, e.g. "tree nuts, shellfish, honey"

    Returns
    -------
    SafetyReport
    """
    flags = []
    manufacturer_notes = []

    # Build lookup sets
    herb_chinese_set = {h.get("chinese", "").strip() for h in formula if h.get("chinese")}
    herb_pct_map = {h.get("chinese", "").strip(): h.get("percentage", 0) for h in formula}

    is_pregnancy_context = any(
        kw in (demographic + condition).lower()
        for kw in ["pregnan", "breastfeed", "lactating", "nursing"]
    )
    is_children_context = any(
        kw in (demographic + condition).lower()
        for kw in ["child", "infant", "paediatric", "pediatric", "kid", "baby", "toddler"]
    )

    # 1. CLASSICAL TCM INCOMPATIBILITIES
    for herb_a, herb_b, note in EIGHTEEN_ANTAGONISMS:
        if herb_a in herb_chinese_set and herb_b in herb_chinese_set:
            flags.append(SafetyFlag(
                level="RED",
                category="Classical Incompatibility",
                herbs_involved=[herb_a, herb_b],
                message=note,
                action="Remove one of these herbs. Do not proceed to manufacturing until resolved.",
            ))

    for herb_a, herb_b, note in NINETEEN_INCOMPATIBILITIES:
        if herb_a in herb_chinese_set and herb_b in herb_chinese_set:
            flags.append(SafetyFlag(
                level="RED",
                category="Classical Incompatibility",
                herbs_involved=[herb_a, herb_b],
                message=note,
                action="Remove one of these herbs.",
            ))

    # 2. RESTRICTED SUBSTANCES
    for herb_cn, rules in RESTRICTED_SUBSTANCES.items():
        if herb_cn in herb_chinese_set:
            pct = herb_pct_map.get(herb_cn, 0)
            if pct >= rules["high_risk_pct"] or rules["high_risk_pct"] == 0:
                level = "RED"
                action = "Critical: {}. Lab analysis required before manufacturing.".format(rules["limit_desc"])
            elif pct >= rules["amber_pct"]:
                level = "AMBER"
                action = "Verify daily dose: {}. Request lab CoA from supplier.".format(rules["limit_desc"])
            else:
                level = "AMBER"
                action = "Monitor: {}".format(rules["limit_desc"])
            flags.append(SafetyFlag(
                level=level,
                category="Restricted Substance - HSA Limit",
                herbs_involved=[herb_cn],
                message=rules["note"],
                action=action,
            ))
            manufacturer_notes.append("{}: {} - lab CoA required.".format(herb_cn, rules["limit_desc"]))

    # 3. HEAVY METAL RISK
    found_hm = herb_chinese_set & {"朱砂", "雄黄", "铅丹", "轻粉", "密陀僧"}
    if found_hm:
        for hm in found_hm:
            flags.append(SafetyFlag(
                level="RED",
                category="Heavy Metal Risk",
                herbs_involved=[hm],
                message="{} is a mineral herb containing toxic metals.".format(hm),
                action="Mandatory heavy metals testing: As<=5ppm, Pb<=10ppm, Hg<=0.5ppm, Cd<=0.3ppm.",
            ))
        manufacturer_notes.append("Heavy metal minerals detected. Full heavy metals CoA required.")

    # 4. PREGNANCY SAFETY
    if is_pregnancy_context:
        high_risk_found = herb_chinese_set & PREGNANCY_HIGH_RISK
        caution_found = herb_chinese_set & PREGNANCY_CAUTION
        if high_risk_found:
            flags.append(SafetyFlag(
                level="RED",
                category="Pregnancy Safety - Category D",
                herbs_involved=list(high_risk_found),
                message="These herbs are contraindicated in pregnancy.",
                action="REMOVE from formula if targeting pregnant women.",
            ))
        if caution_found:
            flags.append(SafetyFlag(
                level="AMBER",
                category="Pregnancy Safety - Caution",
                herbs_involved=list(caution_found),
                message="These herbs require caution during pregnancy.",
                action="Consult registered TCM physician. Add contraindication to label.",
            ))

    # 5. CHILDREN
    if is_children_context:
        child_concern = herb_chinese_set & {"麻黄", "制附子", "川乌", "草乌", "马钱子", "巴豆", "细辛", "朱砂"}
        if child_concern:
            flags.append(SafetyFlag(
                level="RED",
                category="Paediatric Safety",
                herbs_involved=list(child_concern),
                message="These herbs are not recommended for children due to toxicity.",
                action="Remove or substitute. Paediatric TCM specialist review required.",
            ))

    # 6. ANIMAL-DERIVED / CITES
    banned_cites = {"穿山甲", "熊胆", "犀角", "虎骨"}
    found_banned = herb_chinese_set & banned_cites
    if found_banned:
        for h in found_banned:
            flags.append(SafetyFlag(
                level="RED",
                category="CITES - Banned Species",
                herbs_involved=[h],
                message="{}: CITES-listed - trade is banned.".format(h),
                action="Remove immediately. Cannot be legally sourced or registered.",
            ))
    tse_found = {h: ANIMAL_DERIVED[h] for h in herb_chinese_set if h in ANIMAL_DERIVED and h not in banned_cites}
    if tse_found:
        flags.append(SafetyFlag(
            level="AMBER",
            category="Animal-Derived - TSE Undertaking Required",
            herbs_involved=list(tse_found.keys()),
            message="Contains animal-derived ingredients: " + "; ".join("{} ({})".format(k, v) for k, v in tse_found.items()),
            action="TSE Undertaking required for CPM listing. Obtain TSE declaration from each supplier.",
        ))
        manufacturer_notes.append("TSE Undertaking required for: " + ", ".join(tse_found.keys()))

    # 7. HERB-DRUG INTERACTIONS
    for interaction in DRUG_INTERACTIONS:
        if interaction["herbs"] & herb_chinese_set:
            matched = list(interaction["herbs"] & herb_chinese_set)
            flags.append(SafetyFlag(
                level=interaction["level"],
                category="Herb-Drug Interaction",
                herbs_involved=matched,
                message="{} -- {}: {}".format(", ".join(matched), interaction["drug"], interaction["effect"]),
                action="Add to product label under Precautions and Drug Interactions.",
            ))

    # 8. ALLERGEN CROSS-REACTIVITY
    if known_allergies and known_allergies.strip():
        allergy_lower = known_allergies.lower()
        for group in ALLERGEN_GROUPS:
            triggered = any(kw in allergy_lower for kw in group["trigger_keywords"])
            if not triggered:
                continue
            matched_herbs = {cn: desc for cn, desc in group["herbs"].items() if cn in herb_chinese_set}
            if not matched_herbs:
                continue
            herb_details = "; ".join("{} - {}".format(k, v) for k, v in matched_herbs.items())
            flags.append(SafetyFlag(
                level=group["level"],
                category="Allergen Risk - {}".format(group["name"]),
                herbs_involved=list(matched_herbs.keys()),
                message="Allergy '{}' may cross-react with: {}. {}".format(known_allergies, herb_details, group["mechanism"]),
                action=group["label_action"],
            ))
            manufacturer_notes.append("Allergen declaration required ({}): {}".format(
                group["name"], ", ".join(matched_herbs.keys())))

    # 9. ALWAYS-REQUIRED MANUFACTURER NOTES
    manufacturer_notes.extend([
        "Heavy metals test required: As<=5ppm, Cd<=0.3ppm, Pb<=10ppm, Hg<=0.5ppm.",
        "Microbial limits (oral CPM): Total aerobic count <10^5 CFU/g, E. coli absent, Salmonella absent.",
        "Granule format tests: filling variation, water content (<9%), granule size, dispersibility.",
        "GMP certificate from manufacturer required for CPM listing.",
        "Keep batch records and full traceability of raw herb sourcing.",
    ])

    # COMPUTE SCORE
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

    if overall == "GREEN":
        summary = "No critical issues. {} advisory note(s). Safe to proceed with standard QC testing.".format(len(amber_flags))
    elif overall == "AMBER":
        summary = "{} advisory flag(s). No classical incompatibilities. Address AMBER items before manufacturing.".format(len(amber_flags))
    else:
        summary = "{} critical issue(s). Do NOT proceed to manufacturing until all RED flags are resolved.".format(len(red_flags))

    return SafetyReport(
        overall=overall,
        score=score,
        flags=flags,
        summary=summary,
        manufacturer_notes=manufacturer_notes,
    )