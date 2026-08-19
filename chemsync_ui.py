"""
chemsync_ui.py — the consumer-facing ChemSync™ dashboard.

Four steps, matching the ChemSync concept:

    1. SELECT GOAL     member picks a health goal
    2. AI BIO-SCAN     vitals + camera, privacy-first
    3. AI ANALYSIS     personalised insight from the diagnosis pipeline
    4. MATCHED PICKS   a stocked product if one genuinely fits, else a
                       bespoke blend generated from the 551-item inventory

This is a presentation layer. All diagnosis, safety and formulation logic lives
in vision_engine / vitals_engine / formulation_engine / safety_rules and is
reused unchanged — the consumer view must never reach a different clinical
conclusion from the professional one.
"""

import streamlit as st

GOALS = [
    ("sleep",      "😴", "Sleep &amp; Rest",       "Trouble falling or staying asleep, waking unrested",
     ["poor sleep", "insomnia", "Shen disturbance", "anxiety"]),
    ("energy",     "⚡", "Energy &amp; Vitality",  "Persistent tiredness, low stamina, afternoon slumps",
     ["fatigue", "Qi deficiency", "Spleen patterns"]),
    ("digestion",  "🌿", "Digestion &amp; Gut",    "Bloating, irregularity, discomfort after eating",
     ["poor digestion", "bloating and distension", "intestinal complaints", "Spleen patterns"]),
    ("stress",     "🧘", "Stress &amp; Mood",      "Tension, irritability, feeling wound up",
     ["stress", "Liver Qi constraint", "irritability", "low mood"]),
    ("immunity",   "🛡️", "Immunity &amp; Defence", "Frequent colds, slow recovery, low resilience",
     ["low immunity", "Qi deficiency", "Lung patterns"]),
    ("womens",     "🌸", "Women's Health",         "Cycle regularity, menopausal changes",
     ["menstrual disorders", "women's health", "menopausal symptoms", "Blood deficiency"]),
    ("joints",     "🦴", "Joints &amp; Mobility",  "Stiffness, aches, reduced range of movement",
     ["joint pain", "Wind-Damp obstruction", "pain", "bone weakness"]),
    ("skin",       "✨", "Skin &amp; Radiance",    "Dullness, breakouts, dryness",
     ["skin conditions", "Heat patterns", "Blood deficiency"]),
]

STEPS = [
    ("SELECT GOAL",  "Member defines a health goal to start personalised discovery"),
    ("AI BIO-SCAN",  "Camera reads face and tongue in a privacy-first check-up"),
    ("AI ANALYSIS",  "Generating personalised health insights"),
    ("MATCHED PICKS", "Recommends relevant Chemigran health products"),
]


def _css():
    st.markdown("""
    <style>
      .cs-steps { display:flex; gap:.6rem; margin:1rem 0 1.6rem; flex-wrap:wrap; }
      .cs-step {
        flex:1; min-width:150px; border-radius:14px; padding:.9rem 1rem;
        background:linear-gradient(160deg,#0d2137,#132b45);
        border:1px solid #1e3a5f; position:relative;
      }
      .cs-step.done   { border-color:#2563eb; background:linear-gradient(160deg,#10294a,#16375c); }
      .cs-step.active { border-color:#7ec8e3; box-shadow:0 0 0 1px #7ec8e355, 0 0 22px #2563eb33; }
      .cs-step .n {
        font-size:11px; letter-spacing:.14em; color:#64748b; font-weight:700;
      }
      .cs-step.active .n, .cs-step.done .n { color:#7ec8e3; }
      .cs-step .t { font-size:14px; font-weight:700; color:#e2e8f0; margin:.15rem 0 .3rem; }
      .cs-step .d { font-size:11.5px; color:#94a3b8; line-height:1.4; }
      .cs-goal {
        border:1px solid #1e3a5f; border-radius:12px; padding:.9rem 1rem;
        background:#0d1e30; height:100%;
      }
      .cs-goal .g-t { font-size:15px; font-weight:700; color:#7ec8e3; }
      .cs-goal .g-d { font-size:12px; color:#94a3b8; margin-top:.25rem; line-height:1.45; }
      .cs-pick {
        border:1px solid #2563eb55; border-radius:14px; padding:1.1rem 1.3rem;
        background:linear-gradient(135deg,#0d2137,#162435); margin-bottom:.9rem;
      }
      .cs-pick .p-n { font-size:18px; font-weight:700; color:#7ec8e3; }
      .cs-pick .p-p { font-size:14px; color:#86efac; margin-top:.15rem; }
      .cs-why {
        background:#0c1f3a; border-left:3px solid #3b82f6; border-radius:6px;
        padding:.55rem .8rem; font-size:12.5px; color:#cbd5e1; margin-top:.6rem;
      }
    </style>
    """, unsafe_allow_html=True)


def _stepbar(current: int):
    html = '<div class="cs-steps">'
    for i, (title, desc) in enumerate(STEPS, 1):
        cls = "done" if i < current else ("active" if i == current else "")
        html += (
            f'<div class="cs-step {cls}">'
            f'<div class="n">{i} {"✓" if i < current else ""}</div>'
            f'<div class="t">{title}</div><div class="d">{desc}</div></div>'
        )
    st.markdown(html + "</div>", unsafe_allow_html=True)


