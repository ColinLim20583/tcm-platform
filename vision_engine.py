"""
vision_engine.py — Chemigran TCM Visual Diagnosis Engine
--------------------------------------------------------
Uses Claude Vision (claude-sonnet-4-5) to analyse live camera images
(tongue + face) and return structured TCM pattern diagnosis.

Diagnostic framework based on:
  - Classical 四诊 (Sì Zhěn): 望 Wàng (Observation) pillar
  - Tongue diagnosis (舌诊 Shé Zhěn): UTDID & ZSATD reference criteria
  - Face diagnosis (面诊 Miàn Zhěn): Five-Element zone mapping
  - Body constitution (体质 Tǐ Zhì): 9 TCM constitutions (Wang Qi framework)
  - Cross-referenced against published clinical tongue image datasets
    (Accessed via Claude's multimodal training on open medical imagery)
"""

import anthropic
import base64
import json
import io
from PIL import Image, ImageEnhance, ImageFilter


# ─── Image pre-processing ────────────────────────────────────────────────────

def preprocess_image(image_bytes: bytes, max_size: int = 1024) -> bytes:
    """
    Resize, sharpen and normalise an image for best vision API results.
    Returns JPEG bytes.
    """
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    # Resize keeping aspect ratio
    w, h = img.size
    scale = min(max_size / w, max_size / h, 1.0)
    if scale < 1.0:
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    # Mild sharpening for tongue-coating detail
    img = img.filter(ImageFilter.UnsharpMask(radius=1.2, percent=120, threshold=3))

    # Slight contrast boost
    img = ImageEnhance.Contrast(img).enhance(1.15)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def encode_image_b64(image_bytes: bytes) -> str:
    return base64.standard_b64encode(image_bytes).decode("utf-8")


# ─── TCM reference knowledge embedded in prompt ──────────────────────────────

TONGUE_REFERENCE = """
TONGUE DIAGNOSIS REFERENCE (舌诊参考):

TONGUE BODY COLOUR:
  Pale pink (淡红) → Normal; Blood & Qi balanced
  Pale white (淡白) → Qi/Blood deficiency; Cold pattern; Yang deficiency
  Red (红) → Heat pattern; early Yin deficiency
  Deep red/Crimson (绛) → Extreme Heat; Nutritive-level Heat; severe Yin deficiency
  Purple (紫) → Blood stasis; Cold obstructing vessels (bluish-purple) or Heat stasis (reddish-purple)
  Blue-purple → Cold with Blood stasis; pain; Yang deficiency extreme

TONGUE COATING:
  Thin white (薄白) → Normal or mild exterior Wind-Cold
  Thick white (厚白) → Cold-Damp accumulation; Phlegm-Cold
  Thin yellow (薄黄) → Mild Heat; early interior Heat
  Thick yellow (厚黄) → Interior Heat; Damp-Heat accumulation
  Greasy/sticky (腻) → Phlegm-Damp; Damp-Heat; food stagnation
  Dry (燥) → Yin injury; Body fluids damaged by Heat
  Peeled/Geographic (花剥) → Stomach Yin deficiency; chronic illness
  Mirror/No coating (无苔) → Severe Yin deficiency; Stomach Qi exhaustion
  Grey-black (灰黑) → Extreme Cold (moist) or extreme Heat (dry)

TONGUE SHAPE:
  Swollen (胖大) → Qi deficiency; Damp; Phlegm; Yang deficiency
  Teeth-marked edges (齿痕) → Spleen Qi deficiency with Damp
  Thin/Lean (瘦薄) → Blood deficiency; Yin deficiency
  Cracked (裂纹) → Heat consuming fluids; Yin deficiency; chronic Blood deficiency
  Rigid/stiff → Wind; Heat in Pericardium
  Deviated → Wind stroke; Liver Wind
  Trembling (颤动) → Qi/Blood deficiency; Liver Wind

TONGUE MOISTURE:
  Wet/Moist → Cold; Damp; Yang deficiency; normal
  Dry → Heat; Yin deficiency; fluid damage
  Excessively wet/dripping → Cold-Damp; Yang deficiency severe
"""

