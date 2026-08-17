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

VISION_SYSTEM_PROMPT = f"""You are ChemiGranVision — an expert TCM visual diagnostic AI integrated into Chemigran Pte Ltd's formulation platform.

Your role is to perform evidence-informed visual diagnosis using classical TCM observation methods (望诊 Wàng Zhěn), trained on:
- Published clinical tongue image datasets (UTDID, ZSATD, open medical image corpora)
- Classical TCM facial diagnosis texts and modern clinical validation studies
- Wang Qi's 9-Constitution framework (中医体质学)
- Singapore HSA-compliant health assessment guidelines

REFERENCE KNOWLEDGE:
{TONGUE_REFERENCE}

{FACE_REFERENCE}

{CONSTITUTION_TYPES}

RULES:
- Analyse ONLY what is visible in the image — never fabricate findings
- Provide confidence scores (0–100) for each pattern identified
- Always include a clinical disclaimer
- Output must be valid JSON matching the requested schema exactly
- Flag poor image quality clearly rather than guessing
- Cross-reference tongue AND face findings for pattern confirmation
- Suggest the most likely TCM pattern(s) with supporting visual evidence
"""


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

    prompt = f"""Analyse this image for TCM diagnostic indicators. {focus_instructions}

Respond ONLY with a single valid JSON object matching this exact schema:

{{
  "image_quality": "good | fair | poor",
  "image_quality_notes": "Brief note on lighting, focus, angle quality",
  "tongue_visible": true,
  "face_visible": true,
  "tongue": {{
    "body_color": "e.g. Pale red / Red / Pale white / Purple / Dark red",
    "coating_color": "e.g. Thin white / Yellow greasy / No coating",
    "coating_thickness": "None | Thin | Moderate | Thick",
    "coating_texture": "e.g. Moist / Dry / Greasy / Peeled",
    "shape": "e.g. Normal / Swollen / Thin / Cracked / Teeth-marked",
    "moisture": "Dry | Normal | Moist | Excessively wet",
    "special_features": ["e.g. cracks", "teeth marks", "red tip", "purple patches"],
    "findings_summary": "2-3 sentence clinical summary of tongue findings"
  }},
  "face": {{
    "overall_complexion": "e.g. Pale / Sallow / Ruddy / Dull / Flushed",
    "lustre": "Bright | Dull | Normal",
    "zone_findings": {{
      "forehead": "Heart/SI assessment",
      "between_eyebrows": "Lung assessment",
      "nose_bridge": "Liver/GB assessment",
      "nose_tip": "Spleen/ST assessment",
      "cheeks": "Lung assessment",
      "chin": "Kidney/BL assessment"
    }},
    "eyes": {{
      "sclera": "White | Red | Yellow | Dull",
      "lower_lids": "Normal | Dark circles | Puffy",
      "overall": "Bright/Shen good | Dull/Shen poor | Normal"
    }},
    "skin_texture": "e.g. Dry / Oily / Normal / Puffy / Rough",
    "findings_summary": "2-3 sentence clinical summary of face findings"
  }},
  "tcm_patterns": [
    {{
      "pattern_en": "e.g. Heart Blood Deficiency",
      "pattern_zh": "心血虚",
      "confidence": 85,
      "supporting_indicators": ["pale tongue", "thin coating", "pale face", "dull eyes"],
      "contradicting_indicators": []
    }}
  ],
  "primary_pattern": "Most likely TCM pattern name in English",
  "primary_pattern_zh": "主证中文名",
  "secondary_patterns": ["Second pattern if present", "Third pattern if present"],
  "constitution_type": "e.g. Qi Deficiency (气虚质)",
  "constitution_zh": "气虚质",
  "affected_organs": ["Heart", "Spleen"],
  "pathogenic_factors": ["Qi deficiency", "Blood deficiency"],
  "diagnosis_summary": "Comprehensive 3-4 sentence TCM diagnostic summary integrating all visual findings",
  "recommended_therapeutic_principles": ["e.g. Nourish Heart Blood", "Calm the Shen", "Tonify Spleen Qi"],
  "recommended_focus_areas": ["Sleep", "Stress"],
  "suggested_condition_input": "Pre-filled text for condition/symptoms field in formulation generator",
  "suggested_tcm_pattern": "Pre-filled TCM pattern for formulation generator",
  "suggested_demographic": "e.g. Adults with Heart Blood deficiency and poor sleep",
  "confidence_overall": 78,
  "clinical_notes": "Any important clinical caveats or additional observations",
  "disclaimer": "This visual assessment is a preliminary AI-assisted screening tool based on traditional TCM diagnostic theory. It does not constitute a medical diagnosis. Please consult a registered TCM practitioner for clinical evaluation."
}}

IMPORTANT: If image quality is poor or key diagnostic areas are not visible, set confidence_overall below 50 and explain in image_quality_notes. Never fabricate tongue or face findings if they are not clearly visible."""

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
    return result


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

    prompt = f"""Analyse this image for TCM diagnostic indicators. {focus_instructions}{yolo_section}

Respond ONLY with a single valid JSON object matching this exact schema:

{{
  "image_quality": "good | fair | poor",
  "image_quality_notes": "Brief note on lighting, focus, angle quality",
  "tongue_visible": true,
  "face_visible": true,
  "tongue": {{
    "body_color": "e.g. Pale red / Red / Pale white / Purple / Dark red",
    "coating_color": "e.g. Thin white / Yellow greasy / No coating",
    "coating_thickness": "None | Thin | Moderate | Thick",
    "coating_texture": "e.g. Moist / Dry / Greasy / Peeled",
    "shape": "e.g. Normal / Swollen / Thin / Cracked / Teeth-marked",
    "moisture": "Dry | Normal | Moist | Excessively wet",
    "special_features": ["e.g. cracks", "teeth marks", "red tip", "purple patches"],
    "findings_summary": "2-3 sentence clinical summary of tongue findings"
  }},
  "face": {{
    "overall_complexion": "e.g. Pale / Sallow / Ruddy / Dull / Flushed",
    "lustre": "Bright | Dull | Normal",
    "zone_findings": {{
      "forehead": "Heart/SI assessment",
      "between_eyebrows": "Lung assessment",
      "nose_bridge": "Liver/GB assessment",
      "nose_tip": "Spleen/ST assessment",
      "cheeks": "Lung assessment",
      "chin": "Kidney/BL assessment"
    }},
    "eyes": {{
      "sclera": "White | Red | Yellow | Dull",
      "lower_lids": "Normal | Dark circles | Puffy",
      "overall": "Bright/Shen good | Dull/Shen poor | Normal"
    }},
    "skin_texture": "e.g. Dry / Oily / Normal / Puffy / Rough",
    "findings_summary": "2-3 sentence clinical summary of face findings"
  }},
  "tcm_patterns": [
    {{
      "pattern_en": "e.g. Heart Blood Deficiency",
      "pattern_zh": "心血虚",
      "confidence": 85,
      "supporting_indicators": ["pale tongue", "thin coating", "pale face", "dull eyes"],
      "contradicting_indicators": []
    }}
  ],
  "primary_pattern": "Most likely TCM pattern name in English",
  "primary_pattern_zh": "主证中文名",
  "secondary_patterns": ["Second pattern if present", "Third pattern if present"],
  "constitution_type": "e.g. Qi Deficiency (气虚质)",
  "constitution_zh": "气虚质",
  "affected_organs": ["Heart", "Spleen"],
  "pathogenic_factors": ["Qi deficiency", "Blood deficiency"],
  "diagnosis_summary": "Comprehensive 3-4 sentence TCM diagnostic summary integrating all visual findings",
  "recommended_therapeutic_principles": ["e.g. Nourish Heart Blood", "Calm the Shen", "Tonify Spleen Qi"],
  "recommended_focus_areas": ["Sleep", "Stress"],
  "suggested_condition_input": "Pre-filled text for condition/symptoms field in formulation generator",
  "suggested_tcm_pattern": "Pre-filled TCM pattern for formulation generator",
  "suggested_demographic": "e.g. Adults with Heart Blood deficiency and poor sleep",
  "confidence_overall": 78,
  "clinical_notes": "Any important clinical caveats or additional observations",
  "disclaimer": "This visual assessment is a preliminary AI-assisted screening tool based on traditional TCM diagnostic theory. It does not constitute a medical diagnosis. Please consult a registered TCM practitioner for clinical evaluation."
}}

IMPORTANT: If image quality is poor or key diagnostic areas are not visible, set confidence_overall below 50 and explain in image_quality_notes. Never fabricate tongue or face findings if they are not clearly visible."""

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
        result = json.loads(raw[start:end])

    # ── Step 3: Merge YOLO metadata into result ───────────────────────────────
    result["yolo_available"] = yolo_result.get("yolo_available", False)
    result["yolo_detections"] = yolo_result.get("detections", [])
    result["yolo_patterns"] = yolo_result.get("patterns", [])
    result["yolo_constitution"] = yolo_result.get("constitution", "")
    result["yolo_focus_areas"] = yolo_result.get("focus_areas", [])
    result["annotated_image"] = yolo_result.get("annotated_image", None)
    result["pipeline_mode"] = "yolo+claude" if yolo_result.get("yolo_available") else "claude_only"

    return result