def _step_goal():
    st.markdown("#### 1️⃣ What would you like to work on?")
    st.caption("Pick the goal that matters most right now. You can change it later.")

    cols = st.columns(4)
    for i, (key, icon, title, desc, inds) in enumerate(GOALS):
        with cols[i % 4]:
            st.markdown(
                f'<div class="cs-goal"><div class="g-t">{icon} {title}</div>'
                f'<div class="g-d">{desc}</div></div>',
                unsafe_allow_html=True,
            )
            if st.button("Choose", key=f"goal_{key}", use_container_width=True):
                st.session_state.cs_goal = {
                    "key": key, "title": title.replace("&amp;", "&"),
                    "indications": inds,
                }
                st.session_state.cs_step = 2
                st.rerun()


def _goal_banner():
    g = st.session_state.get("cs_goal")
    if not g:
        return
    c1, c2 = st.columns([5, 1])
    c1.success(f"🎯 Goal: **{g['title']}**")
    if c2.button("Change", use_container_width=True):
        for k in ("cs_goal", "cs_scan", "cs_result"):
            st.session_state.pop(k, None)
        st.session_state.cs_step = 1
        st.rerun()


def render(run_scan_callback, generate_callback):
    """
    run_scan_callback()  -> dict | None   the diagnosis (vitals + YOLO + Claude)
    generate_callback(goal, diagnosis) -> dict | None   a bespoke formulation
    """
    _css()
    step = st.session_state.get("cs_step", 1)
    _stepbar(step)

    if step == 1:
        _step_goal()
        return

    _goal_banner()

    if step == 2:
        st.markdown("#### 2️⃣ Bio-Scan")
        st.caption(
            "Your vital signs plus a tongue and face photo. Images are analysed "
            "in the moment and are not stored."
        )
        diagnosis = run_scan_callback()
        if diagnosis:
            st.session_state.cs_scan = diagnosis
            st.session_state.cs_step = 3
            st.rerun()
        return

    if step == 3:
        st.markdown("#### 3️⃣ Your Analysis")
        _render_analysis(st.session_state.get("cs_scan") or {})
        if st.button("See my matched picks →", type="primary", use_container_width=True):
            st.session_state.cs_step = 4
            st.rerun()
        return

    if step == 4:
        st.markdown("#### 4️⃣ Matched Picks")
        _render_picks(
            st.session_state.get("cs_goal") or {},
            st.session_state.get("cs_scan") or {},
            generate_callback,
        )


def _render_analysis(diag: dict):
    if not diag:
        st.info("No scan data yet.")
        return

    pattern = diag.get("primary_pattern") or diag.get("tcm_pattern") or "—"
    conf = diag.get("confidence_overall", 0)

    c1, c2 = st.columns([2, 1])
    c1.markdown(f"**Primary TCM pattern**  \n### {pattern}")
    c2.metric("Confidence", f"{conf}%")

    if diag.get("constitution_type"):
        st.caption(f"Constitution (体质): {diag['constitution_type']}")

    if diag.get("clinical_notes"):
        st.markdown(
            f'<div class="cs-why">{diag["clinical_notes"]}</div>',
            unsafe_allow_html=True,
        )

    supp = diag.get("suppressed_detections") or []
    if supp:
        st.caption(
            f"{len(supp)} detected feature(s) were withheld because the model's "
            "measured accuracy on them is too low to act on."
        )


def _render_picks(goal: dict, diag: dict, generate_callback):
    from product_catalog import match_products, catalogue_status

    indications = list(goal.get("indications", []))
    pattern = diag.get("primary_pattern") or diag.get("tcm_pattern") or ""

    status = catalogue_status()
    matches = match_products(indications, pattern) if status["available"] else []

    if matches:
        st.caption(f"Matched against {status['count']} Chemigran products.")
        for m in matches:
            price = f"SGD {m['price_sgd']}" if m.get("price_sgd") else ""
            st.markdown(
                f'<div class="cs-pick"><div class="p-n">{m["name_en"]} '
                f'{m.get("name_zh","")}</div>'
                f'<div class="p-p">{price} · {m.get("pack_size","")}</div>'
                f'<div class="g-d" style="margin-top:.5rem">{m.get("description","")}</div>'
                f'<div class="cs-why"><b>Why this was matched:</b> '
                f'{", ".join(m["matched_on"]) or "goal alignment"}'
                + (f' · pattern: {", ".join(m["matched_patterns"])}' if m["matched_patterns"] else "")
                + f' · match score {m["match_score"]:.2f}</div></div>',
                unsafe_allow_html=True,
            )
        st.divider()
        st.caption("None of these quite right?")

    else:
        if not status["available"]:
            st.info(
                "No product catalogue loaded yet — add your SKUs to **products.csv** "
                "and ChemSync will match against them here. Until then, every "
                "recommendation is a bespoke blend."
            )
        else:
            st.info(
                "Nothing in the catalogue is a close enough match for this pattern, "
                "so a bespoke blend is the better answer."
            )

    if st.button("🧪 Create a bespoke blend for me", type="primary", use_container_width=True):
        with st.spinner("ChemSync formulating from the 551-product inventory..."):
            st.session_state.cs_result = generate_callback(goal, diag)
        st.rerun()

    result = st.session_state.get("cs_result")
    if result:
        st.divider()
        from app import render_product_card   # reuse the checked renderer
        render_product_card(result, show_business_btn=False, key_suffix="chemsync")