FACE_REFERENCE = """
FACE DIAGNOSIS REFERENCE (面诊参考):

OVERALL COMPLEXION:
  Bright pale → Qi/Blood deficiency; acute Cold invasion
  Dull pale → Yang deficiency; Blood deficiency chronic
  Bright/Flushed red → Excess Heat; Liver Yang rising
  Persistent red cheeks (malar flush) → Yin deficiency Empty Heat (午后潮红)
  Yellow-sallow → Spleen/Stomach deficiency; Damp retention
  Bright yellow → Damp-Heat (Jaundice pattern)
  Dark/Greyish → Kidney deficiency; Blood stasis; Cold retention
  Bluish/Cyanotic → Cold pattern; Blood stasis; pain; Heart Yang deficiency
  Greenish → Liver Qi stagnation; pain; Wind pattern

FIVE-ZONE FACE MAPPING (五脏对应):
  Forehead → Heart & Small Intestine (red = Heart Fire; pale = Heart deficiency)
  Space between eyebrows (印堂) → Lung (dull = Lung Qi deficiency; red = Lung Heat)
  Nose bridge → Liver & Gallbladder (greenish = Liver stagnation; red = Liver Fire)
  Nose tip (鼻准) → Spleen & Stomach (yellow = Spleen weakness; red = Stomach Heat)
  Cheeks → Lung (pale = Lung deficiency; flushed = Lung Heat or Yin def)
  Chin → Kidney & Bladder (dark = Kidney deficiency; puffy = Water retention)
  Around mouth → Spleen/Stomach (pale = Spleen Blood def; yellowish = Damp)

EYES:
  Bright, moist → Good Shen (spirit); healthy
  Dull, lifeless → Poor Shen; Qi/Jing deficiency
  Red sclera → Heat in Liver or Heart
  Yellow sclera → Damp-Heat (Jaundice)
  Pale inner corners → Blood deficiency
  Dark circles / puffy lower lids → Kidney deficiency; Water retention
  Dry eyes → Liver Blood deficiency
  Twitching → Liver Wind; Blood deficiency

SKIN & CONSTITUTION:
  Dry, thin skin → Yin deficiency; Blood deficiency
  Oily skin → Damp-Heat; Phlegm
  Puffy, doughy → Phlegm-Damp constitution
  Loose, sallow → Qi deficiency; Spleen weakness
  Ruddy, robust → Damp-Heat or balanced constitution
"""

CONSTITUTION_TYPES = """
9 TCM BODY CONSTITUTIONS (王琦体质分类):
  1. 平和质 (Balanced) → Energetic, good digestion, resilient
  2. 气虚质 (Qi Deficiency) → Fatigue, pale, soft voice, sweats easily
  3. 阳虚质 (Yang Deficiency) → Cold limbs, pale, low energy, frequent urination
  4. 阴虚质 (Yin Deficiency) → Thin, dry, flushed, restless, night sweats
  5. 痰湿质 (Phlegm-Damp) → Overweight, greasy skin, heavy sensation
  6. 湿热质 (Damp-Heat) → Oily skin, acne, bitter taste, yellow urine
  7. 血瘀质 (Blood Stasis) → Dark complexion, purple lips, fixed pain
  8. 气郁质 (Qi Stagnation) → Emotional, sighing, chest tightness, moody
  9. 特禀质 (Allergic) → Sensitive, prone to allergies, weak immune response
"""

