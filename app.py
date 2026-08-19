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
from vitals_engine import assess_vitals

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
  /* Horizontal padding only — the top padding is Streamlit's and it is what
     keeps content clear of the fixed header. Overriding it pulls the tabs up
     underneath. */
  .block-container { padding-left: 2rem; padding-right: 2rem; }

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
    /* z-index kept below the header so it can never cover the sidebar toggle */
    position:sticky; top:3.5rem; z-index:1; background:#0f1923; padding:.4rem 0;
    overflow-x: auto !important;
    -webkit-overflow-scrolling: touch !important;
    scrollbar-width: none !important;
    flex-wrap: nowrap !important;
    display: flex !important;
  }
  .stTabs [data-baseweb="tab-list"]::-webkit-scrollbar { display: none; }
  /* NOTE: [data-testid="stToolbar"] does NOT match the Share/GitHub menu on
     Streamlit 1.61 — verified live, the menu stayed visible. Left out until the
     real selector is confirmed by inspecting the page, rather than guessing.
     The <header> itself must stay untouched: the sidebar toggle is its child. */

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
    if show_key:
        api_key = st.text_area(
            "🔑 Anthropic API Key",
            value=ANTHROPIC_API_KEY,
            height=120,
            help="Paste your full key here — it will wrap across lines so you can read it"
        ).strip()
    else:
        api_key = st.text_input(
            "🔑 Anthropic API Key",
            value=ANTHROPIC_API_KEY,
            type="password",
            help="Tick 'Show key' on mobile to paste and verify your key"
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
        # Read the real figures from the training run rather than hardcoding.
        try:
            import json as _json
            _rel = _json.loads(
                (_model_path.parent / "class_reliability.json").read_text(encoding="utf-8")
            )
            _n = _rel["train_images"] + _rel["val_images"] + _rel["test_images"]
            _reliable = len(_rel.get("reliable_classes", []))
            st.success(f"Model ready — trained on {_n:,} images")
            st.caption(
                f"mAP50 {_rel['test_map50']:.3f} on {_rel['test_images']} held-out "
                f"test images · {_reliable} of {_rel['nc']} classes meet the "
                f"reliability threshold"
            )
        except Exception:
            st.success("Model ready")
            st.caption("class_reliability.json missing — per-class accuracy unknown")
    else:
        st.markdown("**⚡ YOLOv8 Pipeline**")
        st.caption("No model trained yet")
        st.caption("Run: `python setup_dataset.py --zip ...`")
        st.caption("Then: `python train_yolo.py`")

    st.divider()
    st.markdown(f"*Powered by Claude Vision + claude-sonnet-4-5*")
    st.markdown(f"*{APP_SUBTITLE}*")


# ── Helper: render product card ───────────────────────────────────────────────
def render_field(container, label: str, value):
    """
    Label + free-text value that wraps instead of truncating.

    st.metric clips its value to one line with an ellipsis — fine for numbers,
    but these diagnosis fields are full descriptive sentences.
    """
    text = str(value).strip() or "—"
    safe = (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
    )
    container.markdown(
        '<div style="margin-bottom:.85rem">'
        '<div style="font-size:.75rem;color:#9ca3af;text-transform:uppercase;'
        'letter-spacing:.04em;margin-bottom:.15rem">' + label + '</div>'
        '<div style="font-size:.95rem;line-height:1.45;color:inherit">' + safe + '</div>'
        '</div>',
        unsafe_allow_html=True,
    )


def render_formula_checks(result: dict) -> bool:
    """
    Show the deterministic checks that ran after generation.

    Returns False if the formula must not be displayed at all. A classical
    incompatibility is not a caveat to print underneath a nice-looking product
    card — it means the formula is wrong and showing it invites someone to make it.
    """
    safety = result.get("safety_check") or {}
    grounding = result.get("grounding_check") or {}

    blocking = safety.get("blocking") or []
    if blocking:
        st.error("⛔ Formula blocked — classical incompatibility detected")
        for v in blocking:
            st.markdown(
                f"**{v['rule']}**  \n"
                f"Herbs involved: {'、'.join(v['herbs'])}  \n"
                f"{v['note']}"
            )
        st.caption("Regenerate, or exclude one side of the pair using 'Herbs to avoid'.")
        return False

    for v in safety.get("violations", []):
        st.warning(f"⚠ {v['rule']} — {'、'.join(v['herbs'])}. {v['note']}")

    unknown = grounding.get("unknown_herbs") or []
    if unknown:
        st.error(
            "⛔ Formula contains herbs that are not in the Chemigran inventory and "
            f"cannot be manufactured: {'、'.join(unknown)}"
        )
        return False

    ungrounded = grounding.get("ungrounded") or []
    if ungrounded:
        with st.expander(f"⚠ {len(ungrounded)} herb(s) justified by text not in the inventory", expanded=True):
            st.caption(
                "The stated reason for including these herbs does not match their "
                "recorded actions. Treat the justification as unverified."
            )
            for u in ungrounded:
                st.markdown(
                    f"**{u['herb']}**  \n"
                    f"Claimed: *{u['claimed']}*  \n"
                    f"Inventory records: {u['inventory_says']}"
                )

    flagged = safety.get("flagged_herbs") or {}
    if flagged:
        with st.expander(f"🔍 Safety flags on {len(flagged)} herb(s)"):
            for herb, flags in flagged.items():
                st.markdown(f"**{herb}** — {', '.join(flags)}")

    derived = safety.get("derived_knowledge_count", 0)
    if derived:
        st.caption(
            f"ℹ {derived} herb(s) in this formula rely on generated reference data "
            "that has not been practitioner-reviewed."
        )

    return True


def render_product_card(result: dict, show_business_btn: bool = True, compact: bool = False, key_suffix: str = ""):
    if not render_formula_checks(result):
        return

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

    # ── Vitals conflict warning — measurements override the photo ─────────────
    conflicts = diag.get("vitals_conflicts", [])
    if conflicts:
        st.markdown(
            '<div style="background:#431407;border:2px solid #ea580c;border-radius:10px;'
            'padding:1rem 1.2rem;margin-bottom:1rem">'
            '<div style="color:#fdba74;font-size:15px;font-weight:700">'
            '⚠️ Measured vitals contradict the image-based reading</div>'
            + "".join(f'<div style="color:#fed7aa;font-size:13px;margin-top:.5rem">• {c}</div>'
                      for c in conflicts)
            + '<div style="color:#fff;font-size:13px;margin-top:.6rem">'
              'Confidence has been reduced accordingly. Objective measurements are '
              'more reliable than photo inference.</div></div>',
            unsafe_allow_html=True
        )

    # ── Honest confidence banner ──────────────────────────────────────────────
    is_balanced = ("balanced" in primary.lower()) or ("no significant" in primary.lower())
    capped = diag.get("confidence_capped_because", [])

    if is_balanced:
        st.markdown(
            '<div style="background:#052e16;border:1px solid #166534;border-radius:10px;'
            'padding:.9rem 1.1rem;margin-bottom:1rem;color:#86efac;font-size:14px">'
            '✅ <b>No significant TCM pattern detected — appears balanced (平和质)</b><br>'
            '<span style="color:#4ade80;font-size:13px">This is a normal, healthy result. '
            'Roughly 4 in 10 people fall into this category.</span></div>',
            unsafe_allow_html=True
        )
    elif confidence < 55:
        st.markdown(
            f'<div style="background:#1c1707;border:1px solid #92400e;border-radius:10px;'
            f'padding:.9rem 1.1rem;margin-bottom:1rem;color:#fcd34d;font-size:14px">'
            f'⚠️ <b>Low confidence ({confidence}%) — treat as indicative only</b><br>'
            f'<span style="font-size:13px">'
            f'{"Confidence limited by: " + ", ".join(capped) if capped else "Evidence in this image is limited or ambiguous."}'
            f'</span></div>',
            unsafe_allow_html=True
        )

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
            strength_color = {"strong": "#22c55e", "moderate": "#eab308", "weak": "#ef4444"}
            for pat in patterns_data:
                conf = pat.get("confidence", 0)
                strength = str(pat.get("evidence_strength", "")).lower()
                sc = strength_color.get(strength, "#64748b")
                badge = (f'<span style="background:{sc}22;border:1px solid {sc}66;color:{sc};'
                         f'padding:1px 8px;border-radius:10px;font-size:10px;text-transform:uppercase;'
                         f'letter-spacing:.05em">{strength} evidence</span>') if strength else ""
                st.markdown(f"""
                <div style="margin:.4rem 0;padding:.6rem .8rem;background:#0d1e30;border-radius:8px">
                  <div style="display:flex;justify-content:space-between;align-items:center">
                    <span style="color:#cbd5e1;font-size:13px">{pat.get('pattern_en','')}</span>
                    <span style="color:#7ec8e3;font-size:13px;font-weight:600">{conf}%</span>
                  </div>
                  <div style="color:#475569;font-size:12px">{pat.get('pattern_zh','')}</div>
                  <div class="confidence-bar" style="margin-top:.4rem">
                    <div class="confidence-fill" style="width:{conf}%"></div>
                  </div>
                  <div style="margin-top:.4rem">{badge}</div>
                </div>""", unsafe_allow_html=True)

                support = pat.get("supporting_indicators", []) or []
                contra = pat.get("contradicting_indicators", []) or []
                if support or contra:
                    with st.expander(f"🔎 Evidence for {pat.get('pattern_en','')[:38]}"):
                        if support:
                            st.markdown("**✓ Observed evidence supporting this:**")
                            for s in support:
                                st.markdown(f"<span style='color:#86efac;font-size:13px'>• {s}</span>",
                                            unsafe_allow_html=True)
                        if contra:
                            st.markdown("**✗ Evidence against this:**")
                            for c in contra:
                                st.markdown(f"<span style='color:#fca5a5;font-size:13px'>• {c}</span>",
                                            unsafe_allow_html=True)
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
        # st.metric truncates its value to a single line, which cuts these
        # descriptions off mid-word. Render as markdown so they wrap in full.
        render_field(tc1, "Body Colour", tongue.get("body_color", "—"))
        render_field(tc2, "Coating", tongue.get("coating_color", "—"))
        render_field(tc3, "Shape", tongue.get("shape", "—"))
        render_field(tc4, "Moisture", tongue.get("moisture", "—"))
        if tongue.get("special_features"):
            st.caption("Special features: " + ", ".join(tongue["special_features"]))
        if tongue.get("findings_summary"):
            st.markdown(f'<div class="info-box vision">{tongue["findings_summary"]}</div>', unsafe_allow_html=True)

    # Face findings
    if face and diag.get("face_visible"):
        st.markdown("**🙂 Face Diagnosis (面诊)**")
        fc1, fc2 = st.columns([1, 2])
        with fc1:
            render_field(fc1, "Complexion", face.get("overall_complexion", "—"))
            render_field(fc1, "Lustre", face.get("lustre", "—"))
            render_field(fc1, "Skin", face.get("skin_texture", "—"))
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

    # Herb hints — only when there is an actual pattern to treat
    if not is_balanced:
        hint_herbs = get_pattern_herb_hints(primary)
        if hint_herbs:
            st.markdown(f"**🌿 Key Herbs Suggested for {primary}:**")
            st.markdown(" ".join(f'<span class="meta-pill blue">{h}</span>' for h in hint_herbs), unsafe_allow_html=True)
            st.caption("Indicative only — final formulation is generated from the full 551-herb inventory.")

    # ── Objective vitals panel ────────────────────────────────────────────────
    v = diag.get("vitals")
    if v and v.get("entered"):
        st.markdown("---")
        st.markdown("**📊 Objective Measurements** *(carry more weight than image inference)*")
        pt, bt, mt = v["pulse_tcm"], v["bp_tcm"], v.get("bmi_tcm")
        oc1, oc2, oc3 = st.columns(3)
        oc1.metric("Blood Pressure", f"{v['systolic']}/{v['diastolic']} mmHg", bt["category"])
        oc2.metric("Pulse 脉率", f"{v['pulse']} bpm",
                   f"{pt['category_zh']} {pt['category_en']}")
        if mt:
            oc3.metric("BMI", mt["bmi"], mt["category"])

        if v.get("corroborated_patterns"):
            st.markdown("**Patterns independently supported by ≥2 measurements:**")
            st.markdown(" ".join(
                f'<span class="meta-pill green">{p}</span>'
                for p in v["corroborated_patterns"]
            ), unsafe_allow_html=True)
        elif v.get("objective_patterns"):
            st.markdown("**Patterns suggested by measurements:**")
            st.markdown(" ".join(
                f'<span class="meta-pill blue">{p}</span>'
                for p in v["objective_patterns"]
            ), unsafe_allow_html=True)
        else:
            st.markdown(
                "<span style='color:#86efac;font-size:13px'>"
                "✓ All measurements within normal limits — no pattern indication from vitals"
                "</span>", unsafe_allow_html=True)

    # ── Transparency: what was actually observed vs inferred ─────────────────
    st.markdown("---")
    raw_obs = diag.get("raw_observations", []) or []
    deviations = diag.get("deviations_from_normal", []) or []
    limitations = diag.get("limitations", []) or []
    conf_rationale = diag.get("confidence_rationale", "")

    with st.expander("🔍 How this assessment was reached (transparency)"):
        if conf_rationale:
            st.markdown(f"**Why confidence is {confidence}%:**")
            st.caption(conf_rationale)
            if diag.get("confidence_capped_because"):
                st.caption("Confidence capped by: " + ", ".join(diag["confidence_capped_because"]))
            st.markdown("")

        if raw_obs:
            st.markdown("**📷 Raw visual observations (what the AI literally saw):**")
            for o in raw_obs:
                st.markdown(f"<span style='color:#cbd5e1;font-size:13px'>• {o}</span>",
                            unsafe_allow_html=True)
            st.markdown("")

        st.markdown("**⚖️ Findings outside normal limits:**")
        if deviations:
            for d in deviations:
                st.markdown(f"<span style='color:#fcd34d;font-size:13px'>• {d}</span>",
                            unsafe_allow_html=True)
        else:
            st.markdown("<span style='color:#86efac;font-size:13px'>• None — all observations within normal healthy range</span>",
                        unsafe_allow_html=True)
        st.markdown("")

        st.markdown("**🚧 What this assessment cannot tell you:**")
        has_vitals = bool(diag.get("vitals_entered"))
        default_limits = [
            "Symptom history, sleep, digestion, emotional state (问诊 inquiry)",
            "Sound and odour assessment (闻诊)",
        ]
        if has_vitals:
            default_limits.insert(0,
                "Pulse rate is captured, but the other ~27 classical pulse qualities "
                "(floating/sinking, slippery/choppy, wiry, etc.) require palpation by a practitioner")
        else:
            default_limits.insert(0,
                "Pulse diagnosis (脉诊) — no vitals were entered for this assessment")
        for l in (limitations + default_limits):
            st.markdown(f"<span style='color:#94a3b8;font-size:13px'>• {l}</span>",
                        unsafe_allow_html=True)

        # Method provenance
        mode = diag.get("pipeline_mode", "claude_only")
        st.markdown("")
        st.markdown("**🧬 Method used:**")
        if mode == "yolo+claude":
            st.markdown("<span style='color:#86efac;font-size:13px'>• YOLOv8 object detection (trained on labelled tongue dataset) + Claude Vision synthesis</span>",
                        unsafe_allow_html=True)
            st.caption("Note: the detector is reliable for coating colour; other feature classes have lower validated accuracy.")
        else:
            st.markdown("<span style='color:#93c5fd;font-size:13px'>• Claude Vision only — general-purpose AI applying TCM observation criteria</span>",
                        unsafe_allow_html=True)
            st.caption("No specialised tongue detector is active. Findings are AI inference from the photo, not measurement against a labelled clinical dataset.")

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

    # ══════════════════════════════════════════════════════════════════════════
    # STEP 1 — OBJECTIVE VITALS (required)
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown("### 1️⃣ Vital Signs *(required)*")
    st.caption(
        "Pulse rate is a genuine objective component of 脉诊 (pulse diagnosis) — "
        "迟脉/数脉 (slow/rapid) map directly to Cold/Heat patterns. These "
        "measurements carry more diagnostic weight than anything inferred from a photo."
    )

    with st.container():
        vc1, vc2, vc3, vc4 = st.columns(4)
        with vc1:
            v_systolic = st.number_input("Systolic BP (mmHg)", min_value=60, max_value=260,
                                         value=120, step=1,
                                         help="The upper/larger number on your BP monitor")
        with vc2:
            v_diastolic = st.number_input("Diastolic BP (mmHg)", min_value=30, max_value=160,
                                          value=80, step=1,
                                          help="The lower/smaller number on your BP monitor")
        with vc3:
            v_pulse = st.number_input("Resting Pulse (bpm)", min_value=30, max_value=220,
                                      value=72, step=1,
                                      help="Measure after sitting quietly for 5 minutes")
        with vc4:
            v_age = st.number_input("Age", min_value=1, max_value=120, value=35, step=1)

        vc5, vc6, vc7 = st.columns(3)
        with vc5:
            v_sex = st.selectbox("Sex", ["Female", "Male", "Prefer not to say"])
        with vc6:
            v_height = st.number_input("Height (cm)", min_value=80.0, max_value=230.0,
                                       value=165.0, step=0.5)
        with vc7:
            v_weight = st.number_input("Weight (kg)", min_value=25.0, max_value=250.0,
                                       value=65.0, step=0.5)

        vitals_confirmed = st.checkbox(
            "✓ I confirm these readings were taken at rest within the last 24 hours",
            value=False,
            help="Readings taken during or shortly after exercise, stress or caffeine are not valid at rest."
        )

    # Assess vitals immediately so red flags surface before any scanning
    vitals = None
    if vitals_confirmed:
        vitals = assess_vitals(
            systolic=int(v_systolic), diastolic=int(v_diastolic), pulse=int(v_pulse),
            age=int(v_age), sex=v_sex, height_cm=float(v_height), weight_kg=float(v_weight),
        )
        st.session_state["vitals"] = vitals

        # ── Clinical red flags — these take priority over everything ──────────
        for flag in vitals["red_flags"]:
            if flag["severity"] == "critical":
                st.markdown(
                    f'<div style="background:#450a0a;border:2px solid #dc2626;border-radius:10px;'
                    f'padding:1rem 1.2rem;margin:.6rem 0">'
                    f'<div style="color:#fca5a5;font-size:16px;font-weight:700">🚨 {flag["title"]}</div>'
                    f'<div style="color:#fecaca;font-size:14px;margin-top:.5rem">{flag["message"]}</div>'
                    f'<div style="color:#fff;font-size:14px;font-weight:600;margin-top:.6rem">'
                    f'→ {flag["action"]}</div></div>',
                    unsafe_allow_html=True
                )
            elif flag["severity"] == "high":
                st.warning(f"**{flag['title']}**\n\n{flag['message']}\n\n→ {flag['action']}")
            else:
                st.info(f"**{flag['title']}**\n\n{flag['message']}\n\n→ {flag['action']}")

        # ── TCM reading of the vitals ─────────────────────────────────────────
        pt = vitals["pulse_tcm"]
        bt = vitals["bp_tcm"]
        mt = vitals["bmi_tcm"]

        with st.expander("📈 TCM reading of your vitals", expanded=not vitals["red_flags"]):
            mc1, mc2, mc3 = st.columns(3)
            mc1.metric("Blood Pressure", f"{v_systolic}/{v_diastolic}", bt["category"])
            mc2.metric("Pulse 脉率", f"{v_pulse} bpm",
                       f"{pt['category_zh']} {pt['category_en']}")
            if mt:
                mc3.metric("BMI", mt["bmi"], mt["category"])

            st.markdown(f"**脉诊 Pulse:** {pt['tcm_significance']}")
            if pt.get("note"):
                st.caption(pt["note"])
            st.markdown(f"**Blood pressure:** {bt['tcm_significance']}")
            if mt:
                st.markdown(f"**BMI:** {mt['note']}")

            if vitals["corroborated_patterns"]:
                st.markdown("**Patterns supported by more than one measurement:**")
                st.markdown(" ".join(
                    f'<span class="meta-pill green">{p}</span>'
                    for p in vitals["corroborated_patterns"]
                ), unsafe_allow_html=True)
    else:
        st.info("👆 Enter your vital signs and tick the confirmation box to unlock the camera scan.")

    st.markdown("---")
    st.markdown("### 2️⃣ Camera Scan")

    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.markdown("#### 📷 Capture")

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

        # Capture state. Held in session so the camera widget can be swapped out
        # once we have an image — otherwise st.camera_input keeps its own preview
        # on screen and the photo ends up displayed twice.
        if "cap_bytes" not in st.session_state:
            st.session_state.cap_bytes = None
            st.session_state.cap_label = ""
            st.session_state.cap_nonce = 0   # bumped to reset the widgets on retake

        if st.session_state.cap_bytes is None:
            # Camera input — works on desktop webcam AND mobile phone camera
            st.markdown("#### 📸 Capture Image")
            st.caption("On mobile: tap to open your phone camera. On desktop: uses webcam.")
            camera_image = st.camera_input(
                label="Point camera at tongue / face and capture",
                key=f"cam_{st.session_state.cap_nonce}",
                help="Works on desktop (webcam) and mobile phone (front or rear camera)"
            )

            # Alternative: file upload
            st.markdown("*— or —*")
            uploaded_file = st.file_uploader(
                "Upload a photo instead",
                type=["jpg", "jpeg", "png", "webp"],
                key=f"up_{st.session_state.cap_nonce}",
                help="Upload an existing photo of your tongue or face"
            )

            if camera_image is not None:
                st.session_state.cap_bytes = camera_image.getvalue()
                st.session_state.cap_label = "Captured image"
                st.rerun()
            elif uploaded_file is not None:
                st.session_state.cap_bytes = uploaded_file.read()
                st.session_state.cap_label = "Uploaded image"
                st.rerun()
        else:
            st.success(f"✓ {st.session_state.cap_label} ready — review it on the right, then run the analysis.")
            if st.button("🔄 Retake / choose another photo", use_container_width=True):
                st.session_state.cap_bytes = None
                st.session_state.cap_label = ""
                st.session_state.cap_nonce += 1
                st.rerun()

    with col_right:
        st.markdown("### 🔍 Analysis Results")

        image_bytes = st.session_state.cap_bytes
        if image_bytes:
            st.image(image_bytes, caption=st.session_state.cap_label, use_container_width=True)

        if image_bytes:
            if not vitals_confirmed:
                st.warning("⚠️ Enter and confirm your vital signs above before running analysis.")
            elif not api_key:
                st.error("⚠️ Please enter your Anthropic API key in the sidebar to run analysis.")
            else:
                # ── Detector status ───────────────────────────────────────────
                try:
                    from tongue_detector import get_detector
                    _detector = get_detector()
                    _diag_info = _detector.diagnostics()
                    yolo_ready = _detector.is_ready
                except Exception as e:
                    _detector = None
                    _diag_info = {"ready": False, "load_error": f"{type(e).__name__}: {e}"}
                    yolo_ready = False

                if yolo_ready:
                    st.markdown(
                        f'<div style="background:#052e16;border:1px solid #166534;border-radius:8px;'
                        f'padding:.5rem 1rem;font-size:13px;color:#86efac;margin-bottom:.5rem">'
                        f'⚡ <b>YOLOv8 detector loaded</b> — {_diag_info["num_classes"]} classes, '
                        f'validated mAP50 {_diag_info["validated_map50"]}'
                        f'</div>',
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown(
                        f'<div style="background:#450a0a;border:1px solid #dc2626;border-radius:8px;'
                        f'padding:.7rem 1rem;font-size:13px;color:#fca5a5;margin-bottom:.5rem">'
                        f'✗ <b>YOLOv8 detector NOT loaded</b><br>'
                        f'<span style="font-size:12px;color:#fecaca">'
                        f'{_diag_info.get("load_error","Unknown reason")}</span>'
                        f'</div>',
                        unsafe_allow_html=True
                    )

                with st.expander("🔧 Detector diagnostics"):
                    st.json(_diag_info)

                strict_yolo = st.checkbox(
                    "Require YOLO detection (fail rather than fall back to Claude-only)",
                    value=True,
                    help="Guarantees you always know whether the trained model actually ran."
                )

                analyze_btn = st.button("🧠 Run Full Analysis", type="primary",
                                        use_container_width=True, disabled=not yolo_ready and strict_yolo)
                if not yolo_ready and strict_yolo:
                    st.caption("Analysis is blocked because the detector is unavailable. "
                               "Untick the box above to run Claude-only analysis instead.")

                if analyze_btn:
                    spinner_msg = (
                        "⚡ YOLOv8 detecting tongue features → merging vitals → Claude synthesising..."
                        if yolo_ready else
                        "🔬 Analysing image and vitals..."
                    )
                    with st.spinner(spinner_msg):
                        try:
                            diag = analyze_with_yolo_pipeline(
                                image_bytes, scan_type, api_key,
                                detector=_detector if yolo_ready else None,
                                vitals=vitals,
                                require_yolo=strict_yolo,
                            )

                            # A parse failure returns a dict rather than raising.
                            # Surface it instead of saving an empty diagnosis.
                            if diag.get("error"):
                                st.error(f"Analysis failed: {diag['error']}")
                                with st.expander("Raw model response"):
                                    st.code(diag.get("raw", "(none captured)"))
                                st.stop()

                            st.session_state["last_vision_result"] = diag
                            st.session_state["vision_condition"] = diag.get("suggested_condition_input", "")
                            st.session_state["vision_pattern"] = diag.get("suggested_tcm_pattern", "")
                            st.session_state["vision_demographic"] = diag.get("suggested_demographic", "")
                            diag["scan_type"] = scan_type
                            save_visual_diagnosis(diag)

                            # YOLO ran but detected nothing — meaningful negative result
                            if diag.get("yolo_ran_found_nothing"):
                                st.markdown(
                                    '<div style="background:#052e16;border:1px solid #166534;'
                                    'border-radius:8px;padding:.7rem 1rem;font-size:13px;'
                                    'color:#86efac;margin:.5rem 0">'
                                    '✅ <b>Detector ran and found no abnormal tongue features</b><br>'
                                    '<span style="font-size:12px">Note this covers only the '
                                    'features the model detects reliably — it is not evidence '
                                    'that the tongue is normal.</span></div>',
                                    unsafe_allow_html=True
                                )

                            # Features the detector saw but is not trusted to report
                            supp = diag.get("suppressed_detections") or []
                            if supp:
                                with st.expander(
                                    f"🔇 {len(supp)} detection(s) withheld as unreliable"
                                ):
                                    st.caption(
                                        "The model flagged these, but its measured accuracy "
                                        "on them is too low to act on. They did not influence "
                                        "the diagnosis or the formula."
                                    )
                                    for s in supp:
                                        st.markdown(
                                            f"**{s['class_name']}** {s.get('chinese','')} "
                                            f"— detector confidence {s['confidence']:.2f}  \n"
                                            f"<span style='font-size:12px;color:#94a3b8'>"
                                            f"{s['reason']}</span>",
                                            unsafe_allow_html=True,
                                        )

                            # Show YOLO annotated image if available
                            annotated = diag.get("annotated_image")
                            if annotated is not None:
                                st.markdown("#### 🎯 YOLO Detection Overlay")
                                st.image(annotated, caption="YOLOv8 tongue feature detections", use_container_width=True)

                                # Detection table
                                yolo_dets = diag.get("yolo_detections", [])
                                if yolo_dets:
                                    st.markdown("**Detected Features:**")
                                    rel_colors = {"validated": "#22c55e",
                                                  "moderate": "#eab308",
                                                  "low confidence class": "#ef4444"}
                                    rows = ""
                                    for d in yolo_dets:
                                        lbl = d.get("reliability_label", "")
                                        rc = rel_colors.get(lbl, "#64748b")
                                        rows += (
                                            f"<tr>"
                                            f"<td>{d['zh']}</td>"
                                            f"<td style='color:#94a3b8;font-size:12px'>{d['class_name']}</td>"
                                            f"<td style='color:#7ec8e3;font-weight:600'>{d['confidence']:.0f}%</td>"
                                            f"<td><span style='color:{rc};font-size:11px'>"
                                            f"{lbl} ({d.get('reliability','?')})</span></td>"
                                            f"<td style='font-size:12px;color:#64748b'>{d['tcm_significance']}</td>"
                                            f"</tr>"
                                        )
                                    st.markdown(f"""
                                    <table class="herb-table">
                                      <thead><tr>
                                        <th>Feature (中文)</th><th>Class</th><th>Detection</th>
                                        <th>Class reliability</th><th>TCM Significance</th>
                                      </tr></thead>
                                      <tbody>{rows}</tbody>
                                    </table>""", unsafe_allow_html=True)
                                    st.caption(
                                        "Class reliability is the measured mAP50 for that class on the "
                                        "held-out test set. Only white-coating (0.94) and yellow-coating "
                                        "(0.82) are strongly validated; treat low-reliability detections "
                                        "as hints, not findings."
                                    )

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

    # ── Safety gate: block formulation on critical vitals ─────────────────────
    _v = st.session_state.get("vitals")
    formulation_blocked = bool(_v and _v.get("blocks_formulation"))
    if formulation_blocked:
        crit = [f for f in _v.get("red_flags", []) if f["severity"] == "critical"]
        st.markdown(
            '<div style="background:#450a0a;border:2px solid #dc2626;border-radius:10px;'
            'padding:1.2rem 1.4rem;margin-bottom:1rem">'
            '<div style="color:#fca5a5;font-size:17px;font-weight:700">'
            '🚨 Formulation disabled — your readings need medical attention</div>'
            + "".join(
                f'<div style="color:#fecaca;font-size:14px;margin-top:.6rem">'
                f'<b>{f["title"]}</b><br>{f["message"]}<br>'
                f'<span style="color:#fff;font-weight:600">→ {f["action"]}</span></div>'
                for f in crit)
            + '<div style="color:#fecaca;font-size:13px;margin-top:.8rem;font-style:italic">'
              'Herbal wellness products are not appropriate while readings are in this '
              'range. Please seek medical care first — you can return here afterwards.'
              '</div></div>',
            unsafe_allow_html=True
        )

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

    # Append objective vitals to the AI context
    if _v and _v.get("entered"):
        vision_context_str += (
            f"\n\nOBJECTIVE VITALS: BP {_v['systolic']}/{_v['diastolic']} mmHg "
            f"({_v['bp_tcm']['category']}), pulse {_v['pulse']} bpm "
            f"({_v['pulse_tcm']['category_zh']} {_v['pulse_tcm']['category_en']}), "
            f"age {_v['age']}, {_v['sex']}."
        )
        if _v.get("bmi_tcm"):
            vision_context_str += f" BMI {_v['bmi_tcm']['bmi']} ({_v['bmi_tcm']['category']})."
        if _v.get("corroborated_patterns"):
            vision_context_str += (
                f" Patterns supported by multiple objective measurements: "
                f"{', '.join(_v['corroborated_patterns'])}."
            )
        non_critical = [f for f in _v.get("red_flags", []) if f["severity"] != "critical"]
        if non_critical:
            vision_context_str += (
                " CAUTION — the following require conservative formulation and "
                "explicit safety notes: "
                + "; ".join(f["title"] for f in non_critical) + "."
            )

    if st.button("🌿 Generate Formulation", type="primary", use_container_width=True,
                 disabled=formulation_blocked):
        if formulation_blocked:
            st.error("Formulation is disabled while your vitals are in the critical range.")
        elif not condition:
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
