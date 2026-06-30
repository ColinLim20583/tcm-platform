"""
Chemigran Vendor Document Review  v1.0
RAG-based validation of vendor labels against HSA CPM GL-CHPB-4-001 (Jan 2025)

Two label streams:
  - Country of Origin labels  (vendor sends → must reflect actual retail label)
  - Singapore Sale labels     (Chemigran design → full English, NO Hanyu Pinyin)
"""

import re
import json
import sqlite3
import base64
import io
from datetime import datetime
from pathlib import Path
import anthropic

# ─── HSA RULES ────────────────────────────────────────────────────────────────

# §5.6: 19 prohibited disease/condition claims
PROHIBITED_CLAIMS = [
    "blindness", "cancer", "cataract", "drug addiction", "deafness",
    "diabetes", "epilepsy", "fits", "hypertension", "insanity",
    "kidney disease", "kidney diseases", "leprosy", "menstrual disorder",
    "paralysis", "tuberculosis", "sexual function", "infertility",
    "impotency", "frigidity", "conception", "pregnancy",
]

# Hanyu Pinyin tone-diacritic characters (not present in Chinese or plain EN)
PINYIN_RE = re.compile(
    r'[āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜĀÁǍÀĒÉĚÈĪÍǏÌŌÓǑÒŪÚǓÙǕǗǙǛ]'
)

# Full HSA submission checklist — 17 items from TCM Registration Excel (HSA Requirement sheet)
# mandatory = "Yes" | "Conditional"
SUBMISSION_CHECKLIST = [
    {
        "id": 1,
        "item": "Labels of the product sold/supplied in the country of manufacture (swatches + dimensions)",
        "form": "—",
        "mandatory": "Yes",
        "category": "Origin Labels",
        "remarks": "Must reflect actual retail/supply label used in country of origin",
    },
    {
        "id": 2,
        "item": "Photograph of product content",
        "form": "—",
        "mandatory": "Yes",
        "category": "Photos",
        "remarks": "Clear photo of physical form (powder, liquid, capsule, etc.). Contrasting background. Capsule/sachet contents poured out. Tablets cut in half.",
    },
    {
        "id": 3,
        "item": "Manufacturer licence or certificate",
        "form": "—",
        "mandatory": "Yes",
        "category": "Certificates",
        "remarks": "Valid licence issued by relevant authority in country of manufacture",
    },
    {
        "id": 4,
        "item": "Good Manufacturing Practice (GMP) certificate",
        "form": "GMP Cert",
        "mandatory": "Yes",
        "category": "Certificates",
        "remarks": "Must be current and issued by a recognised certifying body",
    },
    {
        "id": 5,
        "item": "Product registration certificate",
        "form": "—",
        "mandatory": "Yes",
        "category": "Certificates",
        "remarks": "Registration with relevant national health / regulatory authority",
    },
    {
        "id": 6,
        "item": "Test results — Toxic heavy metals & microbial limits",
        "form": "Lab Report",
        "mandatory": "Yes",
        "category": "Test Results",
        "remarks": "See Limits sheet: As ≤5ppm, Cd ≤0.3ppm, Pb ≤10ppm, Hg ≤0.5ppm. TAMC ≤10⁵ CFU/g (oral). No E.coli / Salmonella / Staph aureus.",
    },
    {
        "id": 7,
        "item": "Test results — DEG & EG (oral liquid products only)",
        "form": "Lab Report",
        "mandatory": "Conditional",
        "category": "Test Results",
        "remarks": "Required only if product is in oral liquid form. DEG ≤1000ppm, EG ≤1000ppm.",
    },
    {
        "id": 8,
        "item": "Manufacturing process (procedure and flow chart)",
        "form": "—",
        "mandatory": "Yes",
        "category": "Quality Docs",
        "remarks": "Must include step-by-step SOP and a process flow diagram",
    },
    {
        "id": 9,
        "item": "General quality parameters information",
        "form": "CPMF13-4A",
        "mandatory": "Yes",
        "category": "Quality Docs",
        "remarks": "Complete and submit using prescribed form CPMF13-4A (storage conditions, physical characteristics, physical specs)",
    },
    {
        "id": 10,
        "item": "Finished product specification",
        "form": "—",
        "mandatory": "Yes",
        "category": "Quality Docs",
        "remarks": "Full CoA / spec sheet covering all quality parameters for the dosage form",
    },
    {
        "id": 11,
        "item": "Endorsement of product formula",
        "form": "—",
        "mandatory": "Yes",
        "category": "Undertakings",
        "remarks": "Signed endorsement by overseas manufacturer confirming formula authenticity and accuracy (all active + inactive ingredients)",
    },
    {
        "id": 12,
        "item": "Declaration — product does not contain any western medication",
        "form": "Statutory Declaration",
        "mandatory": "Yes",
        "category": "Undertakings",
        "remarks": "Signed declaration on company letterhead or notarised. No synthetic drugs or active synthetic substances.",
    },
    {
        "id": 13,
        "item": "Legal classification of product",
        "form": "CPMF5-3",
        "mandatory": "Yes",
        "category": "Undertakings",
        "remarks": "Classify product using prescribed form CPMF5-3 (forensic classification in each country of sale)",
    },
    {
        "id": 14,
        "item": "Website address undertaking",
        "form": "CPMF6-4",
        "mandatory": "Yes",
        "category": "Undertakings",
        "remarks": "Provide official website URL using prescribed form CPMF6-4 (required if website/QR code on label)",
    },
    {
        "id": 15,
        "item": "Product containing material — full ingredient list",
        "form": "CPMf9-6",
        "mandatory": "Yes",
        "category": "Undertakings",
        "remarks": "Full list of all ingredients/raw materials using form CPMf9-6 (TSE undertaking for ruminant-derived materials)",
    },
    {
        "id": 16,
        "item": "Information on fermented substance(s) in product",
        "form": "CPMF11-5",
        "mandatory": "Conditional",
        "category": "Undertakings",
        "remarks": "Required ONLY if product contains any fermented ingredient (e.g. Cordyceps, Red Yeast Rice); use CPMF11-5",
    },
    {
        "id": 17,
        "item": "Product leaflet / package insert",
        "form": "—",
        "mandatory": "Yes",
        "category": "SG Labels",
        "remarks": "Must match approved label; include usage, dosage, precautions, contraindications, side effects",
    },
]