NORMAL_BASELINE = """
NORMAL / HEALTHY BASELINE (正常舌象面象) — READ THIS FIRST:

A HEALTHY adult tongue looks like this. This is the MOST COMMON presentation:
  - Pale red / pink body (淡红舌) — the normal colour
  - Thin white coating (薄白苔) — a thin white film is NORMAL, not pathological
  - Normal size, moist but not wet
  - Slight indentations at the edges are COMMON in healthy people and are
    only diagnostically meaningful when DEEP, PRONOUNCED and paired with
    a genuinely swollen, pale body

A HEALTHY adult face looks like this:
  - Even complexion with visible lustre (有神)
  - Slight natural variation in tone across zones is NORMAL
  - Clear eyes

CRITICAL CALIBRATION — COMMON FALSE POSITIVES:
  ✗ Thin white coating is NORMAL. Do NOT call it "Phlegm-Damp" unless the
    coating is genuinely THICK, GREASY and obscures the tongue body beneath.
  ✗ Mild scalloping at tongue edges occurs in a large fraction of healthy
    adults. Do NOT diagnose "Spleen Qi Deficiency" from this alone.
  ✗ Phone cameras wash out colour and add warm/yellow cast. A slightly
    sallow-looking face is usually LIGHTING, not Spleen deficiency.
  ✗ A tongue extended hard for a photo naturally appears wider and flatter.
    Do NOT read this as a "swollen" (胖大) tongue.
  ✗ Shadows under the eyes from overhead light are NOT dark circles.

BASE RATES — you must respect these:
  In a general adult population being casually photographed:
    ~35-45% are 平和质 Balanced Constitution — NO significant pattern
    ~20% show mild Qi deficiency signs
    ~15% show mild Damp signs
    the remainder spread across the other constitutions
  If you diagnose "Spleen Qi Deficiency with Phlegm-Damp" for the majority
  of images you see, you are WRONG. That pattern requires a genuinely
  swollen pale body AND thick greasy coating AND deep teeth marks together.
"""

VISION_SYSTEM_PROMPT = f"""You are ChemiGranVision — a TCM visual assessment AI integrated into Chemigran Pte Ltd's formulation platform.

You perform structured observation (望诊 Wàng Zhěn) on photographs. You are a
careful, conservative observer — closer to a radiologist writing a report than
a practitioner eager to find a pattern.

{NORMAL_BASELINE}

REFERENCE KNOWLEDGE:
{TONGUE_REFERENCE}

{FACE_REFERENCE}

{CONSTITUTION_TYPES}

MANDATORY RULES:

1. DESCRIBE BEFORE YOU DIAGNOSE.
   First record what you literally see — colours, textures, shapes. Only then
   map observations to patterns. Never start from a pattern and look for
   evidence to support it.

2. "BALANCED CONSTITUTION" IS A VALID AND COMMON ANSWER.
   If the tongue is pale red with a thin white coating and the face has even
   tone and lustre, the correct answer is 平和质 (Balanced Constitution) with
   primary_pattern "No significant pattern — Balanced". This is expected for
   roughly 4 in 10 people. Do not manufacture pathology.

3. EVERY PATTERN MUST CITE SPECIFIC VISIBLE EVIDENCE.
   Each entry in tcm_patterns must list concrete observations you actually saw
   in supporting_indicators. If you cannot name at least TWO specific visual
   findings, do not report the pattern.

4. RECORD CONTRADICTING EVIDENCE HONESTLY.
   Fill contradicting_indicators whenever a finding argues against the pattern.
   An empty contradicting list on every pattern is a sign you are not looking.

5. CONFIDENCE MUST BE EARNED — DEFAULT LOW.
   85-95: multiple unambiguous findings, excellent image quality
   65-84 : clear findings, good image
   40-64 : suggestive but ambiguous, or mediocre image quality
   below 40: poor image, obscured view, or genuinely uncertain
   Most casual phone photos in ordinary lighting should land in the 40-70 band.
   A confidence above 85 requires you to justify it in clinical_notes.

6. IMAGE QUALITY CAPS CONFIDENCE.
   If lighting is warm/yellow, the tongue is partly obscured, the image is
   blurry, or colour is unreliable, say so in image_quality_notes AND cap
   confidence_overall at 55. Colour-dependent patterns (Heat, Cold, Blood
   stasis) cannot be assessed reliably under coloured lighting — say so.

7. NEVER FABRICATE. If the tongue is not visible, set tongue_visible false and
   leave tongue fields as "Not assessable". Same for the face. Do not infer
   tongue findings from a face-only photo or vice versa.

8. NO MEDICAL CLAIMS. This is a wellness screening tool, not a diagnosis.
   Output must be valid JSON matching the requested schema exactly.
"""


