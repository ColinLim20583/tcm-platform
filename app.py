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
from config import APP_TITLE, APP_SUBTITLE, VERSION, COMPANY

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

# ─── SESSION STATE ─────────────────────────────────────────────────────────────
if "result" not in st.session_state:
    st.session_state.result = None
if "api_key" not in st.session_state:
    st.session_state.api_key = ""
if "generating" not in st.session_state:
    st.session_state.generating = False
if "business_case" not in st.session_state:
    st.session_state.business_case = ""

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

def render_safety_report(result: dict, demographic: str = "", condition: str = ""):
    """Run and display the safety check for a generated formula."""
    formula = result.get("formula", [])
    if not formula:
        return

    report = check_formula_safety(
        formula=formula,
        demographic=demographic,
        condition=condition,
        dosage_recommendation=result.get("dosage_recommendation", ""),
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

tab1, tab2, tab3, tab4 = st.tabs(["🧪 Formulation Generator", "📚 Knowledge Base", "🌱 Inventory Browser", "🔬 Evidence Enricher"])

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
        )

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