LABEL_TYPES = {
    "sg_inner":     "Singapore Sale — Inner Label",
    "sg_outer":     "Singapore Sale — Outer Label / Carton",
    "sg_insert":    "Singapore Sale — Package Insert",
    "origin_inner": "Country of Origin — Inner Label",
    "origin_outer": "Country of Origin — Outer Label / Carton",
}

# Map uploaded label type → which checklist item(s) it satisfies
LABEL_CHECKLIST_MAP = {
    "sg_inner":     [],         # SG labels are tracked separately
    "sg_outer":     [],
    "sg_insert":    [17],       # Package insert = item 17
    "origin_inner": [1],        # Country of origin label = item 1
    "origin_outer": [1],
}

# ─── LIMITS REFERENCE (from TCM Registration Excel — Limit sheet) ─────────────

HEAVY_METAL_LIMITS = {
    "Arsenic (As) 砷":              {"limit": 5,    "unit": "ppm (mg/kg)", "operator": "≤"},
    "Cadmium (Cd) 镉":              {"limit": 0.3,  "unit": "ppm (mg/kg)", "operator": "≤"},
    "Lead (Pb) 铅":                  {"limit": 10,   "unit": "ppm (mg/kg)", "operator": "≤"},
    "Mercury (Hg) 汞":              {"limit": 0.5,  "unit": "ppm (mg/kg)", "operator": "≤"},
    "Chromium (Cr) 铬 (capsule gelatin only)": {"limit": 2, "unit": "ppm", "operator": "≤", "note": "Capsule gelatin only"},
}