# ─── Confidence calibration (enforced in code, not left to the LLM) ──────────

def calibrate_confidence(result: dict) -> dict:
    """
    Apply hard confidence caps based on evidence quality.

    The LLM cannot be trusted to limit its own confidence, so we enforce
    ceilings here based on measurable properties of the response:
      - poor/fair image quality
      - unreliable colour assessment
      - patterns with too few cited indicators
      - patterns whose evidence_strength is self-declared weak

    Also drops patterns that fail the minimum-evidence bar entirely.
    """
    quality = str(result.get("image_quality", "")).lower()
    color_ok = result.get("color_assessment_reliable", True)

    # ── Determine the ceiling ─────────────────────────────────────────────────
    ceiling = 100
    caps = []

    if quality == "poor":
        ceiling = min(ceiling, 40)
        caps.append("poor image quality")
    elif quality == "fair":
        ceiling = min(ceiling, 65)
        caps.append("fair image quality")

    if color_ok is False:
        ceiling = min(ceiling, 55)
        caps.append("colour unreliable under this lighting")

    # ── Filter and calibrate individual patterns ─────────────────────────────
    patterns = result.get("tcm_patterns", []) or []
    kept = []
    for p in patterns:
        support = p.get("supporting_indicators", []) or []
        strength = str(p.get("evidence_strength", "moderate")).lower()
        conf = p.get("confidence", 50)
        try:
            conf = float(conf)
        except (TypeError, ValueError):
            conf = 50.0

        is_balanced = "balanced" in str(p.get("pattern_en", "")).lower() \
            or "no significant" in str(p.get("pattern_en", "")).lower()

        # Minimum-evidence bar: a pathological pattern needs >= 2 cited findings
        if not is_balanced and len(support) < 2:
            continue

        # Evidence-strength ceilings
        if strength == "weak":
            conf = min(conf, 50)
        elif strength == "moderate":
            conf = min(conf, 75)

        # Fewer cited findings => lower ceiling
        if not is_balanced:
            if len(support) == 2:
                conf = min(conf, 70)
            elif len(support) == 3:
                conf = min(conf, 82)

        # Contradicting evidence reduces confidence
        contra = p.get("contradicting_indicators", []) or []
        if contra:
            conf = max(0, conf - 8 * len(contra))

        p["confidence"] = int(round(min(conf, ceiling)))
        kept.append(p)

    # If every pattern was filtered out, the honest answer is "balanced"
    if not kept:
        kept = [{
            "pattern_en": "No significant pattern — Balanced",
            "pattern_zh": "平和质",
            "confidence": min(60, ceiling),
            "supporting_indicators": ["No findings outside normal limits were identified"],
            "contradicting_indicators": [],
            "evidence_strength": "moderate",
        }]
        result["primary_pattern"] = "No significant pattern — Balanced"
        result["primary_pattern_zh"] = "平和质"
        result["constitution_type"] = "Balanced (平和质)"
        result["constitution_zh"] = "平和质"

    kept.sort(key=lambda x: x.get("confidence", 0), reverse=True)
    result["tcm_patterns"] = kept

    # ── Overall confidence: cannot exceed the top pattern or the ceiling ─────
    overall = result.get("confidence_overall", 50)
    try:
        overall = float(overall)
    except (TypeError, ValueError):
        overall = 50.0

    top = kept[0].get("confidence", 50) if kept else 50
    result["confidence_overall"] = int(round(min(overall, ceiling, top)))

    if caps:
        result["confidence_capped_because"] = caps

    return result


# ─── Shared assessment prompt builder ────────────────────────────────────────

