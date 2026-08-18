"""
app.py — Chemigran TCM Formulation Intelligence Platform v2.0
Enhanced with Visual AI Diagnosis (camera-based TCM assessment)
"""

import streamlit as st
import json
import csv
import io
from datetime import datetime

from config import APP_TITLE, APP_SUBTITLE, VERSION, COMPANY, ANTHROPIC_API_KEY
from database import init_db, save_formulation, get_all_formulations, toggle_star, delete_formulation, search_formulations, save_knowledge_entry, get_knowledge_entries, get_stats, save_visual_diagnosis
from formulation_engine import generate_formulation, generate_business_case, enrich_evidence
from inventory_data import get_all_herbs, get_herb_by_chinese
from vision_engine import analyze_tcm_visual, analyze_with_yolo_pipeline, enrich_visual_diagnosis, get_camera_guidance, get_pattern_herb_hints

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title=APP_TITLE,
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded"
)

init_db()

# ── CSS Theme ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  /* Base */
  .stApp { background-color: #0f1923; color: #e2e8f0; }
  .block-container { padding: 1.5rem 2rem; }

  /* Sidebar */
  [data-testid="stSidebar"] { background-color: #0a1118 !important; border-right: 1px solid #1e3a4f; }
  [data-testid="stSidebar"] * { color: #94a3b8 !important; }
  [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2 { color: #7ec8e3 !important; }

  /* Cards */
  .card { background: #162435; border: 1px solid #1e3a4f; border-radius: 12px; padding: 1.4rem 1.6rem; margin-bottom: 1.2rem; }
  .vision-card { background: linear-gradient(135deg,#0d2137 0%,#162435 100%); border: 1px solid #2563eb44; border-radius: 14px; padding: 1.6rem; margin-bottom: 1.2rem; }
  .diagnosis-card { background: #0d1f2d; border: 2px solid #2563eb55; border-radius: 14px; padding: 1.6rem; margin-bottom: 1rem; }
  .pattern-badge { display:inline-block; background:#1e3a6e; color:#93c5fd; padding:4px 14px; border-radius:20px; font-size:13px; font-weight:600; margin:3px; }
  .confidence-bar { background:#1e293b; border-radius:8px; height:8px; overflow:hidden; margin-top:4px; }
  .confidence-fill { height:8px; border-radius:8px; background:linear-gradient(90deg,#2563eb,#7ec8e3); }

  /* Herb table */
  .herb-table { width:100%; border-collapse:collapse; margin:1rem 0; font-size:13px; }
  .herb-table th { background:#1e3a4f; color:#7ec8e3; padding:8px 12px; text-align:left; font-size:12px; text-transform:uppercase; letter-spacing:.05em; }
  .herb-table td { padding:8px 12px; border-bottom:1px solid #1e3a4f33; color:#cbd5e1; }
  .herb-table tr:hover td { background:#1e3a4f33; }
  .role-jun  { background:#7f1d1d; color:#fca5a5; padding:3px 10px; border-radius:12px; font-size:11px; font-weight:700; }
  .role-chen { background:#7c2d12; color:#fdba74; padding:3px 10px; border-radius:12px; font-size:11px; font-weight:700; }
  .role-zuo  { background:#14532d; color:#86efac; padding:3px 10px; border-radius:12px; font-size:11px; font-weight:700; }
  .role-shi  { background:#1e3a5f; color:#93c5fd; padding:3px 10px; border-radius:12px; font-size:11px; font-weight:700; }

  /* Info boxes */
  .info-box { border-radius:10px; padding:1rem 1.2rem; margin:.7rem 0; font-size:14px; line-height:1.65; }
  .info-box.rationale { background:#0f2918; border-left:4px solid #22c55e; }
  .info-box.safety    { background:#1c1707; border-left:4px solid #eab308; }
  .info-box.gap       { background:#1a0d2e; border-left:4px solid #a855f7; }
  .info-box.evidence  { background:#0c1f3a; border-left:4px solid #3b82f6; }
  .info-box.vision    { background:#0c1a2e; border-left:4px solid #2563eb; }
  .info-box.diagnosis { background:#0f1f12; border-left:4px solid #22c55e; }

  /* Pills */
  .meta-pill { display:inline-block; background:#1e293b; border:1px solid #334155; color:#94a3b8; padding:4px 12px; border-radius:20px; font-size:12px; margin:3px; }
  .meta-pill.green { background:#052e16; border-color:#166534; color:#86efac; }
  .meta-pill.blue  { background:#0c1f3a; border-color:#1e40af; color:#93c5fd; }
  .meta-pill.gold  { background:#1c1302; border-color:#92400e; color:#fcd34d; }

  /* Vision UI */
  .scan-guide { background:#0d1e30; border:1px dashed #2563eb66; border-radius:12px; padding:1.2rem; margin:.8rem 0; }
  .scan-guide h4 { color:#7ec8e3; margin:0 0 .6rem; font-size:15px; }
  .scan-guide li { color:#94a3b8; font-size:13px; margin:.3rem 0; }
  .zone-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:.6rem; margin:1rem 0; }
  .zone-cell { background:#0d1e30; border:1px solid #1e3a4f; border-radius:8px; padding:.6rem .8rem; }
  .zone-cell .zone-label { font-size:10px; color:#64748b; text-transform:uppercase; letter-spacing:.05em; }
  .zone-cell .zone-val { font-size:13px; color:#cbd5e1; margin-top:2px; }

  /* Buttons */
  .stButton > button { background:#1e3a4f; color:#7ec8e3; border:1px solid #2563eb44; border-radius:8px; }
  .stButton > button:hover { background:#2563eb; color:#fff; border-color:#2563eb; }

  /* Headers */
  h1,h2,h3 { color:#7ec8e3 !important; }
  .product-title { font-size:22px; font-weight:700; color:#7ec8e3; }
  .product-zh { font-size:16px; color:#64748b; margin-top:2px; }
  .section-label { font-size:11px; text-transform:uppercase; letter-spacing:.1em; color:#64748b; margin-bottom:.3rem; }

  /* Tabs — swipeable on mobile */
  [data-testid="stHorizontalBlock"] { gap:.5rem; }
  .stTabs [data-baseweb="tab"] { background:#162435; color:#94a3b8; border-radius:8px 8px 0 0; white-space:nowrap; flex-shrink:0; }
  .stTabs [aria-selected="true"] { background:#1e3a4f !important; color:#7ec8e3 !important; }
  .stTabs [data-baseweb="tab-list"] {
    position:sticky; top:3.5rem; z-index:999; background:#0f1923; padding:.4rem 0;
    overflow-x: auto !important;
    -webkit-overflow-scrolling: touch !important;
    scrollbar-width: none !important;
    flex-wrap: nowrap !important;
    display: flex !important;
  }
  .stTabs [data-baseweb="tab-list"]::-webkit-scrollbar { display: none; }
  header[data-testid="stHeader"] { display:none; }
  .block-container { padding-top: 1rem !important; }

  /* Sidebar API key input — wider touch target on mobile */
  [data-testid="stSidebar"] input {
    font-size: 16px !important;
    min-height: 44px !important;
  }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"## 🌿 {COMPANY}")
    st.markdown(f"**{APP_TITLE}**  \n*v{VERSION}*")
    st.divider()

    show_key = st.checkbox("👁 Show key (use on mobile)", value=False)
    api_key = st.text_input(
        "🔑 Anthropic API Key",
        value=ANTHROPIC_API_KEY,
        type="default" if show_key else "password",
        help="Tick 'Show key' on mobile so you can see what you're typing"
    )
    if not api_key:
        st.warning("⚠️ Add your API key to enable AI features")

    st.divider()
    st.markdown("### 📊 Knowledge Base Stats")
    try:
        stats = get_stats()
        col1, col2 = st.columns(2)
        col1.metric("Formulations", stats["total"])
        col2.metric("★ Starred", stats["starred"])
        st.metric("🔬 Vision Scans", stats.get("scans", 0))
        if stats["top_patterns"]:
            st.markdown("**Top TCM Patterns**")
            for pat, cnt in stats["top_patterns"]:
                st.caption(f"• {pat} ({cnt})")
    except Exception:
        pass

    st.divider()

    # YOLO pipeline status
    from pathlib import Path as _Path
    _model_path = _Path(__file__).parent / "models" / "tongue_yolo_best.pt"
    if _model_path.exists():
        st.markdown("**⚡ YOLOv8 Pipeline**")
        st.success("Model ready — 19,585 tongue images")
    else:
        st.markdown("**⚡ YOLOv8 Pipeline**")
        st.caption("No model trained yet")
        st.caption("Run: `python setup_dataset.py --zip ...`")
        st.caption("Then: `python train_yolo.py`")

    st.divider()
    st.markdown(f"*Powered by Claude Vision + claude-sonnet-4-5*")
    st.markdown(f"*{APP_SUBTITLE}*")


# ── Helper: render product card ───────────────────────────────────────────────
def render_product_card(result: dict, show_business_btn: bool = True, compact: bool = False, key_suffix: str = ""):
    name_en = result.get("product_name_en", "Unnamed Product")
    name_zh = result.get("product_name_zh", "")
    pattern = result.get("tcm_pattern", "")
    margin = result.get("gross_margin_est", "—")
    price = result.get("suggested_price_sgd", "—")
    complexity = result.get("formula_complexity", "—")
    commercial = result.get("commercial", {})
    safety = result.get("safety", {})
    formula = result.get("formula", [])
    tags = result.get("tags", [])

    # Header
    st.markdown(f"""
    <div class="card">
      <div class="product-title">🌿 {name_en}</div>
      <div class="product-zh">{name_zh}</div>
      <div style="margin:.5rem 0; color:#64748b; font-size:13px;">
        TCM Pattern: <span style="color:#7ec8e3">{pattern}</span>
      </div>
      <div>
        <span class="meta-pill green">💰 {margin}</span>
        <span class="meta-pill blue">💊 {price}</span>
        <span class="meta-pill gold">⚙️ {complexity}</span>
        <span class="meta-pill">📈 Demand: {commercial.get('market_demand_score','—')}/10</span>
        <span class="meta-pill">🔄 Repeat: {commercial.get('repeat_purchase_score','—')}/10</span>
      </div>
    """, unsafe_allow_html=True)

    # Tags
    if tags:
        tag_list = tags if isinstance(tags, list) else json.loads(tags) if isinstance(tags, str) else []
        tag_html = " ".join(f'<span class="pattern-badge">{t}</span>' for t in tag_list)
        st.markdown(tag_html, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # Herb table
    if formula:
        role_class = {"Jun": "role-jun", "Chen": "role-chen", "Zuo": "role-zuo", "Shi": "role-shi"}
        rows = ""
        for h in formula:
            rc = role_class.get(h.get("role", ""), "role-shi")
            rows += f"""<tr>
              <td>{h.get('chinese','')}</td>
              <td>{h.get('pinyin','')}</td>
              <td>{h.get('english','')}</td>
              <td><span class="{rc}">{h.get('role','')}</span></td>
              <td style="text-align:right;font-weight:600;color:#7ec8e3">{h.get('percentage',0)}%</td>
              <td style="font-size:12px;color:#64748b">{h.get('tcm_function','')[:50]}</td>
            </tr>"""
        st.markdown(f"""
        <table class="herb-table">
          <thead><tr>
            <th>Chinese</th><th>Pinyin</th><th>English</th>
            <th>Role</th><th style="text-align:right">%</th><th>TCM Function</th>
          </tr></thead>
          <tbody>{rows}</tbody>
        </table>""", unsafe_allow_html=True)

    # Info boxes
    rationale = result.get("formula_rationale", "")
    if rationale and not compact:
        st.markdown(f'<div class="info-box rationale"><b>📋 Formula Rationale</b><br>{rationale}</div>', unsafe_allow_html=True)

    safety_rating = safety.get("overall_rating", "")
    contraindications = safety.get("contraindications", [])
    if safety_rating:
        ci = "; ".join(contraindications) if contraindications else "None significant"
        st.markdown(f'<div class="info-box safety"><b>⚠️ Safety: {safety_rating}</b><br>Contraindications: {ci}<br>{safety.get("pregnancy_notes","")}</div>', unsafe_allow_html=True)

    comp_gap = commercial.get("competitive_gap", "")
    if comp_gap and not compact:
        st.markdown(f'<div class="info-box gap"><b>🎯 Competitive Gap</b><br>{comp_gap}</div>', unsafe_allow_html=True)

    evidence = result.get("evidence_summary", "")
    if evidence and not compact:
        with st.expander("🔬 Evidence Summary"):
            st.write(evidence)
            refs = result.get("clinical_references", [])
            if refs:
                st.markdown("**References:**")
                for r in refs:
                    st.caption(f"• {r}")

    # Jun/Chen/Zuo/Shi breakdown
    if not compact:
        with st.expander("🏛️ Formula Structure (Jun / Chen / Zuo / Shi)"):
            c1, c2, c3, c4 = st.columns(4)
            c1.markdown(f"**🔴 Jun (Chief)**\n\n{result.get('jun_rationale','—')}")
            c2.markdown(f"**🟠 Chen (Deputy)**\n\n{result.get('chen_rationale','—')}")
            c3.markdown(f"**🟢 Zuo (Assistant)**\n\n{result.get('zuo_rationale','—')}")
            c4.markdown(f"**🔵 Shi (Envoy)**\n\n{result.get('shi_rationale','—')}")

    with st.expander("💊 Dosage & Manufacturing"):
        st.write(result.get("dosage_recommendation", "—"))
        st.write(result.get("manufacturing_notes", "—"))

    # Action buttons
    col1, col2, col3 = st.columns(3)
    prod_key = name_en.replace(" ", "_")[:20] + (f"_{key_suffix}" if key_suffix else "")

    if col1.button("💾 Save to Knowledge Base", key=f"save_{prod_key}"):
        try:
            save_formulation({
                "condition_input": result.get("tcm_pattern", ""),
                "tcm_pattern": result.get("tcm_pattern", ""),
                "product_name_en": name_en,
                "product_name_zh": name_zh,
                "formula": formula,
                "rationale": rationale,
                "safety": safety,
                "evidence": evidence,
                "commercial": commercial,
                "dosage": result.get("dosage_recommendation", ""),
                "gross_margin_est": margin,
                "formula_complexity": complexity,
                "tags": tags,
                "source": result.get("source", "manual"),
            })
            st.success("✅ Saved!")
        except Exception as e:
            st.error(f"Error: {e}")

    if show_business_btn and col2.button("📊 Ask AI: Full Business Case", key=f"biz_{prod_key}"):
        if not api_key:
            st.error("API key required")
        else:
            with st.spinner("Generating business case..."):
                bc = generate_business_case(name_en, result, api_key)
            with st.expander("📊 Business Case", expanded=True):
                st.markdown(bc)

    # CSV export
    if formula and col3.button("📥 Export CSV", key=f"csv_{prod_key}"):
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=["chinese","pinyin","english","role","percentage","tcm_function"])
        w.writeheader()
        w.writerows(formula)
        st.download_button("⬇️ Download", buf.getvalue(), f"{prod_key}_formula.csv", "text/csv",
                           key=f"dl_{prod_key}")


# ── Helper: render vision diagnosis results ───────────────────────────────────
def render_vision_results(diag: dict):
    if "error" in diag:
        st.error(f"Analysis error: {diag['error']}")
        return

    quality = diag.get("image_quality", "unknown")
    confidence = diag.get("confidence_overall", 0)
    primary = diag.get("primary_pattern", "—")
    primary_zh = diag.get("primary_pattern_zh", "")
    constitution = diag.get("constitution_type", "—")
    constitution_zh = diag.get("constitution_zh", "")
    secondary = diag.get("secondary_patterns", [])
    affected = diag.get("affected_organs", [])
    factors = diag.get("pathogenic_factors", [])
    principles = diag.get("recommended_therapeutic_principles", [])
    focus_areas = diag.get("recommended_focus_areas", [])
    summary = diag.get("diagnosis_summary", "")
    tongue = diag.get("tongue", {})
    face = diag.get("face", {})
    disclaimer = diag.get("disclaimer", "")

    # Header card
    quality_color = {"good": "#22c55e", "fair": "#eab308", "poor": "#ef4444"}.get(quality, "#64748b")
    st.markdown(f"""
    <div class="diagnosis-card">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:1rem">
        <div>
          <div style="font-size:11px;text-transform:uppercase;letter-spacing:.1em;color:#64748b">Primary TCM Pattern</div>
          <div style="font-size:24px;font-weight:700;color:#7ec8e3;margin:.2rem 0">{primary}</div>
          <div style="font-size:15px;color:#475569">{primary_zh}</div>
        </div>
        <div style="text-align:right">
          <div style="font-size:11px;color:#64748b">Image Quality</div>
          <div style="color:{quality_color};font-weight:600">{quality.title()}</div>
          <div style="font-size:11px;color:#64748b;margin-top:.5rem">Confidence</div>
          <div style="font-size:22px;font-weight:700;color:#7ec8e3">{confidence}%</div>
        </div>
      </div>
      <div class="confidence-bar" style="margin-top:.8rem">
        <div class="confidence-fill" style="width:{confidence}%"></div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Patterns & constitution
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**🔬 TCM Patterns Detected**")
        patterns_data = diag.get("tcm_patterns", [])
        if patterns_data:
            for pat in patterns_data:
                conf = pat.get("confidence", 0)
                st.markdown(f"""
                <div style="margin:.4rem 0;padding:.6rem .8rem;background:#0d1e30;border-radius:8px">
                  <div style="display:flex;justify-content:space-between">
                    <span style="color:#cbd5e1;font-size:13px">{pat.get('pattern_en','')}</span>
                    <span style="color:#7ec8e3;font-size:13px;font-weight:600">{conf}%</span>
                  </div>
                  <div style="color:#475569;font-size:12px">{pat.get('pattern_zh','')}</div>
                  <div class="confidence-bar" style="margin-top:.4rem">
                    <div class="confidence-fill" style="width:{conf}%"></div>
                  </div>
                </div>""", unsafe_allow_html=True)
        else:
            st.markdown(f'<span class="pattern-badge">{primary}</span>', unsafe_allow_html=True)
            for s in secondary:
                st.markdown(f'<span class="pattern-badge">{s}</span>', unsafe_allow_html=True)

    with col2:
        st.markdown("**🏛️ Body Constitution**")
        st.markdown(f"""
        <div style="background:#0d1e30;border-radius:10px;padding:.8rem 1rem;margin-bottom:.6rem">
          <div style="color:#7ec8e3;font-size:16px;font-weight:600">{constitution}</div>
          <div style="color:#475569;font-size:13px">{constitution_zh}</div>
        </div>""", unsafe_allow_html=True)

        if affected:
            st.markdown("**Affected Organs:** " + " • ".join(f"<span class='meta-pill'>{o}</span>" for o in affected), unsafe_allow_html=True)
        if factors:
            st.markdown("**Pathogenic Factors:** " + " • ".join(f"<span class='meta-pill'>{f}</span>" for f in factors), unsafe_allow_html=True)

    # Tongue findings
    if tongue and diag.get("tongue_visible"):
        st.markdown("---")
        st.markdown("**👅 Tongue Diagnosis (舌诊)**")
        tc1, tc2, tc3, tc4 = st.columns(4)
        tc1.metric("Body Colour", tongue.get("body_color","—"))
        tc2.metric("Coating", tongue.get("coating_color","—"))
        tc3.metric("Shape", tongue.get("shape","—"))
        tc4.metric("Moisture", tongue.get("moisture","—"))
        if tongue.get("special_features"):
            st.caption("Special features: " + ", ".join(tongue["special_features"]))
        if tongue.get("findings_summary"):
            st.markdown(f'<div class="info-box vision">{tongue["findings_summary"]}</div>', unsafe_allow_html=True)

    # Face findings
    if face and diag.get("face_visible"):
        st.markdown("**🙂 Face Diagnosis (面诊)**")
        fc1, fc2 = st.columns([1, 2])
        with fc1:
            fc1.metric("Complexion", face.get("overall_complexion","—"))
            fc1.metric("Lustre", face.get("lustre","—"))
            fc1.metric("Skin", face.get("skin_texture","—"))
        with fc2:
            zones = face.get("zone_findings", {})
            if zones:
                st.markdown('<div class="zone-grid">', unsafe_allow_html=True)
                zone_labels = {
                    "forehead": "Forehead → Heart",
                    "between_eyebrows": "印堂 → Lung",
                    "nose_bridge": "Nose Bridge → Liver",
                    "nose_tip": "Nose Tip → Spleen",
                    "cheeks": "Cheeks → Lung",
                    "chin": "Chin → Kidney"
                }
                for key, label in zone_labels.items():
                    val = zones.get(key, "—")
                    st.markdown(f"""<div class="zone-cell">
                      <div class="zone-label">{label}</div>
                      <div class="zone-val">{val}</div>
                    </div>""", unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
        if face.get("findings_summary"):
            st.markdown(f'<div class="info-box vision">{face["findings_summary"]}</div>', unsafe_allow_html=True)

    # Diagnosis summary
    st.markdown("---")
    if summary:
        st.markdown(f'<div class="info-box diagnosis"><b>📋 Clinical Diagnosis Summary</b><br><br>{summary}</div>', unsafe_allow_html=True)

    # Therapeutic principles
    if principles:
        st.markdown("**🎯 Recommended Therapeutic Principles:**")
        cols = st.columns(min(len(principles), 3))
        for i, principle in enumerate(principles):
            cols[i % 3].markdown(f'<span class="meta-pill green">✓ {principle}</span>', unsafe_allow_html=True)

    # Herb hints
    hint_herbs = get_pattern_herb_hints(primary)
    if hint_herbs:
        st.markdown(f"**🌿 Key Herbs Suggested for {primary}:**")
        st.markdown(" ".join(f'<span class="meta-pill blue">{h}</span>' for h in hint_herbs), unsafe_allow_html=True)

    # Disclaimer
    if disclaimer:
        st.markdown(f'<div style="background:#1c1110;border:1px solid #7c2d1244;border-radius:8px;padding:.8rem 1rem;margin-top:1rem;font-size:12px;color:#9ca3af">{disclaimer}</div>', unsafe_allow_html=True)

    return diag


# ── TABS ─────────────────────────────────────────────────────────────────────
tab_vision, tab_formulation, tab_knowledge, tab_inventory, tab_evidence = st.tabs([
    "🔬 Visual AI Diagnosis",
    "🧪 Formulation Generator",
    "📚 Knowledge Base",
    "🌿 Inventory Browser",
    "🔍 Evidence Enricher"
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — VISUAL AI DIAGNOSIS
# ══════════════════════════════════════════════════════════════════════════════
with tab_vision:
    st.markdown("## 🔬 Visual AI Diagnosis")
    st.markdown("*Use your computer or phone camera to scan tongue & face. AI analyses TCM patterns and pre-fills the formulation generator.*")

    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.markdown("### 📷 Camera Scan")

        scan_type = st.radio(
            "Scan Type",
            options=["full", "tongue", "face"],
            format_func=lambda x: {"full": "🔬 Full Diagnosis (Tongue + Face)", "tongue": "👅 Tongue Only", "face": "🙂 Face Only"}[x],
            horizontal=True,
            help="Full diagnosis gives highest accuracy by cross-referencing tongue and face findings"
        )

        # Camera guidance
        guide = get_camera_guidance(scan_type)
        with st.expander(f"{guide['icon']} {guide['title']} — Camera Tips", expanded=True):
            st.markdown("**How to scan:**")
            for step in guide["steps"]:
                st.markdown(f"• {step}")
            st.markdown("**Avoid:**")
            for item in guide["avoid"]:
                st.markdown(f"❌ {item}")

        # Camera input — works on desktop webcam AND mobile phone camera
        st.markdown("#### 📸 Capture Image")
        st.caption("On mobile: tap to open your phone camera. On desktop: uses webcam.")
        camera_image = st.camera_input(
            label="Point camera at tongue / face and capture",
            help="Works on desktop (webcam) and mobile phone (front or rear camera)"
        )

        # Alternative: file upload
        st.markdown("*— or —*")
        uploaded_file = st.file_uploader(
            "Upload a photo instead",
            type=["jpg", "jpeg", "png", "webp"],
            help="Upload an existing photo of your tongue or face"
        )

    with col_right:
        st.markdown("### 🔍 Analysis Results")

        image_bytes = None
        if camera_image is not None:
            image_bytes = camera_image.getvalue()
            st.image(camera_image, caption="Captured image", use_container_width=True)
        elif uploaded_file is not None:
            image_bytes = uploaded_file.read()
            st.image(image_bytes, caption="Uploaded image", use_container_width=True)

        if image_bytes:
            if not api_key:
                st.error("⚠️ Please enter your Anthropic API key in the sidebar to run analysis.")
            else:
                # Detect pipeline mode
                try:
                    from tongue_detector import get_detector
                    _detector = get_detector()
                    yolo_ready = _detector.is_ready
                except Exception:
                    _detector = None
                    yolo_ready = False

                if yolo_ready:
                    st.markdown(
                        '<div style="background:#052e16;border:1px solid #166534;border-radius:8px;padding:.5rem 1rem;'
                        'font-size:13px;color:#86efac;margin-bottom:.5rem">'
                        '⚡ <b>YOLOv8 + Claude Pipeline Active</b> — Trained on 19,585 tongue images'
                        '</div>',
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown(
                        '<div style="background:#0c1f3a;border:1px solid #1e40af;border-radius:8px;padding:.5rem 1rem;'
                        'font-size:13px;color:#93c5fd;margin-bottom:.5rem">'
                        '🧠 <b>Claude Vision Mode</b> — Train YOLOv8 model to enable full pipeline'
                        '</div>',
                        unsafe_allow_html=True
                    )

                analyze_btn = st.button("🧠 Analyse with AI Vision", type="primary", use_container_width=True)
                if analyze_btn:
                    spinner_msg = (
                        "⚡ YOLOv8 detecting tongue features → Claude synthesising TCM diagnosis..."
                        if yolo_ready else
                        "🔬 ChemiGranVision analysing tongue & face patterns..."
                    )
                    with st.spinner(spinner_msg):
                        try:
                            diag = analyze_with_yolo_pipeline(
                                image_bytes, scan_type, api_key,
                                detector=_detector if yolo_ready else None
                            )
                            st.session_state["last_vision_result"] = diag
                            st.session_state["vision_condition"] = diag.get("suggested_condition_input", "")
                            st.session_state["vision_pattern"] = diag.get("suggested_tcm_pattern", "")
                            st.session_state["vision_demographic"] = diag.get("suggested_demographic", "")
                            diag["scan_type"] = scan_type
                            save_visual_diagnosis(diag)

                            # Show YOLO annotated image if available
                            annotated = diag.get("annotated_image")
                            if annotated is not None:
                                st.markdown("#### 🎯 YOLO Detection Overlay")
                                st.image(annotated, caption="YOLOv8 tongue feature detections", use_container_width=True)

                                # Detection table
                                yolo_dets = diag.get("yolo_detections", [])
                                if yolo_dets:
                                    st.markdown("**Detected Features:**")
                                    rows = ""
                                    for d in yolo_dets:
                                        rows += (
                                            f"<tr>"
                                            f"<td>{d['zh']}</td>"
                                            f"<td style='color:#94a3b8;font-size:12px'>{d['class_name']}</td>"
                                            f"<td style='color:#7ec8e3;font-weight:600'>{d['confidence']:.0f}%</td>"
                                            f"<td style='font-size:12px;color:#64748b'>{d['tcm_significance']}</td>"
                                            f"</tr>"
                                        )
                                    st.markdown(f"""
                                    <table class="herb-table">
                                      <thead><tr>
                                        <th>Feature (中文)</th><th>Class</th><th>Confidence</th><th>TCM Significance</th>
                                      </tr></thead>
                                      <tbody>{rows}</tbody>
                                    </table>""", unsafe_allow_html=True)

                                # YOLO patterns
                                yolo_patterns = diag.get("yolo_patterns", [])
                                if yolo_patterns:
                                    st.markdown("**YOLO-Derived Patterns:**")
                                    for p in yolo_patterns[:3]:
                                        bar_w = int(p.get("confidence", 0))
                                        st.markdown(
                                            f'<div style="background:#0d1e30;border-radius:8px;padding:.5rem .8rem;margin:.3rem 0">'
                                            f'<div style="display:flex;justify-content:space-between">'
                                            f'<span style="color:#cbd5e1;font-size:13px">{p["pattern"]}</span>'
                                            f'<span style="color:#7ec8e3;font-size:13px;font-weight:600">{bar_w}%</span>'
                                            f'</div>'
                                            f'<div class="confidence-bar" style="margin-top:.3rem">'
                                            f'<div class="confidence-fill" style="width:{bar_w}%"></div>'
                                            f'</div></div>',
                                            unsafe_allow_html=True
                                        )

                        except Exception as e:
                            st.error(f"Analysis failed: {e}")
                            st.session_state["last_vision_result"] = None
        else:
            st.info("📷 Capture or upload an image to begin analysis")
            st.markdown("""
            <div class="scan-guide">
              <h4>🌿 What ChemiGranVision Analyses</h4>
              <ul>
                <li><b>Tongue colour & coating</b> — Blood/Qi status, Heat/Cold, Damp patterns</li>
                <li><b>Tongue shape & moisture</b> — Spleen Qi, Yin deficiency, fluid status</li>
                <li><b>Facial complexion</b> — Five-organ zone mapping (Heart, Liver, Spleen, Lung, Kidney)</li>
                <li><b>Eye assessment</b> — Shen (spirit) quality, Blood status</li>
                <li><b>Body constitution</b> — Wang Qi 9-constitution classification</li>
                <li><b>TCM pattern matching</b> — Cross-referenced against clinical tongue/face image datasets</li>
              </ul>
            </div>""", unsafe_allow_html=True)

    # Show results below
    if "last_vision_result" in st.session_state and st.session_state["last_vision_result"]:
        st.markdown("---")
        st.markdown("## 📊 Diagnosis Results")
        diag = st.session_state["last_vision_result"]
        render_vision_results(diag)

        # Narrative enrichment
        with st.expander("📖 Plain-English Explanation"):
            if st.button("Generate Explanation", key="gen_explain"):
                if api_key:
                    with st.spinner("Generating explanation..."):
                        narrative = enrich_visual_diagnosis(diag, api_key)
                    st.write(narrative)
                else:
                    st.error("API key required")

        # CTA: Send to formulation generator
        st.markdown("---")
        st.markdown("### 🧪 Use This Diagnosis in Formulation Generator")
        cond_prefill = diag.get("suggested_condition_input", "")
        pattern_prefill = diag.get("suggested_tcm_pattern", "")
        focus_prefill = ", ".join(diag.get("recommended_focus_areas", []))

        st.info(f"**Pre-filled condition:** {cond_prefill}  \n**Pre-filled TCM pattern:** {pattern_prefill}  \n**Focus areas:** {focus_prefill}")

        if st.button("➡️ Send to Formulation Generator", type="primary", use_container_width=True):
            st.session_state["vision_to_formula"] = True
            st.success("✅ Diagnosis loaded! Switch to the **🧪 Formulation Generator** tab to generate a formula.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — FORMULATION GENERATOR
# ══════════════════════════════════════════════════════════════════════════════
with tab_formulation:
    st.markdown("## 🧪 AI Formulation Generator")
    st.markdown("*Generate evidence-based TCM granule formulas using Chemigran's 551-herb inventory.*")

    # Check if vision pre-fill is available
    vision_prefill = st.session_state.get("vision_to_formula", False)
    if vision_prefill:
        st.success("🔬 Vision diagnosis pre-filled below — review and generate formula")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("### 📝 Product Profile")

        default_condition = st.session_state.get("vision_condition", "") if vision_prefill else ""
        default_pattern = st.session_state.get("vision_pattern", "") if vision_prefill else ""
        default_demo = st.session_state.get("vision_demographic", "") if vision_prefill else ""

        condition = st.text_area(
            "Health Condition / Symptoms *",
            value=default_condition,
            placeholder="e.g. Poor sleep, difficulty falling asleep, waking at 3am, palpitations, dream-disturbed sleep",
            height=100
        )
        tcm_pattern = st.text_input(
            "TCM Pattern (optional — AI will determine if blank)",
            value=default_pattern,
            placeholder="e.g. Heart Blood Deficiency; Liver Qi Stagnation"
        )
        demographic = st.text_input(
            "Target Demographic",
            value=default_demo,
            placeholder="e.g. Singapore professionals aged 30–50, female, high stress"
        )

    with col2:
        st.markdown("### ⚙️ Formula Preferences")
        preferences = st.text_area(
            "Special Requirements",
            placeholder="e.g. Max 8 herbs, focus on Suan Zao Ren Tang base, suitable for vegetarians",
            height=80
        )
        avoid_herbs = st.text_input(
            "Herbs to Avoid",
            placeholder="e.g. 附子, 麻黄 (separate with commas)"
        )
        format_type = st.selectbox(
            "Product Format",
            ["Granule blend", "Single-dose sachet 5g", "Single-dose sachet 3g", "Capsule-fill granule"]
        )

    # Vision context integration
    vision_context_str = ""
    if vision_prefill and "last_vision_result" in st.session_state:
        vr = st.session_state["last_vision_result"]
        vision_context_str = (
            f"Vision diagnosis detected: {vr.get('primary_pattern','')} ({vr.get('primary_pattern_zh','')}). "
            f"Constitution: {vr.get('constitution_type','')}. "
            f"Tongue: {vr.get('tongue',{}).get('findings_summary','')} "
            f"Face: {vr.get('face',{}).get('findings_summary','')} "
            f"Therapeutic principles: {', '.join(vr.get('recommended_therapeutic_principles',[]))}"
        )
        with st.expander("🔬 Vision Diagnosis Context (sent to AI)"):
            st.write(vision_context_str)

    if st.button("🌿 Generate Formulation", type="primary", use_container_width=True):
        if not condition:
            st.error("Please enter a health condition / symptoms")
        elif not api_key:
            st.error("Please enter your Anthropic API key in the sidebar")
        else:
            with st.spinner("🧠 ChemiGranAI generating formulation from 551-herb inventory..."):
                try:
                    result = generate_formulation({
                        "condition": condition,
                        "tcm_pattern": tcm_pattern,
                        "demographic": demographic,
                        "preferences": preferences,
                        "avoid_herbs": avoid_herbs,
                        "format": format_type,
                        "vision_context": vision_context_str,
                    }, api_key)
                    result["source"] = "vision+ai" if vision_prefill else "manual"
                    st.session_state["last_result"] = result
                    if vision_prefill:
                        st.session_state["vision_to_formula"] = False
                except Exception as e:
                    st.error(f"Generation failed: {e}")

    if "last_result" in st.session_state and st.session_state["last_result"]:
        st.markdown("---")
        st.markdown("## 📊 Generated Formula")
        render_product_card(st.session_state["last_result"], key_suffix="gen")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — KNOWLEDGE BASE
# ══════════════════════════════════════════════════════════════════════════════
with tab_knowledge:
    st.markdown("## 📚 Knowledge Base")
    st.markdown("*All saved formulations from manual generation and vision-assisted diagnosis.*")

    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        search_q = st.text_input("🔍 Search", placeholder="Product name, condition, TCM pattern, tags...")
    with col2:
        show_starred = st.checkbox("★ Starred only")
    with col3:
        if st.button("🔄 Refresh"):
            st.rerun()

    formulations = search_formulations(search_q) if search_q else get_all_formulations()
    if show_starred:
        formulations = [f for f in formulations if f.get("starred")]

    if not formulations:
        st.info("No formulations saved yet. Generate one in the Formulation Generator tab.")
    else:
        st.caption(f"{len(formulations)} formulation(s) found")
        for form in formulations:
            fid = form["id"]
            name = form.get("product_name_en", "Unnamed")
            name_zh = form.get("product_name_zh", "")
            pattern = form.get("tcm_pattern", "")
            created = form.get("created_at", "")[:16]
            starred = form.get("starred", 0)
            source = form.get("source", "manual")

            star_icon = "★" if starred else "☆"
            source_badge = "🔬 Vision+AI" if source == "vision+ai" else "✍️ Manual"

            with st.expander(f"{star_icon} {name} | {name_zh} | {pattern} | {source_badge} | {created}"):
                formula_list = form.get("formula_json", [])
                if formula_list:
                    render_product_card({
                        "product_name_en": name,
                        "product_name_zh": name_zh,
                        "tcm_pattern": pattern,
                        "formula": formula_list,
                        "safety": form.get("safety_json", {}),
                        "commercial": form.get("commercial_json", {}),
                        "gross_margin_est": form.get("gross_margin_est", ""),
                        "suggested_price_sgd": form.get("commercial_json", {}).get("suggested_price_sgd", ""),
                        "formula_complexity": form.get("formula_complexity", ""),
                        "formula_rationale": form.get("rationale", ""),
                        "evidence_summary": form.get("evidence", ""),
                        "dosage_recommendation": form.get("dosage", ""),
                        "tags": form.get("tags", []),
                    }, show_business_btn=True, compact=True, key_suffix=f"kb{fid}")

                c1, c2, c3 = st.columns(3)
                if c1.button(f"{'★ Unstar' if starred else '☆ Star'}", key=f"star_{fid}"):
                    toggle_star(fid)
                    st.rerun()
                if c2.button("🗑️ Delete", key=f"del_{fid}"):
                    delete_formulation(fid)
                    st.rerun()
                if c3.button("📊 Business Case", key=f"bc_{fid}"):
                    if api_key:
                        with st.spinner("Generating..."):
                            bc = generate_business_case(name, {
                                "product_name_zh": name_zh,
                                "tcm_pattern": pattern,
                                "formula": formula_list,
                                "gross_margin_est": form.get("gross_margin_est",""),
                                "commercial": form.get("commercial_json",{}),
                            }, api_key)
                        st.markdown(bc)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — INVENTORY BROWSER
# ══════════════════════════════════════════════════════════════════════════════
with tab_inventory:
    st.markdown("## 🌿 Inventory Browser")
    st.markdown("*Browse and search the 551-herb Chemigran granule inventory.*")

    all_herbs = get_all_herbs()
    all_categories = sorted(set(c for h in all_herbs for c in h.get("categories", [])))

    col1, col2 = st.columns([2, 1])
    with col1:
        inv_search = st.text_input("🔍 Search herbs", placeholder="Chinese name, pinyin, English, TCM function...")
    with col2:
        selected_cat = st.selectbox("Filter by Category", ["All"] + all_categories)

    filtered = all_herbs
    if inv_search:
        q = inv_search.lower()
        filtered = [h for h in filtered if
                    q in h.get("chinese","").lower() or
                    q in h.get("pinyin","").lower() or
                    q in h.get("english","").lower() or
                    q in h.get("tcm_functions","").lower()]
    if selected_cat != "All":
        filtered = [h for h in filtered if selected_cat in h.get("categories", [])]

    st.caption(f"Showing {len(filtered)} of {len(all_herbs)} herbs")

    for herb in filtered[:50]:
        with st.expander(f"{herb['chinese']} — {herb['pinyin']} — {herb['english']}"):
            c1, c2, c3 = st.columns(3)
            c1.metric("Extract Ratio", herb["extract_ratio"])
            c2.metric("Raw per 1g granule", f"{herb['raw_per_g']}g")
            c3.metric("Raw per bag", f"{herb['raw_per_bag']}g")
            st.markdown(f"**TCM Functions:** {herb['tcm_functions']}")
            st.markdown(f"**Contraindications:** {herb['contraindications']}")
            cats = herb.get("categories", [])
            st.markdown("**Categories:** " + " ".join(f'<span class="meta-pill">{c}</span>' for c in cats),
                        unsafe_allow_html=True)

            if api_key:
                condition_for_evidence = st.text_input("Enrich evidence for condition:", key=f"ev_cond_{herb['id']}",
                                                        placeholder="e.g. insomnia, thyroid nodule")
                if st.button("🔬 Fetch Evidence", key=f"ev_btn_{herb['id']}"):
                    with st.spinner("Fetching..."):
                        ev = enrich_evidence(herb["chinese"], condition_for_evidence or "general", api_key)
                    st.markdown(f'<div class="info-box evidence">{ev}</div>', unsafe_allow_html=True)
                    if st.button("💾 Save Evidence", key=f"ev_save_{herb['id']}"):
                        save_knowledge_entry(herb["chinese"], herb["english"], ev, "AI enrichment")
                        st.success("Saved!")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — EVIDENCE ENRICHER
# ══════════════════════════════════════════════════════════════════════════════
with tab_evidence:
    st.markdown("## 🔍 Evidence Enricher")
    st.markdown("*Search clinical evidence for specific herbs and conditions. Powered by claude-haiku-4-5-20251001 for speed.*")

    col1, col2 = st.columns(2)
    with col1:
        ev_herb = st.text_input("Herb (Chinese or English)", placeholder="e.g. 炒酸枣仁 or Ziziphus Seed")
    with col2:
        ev_condition = st.text_input("Condition / Indication", placeholder="e.g. insomnia, sleep quality, anxiety")

    if st.button("🔬 Fetch Clinical Evidence", type="primary"):
        if not ev_herb or not ev_condition:
            st.warning("Please enter both herb and condition")
        elif not api_key:
            st.error("API key required")
        else:
            with st.spinner("Searching clinical evidence..."):
                ev_text = enrich_evidence(ev_herb, ev_condition, api_key)
            st.markdown(f'<div class="info-box evidence">{ev_text}</div>', unsafe_allow_html=True)

            col1, col2 = st.columns(2)
            if col1.button("💾 Save to Knowledge Base"):
                save_knowledge_entry(ev_herb, ev_herb, ev_text, "Evidence Enricher", ev_condition)
                st.success("Saved!")

    st.markdown("---")
    st.markdown("### 📋 Saved Knowledge Entries")
    filter_herb = st.text_input("Filter by herb:", placeholder="Chinese name...")
    entries = get_knowledge_entries(filter_herb)
    for entry in entries:
        with st.expander(f"{entry.get('herb_chinese','')} — {entry.get('category','')} — {entry.get('created_at','')[:16]}"):
            st.write(entry.get("evidence_text",""))