MICROBIAL_LIMITS = {
    "Total Aerobic Microbial Count (TAMC) — Oral":    {"limit": "≤ 1×10⁵", "unit": "CFU/g or ml"},
    "Total Aerobic Microbial Count (TAMC) — Topical": {"limit": "≤ 1×10⁴", "unit": "CFU/g or ml"},
    "Total Yeast & Mould Count (TYMC)":               {"limit": "≤ 5×10²",  "unit": "CFU/g"},
    "Escherichia coli 大肠埃希菌 (Oral)":              {"limit": "Absent",   "unit": "in 1 g or ml"},
    "Salmonella spp. 沙门菌":                          {"limit": "Absent",   "unit": "in 10 g or ml"},
    "Staphylococcus aureus 金黄色葡萄球菌 (Oral)":     {"limit": "Absent",   "unit": "in 1 g or ml"},
    "Pseudomonas aeruginosa (Topical)":                {"limit": "Absent",   "unit": "in 10 g or ml"},
    "Staphylococcus aureus 金黄色葡萄球菌 (Topical)":  {"limit": "Absent",   "unit": "in 1 g or ml"},
}

DEG_EG_LIMITS = {
    "Diethylene Glycol (DEG) 二甘醇": {"limit": 1000, "unit": "ppm (mg/kg)", "operator": "≤", "note": "Oral liquids only"},
    "Ethylene Glycol (EG) 乙二醇":    {"limit": 1000, "unit": "ppm (mg/kg)", "operator": "≤", "note": "Oral liquids only"},
}

VITAMIN_MINERAL_LIMITS = {
    "Biotin":                    "0.9 mg/day",
    "Folic Acid":                "0.9 mg/day",
    "Nicotinic Acid":            "15 mg/day",
    "Vitamin A (retinol)":       "1.5 mg/day (5000 IU)",
    "Vitamin B1":                "100 mg/day",
    "Vitamin B2":                "40 mg/day",
    "Vitamin B5 (Pantothenic)":  "200 mg/day",
    "Vitamin B6":                "100 mg/day",
    "Vitamin B12":               "0.6 mg/day",
    "Vitamin C":                 "1000 mg/day",
    "Vitamin D":                 "0.025 mg/day (1000 IU)",
    "Vitamin E":                 "536 mg/day (800 IU)",
    "Vitamin K1/K2":             "0.12 mg/day",
    "Boron":                     "6.4 mg/day",
    "Calcium":                   "1200 mg/day",
    "Chromium":                  "0.5 mg/day",
    "Copper":                    "2 mg/day",
    "Iodine":                    "0.15 mg/day",
    "Iron":                      "15 mg/day (30 mg/day for pregnant women multivitamin)",
    "Magnesium":                 "350 mg/day",
    "Manganese":                 "3.5 mg/day",
    "Molybdenum":                "0.36 mg/day",
    "Phosphorus":                "800 mg/day",
    "Selenium":                  "0.2 mg/day",
    "Zinc":                      "15 mg/day",
}

# ─── DATABASE ─────────────────────────────────────────────────────────────────

DB_PATH = Path(__file__).parent / "tcm_knowledge.db"


def _conn():
    return sqlite3.connect(str(DB_PATH))


def init_vendor_tables():
    """Create vendor review tables if they don't exist.
    Also ensures the core formulations table exists so get_all_product_names()
    never fails with 'no such table' even on a fresh database.
    """
    with _conn() as con:
        # Ensure core formulations table exists (created by database.py init_db,
        # but guard here in case init order changes on Streamlit Cloud)
        con.execute("""
            CREATE TABLE IF NOT EXISTS formulations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL DEFAULT '',
                session_name TEXT,
                product_name_en TEXT,
                product_name_zh TEXT,
                formula_json TEXT,
                rationale TEXT,
                safety_json TEXT,
                evidence TEXT,
                commercial_json TEXT,
                dosage TEXT,
                starred INTEGER DEFAULT 0
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS vendor_docs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id   TEXT NOT NULL,
                product_name TEXT NOT NULL,
                doc_type     TEXT NOT NULL,
                filename     TEXT NOT NULL,
                extracted_text TEXT,
                ai_findings  TEXT,
                overall      TEXT DEFAULT 'PENDING',
                created_at   TEXT DEFAULT (datetime('now'))
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS submission_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id  TEXT NOT NULL,
                checklist_id INTEGER NOT NULL,
                status      TEXT DEFAULT 'PENDING',
                notes       TEXT,
                updated_at  TEXT DEFAULT (datetime('now')),
                UNIQUE(product_id, checklist_id)
            )
        """)
        con.commit()