def build_assessment_prompt(focus_instructions: str, yolo_section: str = "") -> str:
    """
    Build the calibrated TCM assessment prompt.
    Used by both analyze_tcm_visual() and analyze_with_yolo_pipeline()
    so both paths share identical anti-bias calibration.
    """
    return f"""Assess this image using TCM observation method. {focus_instructions}{yolo_section}

WORK IN THIS ORDER:

STEP 1 — RAW OBSERVATION. Before thinking about any TCM pattern, describe
literally what you see: actual colours, actual textures, actual shapes. Put
this in raw_observations.

STEP 2 — COMPARE TO NORMAL. For each observation, decide whether it falls
within the healthy baseline or genuinely deviates from it. Remember: pale-red
body with thin white coating is NORMAL. Mild edge scalloping is NORMAL.

STEP 3 — ONLY THEN assign patterns, and only for genuine deviations. If
everything is within normal limits, report "No significant pattern — Balanced"
and constitution 平和质. That is a correct and common result.

Respond ONLY with a single valid JSON object matching this exact schema:

{{
  "raw_observations": [
    "Literal description of what you see, e.g. 'tongue body is medium pink, slightly lighter at the tip'",
    "e.g. 'thin translucent white film across the middle third, tongue surface visible beneath'",
    "e.g. 'image has a warm colour cast from indoor incandescent lighting'"
  ],
  "deviations_from_normal": [
    "Only findings that genuinely fall OUTSIDE the healthy baseline. Empty list is a valid and common answer."
  ],
  "image_quality": "good | fair | poor",
  "image_quality_notes": "Note lighting colour cast, focus, angle, and what this makes unreliable",
  "color_assessment_reliable": true,
  "tongue_visible": true,
  "face_visible": true,
  "tongue": {{
    "body_color": "Observed colour, or 'Not assessable' if not visible",
    "coating_color": "Observed coating, or 'Not assessable'",
    "coating_thickness": "None | Thin | Moderate | Thick | Not assessable",
    "coating_texture": "Moist | Dry | Greasy | Peeled | Not assessable",
    "shape": "Normal | Swollen | Thin | Cracked | Teeth-marked | Not assessable",
    "moisture": "Dry | Normal | Moist | Excessively wet | Not assessable",
    "special_features": ["Only genuinely notable features. Empty list if none."],
    "within_normal_limits": true,
    "findings_summary": "2-3 sentences. Say plainly if findings are normal."
  }},
  "face": {{
    "overall_complexion": "Observed, or 'Not assessable'",
    "lustre": "Bright | Dull | Normal | Not assessable",
    "zone_findings": {{
      "forehead": "State 'Normal' if unremarkable — do not invent findings",
      "between_eyebrows": "Normal, or specific observed deviation",
      "nose_bridge": "Normal, or specific observed deviation",
      "nose_tip": "Normal, or specific observed deviation",
      "cheeks": "Normal, or specific observed deviation",
      "chin": "Normal, or specific observed deviation"
    }},
    "eyes": {{
      "sclera": "White | Red | Yellow | Dull | Not assessable",
      "lower_lids": "Normal | Dark circles | Puffy | Not assessable",
      "overall": "Bright/Shen good | Dull/Shen poor | Normal | Not assessable"
    }},
    "skin_texture": "Observed, or 'Not assessable'",
    "within_normal_limits": true,
    "findings_summary": "2-3 sentences. Say plainly if findings are normal."
  }},
  "tcm_patterns": [
    {{
      "pattern_en": "Pattern name, or 'No significant pattern — Balanced'",
      "pattern_zh": "中文名 or 平和质",
      "confidence": 55,
      "supporting_indicators": ["MUST list at least 2 specific things you actually saw"],
      "contradicting_indicators": ["Findings that argue against this pattern — be honest"],
      "evidence_strength": "strong | moderate | weak"
    }}
  ],
  "primary_pattern": "Most likely pattern, or 'No significant pattern — Balanced'",
  "primary_pattern_zh": "主证中文名 or 平和质",
  "secondary_patterns": ["Only if genuinely present — empty list is fine"],
  "constitution_type": "e.g. Balanced (平和质) / Qi Deficiency (气虚质)",
  "constitution_zh": "平和质",
  "affected_organs": ["Only organs with actual visual evidence — empty list if none"],
  "pathogenic_factors": ["Only factors with actual visual evidence — empty list if none"],
  "diagnosis_summary": "3-4 sentences. If the person appears healthy, say so clearly and do not pad with speculative pathology.",
  "recommended_therapeutic_principles": ["For a balanced result, use general wellness maintenance principles"],
  "recommended_focus_areas": ["General wellness if balanced"],
  "suggested_condition_input": "Pre-fill text for formulation generator. If balanced, describe general wellness goals rather than symptoms.",
  "suggested_tcm_pattern": "Pre-fill pattern, or 'Balanced constitution — general wellness'",
  "suggested_demographic": "Brief demographic description",
  "confidence_overall": 55,
  "confidence_rationale": "One sentence explaining WHY this confidence level — reference image quality and evidence strength",
  "limitations": ["What this photo could NOT tell you, e.g. 'Pulse and symptom history unavailable', 'Warm lighting makes colour assessment unreliable'"],
  "clinical_notes": "Caveats. If confidence is above 85, justify it here.",
  "disclaimer": "This visual assessment is a preliminary AI-assisted wellness screening tool based on traditional TCM observation theory. It is not a medical diagnosis and cannot replace examination by a registered TCM practitioner, which includes pulse diagnosis, inquiry, and clinical history."
}}

REMINDERS BEFORE YOU ANSWER:
- A healthy tongue with thin white coating is NORMAL. Report it as normal.
- Do not diagnose Spleen Qi Deficiency / Phlegm-Damp unless you see a genuinely
  swollen pale body AND thick greasy coating AND deep pronounced teeth marks.
- Casual phone photos rarely justify confidence above 70.
- Every pattern needs at least 2 specific cited observations or you must drop it.
- Empty lists are honest answers. Padding with speculative findings is not."""


