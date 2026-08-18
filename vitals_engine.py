"""
vitals_engine.py — Objective Vitals Capture & TCM Interpretation
----------------------------------------------------------------
Adds measurable clinical data to the visual assessment pipeline.

Why this matters:
  Photographs give only 望诊 (observation), one of the Four Examinations.
  Pulse rate is a genuine, objective component of 脉诊 (pulse diagnosis) —
  the classical 迟脉/数脉 (slow/rapid) distinction maps directly onto
  Cold/Heat patterns and is measurable rather than inferred.

  Blood pressure is not classical TCM, but modern integrative TCM practice
  has well-documented correspondences (Liver Yang Rising in hypertension,
  Qi/Yang deficiency in hypotension) supported by clinical literature.

IMPORTANT — SCOPE:
  These mappings are TCM pattern correlations for wellness formulation.
  They are NOT diagnoses of hypertension, arrhythmia, or any medical
  condition. Red-flag thresholds below follow standard clinical guidance
  (ACC/AHA 2017 BP categories) purely to route users to real medical care
  when readings are dangerous.
"""

from typing import Optional


# ══════════════════════════════════════════════════════════════════════════════
# CLINICAL RED FLAGS — these route the user to medical care, not herbs
# ══════════════════════════════════════════════════════════════════════════════

def check_red_flags(systolic: int, diastolic: int, pulse: int, age: int) -> list:
    """
    Detect readings that require medical attention rather than herbal formulation.
    Returns a list of {severity, title, message, action} dicts.

    Thresholds follow ACC/AHA 2017 guidance and standard resting HR ranges.
    """
    flags = []

    # ── Hypertensive crisis ───────────────────────────────────────────────────
    if systolic >= 180 or diastolic >= 120:
        flags.append({
            "severity": "critical",
            "title": "Hypertensive Crisis — Seek Immediate Medical Care",
            "message": (
                f"Your reading of {systolic}/{diastolic} mmHg is in the hypertensive "
                f"crisis range (≥180/120). This can cause organ damage and requires "
                f"urgent medical evaluation — not herbal treatment."
            ),
            "action": "Go to an emergency department or call emergency services now.",
        })

    # ── Stage 2 hypertension ──────────────────────────────────────────────────
    elif systolic >= 140 or diastolic >= 90:
        flags.append({
            "severity": "high",
            "title": "Elevated Blood Pressure — Medical Review Recommended",
            "message": (
                f"Your reading of {systolic}/{diastolic} mmHg is in the Stage 2 "
                f"hypertension range. Herbal wellness products are not a substitute "
                f"for medical management of high blood pressure."
            ),
            "action": "Please consult a doctor before starting any herbal regimen.",
        })

    # ── Significant hypotension ───────────────────────────────────────────────
    if systolic < 90 or diastolic < 60:
        flags.append({
            "severity": "high",
            "title": "Low Blood Pressure — Medical Review Recommended",
            "message": (
                f"Your reading of {systolic}/{diastolic} mmHg is below the normal "
                f"range. If accompanied by dizziness, fainting or fatigue, this "
                f"needs medical assessment."
            ),
            "action": "Consult a doctor, especially if you feel lightheaded.",
        })

    # ── Tachycardia at rest ───────────────────────────────────────────────────
    if pulse > 120:
        flags.append({
            "severity": "critical",
            "title": "Very High Resting Pulse — Seek Medical Care",
            "message": (
                f"A resting pulse of {pulse} bpm is significantly elevated. "
                f"This requires medical evaluation to rule out arrhythmia, "
                f"infection, thyroid dysfunction or other causes."
            ),
            "action": "Contact a doctor promptly.",
        })
    elif pulse > 100:
        flags.append({
            "severity": "moderate",
            "title": "Elevated Resting Pulse",
            "message": (
                f"A resting pulse of {pulse} bpm is above the normal range "
                f"(60–100 bpm). If this is consistent at rest, mention it to a doctor."
            ),
            "action": "Monitor and discuss with a healthcare provider.",
        })

    # ── Bradycardia ───────────────────────────────────────────────────────────
    if pulse < 50:
        flags.append({
            "severity": "high",
            "title": "Low Resting Pulse",
            "message": (
                f"A resting pulse of {pulse} bpm is below the normal range. "
                f"This is normal in trained athletes but otherwise warrants "
                f"medical review, particularly with dizziness or fatigue."
            ),
            "action": "Consult a doctor unless you are a trained endurance athlete.",
        })

    return flags