def save_vendor_doc(product_id, product_name, doc_type, filename, extracted_text, ai_findings, overall):
    with _conn() as con:
        con.execute("""
            INSERT INTO vendor_docs
              (product_id, product_name, doc_type, filename, extracted_text, ai_findings, overall)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (product_id, product_name, doc_type, filename,
              extracted_text, json.dumps(ai_findings), overall))
        con.commit()


def get_vendor_docs(product_id):
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM vendor_docs WHERE product_id=? ORDER BY created_at DESC",
            (product_id,)
        ).fetchall()
        cols = [d[0] for d in con.execute("SELECT * FROM vendor_docs LIMIT 0").description or
                [("id",),("product_id",),("product_name",),("doc_type",),("filename",),
                 ("extracted_text",),("ai_findings",),("overall",),("created_at",)]]
    return [dict(zip(cols, r)) for r in rows]


def upsert_checklist_status(product_id, checklist_id, status, notes=""):
    with _conn() as con:
        con.execute("""
            INSERT INTO submission_status (product_id, checklist_id, status, notes, updated_at)
            VALUES (?, ?, ?, ?, datetime('now'))
            ON CONFLICT(product_id, checklist_id) DO UPDATE SET
                status=excluded.status, notes=excluded.notes, updated_at=excluded.updated_at
        """, (product_id, checklist_id, status, notes))
        con.commit()


def get_checklist_status(product_id):
    with _conn() as con:
        rows = con.execute(
            "SELECT checklist_id, status, notes FROM submission_status WHERE product_id=?",
            (product_id,)
        ).fetchall()
    return {r[0]: {"status": r[1], "notes": r[2]} for r in rows}


def get_all_product_names():
    """Return list of (product_id, product_name) from saved formulations."""
    with _conn() as con:
        rows = con.execute(
            "SELECT id, product_name_en, product_name_zh FROM formulations ORDER BY created_at DESC"
        ).fetchall()
    return [(str(r[0]), f"{r[1]} {r[2]}".strip()) for r in rows]


# ─── RULE-BASED CHECKS ────────────────────────────────────────────────────────

def has_pinyin(text: str) -> bool:
    """Detect Hanyu Pinyin tone marks. Returns True if found (FAIL for SG labels)."""
    return bool(PINYIN_RE.search(text))


def check_prohibited_claims(text: str) -> list:
    """Return list of prohibited disease claims found in text (should be empty)."""
    text_lower = text.lower()
    return [c for c in PROHIBITED_CLAIMS if c in text_lower]


# ─── AI ANALYSIS ──────────────────────────────────────────────────────────────

_SYSTEM = """You are a Singapore HSA CPM regulatory compliance reviewer.
You validate product labels against GL-CHPB-4-001 (January 2025).
Respond ONLY with valid JSON — no markdown, no preamble."""


def _hsa_prompt(label_desc: str, product_name: str, content_block) -> str:
    is_sg = label_desc.startswith("Singapore")
    is_outer = "Outer" in label_desc
    is_insert = "Insert" in label_desc

    checks = """
Check these fields and return true/false/null (null = cannot determine):
{
  "trade_brand_name": true/false/null,
  "product_name_present": true/false/null,
  "batch_number_field": true/false/null,
  "expiry_date_field": true/false/null,
  "ingredients_with_quantities": true/false/null,"""

    if is_sg:
        checks += """
  "full_english_present": true/false/null,
  "has_hanyu_pinyin": true/false/null,
  "prohibited_claims_found": ["list any of: cancer, diabetes, hypertension, kidney disease, epilepsy, blindness, tuberculosis, pregnancy, infertility, impotency, etc"],"""

    if is_sg and is_outer:
        checks += """
  "importer_wholesaler_name_address": true/false/null,
  "manufacturer_name_address": true/false/null,
  "hsa_statement_english": true/false/null,
  "hsa_statement_chinese": true/false/null,
  "hsa_statement_boxed_area": true/false/null,"""

    if is_sg and is_insert:
        checks += """
  "dosage_present": true/false/null,
  "indication_present": true/false/null,
  "contraindication_present": true/false/null,
  "side_effects_present": true/false/null,
  "admin_frequency_method": true/false/null,"""

    if not is_sg:
        checks += """
  "reflects_actual_retail_label": true/false/null,
  "manufacturer_name_address": true/false/null,"""

    checks += """
  "extracted_text": "paste key visible text from the label",
  "label_dimensions": "if visible e.g. 121x42mm",
  "overall_assessment": "PASS" or "FAIL" or "INCOMPLETE",
  "missing_items": ["list of missing required fields"],
  "flags": ["specific compliance issues found"],
  "notes": "other observations"
}"""
    return checks


def analyze_label_image(image_bytes: bytes, ext: str, label_type: str, product_name: str, api_key: str) -> dict:
    """Analyze a label image using Claude vision (supports jpg, png, webp, gif)."""
    client = anthropic.Anthropic(api_key=api_key)
    label_desc = LABEL_TYPES.get(label_type, label_type)

    media_map = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
                 "gif": "image/gif", "webp": "image/webp"}
    media_type = media_map.get(ext.lower(), "image/jpeg")
    b64 = base64.standard_b64encode(image_bytes).decode("utf-8")

    prompt = f"""Analyze this {label_desc} image for product "{product_name}" against HSA GL-CHPB-4-001.

{_hsa_prompt(label_desc, product_name, None)}"""

    try:
        resp = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1500,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": b64,
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            }],
        )
        raw = resp.content[0].text.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw)
    except json.JSONDecodeError as e:
        return {
            "overall_assessment": "INCOMPLETE",
            "flags": [f"AI response not parseable: {e}"],
            "missing_items": [],
            "extracted_text": raw[:500] if "raw" in dir() else "",
            "notes": "JSON parse error from vision model.",
        }
    except Exception as e:
        return {
            "overall_assessment": "INCOMPLETE",
            "flags": [f"Vision API error: {e}"],
            "missing_items": [],
            "extracted_text": "",
            "notes": str(e),
        }


def analyze_label_text(text: str, label_type: str, product_name: str, api_key: str) -> dict:
    """Analyze extracted label text using Claude Haiku (faster, cheaper for text)."""
    client = anthropic.Anthropic(api_key=api_key)
    label_desc = LABEL_TYPES.get(label_type, label_type)

    prompt = f"""You are validating a {label_desc} for product "{product_name}" against HSA GL-CHPB-4-001.

LABEL TEXT:
{text[:4000]}

{_hsa_prompt(label_desc, product_name, text)}"""

    try:
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1200,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = resp.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw)
    except json.JSONDecodeError as e:
        return {
            "overall_assessment": "INCOMPLETE",
            "flags": [f"AI response not parseable: {e}"],
            "missing_items": [],
            "extracted_text": text[:500],
            "notes": "JSON parse error from text model.",
        }
    except Exception as e:
        return {
            "overall_assessment": "INCOMPLETE",
            "flags": [f"Text API error: {e}"],
            "missing_items": [],
            "extracted_text": text[:500],
            "notes": str(e),
        }


# ─── TEST RESULT VALIDATOR ────────────────────────────────────────────────────

def validate_heavy_metals(results: dict) -> list:
    """Validate {metal_name: value_ppm} against HSA limits. Returns list of result dicts."""
    limits_map = {
        "arsenic":  ("Arsenic (As) 砷",  5,    "ppm"),
        "as":       ("Arsenic (As) 砷",  5,    "ppm"),
        "cadmium":  ("Cadmium (Cd) 镉",  0.3,  "ppm"),
        "cd":       ("Cadmium (Cd) 镉",  0.3,  "ppm"),
        "lead":     ("Lead (Pb) 铅",     10,   "ppm"),
        "pb":       ("Lead (Pb) 铅",     10,   "ppm"),
        "mercury":  ("Mercury (Hg) 汞",  0.5,  "ppm"),
        "hg":       ("Mercury (Hg) 汞",  0.5,  "ppm"),
        "chromium": ("Chromium (Cr) 铬", 2,    "ppm"),
        "cr":       ("Chromium (Cr) 铬", 2,    "ppm"),
    }
    rows = []
    for k, v in results.items():
        key = k.lower().strip()
        if key in limits_map:
            name, limit, unit = limits_map[key]
            try:
                val = float(v)
                ok = val <= limit
                rows.append({
                    "metal": name, "value": val, "limit": limit, "unit": unit,
                    "status": "PASS" if ok else "FAIL",
                    "note": "" if ok else f"{val} exceeds limit of {limit} {unit}",
                })
            except (ValueError, TypeError):
                rows.append({
                    "metal": name, "value": v, "limit": limit, "unit": unit,
                    "status": "N/A", "note": "Non-numeric value",
                })
    return rows


def validate_deg_eg(results: dict) -> list:
    """Validate DEG/EG values against 1000 ppm limit (oral liquids only)."""
    limits_map = {
        "deg":               ("Diethylene Glycol (DEG)", 1000, "ppm"),
        "diethylene glycol": ("Diethylene Glycol (DEG)", 1000, "ppm"),
        "eg":                ("Ethylene Glycol (EG)",    1000, "ppm"),
        "ethylene glycol":   ("Ethylene Glycol (EG)",    1000, "ppm"),
    }
    rows = []
    for k, v in results.items():
        key = k.lower().strip()
        if key in limits_map:
            name, limit, unit = limits_map[key]
            try:
                val = float(v)
                ok = val <= limit
                rows.append({
                    "parameter": name, "value": val, "limit": limit, "unit": unit,
                    "status": "PASS" if ok else "FAIL",
                    "note": "" if ok else f"{val} exceeds limit of {limit} {unit}",
                })
            except (ValueError, TypeError):
                rows.append({
                    "parameter": name, "value": v, "limit": limit, "unit": unit,
                    "status": "N/A", "note": "Non-numeric value",
                })
    return rows


# ─── PDF TEXT EXTRACTION ──────────────────────────────────────────────────────

def extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extract text from PDF bytes; tries pdfplumber first, pypdf as fallback.
    Returns empty string for scanned PDFs (no selectable text).
    """
    try:
        import pdfplumber, io as _io
        with pdfplumber.open(_io.BytesIO(pdf_bytes)) as pdf:
            text = "\n".join(p.extract_text() or "" for p in pdf.pages).strip()
            if text:
                return text
    except ImportError:
        pass
    except Exception:
        pass
    try:
        from pypdf import PdfReader
        import io as _io
        reader = PdfReader(_io.BytesIO(pdf_bytes))
        text = "\n".join(page.extract_text() or "" for page in reader.pages).strip()
        if text:
            return text
    except ImportError:
        pass
    except Exception:
        pass
    # Return empty string so caller knows to prompt for image upload instead
    return ""


# ─── COMPLIANCE ROW BUILDER ───────────────────────────────────────────────────

_FIELD_LABELS = {
    "product_name_present":         "Product name present",
    "manufacturer_name_address":    "Manufacturer name & address",
    "net_quantity":                 "Net quantity / weight",
    "ingredient_list":              "Ingredient list",
    "dosage_instructions":          "Dosage / directions for use",
    "contraindication_present":     "Contraindications / warnings",
    "side_effects_present":         "Side effects",
    "admin_frequency_method":       "Administration frequency & method",
    "english_only":                 "English only (no Hanyu Pinyin)",
    "chinese_name_present":         "Chinese name present",
    "hsa_advisory_statement":       "HSA advisory statement",
    "batch_no_expiry":              "Batch number & expiry date",
    "storage_instructions":         "Storage instructions",
    "no_prohibited_claims":         "No prohibited disease claims",
    "reflects_actual_retail_label": "Reflects actual retail label (origin)",
    "registration_no":              "Product registration / licence number",
}


def build_compliance_rows(label_type: str, findings: dict) -> list:
    """Build a list of {field, status, note} dicts for display in the compliance panel."""
    rows = []
    for field, label in _FIELD_LABELS.items():
        if field == "reflects_actual_retail_label" and not label_type.startswith("origin"):
            rows.append({"field": label, "status": "N/A", "note": "Origin labels only"})
            continue
        if field == "english_only" and label_type.startswith("origin"):
            rows.append({"field": label, "status": "N/A", "note": "SG labels only"})
            continue
        val = findings.get(field)
        if val is True:
            status = "PASS"
        elif val is False:
            status = "FAIL"
        else:
            status = "N/A"
        rows.append({"field": label, "status": status, "note": ""})
    return rows