# ─── Main analysis function ──────────────────────────────────────────────────

def analyze_tcm_visual(image_bytes: bytes, scan_focus: str, api_key: str) -> dict:
    """
    Analyse a camera image for TCM diagnostic indicators.

    Args:
        image_bytes: Raw image bytes from st.camera_input() or file upload
        scan_focus: "tongue" | "face" | "full" (tongue + face combined)
        api_key: Anthropic API key

    Returns:
        Structured dict with TCM diagnosis, patterns, and formulation pre-fill data
    """
    client = anthropic.Anthropic(api_key=api_key)

    # Pre-process
    processed = preprocess_image(image_bytes)
    b64 = encode_image_b64(processed)

    focus_instructions = {
        "tongue": "Focus primarily on TONGUE diagnosis. The image may or may not show the face — prioritise the tongue.",
        "face": "Focus on FACIAL complexion, skin, eyes, and five-zone face mapping. Analyse the face holistically.",
        "full": "Perform COMPREHENSIVE analysis of BOTH tongue (if shown) and face. Cross-reference findings between tongue and face for higher-confidence pattern identification.",
    }.get(scan_focus, "Analyse all visible diagnostic indicators.")

    prompt = build_assessment_prompt(focus_instructions)

    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=3000,
        system=VISION_SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": b64,
                    },
                },
                {"type": "text", "text": prompt}
            ],
        }]
    )

    raw = response.content[0].text.strip()
    start = raw.find('{')
    end = raw.rfind('}') + 1
    if start == -1 or end == 0:
        return {
            "error": "Could not parse vision response",
            "raw": raw,
            "confidence_overall": 0,
            "disclaimer": "Analysis failed. Please retake the image with better lighting."
        }

    result = json.loads(raw[start:end])
    return calibrate_confidence(result)


# ─── Comparative pattern enrichment ─────────────────────────────────────────