def has_blocking_flag(flags: list) -> bool:
    """True if any flag is severe enough to block herbal formulation."""
    return any(f["severity"] == "critical" for f in flags)


# ══════════════════════════════════════════════════════════════════════════════
# TCM PULSE RATE CLASSIFICATION (脉率)
# ══════════════════════════════════════════════════════════════════════════════

def classify_pulse_rate(pulse: int, age: int) -> dict:
    """
    Classify pulse rate using classical TCM categories, age-adjusted.

    Classical reference: a normal pulse (平脉) is 4–5 beats per respiratory
    cycle, roughly 60–90 bpm in an adult at rest.
      迟脉 (Chí mài, Slow)  < 60  → Cold pattern, Yang deficiency
      平脉 (Píng mài, Normal) 60–90
      数脉 (Shuò mài, Rapid) > 90  → Heat pattern
      疾脉 (Jí mài, Racing)  > 120 → Extreme Heat, Yin exhaustion
    """
    # Age adjustment: resting HR trends slightly higher in older adults,
    # and trained/younger adults commonly sit lower without pathology.
    if age >= 65:
        slow_cut, rapid_cut = 58, 88
    elif age <= 30:
        slow_cut, rapid_cut = 55, 92
    else:
        slow_cut, rapid_cut = 60, 90

    if pulse > 120:
        return {
            "category_zh": "疾脉", "category_pinyin": "Jí mài", "category_en": "Racing pulse",
            "tcm_significance": "Extreme Heat; Yin exhaustion; critical Yang floating",
            "patterns": ["Extreme Heat", "Yin Exhaustion"],
            "strength": "strong",
            "note": "Requires medical evaluation before any TCM interpretation.",
        }
    if pulse > rapid_cut:
        return {
            "category_zh": "数脉", "category_pinyin": "Shuò mài", "category_en": "Rapid pulse",
            "tcm_significance": "Heat pattern — excess Heat if forceful, Empty Heat from Yin deficiency if weak",
            "patterns": ["Heat", "Yin Deficiency with Empty Heat"],
            "strength": "strong" if pulse > rapid_cut + 10 else "moderate",
            "note": "Rapid pulse is a reliable objective Heat indicator.",
        }
    if pulse < slow_cut:
        return {
            "category_zh": "迟脉", "category_pinyin": "Chí mài", "category_en": "Slow pulse",
            "tcm_significance": "Cold pattern; Yang deficiency; Qi stagnation with Cold",
            "patterns": ["Cold", "Yang Deficiency"],
            "strength": "strong" if pulse < slow_cut - 8 else "moderate",
            "note": "Common and benign in trained athletes — ask about exercise history.",
        }
    return {
        "category_zh": "平脉", "category_pinyin": "Píng mài", "category_en": "Normal pulse",
        "tcm_significance": "Normal rate — no Heat or Cold indication from rate alone",
        "patterns": [],
        "strength": "normal",
        "note": "Rate is normal. Note that rate is only one of ~28 classical pulse qualities.",
    }


# ══════════════════════════════════════════════════════════════════════════════
# BLOOD PRESSURE → TCM PATTERN CORRELATION
# ══════════════════════════════════════════════════════════════════════════════

