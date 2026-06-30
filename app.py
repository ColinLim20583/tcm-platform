"""
Chemigran TCM Formulation Intelligence Platform
Run: streamlit run app.py
"""

import streamlit as st
import pandas as pd
import json
from datetime import datetime

import database as db
from formulation_engine import generate_formulation, generate_business_case, enrich_evidence
from inventory_data import get_all_herbs, filter_herbs_by_condition
from safety_checker import check_formula_safety
from label_generator import generate_label
from config import APP_TITLE, APP_SUBTITLE, VERSION, COMPANY
import vendor_review as vr

# ─── PAGE CONFIG ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ChemiGran AI | TCM Formulation Platform",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CSS ─────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  /* Global */
  body, .stApp { background-color: #0f1923; color: #e2e8f0; }
  h1,h2,h3,h4 { color: #e2e8f0 !important; }

  /* Sidebar */
  [data-testid="stSidebar"] { background: #111d2b; border-right: 1px solid #1e3a52; }
  [data-testid="stSidebar"] * { color: #c9d8e8 !important; }

  /* Inputs */
  .stTextInput input, .stTextArea textarea, .stSelectbox select {
    background: #162334 !important; color: #e2e8f0 !important;
    border: 1px solid #2d4a6a !important; border-radius: 6px !important;
  }

  /* Product Card */
  .product-card {
    background: #162334; border: 1px solid #2d4a6a;
    border-radius: 12px; padding: 24px; margin-bottom: 20px;
  }
  .card-header {
    background: linear-gradient(135deg, #1a3a5c, #0f2744);
    border-radius: 10px 10px 0 0; padding: 18px 22px; margin: -24px -24px 20px -24px;
    border-bottom: 2px solid #2e5f8a;
  }
  .product-title { font-size: 22px; font-weight: 700; color: #7ec8e3; margin: 0; }
  .product-subtitle { font-size: 14px; color: #8aa5bf; margin-top: 4px; }
  .meta-row { display: flex; gap: 20px; margin: 14px 0; flex-wrap: wrap; }
  .meta-pill {
    background: #1e3a52; border: 1px solid #2d5a7a;
    border-radius: 6px; padding: 6px 14px; font-size: 13px; color: #a8c8e0;
  }
  .meta-pill span { color: #7ec8e3; font-weight: 600; }

  /* Herb Table */
  .herb-table { width: 100%; border-collapse: collapse; margin: 12px 0; }
  .herb-table th {
    background: #1a3a5c; color: #7ec8e3; font-size: 12px;
    text-transform: uppercase; letter-spacing: 0.05em;
    padding: 10px 14px; text-align: left; border-bottom: 2px solid #2d5a7a;
  }
  .herb-table td { padding: 10px 14px; font-size: 14px; border-bottom: 1px solid #1e3a52; color: #c9d8e8; }
  .herb-table tr:hover td { background: #1a3050; }
  .role-jun  { background:#7f1d1d; color:#fca5a5; padding:3px 10px; border-radius:4px; font-weight:700; font-size:12px; }
  .role-chen { background:#78350f; color:#fcd34d; padding:3px 10px; border-radius:4px; font-weight:700; font-size:12px; }
  .role-zuo  { background:#14532d; color:#86efac; padding:3px 10px; border-radius:4px; font-weight:700; font-size:12px; }
  .role-shi  { background:#1e3a5f; color:#93c5fd; padding:3px 10px; border-radius:4px; font-weight:700; font-size:12px; }
  .pct-badge { background:#1e3a52; color:#7ec8e3; padding:3px 10px; border-radius:4px; font-weight:700; font-size:13px; }

  /* Info Boxes */
  .info-box {
    border-radius: 8px; padding: 14px 18px; margin: 10px 0; font-size: 14px; line-height: 1.6;
  }
  .info-box.rationale { background:#1a2f1a; border-left: 3px solid #4ade80; color: #c9d8e8; }
  .info-box.safety    { background:#2a1f0e; border-left: 3px solid #fbbf24; color: #c9d8e8; }
  .info-box.gap       { background:#1a1f3a; border-left: 3px solid #818cf8; color: #c9d8e8; }
  .info-box.evidence  { background:#1a2535; border-left: 3px solid #38bdf8; color: #c9d8e8; }
  .info-box-label { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.07em; margin-bottom: 6px; }
  .info-box.rationale .info-box-label { color: #4ade80; }
  .info-box.safety    .info-box-label { color: #fbbf24; }
  .info-box.gap       .info-box-label { color: #818cf8; }
  .info-box.evidence  .info-box-label { color: #38bdf8; }

  /* Score badges */
  .score-grid { display: flex; gap: 12px; flex-wrap: wrap; margin: 10px 0; }
  .score-item { text-align: center; background: #1a3a5c; border-radius: 8px; padding: 10px 16px; min-width: 80px; }
  .score-val  { font-size: 22px; font-weight: 700; color: #7ec8e3; }
  .score-lbl  { font-size: 11px; color: #8aa5bf; margin-top: 2px; }

  /* CTA Button */
  .stButton > button {
    background: linear-gradient(135deg, #2563eb, #1d4ed8) !important;
    color: white !important; border: none !important; border-radius: 8px !important;
    padding: 10px 24px !important; font-weight: 600 !important; font-size: 14px !important;
    cursor: pointer !important;
  }
  .stButton > button:hover { background: linear-gradient(135deg, #1d4ed8, #1e40af) !important; }

  /* Divider */
  hr { border-color: #2d4a6a !important; margin: 16px 0; }

  /* Safety Report */
  .safety-banner { border-radius: 10px; padding: 18px 22px; margin: 16px 0; }
  .safety-banner.green  { background: #0d2b1a; border: 2px solid #22c55e; }
  .safety-banner.amber  { background: #2a1f0e; border: 2px solid #f59e0b; }
  .safety-banner.red    { background: #2a0e0e; border: 2px solid #ef4444; }
  .safety-banner .sb-title { font-size: 18px; font-weight: 700; margin-bottom: 6px; }
  .safety-banner.green  .sb-title { color: #22c55e; }
  .safety-banner.amber  .sb-title { color: #f59e0b; }
  .safety-banner.red    .sb-title { color: #ef4444; }
  .safety-banner .sb-summary { font-size: 14px; color: #c9d8e8; line-height: 1.5; }
  .safety-score-ring { display:inline-block; background:#1a3a5c; border-radius:50%;
    width:64px; height:64px; line-height:64px; text-align:center;
    font-size:22px; font-weight:800; color:#7ec8e3; margin-right:16px; float:left; }
  .flag-card { border-radius: 8px; padding: 12px 16px; margin: 8px 0; }
  .flag-card.RED   { background: #2a0e0e; border-left: 4px solid #ef4444; }
  .flag-card.AMBER { background: #2a1f0e; border-left: 4px solid #f59e0b; }
  .flag-card.INFO  { background: #1a2535; border-left: 4px solid #38bdf8; }
  .flag-cat  { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 4px; }
  .flag-card.RED   .flag-cat { color: #ef4444; }
  .flag-card.AMBER .flag-cat { color: #f59e0b; }
  .flag-card.INFO  .flag-cat { color: #38bdf8; }
  .flag-msg  { font-size: 13px; color: #c9d8e8; margin-bottom: 6px; }
  .flag-action { font-size: 12px; color: #8aa5bf; font-style: italic; }
  .flag-herbs { font-size: 12px; color: #7ec8e3; margin-bottom: 4px; }

  /* Knowledge base table */
  .kb-row {
    background: #162334; border: 1px solid #2d4a6a; border-radius: 8px;
    padding: 14px 18px; margin-bottom: 10px; cursor: pointer;
  }
  .kb-row:hover { border-color: #4a8ab5; }
  .kb-title { font-size: 15px; font-weight: 600; color: #7ec8e3; }
  .kb-meta  { font-size: 12px; color: #8aa5bf; margin-top: 4px; }
  .tag { background:#1e3a52; color:#7ec8e3; border-radius:4px; padding:2px 8px; font-size:11px; margin-right:4px; }
</style>
""", unsafe_allow_html=True)

# ─── PASSWORD GATE ────────────────────────────────────────────────────────────
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        st.markdown("<h2 style='color:#7ec8e3'>🌿 Chemigran TCM Platform</h2>", unsafe_allow_html=True)
        pwd = st.text_input("Enter password to access", type="password")
        if st.button("Login"):
            correct = st.secrets.get("APP_PASSWORD", "Chemigran#0606")
            if pwd == correct:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Incorrect password.")
        st.stop()

check_password()
# ─────────────────────────────────────────────────────────────────────────────

# ─── INIT ─────────────────────────────────────────────────────────────────────
db.init_db()
vr.init_vendor_tables()

# ─── SESSION STATE ─────────────────────────────────────────────────────────────
if "result" not in st.session_state:
    st.session_state.result = None
if "api_key" not in st.session_state:
    st.session_state.api_key = ""
if "generating" not in st.session_state:
    st.session_state.generating = False
if "business_case" not in st.session_state:
    st.session_state.business_case = ""
if "last_allergies" not in st.session_state:
    st.session_state.last_allergies = ""

# ─── SIDEBAR ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"### 🌿 {COMPANY}")
    st.markdown(f"*TCM Formulation AI Platform v{VERSION}*")
    st.divider()

    api_key = st.text_input(
        "Anthropic API Key",
        value=st.session_state.api_key,
        type="password",
        placeholder="sk-ant-...",
        help="Enter your Anthropic API key. Never stored — session only."
    )
    if api_key:
        st.session_state.api_key = api_key

    st.divider()
    stats = db.get_stats()
    st.markdown(f"**Knowledge Base**")
    st.markdown(f"📋 {stats['total']} formulations saved")
    st.markdown(f"⭐ {stats['starred']} starred")
    st.divider()
    st.markdown(f"**Inventory**")
    st.markdown(f"🌱 551 Chemigran granule SKUs")
    st.divider()
    st.markdown("*Singapore & Southeast Asia*")

# ─── HELPERS ─────────────────────────────────────────────────────────────────
def role_badge(role):
    role_map = {"Jun": "jun", "Chen": "chen", "Zuo": "zuo", "Shi": "shi"}
    cls = role_map.get(role, "shi")
    role_label = {"Jun":"Jun (Chief)","Chen":"Chen (Deputy)","Zuo":"Zuo (Asst.)","Shi":"Shi (Envoy)"}.get(role, role)
    return f'<span class="role-{cls}">{role_label}</span>'

def render_safety_report(result: dict, demographic: str = "", condition: str = "", known_allergies: str = ""):
    """Run and display the safety check for a generated formula."""
    formula = result.get("formula", [])
    if not formula:
        return

    report = check_formula_safety(
        formula=formula,
        demographic=demographic,
        condition=condition,
        dosage_recommendation=result.get("dosage_recommendation", ""),
        known_allergies=known_allergies,
    )

    overall = report.overall
    score = report.score
    banner_cls = overall.lower()
    icon = {"GREEN": "✅", "AMBER": "⚠️", "RED": "🚨"}.get(overall, "")
    label = {"GREEN": "SAFE TO PROCEED", "AMBER": "REVIEW REQUIRED", "RED": "DO NOT MANUFACTURE — CRITICAL ISSUES"}.get(overall, overall)

    st.markdown(f"""
    <div class="safety-banner {banner_cls}">
      <div style="overflow:hidden">
        <div class="safety-score-ring">{score}</div>
        <div class="sb-title">{icon} Safety Score: {score}/100 — {label}</div>
        <div class="sb-summary">{report.summary}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    red_flags = [f for f in report.flags if f.level == "RED"]
    amber_flags = [f for f in report.flags if f.level == "AMBER"]
    info_flags = [f for f in report.flags if f.level == "INFO"]

    if red_flags:
        st.markdown("#### 🚨 Critical Issues — Must Resolve Before Manufacturing")
        for flag in red_flags:
            herbs_str = " · ".join(flag.herbs_involved)
            st.markdown(f"""
            <div class="flag-card RED">
              <div class="flag-cat">{flag.category}</div>
              <div class="flag-herbs">Herb(s): {herbs_str}</div>
              <div class="flag-msg">{flag.message}</div>
              <div class="flag-action">Action: {flag.action}</div>
            </div>
            """, unsafe_allow_html=True)

    if amber_flags:
        st.markdown("#### ⚠️ Advisory — Address Before Submission")
        for flag in amber_flags:
            herbs_str = " · ".join(flag.herbs_involved)
            st.markdown(f"""
            <div class="flag-card AMBER">
              <div class="flag-cat">{flag.category}</div>
              <div class="flag-herbs">Herb(s): {herbs_str}</div>
              <div class="flag-msg">{flag.message}</div>
              <div class="flag-action">Action: {flag.action}</div>
            </div>
            """, unsafe_allow_html=True)

    if not red_flags and not amber_flags:
        st.markdown("""
        <div class="flag-card INFO">
          <div class="flag-cat">No incompatibilities or restricted substances detected</div>
          <div class="flag-msg">Standard QC testing and lab certificates still required for all CPM products.</div>
        </div>
        """, unsafe_allow_html=True)

    with st.expander("📋 Manufacturer Checklist (required for every batch)"):
        for note in report.manufacturer_notes:
            st.markdown(f"- {note}")

    st.caption(f"Safety check run: {datetime.now().strftime('%Y-%m-%d %H:%M')}  ·  Rules: TCM 十八反/十九畏, HSA CPM Guidelines GL-CHPB-4-001 (Jan 2025)")


def render_product_card(result: dict, show_business_btn: bool = True):
    commercial = result.get("commercial", {})
    formula = result.get("formula", [])
    safety = result.get("safety", {})
    n_herbs = len(formula)
    complexity = result.get("formula_complexity", f"Medium — {n_herbs} herbs")
    margin = result.get("gross_margin_est", "60-70%")
    price = result.get("suggested_price_sgd", "SGD 55-85")
    pattern = result.get("tcm_pattern", "")

    # Card header
    st.markdown(f"""
    <div class="product-card">
      <div class="card-header">
        <div class="product-title">{result.get('product_name_en','')} &nbsp; {result.get('product_name_zh','')}</div>
        <div class="product-subtitle">{pattern}</div>
      </div>
      <div class="meta-row">
        <div class="meta-pill">Gross margin est. <span>{margin}</span></div>
        <div class="meta-pill">Price <span>{price} / 30-day pack</span></div>
        <div class="meta-pill">Formula complexity <span>{complexity}</span></div>
        <div class="meta-pill">Market demand <span>{commercial.get('market_demand_score','–')}/10</span></div>
        <div class="meta-pill">Repeat purchase <span>{commercial.get('repeat_purchase_score','–')}/10</span></div>
      </div>
    """, unsafe_allow_html=True)

    # Herb table
    if formula:
        rows_html = ""
        for h in formula:
            rows_html += f"""
            <tr>
              <td><strong>{h.get('chinese','')}</strong></td>
              <td><em style="color:#8aa5bf">{h.get('pinyin','')}</em></td>
              <td>{h.get('english','')}</td>
              <td>{role_badge(h.get('role',''))}</td>
              <td><span class="pct-badge">{h.get('percentage',0)}%</span></td>
            </tr>"""

        st.markdown(f"""
        <table class="herb-table">
          <thead><tr>
            <th>Herb</th><th>Pinyin</th><th>English</th><th>Role</th><th>%</th>
          </tr></thead>
          <tbody>{rows_html}</tbody>
        </table>
        """, unsafe_allow_html=True)

    # Rationale
    rationale = result.get("formula_rationale", "")
    if rationale:
        st.markdown(f"""
        <div class="info-box rationale">
          <div class="info-box-label">Clinical &amp; commercial rationale</div>
          {rationale}
        </div>""", unsafe_allow_html=True)

    # Safety
    overall = safety.get("overall_rating", "")
    contra = safety.get("contraindications", [])
    interactions = safety.get("drug_interactions", [])
    reg = safety.get("regulatory_notes", "")
    safety_text = ""
    if overall: safety_text += f"<strong>{overall}.</strong> "
    if contra: safety_text += "Contraindications: " + "; ".join(contra) + ". "
    if interactions: safety_text += "Drug interactions: " + "; ".join(interactions) + ". "
    if reg: safety_text += reg

    if safety_text:
        st.markdown(f"""
        <div class="info-box safety">
          <div class="info-box-label">Safety &amp; regulatory</div>
          {safety_text}
        </div>""", unsafe_allow_html=True)

    # Competitive gap
    gap = commercial.get("competitive_gap", "")
    if gap:
        st.markdown(f"""
        <div class="info-box gap">
          <div class="info-box-label">Competitive gap</div>
          {gap}
        </div>""", unsafe_allow_html=True)

    # Evidence
    evidence = result.get("evidence_summary", "")
    if evidence:
        with st.expander("📚 Evidence summary & clinical references"):
            st.markdown(f"""
            <div class="info-box evidence">
              <div class="info-box-label">Evidence summary</div>
              {evidence}
            </div>""", unsafe_allow_html=True)
            refs = result.get("clinical_references", [])
            if refs:
                st.markdown("**References:**")
                for r in refs:
                    st.markdown(f"- {r}")

    # Jun/Chen/Zuo/Shi detail
    with st.expander("🧪 Formula rationale detail"):
        cols = st.columns(4)
        for col, (label, key, color) in zip(cols, [
            ("Jun (Chief)", "jun_rationale", "#fca5a5"),
            ("Chen (Deputy)", "chen_rationale", "#fcd34d"),
            ("Zuo (Assistant)", "zuo_rationale", "#86efac"),
            ("Shi (Envoy)", "shi_rationale", "#93c5fd"),
        ]):
            with col:
                st.markdown(f"<span style='color:{color};font-weight:700;font-size:13px'>{label}</span>", unsafe_allow_html=True)
                st.markdown(result.get(key, "—"), unsafe_allow_html=False)

    # Dosage & manufacturing
    with st.expander("⚗️ Dosage & manufacturing"):
        st.markdown(f"**Dosage:** {result.get('dosage_recommendation','—')}")
        st.markdown(f"**Manufacturing notes:** {result.get('manufacturing_notes','—')}")

    st.markdown("</div>", unsafe_allow_html=True)  # close product-card

    # Action buttons
    col1, col2, col3, col4 = st.columns([2, 2, 2, 4])
    with col1:
        if st.button("💾 Save to Knowledge Base", key="save_btn"):
            db.save_formulation({
                "condition_input": st.session_state.get("last_condition",""),
                "tcm_pattern": result.get("tcm_pattern",""),
                "demographic": st.session_state.get("last_demographic",""),
                "product_name_en": result.get("product_name_en",""),
                "product_name_zh": result.get("product_name_zh",""),
                "formula": result.get("formula",[]),
                "rationale": result.get("formula_rationale",""),
                "safety": result.get("safety",{}),
                "evidence": result.get("evidence_summary",""),
                "commercial": result.get("commercial",{}),
                "dosage": result.get("dosage_recommendation",""),
                "gross_margin_est": result.get("gross_margin_est",""),
                "formula_complexity": result.get("formula_complexity",""),
                "tags": result.get("tags",[]),
            })
            st.success("Saved to Knowledge Base!")

    with col2:
        if show_business_btn and st.button("📊 Ask AI: full business case ↗", key="biz_btn"):
            with st.spinner("Generating business case..."):
                st.session_state.business_case = generate_business_case(
                    result.get("product_name_en",""),
                    result,
                    st.session_state.api_key
                )

    with col3:
        # Export formula as CSV
        if formula:
            df = pd.DataFrame(formula)
            csv = df.to_csv(index=False)
            st.download_button("⬇️ Export formula CSV", csv,
                               file_name=f"{result.get('product_name_en','formula').replace(' ','_')}.csv",
                               mime="text/csv", key="dl_csv")

    # Business case result
    if st.session_state.business_case:
        st.markdown("---")
        st.markdown("### 📊 Full Business Case")
        st.markdown(st.session_state.business_case)


# ─── MAIN TABS ────────────────────────────────────────────────────────────────
st.markdown(f"<h1 style='color:#7ec8e3;margin-bottom:4px'>🌿 {APP_TITLE}</h1>", unsafe_allow_html=True)
st.markdown(f"<p style='color:#8aa5bf;margin-top:0'>{APP_SUBTITLE}</p>", unsafe_allow_html=True)
st.divider()

tab1, tab2, tab3, tab4, tab5 = st.tabs(["🧪 Formulation Generator", "📚 Knowledge Base", "🌱 Inventory Browser", "🔬 Evidence Enricher", "📋 Submission Review"])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — FORMULATION GENERATOR
# ═══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown("### New Formulation")
    st.markdown("*Powered by Claude AI · Constrained to Chemigran's 551-granule inventory*")

    col_left, col_right = st.columns([1, 1])

    with col_left:
        condition = st.text_area(
            "Health Condition / Symptoms *",
            placeholder="e.g. Chronic insomnia, difficulty falling asleep, waking at 3am, fatigue, anxiety...",
            height=100,
            help="Describe the health condition, symptoms, or therapeutic goal in plain language."
        )

        tcm_pattern = st.text_input(
            "TCM Pattern (optional — AI will determine if left blank)",
            placeholder="e.g. Heart and Spleen Deficiency, Liver Qi Stagnation...",
        )

        demographic = st.text_input(
            "Target Demographic",
            placeholder="e.g. Working women aged 30-45, Singapore professionals...",
        )

    with col_right:
        age_group = st.selectbox(
            "Age Group",
            ["All adults", "Young adults (18-35)", "Middle-aged (35-55)", "Seniors (55+)", "Children (adjusted dose)"]
        )

        preferences = st.text_area(
            "Special Requirements / Preferences",
            placeholder="e.g. Avoid animal products, maximum 7 herbs, focus on gentle formula, suitable for long-term use...",
            height=80,
        )

        avoid_herbs = st.text_input(
            "Herbs to Exclude (optional)",
            placeholder="e.g. 当归 (pregnancy concern), 大黄 (diarrhoea)...",
        )

        known_allergies = st.text_input(
            "Known Allergies / Sensitivities (optional)",
            placeholder="e.g. tree nuts, shellfish, honey, ragweed, latex, sulphites, soy...",
            help="Enter patient or target demographic's known allergies. The safety checker will flag herbs that may cross-react.",
        )

        focus_area = st.multiselect(
            "Focus Areas (helps AI select herbs)",
            ["Sleep", "Stress", "Gut Health", "Women's Wellness", "Healthy Aging",
             "Thyroid", "Immune Support", "Pain", "Skin", "Respiratory",
             "Men's Health", "Cognitive", "Cardiovascular"],
            default=[]
        )

    st.divider()

    generate_col, note_col = st.columns([1, 3])
    with generate_col:
        gen_btn = st.button("🔬 Generate Formula", type="primary", use_container_width=True)
    with note_col:
        st.markdown("<small style='color:#6b8ba4'>AI will select herbs from Chemigran's inventory, apply TCM theory, cite evidence, and provide safety + commercial assessment.</small>", unsafe_allow_html=True)

    if gen_btn:
        if not st.session_state.api_key:
            st.error("Please enter your Anthropic API key in the sidebar.")
        elif not condition.strip():
            st.warning("Please describe the health condition.")
        else:
            st.session_state.last_condition = condition
            st.session_state.last_demographic = demographic
            st.session_state.last_allergies = known_allergies
            st.session_state.business_case = ""

            focus_str = ", ".join(focus_area) if focus_area else ""
            user_input = {
                "condition": condition,
                "tcm_pattern": tcm_pattern,
                "demographic": f"{demographic} | {age_group}",
                "preferences": f"{preferences} | Focus: {focus_str}",
                "avoid_herbs": avoid_herbs,
            }

            with st.spinner("🤖 ChemiGran AI is formulating... analysing inventory, applying TCM theory, searching evidence..."):
                try:
                    result = generate_formulation(user_input, st.session_state.api_key)
                    st.session_state.result = result
                except Exception as e:
                    st.error(f"Generation error: {e}")
                    st.session_state.result = None

    if st.session_state.result:
        st.divider()

        # ── SAFETY CHECK (always shown first) ────────────────────────────────
        st.markdown("## 🛡️ Safety Validation")
        st.markdown("*Checked against: TCM 十八反/十九畏 classical rules · HSA CPM dosage limits · Pregnancy flags · CITES banned species · Herb–drug interactions*")
        render_safety_report(
            st.session_state.result,
            demographic=st.session_state.get("last_demographic", ""),
            condition=st.session_state.get("last_condition", ""),
            known_allergies=st.session_state.get("last_allergies", ""),
        )

        st.divider()

        # ── LABEL GENERATOR ──────────────────────────────────────────────────
        st.markdown("## 🏷️ Label Design")
        st.markdown("*Premium HSA CPM compliant · Bilingual EN/ZH · Color theme auto-selected · Opens in Adobe Illustrator*")
        lbl_col1, lbl_col2, lbl_col3, lbl_col4 = st.columns([2, 2, 2, 4])
        product_slug = st.session_state.result.get("product_name_en", "formula").replace(" ", "_")[:30]
        with lbl_col1:
            try:
                sachet_svg = generate_label(st.session_state.result, "sachet")
                st.download_button(
                    "📥 Sachet Label (40×120mm)",
                    data=sachet_svg,
                    file_name=f"{product_slug}_sachet_label.svg",
                    mime="image/svg+xml",
                    key="lbl_sachet",
                    help="Granule stick pack label with botanical art. Open in Adobe Illustrator."
                )
            except Exception as e:
                st.error(f"Sachet label error: {e}")
        with lbl_col2:
            try:
                inner_svg = generate_label(st.session_state.result, "inner")
                st.download_button(
                    "📥 Inner Label (121×42mm)",
                    data=inner_svg,
                    file_name=f"{product_slug}_inner_label.svg",
                    mime="image/svg+xml",
                    key="lbl_inner",
                    help="Two-panel bottle/jar inner label matching Chemigran standard. Open in Adobe Illustrator."
                )
            except Exception as e:
                st.error(f"Inner label error: {e}")
        with lbl_col3:
            try:
                box_svg = generate_label(st.session_state.result, "box")
                st.download_button(
                    "📥 Box Front (59×103mm)",
                    data=box_svg,
                    file_name=f"{product_slug}_box_label.svg",
                    mime="image/svg+xml",
                    key="lbl_box",
                    help="Retail box front panel with botanical art. Open in Adobe Illustrator."
                )
            except Exception as e:
                st.error(f"Box label error: {e}")
        with lbl_col4:
            st.caption(
                "SVG files open in Adobe Illustrator with correct mm dimensions. "
                "All text and shapes are fully editable. Replace [BATCH NO.], [EXP DATE] and "
                "[PENDING REGISTRATION] before printing. Labels include all HSA CPM mandatory fields."
            )
        # ─────────────────────────────────────────────────────────────────────

        st.divider()
        st.markdown("## 🌿 Generated Formulation")
        render_product_card(st.session_state.result)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — KNOWLEDGE BASE
# ═══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("### Knowledge Base")
    st.markdown("*All saved formulations. Click to expand details.*")

    kb_col1, kb_col2 = st.columns([3, 1])
    with kb_col1:
        search_q = st.text_input("🔍 Search formulations", placeholder="product name, condition, TCM pattern, tag...")
    with kb_col2:
        show_starred = st.checkbox("⭐ Starred only")

    if search_q:
        rows = db.search_formulations(search_q)
    else:
        rows = db.get_all_formulations()

    if show_starred:
        rows = [r for r in rows if r.get("starred")]

    if not rows:
        st.info("No saved formulations yet. Generate a formula in the Formulation Generator tab and save it.")
    else:
        st.markdown(f"**{len(rows)} formulation(s)**")
        for row in rows:
            formula_list = row.get("formula_json", [])
            if isinstance(formula_list, str):
                try: formula_list = json.loads(formula_list)
                except: formula_list = []

            tags = row.get("tags", [])
            if isinstance(tags, str):
                try: tags = json.loads(tags)
                except: tags = []

            tags_html = "".join(f'<span class="tag">{t}</span>' for t in (tags if isinstance(tags, list) else []))
            n_herbs = len(formula_list) if isinstance(formula_list, list) else "?"
            star = "⭐" if row.get("starred") else "☆"
            created = row.get("created_at","")[:16].replace("T"," ")

            with st.expander(f"{star} **{row.get('product_name_en','Unnamed')}**  {row.get('product_name_zh','')}  —  {created}"):
                st.markdown(f"**TCM Pattern:** {row.get('tcm_pattern','')}")
                st.markdown(f"**Condition:** {row.get('condition_input','')}")
                st.markdown(f"**Demographic:** {row.get('demographic','')}")
                st.markdown(f"**Gross Margin:** {row.get('gross_margin_est','')}  |  **Complexity:** {row.get('formula_complexity','')}")

                if tags_html:
                    st.markdown(tags_html, unsafe_allow_html=True)

                if isinstance(formula_list, list) and formula_list:
                    df = pd.DataFrame(formula_list)
                    display_cols = [c for c in ["chinese","pinyin","english","role","percentage","tcm_function"] if c in df.columns]
                    st.dataframe(df[display_cols], use_container_width=True, hide_index=True)

                commercial = row.get("commercial_json", {})
                if isinstance(commercial, dict):
                    st.markdown(f"**USP:** {commercial.get('usp','')}")
                    st.markdown(f"**Competitive Gap:** {commercial.get('competitive_gap','')}")

                rationale = row.get("rationale","")
                if rationale:
                    st.markdown(f"""
                    <div class="info-box rationale">
                      <div class="info-box-label">Formula Rationale</div>
                      {rationale}
                    </div>""", unsafe_allow_html=True)

                btn_col1, btn_col2, btn_col3 = st.columns(3)
                with btn_col1:
                    if st.button(f"{'⭐ Unstar' if row.get('starred') else '☆ Star'}", key=f"star_{row['id']}"):
                        db.toggle_star(row["id"]); st.rerun()
                with btn_col2:
                    if isinstance(formula_list, list) and formula_list:
                        df_export = pd.DataFrame(formula_list)
                        st.download_button("⬇️ Export CSV", df_export.to_csv(index=False),
                                           file_name=f"{row.get('product_name_en','formula')}.csv",
                                           mime="text/csv", key=f"dl_{row['id']}")
                with btn_col3:
                    if st.button("🗑️ Delete", key=f"del_{row['id']}"):
                        db.delete_formulation(row["id"]); st.rerun()

                if st.session_state.api_key and st.button("📊 Generate Business Case", key=f"biz_{row['id']}"):
                    formula_data = {
                        "tcm_pattern": row.get("tcm_pattern",""),
                        "product_name_zh": row.get("product_name_zh",""),
                        "formula": formula_list,
                        "gross_margin_est": row.get("gross_margin_est",""),
                        "suggested_price_sgd": "",
                        "commercial": commercial if isinstance(commercial,dict) else {},
                    }
                    with st.spinner("Generating business case..."):
                        bc = generate_business_case(row.get("product_name_en",""), formula_data, st.session_state.api_key)
                    st.markdown("---")
                    st.markdown("### 📊 Business Case")
                    st.markdown(bc)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — INVENTORY BROWSER
# ═══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown("### Chemigran Granule Inventory Browser")
    st.markdown("*551 SKUs. Search by name, filter by category.*")

    herbs = get_all_herbs()
    all_cats = sorted(set(c for h in herbs for c in h.get("categories", [])))

    inv_col1, inv_col2 = st.columns([2, 1])
    with inv_col1:
        search_herb = st.text_input("🔍 Search herbs", placeholder="Chinese name, English name, pinyin...")
    with inv_col2:
        cat_filter = st.multiselect("Filter by category", all_cats)

    filtered = herbs
    if search_herb:
        s = search_herb.lower()
        filtered = [h for h in filtered if
                    s in h.get("chinese","").lower() or
                    s in h.get("english","").lower() or
                    s in h.get("pinyin","").lower()]
    if cat_filter:
        filtered = [h for h in filtered if any(c in h.get("categories",[]) for c in cat_filter)]

    st.markdown(f"**{len(filtered)} herbs shown**")

    df_herbs = pd.DataFrame([{
        "ID": h["id"],
        "Chinese": h["chinese"],
        "Pinyin": h.get("pinyin",""),
        "English": h.get("english",""),
        "Extract Ratio": h["extract_ratio"],
        "Raw/g": h["raw_per_g"],
        "Categories": ", ".join(h.get("categories",[])),
        "TCM Functions": "; ".join(h.get("tcm_functions",[])[:2]),
        "Contraindications": "; ".join(h.get("contraindications",[])),
    } for h in filtered])

    st.dataframe(df_herbs, use_container_width=True, hide_index=True,
                 column_config={
                     "ID": st.column_config.NumberColumn(width="small"),
                     "Extract Ratio": st.column_config.NumberColumn(format="%.2f"),
                 })

    # Herb detail
    st.divider()
    st.markdown("#### Herb Detail")
    selected_chinese = st.selectbox("Select herb for details", options=[""] + [h["chinese"] for h in filtered])
    if selected_chinese:
        herb_data = next((h for h in herbs if h["chinese"] == selected_chinese), None)
        if herb_data:
            detail_col1, detail_col2 = st.columns(2)
            with detail_col1:
                st.markdown(f"**Chinese:** {herb_data['chinese']}")
                st.markdown(f"**Pinyin:** {herb_data.get('pinyin','')}")
                st.markdown(f"**English:** {herb_data.get('english','')}")
                st.markdown(f"**Extract Ratio:** {herb_data['extract_ratio']}:1")
                st.markdown(f"**Raw herb per gram of granule:** {herb_data['raw_per_g']}g")
            with detail_col2:
                cats = herb_data.get("categories", [])
                funcs = herb_data.get("tcm_functions", [])
                contras = herb_data.get("contraindications", [])
                st.markdown(f"**Categories:** {', '.join(cats)}")
                st.markdown("**TCM Functions:**")
                for f in funcs:
                    st.markdown(f"  - {f}")
                if contras:
                    st.markdown("**Contraindications:**")
                    for c in contras:
                        st.markdown(f"  ⚠️ {c}")

            if st.session_state.api_key:
                condition_for_evidence = st.text_input(f"Search evidence for {selected_chinese} in context of:", placeholder="e.g. insomnia, thyroid nodules...")
                if st.button("🔬 Enrich Evidence"):
                    with st.spinner("Searching clinical evidence..."):
                        ev = enrich_evidence(selected_chinese, condition_for_evidence, st.session_state.api_key)
                    st.markdown(f"""<div class="info-box evidence">
                    <div class="info-box-label">Evidence Summary</div>{ev}</div>""", unsafe_allow_html=True)
                    db.save_knowledge_entry(
                        selected_chinese, herb_data.get("english",""), ev,
                        source="Claude AI / PubMed", category=", ".join(cats[:2])
                    )
                    st.success("Evidence saved to Knowledge Base")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 — EVIDENCE ENRICHER
# ═══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.markdown("### Evidence Enricher")
    st.markdown("*Search clinical evidence for any herb in the inventory and save to Knowledge Base.*")

    ev_col1, ev_col2 = st.columns(2)
    with ev_col1:
        ev_herb = st.text_input("Herb (Chinese name)", placeholder="e.g. 酸枣仁")
    with ev_col2:
        ev_condition = st.text_input("In context of condition", placeholder="e.g. insomnia")

    if st.button("🔬 Search Evidence", key="ev_search"):
        if not st.session_state.api_key:
            st.error("Enter API key in sidebar.")
        elif not ev_herb.strip():
            st.warning("Enter an herb name.")
        else:
            with st.spinner("Retrieving evidence..."):
                ev_text = enrich_evidence(ev_herb, ev_condition, st.session_state.api_key)
            st.markdown(f"""<div class="info-box evidence">
            <div class="info-box-label">Evidence Summary — {ev_herb}</div>{ev_text}</div>""", unsafe_allow_html=True)
            db.save_knowledge_entry(ev_herb, "", ev_text, source="Claude AI / PubMed", category=ev_condition)
            st.success("Saved to Knowledge Base.")

    st.divider()
    st.markdown("#### Saved Evidence Entries")
    ev_search_filter = st.text_input("Filter by herb", placeholder="Chinese name...")
    entries = db.get_knowledge_entries(ev_search_filter)
    if not entries:
        st.info("No evidence entries yet.")
    for entry in entries:
        with st.expander(f"**{entry['herb_chinese']}** — {entry.get('category','')} — {entry['created_at'][:16]}"):
            st.markdown(entry.get("evidence_text",""))

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 5 — SUBMISSION REVIEW (RAG Vendor Document Validator)
# ═══════════════════════════════════════════════════════════════════════════════
with tab5:
    st.markdown("### 📋 Submission Review — Vendor Document Validator")
    st.markdown(
        "*Upload vendor label images or PDFs. AI validates each document against "
        "HSA GL-CHPB-4-001 (Jan 2025) and tracks your full submission readiness.*"
    )

    st.markdown("""
    <style>
      .check-row { display:flex; align-items:center; gap:10px; padding:6px 0;
                   border-bottom:1px solid #1e3a52; font-size:14px; }
      .check-row:last-child { border-bottom:none; }
      .check-badge { min-width:90px; font-size:12px; font-weight:700;
                     padding:3px 10px; border-radius:4px; text-align:center; }
      .badge-pass  { background:#0d2b1a; color:#22c55e; border:1px solid #22c55e; }
      .badge-fail  { background:#2a0e0e; color:#ef4444; border:1px solid #ef4444; }
      .badge-na    { background:#1e2a3a; color:#6b8ba4; border:1px solid #2d4a6a; }
    </style>
    """, unsafe_allow_html=True)

    # ── Step 1: Select Product ────────────────────────────────────────────────
    st.markdown("#### Step 1 — Select Product")
    products = vr.get_all_product_names()

    if not products:
        st.info("No saved products yet. Generate and save a formulation in the Formulation Generator tab first.")
    else:
        product_options = {name: pid for pid, name in products}
        selected_product_name = st.selectbox(
            "Product",
            options=list(product_options.keys()),
            help="Products saved to your Knowledge Base"
        )
        selected_product_id = product_options[selected_product_name]

        # ── Step 2: Upload & Analyse Document ────────────────────────────────
        st.divider()
        st.markdown("#### Step 2 — Upload Vendor Document")

        up_col1, up_col2 = st.columns([1, 1])
        with up_col1:
            doc_type = st.selectbox(
                "Document Type",
                options=list(vr.LABEL_TYPES.keys()),
                format_func=lambda k: vr.LABEL_TYPES[k],
            )
        with up_col2:
            uploaded_file = st.file_uploader(
                "Upload label image or PDF",
                type=["jpg", "jpeg", "png", "webp", "pdf"],
                help="Swatch photos (JPG/PNG/WEBP) or PDF documents"
            )

        with st.expander("Or paste label text directly"):
            pasted_text = st.text_area(
                "Paste label text",
                height=150,
                placeholder="Paste all visible text from the label here."
            )

        analyse_btn = st.button("Analyse Document", type="primary")

        if analyse_btn:
            if not st.session_state.api_key:
                st.error("Enter your Anthropic API key in the sidebar.")
            elif not uploaded_file and not (pasted_text or "").strip():
                st.warning("Upload a file or paste label text.")
            else:
                with st.spinner("AI is reviewing document against HSA GL-CHPB-4-001..."):
                    findings = {}
                    extracted_text = ""
                    filename = "(pasted text)"

                    if uploaded_file:
                        filename = uploaded_file.name
                        file_bytes = uploaded_file.read()
                        ext = filename.rsplit(".", 1)[-1].lower()

                        if ext == "pdf":
                            extracted_text = vr.extract_pdf_text(file_bytes)
                            if extracted_text.strip():
                                findings = vr.analyze_label_text(
                                    extracted_text, doc_type, selected_product_name,
                                    st.session_state.api_key
                                )
                            else:
                                findings = {
                                    "overall_assessment": "INCOMPLETE",
                                    "flags": ["PDF appears scanned — upload as JPG/PNG for vision analysis."],
                                    "missing_items": [], "extracted_text": ""
                                }
                        else:
                            findings = vr.analyze_label_image(
                                file_bytes, ext, doc_type, selected_product_name,
                                st.session_state.api_key
                            )
                            extracted_text = findings.get("extracted_text", "")

                    elif pasted_text.strip():
                        extracted_text = pasted_text.strip()
                        findings = vr.analyze_label_text(
                            extracted_text, doc_type, selected_product_name,
                            st.session_state.api_key
                        )

                    # Rule-based cross-checks
                    if extracted_text and doc_type.startswith("sg"):
                        if vr.has_pinyin(extracted_text):
                            findings.setdefault("flags", []).append(
                                "Hanyu Pinyin tone marks detected — remove from Singapore sale labels."
                            )
                            findings["has_hanyu_pinyin"] = True
                        found_claims = vr.check_prohibited_claims(extracted_text)
                        if found_claims:
                            findings.setdefault("flags", []).append(
                                "Prohibited disease claims: " + ", ".join(found_claims)
                            )
                            findings["prohibited_claims_found"] = found_claims

                    overall = findings.get("overall_assessment", "INCOMPLETE")

                    vr.save_vendor_doc(
                        selected_product_id, selected_product_name,
                        doc_type, filename, extracted_text, findings, overall
                    )

                    # Auto-tick submission tracker
                    for cid in vr.LABEL_CHECKLIST_MAP.get(doc_type, []):
                        sm = {"PASS": "DONE", "FAIL": "ISSUES", "INCOMPLETE": "PENDING", "ERROR": "PENDING"}
                        vr.upsert_checklist_status(
                            selected_product_id, cid, sm.get(overall, "PENDING"),
                            f"From {filename}"
                        )

                    st.session_state[f"vr_{selected_product_id}_{doc_type}"] = findings

        # ── Step 3: Compliance Results ─────────────────────────────────────────
        findings_key = f"vr_{selected_product_id}_{doc_type}"
        if findings_key in st.session_state:
            findings = st.session_state[findings_key]
            overall = findings.get("overall_assessment", "INCOMPLETE")

            st.divider()
            st.markdown("#### Step 3 — Compliance Check Results")

            bcolors = {"PASS":"#22c55e","FAIL":"#ef4444","INCOMPLETE":"#f59e0b","ERROR":"#ef4444"}
            bbg     = {"PASS":"#0d2b1a","FAIL":"#2a0e0e","INCOMPLETE":"#2a1f0e","ERROR":"#2a0e0e"}
            bicon   = {"PASS":"✅","FAIL":"❌","INCOMPLETE":"⚠️","ERROR":"🚨"}
            bc = bcolors.get(overall, "#f59e0b")
            bg = bbg.get(overall, "#2a1f0e")
            ic = bicon.get(overall, "⚠️")

            st.markdown(f"""
            <div style="background:{bg};border:2px solid {bc};border-radius:10px;
                        padding:14px 20px;margin-bottom:16px;">
              <span style="color:{bc};font-size:18px;font-weight:700">
                {ic} {vr.LABEL_TYPES.get(doc_type, doc_type)} — {overall}
              </span>
            </div>
            """, unsafe_allow_html=True)

            compliance_rows = vr.build_compliance_rows(doc_type, findings)
            rows_html = ""
            for row in compliance_rows:
                s = row["status"]
                bcls = "badge-pass" if "PASS" in s else "badge-fail" if "FAIL" in s else "badge-na"
                rows_html += (
                    f'<div class="check-row">'
                    f'<span class="check-badge {bcls}">{s}</span>'
                    f'<span style="flex:1;color:#c9d8e8">{row["field"]}</span>'
                    f'<span style="color:#8aa5bf;font-size:12px;font-style:italic">{row["note"]}</span>'
                    f'</div>'
                )
            st.markdown(
                f'<div style="background:#162334;border:1px solid #2d4a6a;'
                f'border-radius:10px;padding:16px 20px">{rows_html}</div>',
                unsafe_allow_html=True
            )

            flags = findings.get("flags", [])
            missing = findings.get("missing_items", [])
            if flags:
                st.markdown("**Issues flagged:**")
                for f in flags:
                    st.markdown(f"- {f}")
            if missing:
                st.markdown("**Missing required items:**")
                for m in missing:
                    st.markdown(f"- {m}")
            ext_text = findings.get("extracted_text", "")
            if ext_text:
                with st.expander("View extracted label text"):
                    st.text(ext_text[:2000])

        # ── Step 4: Submission Tracker ────────────────────────────────────────
        st.divider()
        st.markdown("#### Step 4 — HSA Submission Readiness Tracker")
        st.caption(
            "17-item checklist from TCM Registration Excel (HSA Requirement sheet). "
            "Mandatory = required for all products. Conditional = required only where stated."
        )

        checklist_status = vr.get_checklist_status(selected_product_id)

        # Conditional flags
        c1, c2 = st.columns(2)
        with c1:
            is_oral_liquid = st.checkbox(
                "Product is oral liquid (DEG/EG test required)",
                key="chk_oral_liquid"
            )
        with c2:
            has_fermented = st.checkbox(
                "Product contains fermented ingredient (CPMF11-5 required)",
                key="chk_fermented"
            )

        categories = list(dict.fromkeys(c["category"] for c in vr.SUBMISSION_CHECKLIST))
        done_count = 0
        total_required = 0

        for cat in categories:
            items_in_cat = [c for c in vr.SUBMISSION_CHECKLIST if c["category"] == cat]
            st.markdown(f"**{cat}**")
            for item in items_in_cat:
                # Resolve conditional items
                if item["mandatory"] == "Conditional":
                    if item["id"] == 7 and not is_oral_liquid:
                        continue   # DEG/EG — only for oral liquids
                    if item["id"] == 16 and not has_fermented:
                        continue   # Fermented substance — only if applicable

                total_required += 1
                cur = checklist_status.get(item["id"], {})
                cur_status = cur.get("status", "PENDING")
                if cur_status == "DONE":
                    done_count += 1

                # Mandatory / Conditional badge
                mand_badge = (
                    "<span style='font-size:10px;color:#6b8ba4;"
                    "border:1px solid #2d4a6a;border-radius:3px;"
                    "padding:1px 5px;margin-right:4px'>COND</span>"
                    if item["mandatory"] == "Conditional" else ""
                )
                # Form reference badge
                form_ref = item.get("form", "—")
                form_badge = (
                    f"<span style='font-size:10px;color:#7ec8e3;"
                    f"border:1px solid #2d5a7e;border-radius:3px;"
                    f"padding:1px 5px;margin-right:6px'>{form_ref}</span>"
                    if form_ref and form_ref != "—" else ""
                )
                remarks = item.get("remarks", "")

                status_html = {
                    "DONE":    "<span style='color:#22c55e;font-weight:700'>✅ Done</span>",
                    "ISSUES":  "<span style='color:#ef4444;font-weight:700'>❌ Issues</span>",
                    "PENDING": "<span style='color:#f59e0b;font-weight:700'>⏳ Pending</span>",
                }.get(cur_status, "<span style='color:#f59e0b;font-weight:700'>⏳ Pending</span>")

                col_item, col_status, col_action = st.columns([5, 1, 1])
                with col_item:
                    st.markdown(
                        f"<div style='line-height:1.4'>"
                        f"{mand_badge}{form_badge}"
                        f"<span style='font-size:13px;color:#c9d8e8'>"
                        f"<b>{item['id']}.</b> {item['item']}</span>"
                        f"<br><span style='font-size:11px;color:#6b8ba4;padding-left:4px'>"
                        f"{remarks}</span></div>",
                        unsafe_allow_html=True
                    )
                with col_status:
                    st.markdown(status_html, unsafe_allow_html=True)
                with col_action:
                    opts = ["PENDING", "DONE", "ISSUES"]
                    idx_s = opts.index(cur_status) if cur_status in opts else 0
                    new_st = st.selectbox(
                        "Status", opts, index=idx_s,
                        key=f"tr_{selected_product_id}_{item['id']}",
                        label_visibility="collapsed"
                    )
                    if new_st != cur_status:
                        vr.upsert_checklist_status(selected_product_id, item["id"], new_st)
                        st.rerun()
            st.markdown("---")

        pct = int(done_count / total_required * 100) if total_required else 0
        pct_color = "#22c55e" if pct == 100 else "#f59e0b" if pct >= 50 else "#ef4444"
        ready_msg = (
            "<div style='color:#22c55e;font-weight:700;margin-top:8px'>"
            "🎉 All items complete — ready to submit via HSA PRISM!</div>"
            if pct == 100 else ""
        )
        st.markdown(f"""
        <div style="background:#162334;border:1px solid #2d4a6a;border-radius:10px;
                    padding:16px 20px;text-align:center;margin-top:12px">
          <div style="font-size:32px;font-weight:800;color:{pct_color}">{pct}%</div>
          <div style="color:#8aa5bf;font-size:14px">{done_count} of {total_required} items complete</div>
          {ready_msg}
        </div>
        """, unsafe_allow_html=True)

        # ── HSA Limits Reference ────────────────────────────────────────────        st.divider()
        st.markdown("#### 📊 HSA Limits Reference")
        st.caption("From TCM Registration Excel — Limit sheet. Use when reviewing lab test reports (checklist item 6).")

        lim_tab1, lim_tab2, lim_tab3, lim_tab4 = st.tabs([
            "⚗️ Heavy Metals", "🦠 Microbial", "🧪 DEG / EG", "💊 Vitamins & Minerals"
        ])

        def _limits_table(rows_html, headers):
            ths = "".join(
                f"<th style='color:#7ec8e3;padding:6px 12px;border-bottom:2px solid #2d4a6a;"
                f"text-align:left'>{h}</th>" for h in headers
            )
            return (
                f"<table style='width:100%;border-collapse:collapse;font-size:13px'>"
                f"<tr>{ths}</tr>{rows_html}</table>"
            )

        with lim_tab1:
            hm_rows = "".join(
                f"<tr style='border-bottom:1px solid #1e3a52'>"
                f"<td style='color:#c9d8e8;padding:5px 12px'>{k}</td>"
                f"<td style='color:#22c55e;font-weight:700;padding:5px 12px'>"
                f"{v['operator']} {v['limit']} {v['unit']}</td>"
                f"<td style='color:#6b8ba4;font-size:11px;padding:5px 12px'>"
                f"{v.get('note','')}</td></tr>"
                for k, v in vr.HEAVY_METAL_LIMITS.items()
            )
            st.markdown(
                _limits_table(hm_rows, ["Heavy Metal", "HSA Limit", "Notes"]),
                unsafe_allow_html=True
            )

        with lim_tab2:
            mc_rows = "".join(
                f"<tr style='border-bottom:1px solid #1e3a52'>"
                f"<td style='color:#c9d8e8;padding:5px 12px'>{k}</td>"
                f"<td style='color:#22c55e;font-weight:700;padding:5px 12px'>"
                f"{v['limit']}</td>"
                f"<td style='color:#6b8ba4;font-size:11px;padding:5px 12px'>"
                f"{v['unit']}</td></tr>"
                for k, v in vr.MICROBIAL_LIMITS.items()
            )
            st.markdown(
                _limits_table(mc_rows, ["Micro-organism", "Limit", "Unit"]),
                unsafe_allow_html=True
            )

        with lim_tab3:
            deg_rows = "".join(
                f"<tr style='border-bottom:1px solid #1e3a52'>"
                f"<td style='color:#c9d8e8;padding:5px 12px'>{k}</td>"
                f"<td style='color:#22c55e;font-weight:700;padding:5px 12px'>"
                f"{v['operator']} {v['limit']} {v['unit']}</td>"
                f"<td style='color:#6b8ba4;font-size:11px;padding:5px 12px'>"
                f"{v.get('note','')}</td></tr>"
                for k, v in vr.DEG_EG_LIMITS.items()
            )
            st.markdown(
                _limits_table(deg_rows, ["Parameter", "HSA Limit", "Notes"]),
                unsafe_allow_html=True
            )
            st.info("DEG/EG testing required only for oral liquid products (checklist item 7).")

        with lim_tab4:
            vm_rows = "".join(
                f"<tr style='border-bottom:1px solid #1e3a52'>"
                f"<td style='color:#c9d8e8;padding:5px 12px'>{k}</td>"
                f"<td style='color:#22c55e;font-weight:700;padding:5px 12px'>"
                f"{v}</td></tr>"
                for k, v in vr.VITAMIN_MINERAL_LIMITS.items()
            )
            st.markdown(
                _limits_table(vm_rows, ["Nutrient", "Maximum Daily Limit"]),
                unsafe_allow_html=True
            )
            st.caption("* Iron 15 mg/day; 30 mg/day may be considered for multivitamin supplements for pregnant women.")

        # ── Step 5: Previous documents ────────────────────────────────────────
        st.divider()
        st.markdown("#### Previously Reviewed Documents")
        prev_docs = vr.get_vendor_docs(selected_product_id)
        if not prev_docs:
            st.info("No documents reviewed yet for this product.")
        else:
            for doc in prev_docs:
                overall_d = doc.get("overall", "PENDING")
                icon_d = {"PASS":"✅","FAIL":"❌","INCOMPLETE":"⚠️","ERROR":"🚨"}.get(overall_d, "⏳")
                label_d = vr.LABEL_TYPES.get(doc.get("doc_type",""), doc.get("doc_type",""))
                with st.expander(f"{icon_d} {label_d} — {doc.get('filename','')} — {doc.get('created_at','')[:16]}"):
                    try:
                        findings_d = json.loads(doc.get("ai_findings","{}") or "{}")
                    except Exception:
                        findings_d = {}
                    flags_d = findings_d.get("flags", [])
                    missing_d = findings_d.get("missing_items", [])
                    if flags_d:
                        st.markdown("**Issues:**")
                        for f2 in flags_d:
                            st.markdown(f"- {f2}")
                    if missing_d:
                        st.markdown("**Missing:**")
                        for m2 in missing_d:
                            st.markdown(f"- {m2}")
                    if not flags_d and not missing_d:
                        st.success("No issues found.")
                    ext_d = doc.get("extracted_text", "")
                    if ext_d:
                        with st.expander("Label text"):
                            st.text(ext_d[:1500])
               findings_d = {}
                try:
                    findings_d = json.loads(doc.get("ai_findings","{}") or "{}")
                except Exception:
                    pass
                flags_d = findings_d.get("flags", [])
                missing_d = findings_d.get("missing_items", [])
                if flags_d:
                    st.markdown("**Issues:**")
                    for f in flags_d:
                        st.markdown(f"- {f}")
                if missing_d:
                    st.markdown("**Missing:**")
                    for m in missing_d:
                        st.markdown(f"- {m}")
                if not flags_d and not missing_d:
                    st.success("No issues found.")
                ext_d = doc.get("extracted_text","")
                if ext_d:
                    with st.expander("Label text"):
                        st.text(ext_d[:1500])