def enrich_visual_diagnosis(diagnosis: dict, api_key: str) -> str:
    """
    Generate a detailed clinical narrative from the structured visual diagnosis.
    Uses Haiku for speed.
    """
    client = anthropic.Anthropic(api_key=api_key)

    primary = diagnosis.get("primary_pattern", "Unknown pattern")
    summary = diagnosis.get("diagnosis_summary", "")
    principles = diagnosis.get("recommended_therapeutic_principles", [])
    constitution = diagnosis.get("constitution_type", "")
    tongue_findings = diagnosis.get("tongue", {}).get("findings_summary", "")
    face_findings = diagnosis.get("face", {}).get("findings_summary", "")

    prompt = f"""Based on the following TCM visual diagnosis results, write a clear, educational explanation (3 short paragraphs) for the patient/user.

PRIMARY PATTERN: {primary}
CONSTITUTION: {constitution}
TONGUE FINDINGS: {tongue_findings}
FACE FINDINGS: {face_findings}
DIAGNOSIS SUMMARY: {summary}
THERAPEUTIC PRINCIPLES: {', '.join(principles)}

Write in plain, friendly English — not overly clinical. Explain:
1. What the visual signs mean in TCM terms
2. How this pattern typically manifests as symptoms in daily life
3. What TCM treatment approach (herb types, lifestyle) is generally recommended

Keep total response under 250 words."""

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text


# ─── Image guidance helpers ──────────────────────────────────────────────────

def get_camera_guidance(scan_type: str) -> dict:
    """Returns user-facing camera guidance for each scan type."""
    guides = {
        "tongue": {
            "title": "Tongue Scan Guide",
            "steps": [
                "Find good natural or white LED lighting — avoid yellow light",
                "Open mouth wide and extend tongue fully",
                "Hold camera 20–30 cm from tongue",
                "Keep tongue relaxed and flat — don't curl edges",
                "Take photo in a single steady capture",
            ],
            "avoid": [
                "Eating, drinking or brushing teeth 30 min before scan",
                "Coloured foods (berries, coffee) that stain tongue",
                "Flash photography — causes colour distortion",
            ],
            "icon": "👅",
        },
        "face": {
            "title": "Face Scan Guide",
            "steps": [
                "Use natural daylight or neutral white lighting",
                "Face camera directly — no side angles",
                "Remove heavy makeup for best complexion reading",
                "Relax facial muscles — neutral expression",
                "Keep hair away from face",
            ],
            "avoid": [
                "Strong directional lighting (shadows distort complexion)",
                "Sunglasses or tinted lenses",
                "Filters or beauty modes on phone camera",
            ],
            "icon": "🙂",
        },
        "full": {
            "title": "Full Diagnostic Scan Guide",
            "steps": [
                "Step 1 — Face scan first: neutral expression, good lighting",
                "Step 2 — Open mouth and extend tongue clearly",
                "Both tongue and face should be visible in one frame if possible",
                "Or take two separate photos (face first, then tongue)",
                "Use natural or neutral white light only",
            ],
            "avoid": [
                "Heavy makeup, coloured foods, yellow lighting",
                "Flash or phone beauty/filter modes",
            ],
            "icon": "🔬",
        },
    }
    return guides.get(scan_type, guides["full"])


PATTERN_HERB_HINTS = {
    "Heart Blood Deficiency": ["炒酸枣仁", "当归", "龙眼肉", "茯神", "柏子仁"],
    "Liver Qi Stagnation": ["柴胡", "白芍", "香附", "郁金", "合欢皮"],
    "Spleen Qi Deficiency": ["党参", "白术", "茯苓", "炙甘草", "山药"],
    "Kidney Yin Deficiency": ["熟地黄", "山茱萸", "枸杞子", "女贞子", "旱莲草"],
    "Kidney Yang Deficiency": ["制附子", "肉桂", "仙灵脾", "菟丝子", "巴戟天"],
    "Phlegm-Damp": ["法半夏", "陈皮", "茯苓", "薏苡仁", "苍术"],
    "Damp-Heat": ["黄连", "黄芩", "茵陈", "龙胆草", "泽泻"],
    "Blood Stasis": ["丹参", "桃仁", "红花", "川芎", "赤芍"],
    "Yin Deficiency with Empty Heat": ["知母", "黄柏", "生地黄", "麦冬", "地骨皮"],
    "Heart-Spleen Deficiency": ["党参", "炒酸枣仁", "龙眼肉", "白术", "茯神"],
    "Liver Yang Rising": ["天麻", "钩藤", "石决明", "白芍", "牛膝"],
    "Qi and Blood Deficiency": ["黄芪", "当归", "党参", "熟地黄", "白芍"],
}