def classify_blood_pressure(systolic: int, diastolic: int, age: int) -> dict:
    """
    Map BP into both the standard clinical category and documented TCM
    pattern correlations used in modern integrative practice.
    """
    pulse_pressure = systolic - diastolic

    if systolic >= 180 or diastolic >= 120:
        category, cat_color = "Hypertensive Crisis", "critical"
    elif systolic >= 140 or diastolic >= 90:
        category, cat_color = "Stage 2 Hypertension", "high"
    elif systolic >= 130 or diastolic >= 80:
        category, cat_color = "Stage 1 Hypertension", "elevated"
    elif systolic >= 120:
        category, cat_color = "Elevated", "elevated"
    elif systolic < 90 or diastolic < 60:
        category, cat_color = "Hypotension", "low"
    else:
        category, cat_color = "Normal", "normal"

    patterns, significance = [], ""

    if category in ("Stage 1 Hypertension", "Stage 2 Hypertension", "Hypertensive Crisis", "Elevated"):
        patterns = ["Liver Yang Rising", "Liver Fire", "Phlegm-Damp obstruction"]
        significance = (
            "Raised BP correlates in integrative TCM with Liver Yang Rising (肝阳上亢), "
            "particularly with headache, irritability or red face. In older adults it "
            "often reflects underlying Kidney Yin deficiency failing to anchor Liver Yang."
        )
        if age >= 55:
            patterns.append("Kidney Yin Deficiency with Liver Yang Rising")
        if pulse_pressure > 60:
            patterns.append("Yin Deficiency (wide pulse pressure)")
            significance += (
                f" A wide pulse pressure ({pulse_pressure} mmHg) suggests arterial "
                f"stiffening, correlated with Yin deficiency patterns."
            )

    elif category == "Hypotension":
        patterns = ["Qi Deficiency", "Yang Deficiency", "Blood Deficiency"]
        significance = (
            "Low BP correlates with Qi deficiency (气虚) or Yang deficiency (阳虚), "
            "especially with fatigue, cold limbs, dizziness on standing or pale complexion."
        )
    else:
        significance = "Blood pressure is within normal limits — no BP-derived pattern indication."

    return {
        "category": category,
        "category_level": cat_color,
        "systolic": systolic,
        "diastolic": diastolic,
        "pulse_pressure": pulse_pressure,
        "patterns": patterns,
        "tcm_significance": significance,
    }


# ══════════════════════════════════════════════════════════════════════════════
# BMI → CONSTITUTION CORRELATION
# ══════════════════════════════════════════════════════════════════════════════

def classify_bmi(height_cm: float, weight_kg: float) -> Optional[dict]:
    """
    BMI with Asian-population cutoffs (WHO Asia-Pacific), which are lower
    than Western cutoffs and more appropriate for a Singapore/SEA market.

    Phlegm-Damp constitution (痰湿质) has a well-documented association with
    higher BMI in the Wang Qi constitution literature.
    """
    if not height_cm or not weight_kg or height_cm <= 0:
        return None

    bmi = weight_kg / ((height_cm / 100) ** 2)

    if bmi < 18.5:
        category = "Underweight"
        patterns = ["Qi Deficiency", "Blood Deficiency", "Yin Deficiency"]
        note = "Low BMI correlates with Qi/Blood deficiency constitutions (气虚质/血虚)."
    elif bmi < 23:
        category = "Normal (Asian cutoff)"
        patterns = []
        note = "BMI within the healthy range for Asian populations."
    elif bmi < 27.5:
        category = "Overweight (Asian cutoff)"
        patterns = ["Phlegm-Damp"]
        note = "Raised BMI is associated with Phlegm-Damp constitution (痰湿质)."
    else:
        category = "Obese (Asian cutoff)"
        patterns = ["Phlegm-Damp", "Damp-Heat"]
        note = (
            "Higher BMI is strongly associated with Phlegm-Damp (痰湿质) and "
            "Damp-Heat (湿热质) constitutions in the Wang Qi framework."
        )

    return {
        "bmi": round(bmi, 1),
        "category": category,
        "patterns": patterns,
        "note": note,
    }


# ══════════════════════════════════════════════════════════════════════════════
# MAIN ASSESSMENT
# ══════════════════════════════════════════════════════════════════════════════

