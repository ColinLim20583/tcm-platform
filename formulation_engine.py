import anthropic
import json
import re
from inventory_data import filter_herbs_by_condition, format_herb_list_for_prompt

SYSTEM_PROMPT = """You are ChemiGranAI — an expert TCM formulation scientist, nutraceutical product developer, and evidence-based medicine researcher embedded in Chemigran Pte Ltd's product development platform.

Your role:
1. Generate evidence-informed TCM formulations using ONLY herbs from the provided Chemigran inventory
2. Follow classical TCM formula structure: Jun (Chief), Chen (Deputy), Zuo (Assistant), Shi (Envoy)
3. Ensure herb compatibility and safety — flag contraindications clearly
4. Provide real, citable clinical evidence for key herbs
5. Give commercial assessments calibrated for Singapore/SEA market
6. Think simultaneously as a TCM physician AND a product strategist

RULES:
- NEVER invent or suggest herbs not in the inventory
- All percentages in the formula MUST sum to exactly 100%
- Always output valid JSON exactly matching the schema requested
- Cite real research (PubMed, clinical trials) where possible
- Safety warnings must be practical and regulatory-aware (Singapore HSA)"""


def generate_formulation(user_input: dict, api_key: str) -> dict:
    client = anthropic.Anthropic(api_key=api_key)

    condition = user_input.get("condition", "")
    tcm_pattern = user_input.get("tcm_pattern", "")
    demographic = user_input.get("demographic", "")
    preferences = user_input.get("preferences", "")
    format_type = user_input.get("format", "granule blend")
    avoid = user_input.get("avoid_herbs", "")

    search_text = f"{condition} {tcm_pattern} {preferences}"
    relevant_herbs = filter_herbs_by_condition(search_text, max_herbs=80)
    herb_list = format_herb_list_for_prompt(relevant_herbs)

    prompt = f"""Generate a complete TCM granule formulation for the following profile.

=== PATIENT / PRODUCT PROFILE ===
Health Condition / Symptoms: {condition}
TCM Pattern: {tcm_pattern if tcm_pattern else "Determine based on condition"}
Target Demographic: {demographic}
Product Format: {format_type}
Special Requirements: {preferences}
Herbs to Avoid: {avoid if avoid else "None"}

=== AVAILABLE CHEMIGRAN INVENTORY (use ONLY these herbs) ===
{herb_list}

=== OUTPUT SCHEMA ===
Respond ONLY with a single valid JSON object matching this exact schema:

{{
  "product_name_en": "English product name",
  "product_name_zh": "中文产品名称",
  "tcm_pattern": "Full TCM pattern name in English and Chinese",
  "pattern_explanation": "2-3 sentence explanation of the TCM pattern and why it fits this condition",
  "formula": [
    {{
      "chinese": "中文名",
      "pinyin": "Pīn Yīn",
      "english": "English herb name",
      "role": "Jun",
      "role_name": "Chief",
      "percentage": 25,
      "tcm_function": "Primary TCM function in this formula",
      "evidence": "Brief evidence note or clinical reference"
    }}
  ],
  "formula_rationale": "Comprehensive explanation of the formula logic (Jun/Chen/Zuo/Shi roles and how they work together)",
  "jun_rationale": "Why the Jun herb was chosen",
  "chen_rationale": "Why the Chen herbs were chosen",
  "zuo_rationale": "Why the Zuo herbs were chosen",
  "shi_rationale": "Why the Shi herb was chosen",
  "formula_complexity": "Very low — N herbs / Low — N herbs / Medium — N herbs / High — N herbs",
  "gross_margin_est": "XX-XX%",
  "suggested_price_sgd": "SGD XX-XX per 30-day pack",
  "safety": {{
    "overall_rating": "Safe / Use with caution / Specialist supervision recommended",
    "contraindications": ["list of contraindications"],
    "pregnancy_notes": "pregnancy safety note",
    "drug_interactions": ["list of drug interactions"],
    "regulatory_notes": "Singapore HSA classification and labelling notes",
    "notes": "Any other safety notes"
  }},
  "evidence_summary": "2-3 paragraph summary of clinical evidence supporting key herbs in this formula",
  "clinical_references": [
    "Author et al. (Year). Title. Journal. PMID or DOI."
  ],
  "commercial": {{
    "target_market": "Description of target customer",
    "usp": "Unique selling proposition",
    "positioning": "Product positioning statement",
    "market_demand_score": 8,
    "margin_potential_score": 7,
    "repeat_purchase_score": 9,
    "competitive_gap": "Description of competitive advantage and gap in market",
    "channel_recommendation": "Recommended distribution channels"
  }},
  "dosage_recommendation": "e.g. 5g twice daily dissolved in warm water, before meals",
  "manufacturing_notes": "Notes on manufacturing complexity, mixing order, etc.",
  "tags": ["Sleep", "Stress", "Women's Health"]
}}

CRITICAL: All formula percentages must sum to exactly 100. Use only herbs from the inventory."""

    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=8192,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = response.content[0].text.strip()

    # Extract JSON robustly — stops at first complete object (handles trailing text)
    start = raw.find('{')
    if start == -1:
        raise ValueError("No valid JSON found in response")
    result, _ = json.JSONDecoder().raw_decode(raw, start)

    # Validate percentages sum to 100
    total_pct = sum(h.get("percentage", 0) for h in result.get("formula", []))
    if abs(total_pct - 100) > 2:
        result["_warning"] = f"Percentages sum to {total_pct}% — may need adjustment"

    return result


def generate_business_case(product_name: str, formula_data: dict, api_key: str) -> str:
    client = anthropic.Anthropic(api_key=api_key)
    commercial = formula_data.get("commercial", {})
    herbs = formula_data.get("formula", [])
    herb_names = ", ".join(h.get("english", h.get("chinese", "")) for h in herbs)

    prompt = f"""Write a detailed business case for the following TCM granule product targeting Singapore market.

PRODUCT: {product_name} ({formula_data.get('product_name_zh','')})
TCM PATTERN: {formula_data.get('tcm_pattern','')}
KEY HERBS: {herb_names}
GROSS MARGIN EST: {formula_data.get('gross_margin_est','')}
SUGGESTED PRICE: {formula_data.get('suggested_price_sgd','')}
USP: {commercial.get('usp','')}
COMPETITIVE GAP: {commercial.get('competitive_gap','')}

Provide a structured business case covering:
1. Executive Summary (2-3 sentences)
2. Market Opportunity (Singapore TCM market context, target segment size)
3. Product Differentiation (vs existing products)
4. Revenue Model (price, volume assumptions, margin)
5. Go-to-Market Strategy (channels, launch sequence)
6. Risk Assessment (top 3 risks and mitigations)
7. 12-Month Revenue Projection (table format)
8. Investment Required (regulatory, marketing, inventory)
9. Recommendation (Go / No-Go with rationale)

Write in clear, professional business English. Be specific with numbers where possible."""

    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=3000,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text


def enrich_evidence(herb_chinese: str, condition: str, api_key: str) -> str:
    client = anthropic.Anthropic(api_key=api_key)
    prompt = f"""Provide a concise evidence summary for {herb_chinese} in the context of {condition}.
Include:
- Key clinical studies or systematic reviews (with PMID/DOI if known)
- Mechanism of action
- Effective dosage range (raw herb equivalent)
- Safety profile summary

Keep it under 300 words. Cite real published research only."""

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text