def get_pattern_herb_hints(primary_pattern: str) -> list:
    """Match primary pattern to likely key herbs from inventory."""
    for key, herbs in PATTERN_HERB_HINTS.items():
        if any(word.lower() in primary_pattern.lower() for word in key.split()):
            return herbs
    return []


# ─── YOLO + Claude combined pipeline ─────────────────────────────────────────

def analyze_with_yolo_pipeline(
    image_bytes: bytes,
    scan_focus: str,
    api_key: str,
    detector=None,
    conf_threshold: float = 0.25,
) -> dict:
    """
    Full Option-3 pipeline:
      1. Run YOLOv8 tongue feature detection (if model available)
      2. Build structured YOLO context string
      3. Pass context + image to Claude Vision for synthesis
      4. Merge YOLO metadata into result

    Returns the same schema as analyze_tcm_visual() plus:
      {
        "yolo_available": bool,
        "yolo_detections": [...],
        "yolo_patterns": [...],
        "yolo_constitution": "...",
        "yolo_focus_areas": [...],
        "annotated_image": PIL.Image or None,
        "pipeline_mode": "yolo+claude" | "claude_only"
      }
    """
    # ── Step 1: YOLO detection ────────────────────────────────────────────────
    yolo_result = {"yolo_available": False, "detections": []}

    if detector is None:
        try:
            from tongue_detector import get_detector
            detector = get_detector()
        except Exception:
            pass

    if detector is not None and getattr(detector, "is_ready", False):
        try:
            yolo_result = detector.detect(image_bytes, conf_threshold=conf_threshold)
        except Exception as e:
            yolo_result = {"yolo_available": False, "detections": [], "error": str(e)}

    yolo_context = yolo_result.get("claude_context", "")

    # ── Step 2: Claude Vision (with YOLO pre-context injected) ────────────────
    client = anthropic.Anthropic(api_key=api_key)
    processed = preprocess_image(image_bytes)
    b64 = encode_image_b64(processed)

    focus_instructions = {
        "tongue": "Focus primarily on TONGUE diagnosis.",
        "face": "Focus on FACIAL complexion, skin, eyes, and five-zone face mapping.",
        "full": "Perform COMPREHENSIVE analysis of BOTH tongue (if shown) and face.",
    }.get(scan_focus, "Analyse all visible diagnostic indicators.")

    # Prepend YOLO structured findings if available
    yolo_section = ""
    if yolo_context:
        yolo_section = f"\n\nOBJECTIVE AI PRE-DETECTION (YOLOv8 trained on 19,585 tongue images):\n{yolo_context}\n\nPlease incorporate these objective detections into your analysis. They are the result of a specialised tongue-feature detector; treat them as a second clinical observer's findings.\n"

    prompt = build_assessment_prompt(focus_instructions, yolo_section)

    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=3000,
        system=VISION_SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": b64,
                    },
                },
                {"type": "text", "text": prompt}
            ],
        }]
    )

    raw = response.content[0].text.strip()
    start = raw.find('{')
    end = raw.rfind('}') + 1
    if start == -1 or end == 0:
        result = {
            "error": "Could not parse vision response",
            "raw": raw,
            "confidence_overall": 0,
            "disclaimer": "Analysis failed. Please retake the image with better lighting."
        }
    else:
        result = calibrate_confidence(json.loads(raw[start:end]))

    # ── Step 3: Merge YOLO metadata into result ───────────────────────────────
    result["yolo_available"] = yolo_result.get("yolo_available", False)
    result["yolo_detections"] = yolo_result.get("detections", [])
    result["yolo_patterns"] = yolo_result.get("patterns", [])
    result["yolo_constitution"] = yolo_result.get("constitution", "")
    result["yolo_focus_areas"] = yolo_result.get("focus_areas", [])
    result["annotated_image"] = yolo_result.get("annotated_image", None)
    result["pipeline_mode"] = "yolo+claude" if yolo_result.get("yolo_available") else "claude_only"

    return result