def assess_vitals(
    systolic: int,
    diastolic: int,
    pulse: int,
    age: int,
    sex: str,
    height_cm: float = None,
    weight_kg: float = None,
) -> dict:
    """
    Full objective vitals assessment.

    Returns a dict containing clinical red flags, TCM correlations for each
    measurement, and a formatted context block for the Claude synthesis step.
    """
    flags = check_red_flags(systolic, diastolic, pulse, age)
    pulse_info = classify_pulse_rate(pulse, age)
    bp_info = classify_blood_pressure(systolic, diastolic, age)
    bmi_info = classify_bmi(height_cm, weight_kg) if (height_cm and weight_kg) else None

    # Aggregate objectively-supported patterns, tracking WHICH measurement
    # supports each so corroboration means independent sources agreeing.
    sources = {
        "pulse": pulse_info.get("patterns", []),
        "bp": bp_info.get("patterns", []),
        "bmi": bmi_info.get("patterns", []) if bmi_info else [],
    }

    def canonical(p: str) -> str:
        """Collapse pattern name variants so they corroborate correctly."""
        s = p.lower()
        if "phlegm-damp" in s:
            return "Phlegm-Damp"
        if "damp-heat" in s:
            return "Damp-Heat"
        if "liver yang" in s or "liver fire" in s:
            return "Liver Yang Rising / Liver Fire"
        if "yin deficiency" in s:
            return "Yin Deficiency"
        if "yang deficiency" in s:
            return "Yang Deficiency"
        if "qi deficiency" in s:
            return "Qi Deficiency"
        if "blood deficiency" in s:
            return "Blood Deficiency"
        if s == "heat":
            return "Heat"
        if s == "cold":
            return "Cold"
        return p

    # A pattern is corroborated when >= 2 DIFFERENT measurements support it
    support_map = {}
    for src, plist in sources.items():
        for p in plist:
            support_map.setdefault(canonical(p), set()).add(src)

    corroborated = sorted(
        support_map.items(), key=lambda x: (-len(x[1]), x[0])
    )
    objective_patterns = [p for p, _ in corroborated]

    return {
        "entered": True,
        "systolic": systolic,
        "diastolic": diastolic,
        "pulse": pulse,
        "age": age,
        "sex": sex,
        "height_cm": height_cm,
        "weight_kg": weight_kg,
        "red_flags": flags,
        "blocks_formulation": has_blocking_flag(flags),
        "pulse_tcm": pulse_info,
        "bp_tcm": bp_info,
        "bmi_tcm": bmi_info,
        "objective_patterns": objective_patterns,
        "corroborated_patterns": [p for p, srcs in corroborated if len(srcs) >= 2],
        "pattern_support": {p: sorted(s) for p, s in support_map.items()},
        "claude_context": build_vitals_context(
            systolic, diastolic, pulse, age, sex, pulse_info, bp_info, bmi_info
        ),
    }


def build_vitals_context(
    systolic, diastolic, pulse, age, sex, pulse_info, bp_info, bmi_info
) -> str:
    """Structured vitals block injected into the Claude synthesis prompt."""
    lines = [
        "=== OBJECTIVE VITAL SIGNS (measured, not inferred) ===",
        f"Age: {age}    Sex: {sex}",
        f"Blood Pressure: {systolic}/{diastolic} mmHg  →  {bp_info['category']}"
        f"  (pulse pressure {bp_info['pulse_pressure']} mmHg)",
        f"Resting Pulse: {pulse} bpm  →  {pulse_info['category_zh']} "
        f"({pulse_info['category_pinyin']}, {pulse_info['category_en']})",
    ]

    if bmi_info:
        lines.append(f"BMI: {bmi_info['bmi']}  →  {bmi_info['category']}")

    lines.append("")
    lines.append("TCM CORRELATIONS FROM THESE MEASUREMENTS:")
    lines.append(f"  Pulse rate: {pulse_info['tcm_significance']}")
    lines.append(f"  Blood pressure: {bp_info['tcm_significance']}")
    if bmi_info:
        lines.append(f"  BMI: {bmi_info['note']}")

    lines.append("")
    lines.append(
        "HOW TO USE THIS: These are OBJECTIVE MEASUREMENTS and carry more "
        "diagnostic weight than anything inferred from a photograph. Where the "
        "vitals and the image disagree, favour the vitals and say so explicitly "
        "in clinical_notes.\n"
        "Critically: a rapid pulse (数脉) is objective evidence of a Heat pattern "
        "and ARGUES AGAINST a pure Cold/Yang-deficiency diagnosis. A slow pulse "
        "(迟脉) argues against a Heat diagnosis. Respect these constraints — do "
        "not produce a diagnosis that contradicts the measured pulse."
    )
    lines.append("=== END VITAL SIGNS ===")

    return "\n".join(lines)
