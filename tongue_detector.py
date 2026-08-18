"""
tongue_detector.py — YOLOv8 Tongue Feature Detector + TCM Pattern Mapper
------------------------------------------------------------------------
Runs the trained YOLOv8 model on a camera image and returns:
  - Detected tongue features with bounding boxes and confidence scores
  - Mapped TCM patterns and indicators
  - Annotated image with detection overlay
  - Structured context string for Claude Vision synthesis
"""

import json
import io
from pathlib import Path
from collections import defaultdict
from PIL import Image, ImageDraw, ImageFont

# ── TCM mapping ───────────────────────────────────────────────────────────────
TCM_MEANING = {
    "jiankangshe":  {"zh": "健康舌",  "meaning": "Healthy tongue",          "tcm": "Balanced constitution",                          "color": (34,197,94)},
    "botaishe":     {"zh": "薄苔舌",  "meaning": "Thin coating",             "tcm": "Normal or mild exterior pattern",                "color": (148,163,184)},
    "hongshe":      {"zh": "红舌",    "meaning": "Red tongue body",          "tcm": "Heat pattern; Yin deficiency",                   "color": (239,68,68)},
    "zishe":        {"zh": "紫舌",    "meaning": "Purple tongue",            "tcm": "Blood stasis; Cold obstructing vessels",         "color": (168,85,247)},
    "pangdashe":    {"zh": "胖大舌",  "meaning": "Swollen tongue",           "tcm": "Spleen Qi deficiency; Phlegm-Damp",              "color": (249,115,22)},
    "shoushe":      {"zh": "瘦舌",    "meaning": "Thin/lean tongue",         "tcm": "Blood deficiency; Yin deficiency",               "color": (234,179,8)},
    "hongdianshe":  {"zh": "红点舌",  "meaning": "Red dots on tongue",       "tcm": "Heat toxin; Blood Heat",                         "color": (220,38,38)},
    "liewenshe":    {"zh": "裂纹舌",  "meaning": "Cracked tongue",           "tcm": "Yin deficiency; Heat consuming fluids",          "color": (245,158,11)},
    "chihenshe":    {"zh": "齿痕舌",  "meaning": "Teeth-marked edges",       "tcm": "Spleen Qi deficiency with Damp retention",       "color": (16,185,129)},
    "baitaishe":    {"zh": "白苔舌",  "meaning": "White coating",            "tcm": "Cold pattern; Normal (thin); Cold-Damp (thick)", "color": (226,232,240)},
    "huangtaishe":  {"zh": "黄苔舌",  "meaning": "Yellow coating",           "tcm": "Heat; Damp-Heat; interior Heat accumulation",    "color": (234,179,8)},
    "heitaishe":    {"zh": "黑苔舌",  "meaning": "Black/grey coating",       "tcm": "Extreme Cold (moist) or extreme Heat (dry)",     "color": (71,85,105)},
    "huataishe":    {"zh": "花苔舌",  "meaning": "Peeled/geographic coating","tcm": "Stomach Yin deficiency; chronic illness",        "color": (251,191,36)},
    "shenquao":     {"zh": "肾区凹",  "meaning": "Kidney zone concave",      "tcm": "Kidney deficiency (Yin or Yang)",                "color": (59,130,246)},
    "shenqutu":     {"zh": "肾区凸",  "meaning": "Kidney zone convex",       "tcm": "Kidney excess pattern",                          "color": (37,99,235)},
    "gandanao":     {"zh": "肝胆区凹","meaning": "Liver/GB zone concave",    "tcm": "Liver Blood or Yin deficiency",                  "color": (34,197,94)},
    "gandantu":     {"zh": "肝胆区凸","meaning": "Liver/GB zone convex",     "tcm": "Liver Qi stagnation; Liver Fire",                "color": (21,128,61)},
    "piweiao":      {"zh": "脾胃区凹","meaning": "Spleen/Stomach zone concave","tcm": "Spleen Qi or Yang deficiency",                 "color": (249,115,22)},
    "piweitu":      {"zh": "脾胃区凸","meaning": "Spleen/Stomach zone convex", "tcm": "Food stagnation; Stomach excess",              "color": (234,88,12)},
    "xinfeiao":     {"zh": "心肺区凹","meaning": "Heart/Lung zone concave",  "tcm": "Heart or Lung Qi/Blood deficiency",              "color": (236,72,153)},
    "xinfeitu":     {"zh": "心肺区凸","meaning": "Heart/Lung zone convex",   "tcm": "Heart Fire; Lung Heat or Phlegm",                "color": (190,24,93)},
}

# ── Per-class validated reliability ───────────────────────────────────────────
# Measured mAP50 on the held-out test set. Detections from unreliable classes
# have their confidence down-weighted so the pipeline does not present a
# poorly-validated class with the same authority as a well-validated one.
# Overall model mAP50 = 0.325 — only the coating classes are genuinely strong.
CLASS_RELIABILITY = {
    "baitaishe":    0.94,   # white coating   — mAP50 0.935  (strong)
    "huangtaishe":  0.82,   # yellow coating  — mAP50 0.817  (strong)
    "shoushe":      0.62,   # thin tongue     — mAP50 0.623  (moderate)
    "jiankangshe":  0.50,
    "botaishe":     0.45,
    "hongshe":      0.40,
    "pangdashe":    0.35,
    "chihenshe":    0.35,
    "liewenshe":    0.35,
    "hongdianshe":  0.30,
    "zishe":        0.30,
    "heitaishe":    0.25,
    "huataishe":    0.25,
    # Zone classes were the weakest in training — treat as indicative only
    "shenquao":     0.20, "shenqutu":  0.20,
    "gandanao":     0.20, "gandantu":  0.20,
    "piweiao":      0.20, "piweitu":   0.20,
    "xinfeiao":     0.20, "xinfeitu":  0.20,
}
DEFAULT_RELIABILITY = 0.25

# ── Pattern synthesis rules ───────────────────────────────────────────────────
# Each rule is (required_features, pattern, confidence_bonus, mode)
#   mode "all" → EVERY listed feature must be detected (combination patterns)
#   mode "any" → a single listed feature is sufficient (single-sign patterns)
#
# NOTE: combination patterns such as Spleen Qi Deficiency with Phlegm-Damp are
# genuinely combination findings. Requiring only one of their features (the old
# behaviour) produced the same pattern for almost every image.
PATTERN_RULES = [
    # ── Combination patterns — ALL features required ──────────────────────────
    ({"pangdashe", "chihenshe"},   "Spleen Qi Deficiency with Phlegm-Damp",  12, "all"),
    ({"liewenshe", "shoushe"},     "Yin Deficiency with Empty Heat",         12, "all"),
    ({"hongshe", "huangtaishe"},   "Excess Heat / Liver Fire",               12, "all"),
    ({"hongshe", "liewenshe"},     "Yin Deficiency with Heat",               10, "all"),
    ({"pangdashe", "baitaishe"},   "Spleen Yang Deficiency with Cold-Damp",  10, "all"),
    ({"huangtaishe", "chihenshe"}, "Damp-Heat accumulation",                 10, "all"),
    ({"shenquao", "shoushe"},      "Kidney Yin Deficiency",                   8, "all"),
    ({"shenquao", "pangdashe"},    "Kidney Yang Deficiency",                  8, "all"),
    ({"gandantu", "hongshe"},      "Liver Fire Rising",                       8, "all"),

    # ── Single-sign patterns — one distinctive feature is sufficient ──────────
    ({"zishe"},                    "Blood Stasis",                            6, "any"),
    ({"huataishe"},                "Stomach Yin Deficiency",                  6, "any"),
    ({"heitaishe"},                "Extreme pattern (Cold or Heat)",          6, "any"),
    ({"hongdianshe"},              "Heat Toxin / Blood Heat",                 6, "any"),
    ({"xinfeiao"},                 "Heart-Lung Qi Deficiency",                4, "any"),
    ({"piweiao"},                  "Spleen-Stomach Deficiency",               4, "any"),
]

# Detections below this confidence are ignored entirely
MIN_DETECTION_CONF = 35.0

CONSTITUTION_MAP = {
    "pangdashe": "Phlegm-Damp Constitution (痰湿质)",
    "shoushe":   "Yin Deficiency Constitution (阴虚质)",
    "zishe":     "Blood Stasis Constitution (血瘀质)",
    "hongshe":   "Damp-Heat Constitution (湿热质)",
    "chihenshe": "Qi Deficiency Constitution (气虚质)",
    "liewenshe": "Yin Deficiency Constitution (阴虚质)",
}

# Suggested formulation focus areas per detected feature
FOCUS_MAP = {
    "hongshe":     ["Heat Clearing", "Yin Tonic"],
    "zishe":       ["Blood Stasis", "Circulation"],
    "pangdashe":   ["Spleen Qi", "Phlegm-Damp", "Gut Health"],
    "shoushe":     ["Blood Tonic", "Yin Tonic", "Healthy Aging"],
    "liewenshe":   ["Yin Tonic", "Healthy Aging"],
    "chihenshe":   ["Spleen Qi", "Gut Health"],
    "huangtaishe": ["Damp-Heat", "Gut Health"],
    "shenquao":    ["Kidney Tonic", "Healthy Aging", "Men's Health"],
    "gandantu":    ["Liver Qi", "Stress"],
    "xinfeiao":    ["Heart Tonic", "Sleep", "Stress"],
    "piweiao":     ["Spleen Qi", "Gut Health"],
    "huataishe":   ["Stomach Yin", "Healthy Aging"],
    "hongdianshe": ["Heat Clearing", "Detox"],
}


class DetectorNotAvailable(RuntimeError):
    """Raised in strict mode when the YOLO model cannot be loaded."""
    pass


class TongueDetector:
    def __init__(self, model_path: str = None):
        """
        Load the trained YOLOv8 model.

        Records the precise failure reason in self.load_error so the UI can
        report exactly why detection is unavailable rather than silently
        degrading to Claude-only analysis.
        """
        self.model = None
        self.model_path = None
        self.load_error = None
        self.class_names = []

        base = Path(__file__).parent / "models"
        if model_path is None:
            candidates = ["tongue_yolo_best.pt", "tongue_yolo_last.pt"]
            for c in candidates:
                p = base / c
                if p.exists():
                    model_path = str(p)
                    break

        if not model_path or not Path(model_path).exists():
            self.load_error = (
                f"Model file not found. Expected models/tongue_yolo_best.pt "
                f"under {base}. Train with train_yolo.py or train_colab.ipynb, "
                f"then place the weights there."
            )
            print(f"✗ TongueDetector: {self.load_error}")
            return

        try:
            from ultralytics import YOLO
        except ImportError as e:
            self.load_error = (
                f"ultralytics is not installed ({e}). Install with: "
                f"pip install ultralytics torch torchvision"
            )
            print(f"✗ TongueDetector: {self.load_error}")
            return
        except Exception as e:
            self.load_error = (
                f"ultralytics failed to import: {type(e).__name__}: {e}. "
                f"This is usually an OpenCV binary incompatibility — try "
                f"pip install opencv-python-headless"
            )
            print(f"✗ TongueDetector: {self.load_error}")
            return

        try:
            self.model = YOLO(model_path)
            self.model_path = model_path
            names = getattr(self.model, "names", {}) or {}
            self.class_names = [names[k] for k in sorted(names)] if names else []
            print(f"✓ TongueDetector loaded: {model_path} ({len(self.class_names)} classes)")
        except Exception as e:
            self.load_error = f"Model failed to load: {type(e).__name__}: {e}"
            self.model = None
            print(f"✗ TongueDetector: {self.load_error}")

    @property
    def is_ready(self) -> bool:
        return self.model is not None

    def require_ready(self):
        """Raise a descriptive error if the detector is not usable."""
        if not self.is_ready:
            raise DetectorNotAvailable(
                self.load_error or "YOLO detector is unavailable for an unknown reason."
            )

    def diagnostics(self) -> dict:
        """Machine-readable status for the UI diagnostics panel."""
        return {
            "ready": self.is_ready,
            "model_path": self.model_path,
            "num_classes": len(self.class_names),
            "class_names": self.class_names,
            "load_error": self.load_error,
            "validated_map50": 0.325,
            "strong_classes": [c for c, r in CLASS_RELIABILITY.items() if r >= 0.6],
        }

    def detect(self, image_bytes: bytes, conf_threshold: float = 0.25,
               strict: bool = False) -> dict:
        """
        Run YOLOv8 detection on image bytes.

        Args:
            strict: if True, raise DetectorNotAvailable instead of returning
                    an empty result when the model is not loaded.
        """
        if not self.is_ready:
            if strict:
                self.require_ready()
            return {"detections": [], "yolo_available": False,
                    "load_error": self.load_error}

        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        results = self.model.predict(img, conf=conf_threshold, verbose=False)[0]

        detections = []
        class_scores = defaultdict(list)

        for box in results.boxes:
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            cls_name = results.names.get(cls_id, f"class_{cls_id}")
            x1, y1, x2, y2 = [float(v) for v in box.xyxy[0]]
            meaning = TCM_MEANING.get(cls_name, {})

            det = {
                "class_id": cls_id,
                "class_name": cls_name,
                "confidence": round(conf * 100, 1),
                "bbox": [x1, y1, x2, y2],
                "zh": meaning.get("zh", ""),
                "meaning": meaning.get("meaning", cls_name),
                "tcm_significance": meaning.get("tcm", ""),
            }
            detections.append(det)
            class_scores[cls_name].append(conf)

        # Deduplicate: keep highest confidence per class
        seen = {}
        for d in sorted(detections, key=lambda x: -x["confidence"]):
            if d["class_name"] not in seen:
                seen[d["class_name"]] = d
        detections = list(seen.values())

        # Drop detections below the minimum usable confidence, and annotate
        # each surviving detection with its validated class reliability
        detections = [d for d in detections if d["confidence"] >= MIN_DETECTION_CONF]
        for d in detections:
            rel = CLASS_RELIABILITY.get(d["class_name"], DEFAULT_RELIABILITY)
            d["reliability"] = round(rel, 2)
            d["reliability_label"] = (
                "validated" if rel >= 0.6 else
                "moderate" if rel >= 0.35 else "low confidence class"
            )
        detections.sort(key=lambda x: -x["confidence"])
        seen = {d["class_name"]: d for d in detections}

        # Synthesise patterns from detections
        patterns = self._synthesise_patterns(detections)
        constitution = self._determine_constitution(detections)
        focus_areas = self._determine_focus(detections)
        annotated = self._annotate_image(img, detections)

        return {
            "yolo_available": True,
            "model_path": self.model_path,
            "detections": detections,
            "detected_classes": list(seen.keys()),
            "patterns": patterns,
            "primary_pattern": patterns[0]["pattern"] if patterns else "Unable to determine",
            "constitution": constitution,
            "focus_areas": focus_areas,
            "annotated_image": annotated,  # PIL Image with boxes drawn
            "claude_context": self._build_claude_context(detections, patterns, constitution),
        }

    def _synthesise_patterns(self, detections: list) -> list:
        """
        Synthesise TCM patterns from detected feature combinations.

        Combination rules require ALL their features to be present. Confidence
        is weighted by each class's validated reliability (mAP50), so a
        detection from a weak class cannot drive a high-confidence pattern.
        """
        detected_set = {d["class_name"] for d in detections}
        conf_by_class = {d["class_name"]: d["confidence"] for d in detections}
        patterns = []

        for required, pattern, bonus, mode in PATTERN_RULES:
            if mode == "all":
                if not required.issubset(detected_set):
                    continue
                matched = required
            else:
                matched = required & detected_set
                if not matched:
                    continue

            # Reliability-weighted mean confidence across the matched features
            weighted, total_w = 0.0, 0.0
            for cls in matched:
                rel = CLASS_RELIABILITY.get(cls, DEFAULT_RELIABILITY)
                weighted += conf_by_class.get(cls, 50) * rel
                total_w += rel
            base_conf = (weighted / total_w) if total_w else 50.0

            # Reliability of the weakest contributing class caps the pattern
            weakest = min(CLASS_RELIABILITY.get(c, DEFAULT_RELIABILITY) for c in matched)
            ceiling = 40 + (weakest * 55)      # rel 0.20 -> 51%, rel 0.94 -> 92%

            total_conf = min(ceiling, base_conf + bonus)

            patterns.append({
                "pattern": pattern,
                "confidence": round(total_conf, 1),
                "triggers": sorted(matched),
                "reliability": round(weakest, 2),
                "evidence_strength": (
                    "strong" if weakest >= 0.6 else
                    "moderate" if weakest >= 0.35 else "weak"
                ),
            })

        # Fallback: single-feature interpretation, but only for reliable classes
        if not patterns:
            for det in sorted(detections, key=lambda x: -x["confidence"])[:3]:
                cls = det["class_name"]
                rel = CLASS_RELIABILITY.get(cls, DEFAULT_RELIABILITY)
                if rel < 0.4:
                    continue          # too unreliable to stand alone
                tcm = TCM_MEANING.get(cls, {}).get("tcm", "")
                if tcm:
                    patterns.append({
                        "pattern": tcm.split(";")[0].strip(),
                        "confidence": round(min(det["confidence"], 40 + rel * 55), 1),
                        "triggers": [cls],
                        "reliability": round(rel, 2),
                        "evidence_strength": "moderate" if rel >= 0.6 else "weak",
                    })

        patterns.sort(key=lambda x: -x["confidence"])
        return patterns[:5]

    def _determine_constitution(self, detections: list) -> str:
        for det in sorted(detections, key=lambda x: -x["confidence"]):
            if det["class_name"] in CONSTITUTION_MAP:
                return CONSTITUTION_MAP[det["class_name"]]
        return "To be determined by clinical assessment"

    def _determine_focus(self, detections: list) -> list:
        focus = set()
        for det in detections:
            focus.update(FOCUS_MAP.get(det["class_name"], []))
        return list(focus)[:6]

    def _annotate_image(self, img: Image.Image, detections: list) -> Image.Image:
        """Draw bounding boxes and labels on the image."""
        draw = ImageDraw.Draw(img.copy())
        annotated = img.copy()
        draw = ImageDraw.Draw(annotated)

        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
            small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
        except Exception:
            font = ImageFont.load_default()
            small_font = font

        for det in detections:
            x1, y1, x2, y2 = det["bbox"]
            cls_name = det["class_name"]
            conf = det["confidence"]
            color = TCM_MEANING.get(cls_name, {}).get("color", (100, 200, 255))
            zh = TCM_MEANING.get(cls_name, {}).get("zh", cls_name)

            # Box
            draw.rectangle([x1, y1, x2, y2], outline=color, width=3)

            # Label background
            label = f"{zh} {conf:.0f}%"
            bbox_text = draw.textbbox((x1, y1 - 20), label, font=font)
            draw.rectangle([bbox_text[0]-2, bbox_text[1]-2, bbox_text[2]+2, bbox_text[3]+2],
                           fill=(*color, 200))
            draw.text((x1, y1 - 20), label, fill=(255, 255, 255), font=font)

        return annotated

    def _build_claude_context(self, detections: list, patterns: list, constitution: str) -> str:
        """Build a structured context string to pass to Claude Vision for synthesis."""
        if not detections:
            return ""

        lines = ["=== YOLOv8 TONGUE FEATURE DETECTIONS (objective) ==="]
        lines.append(
            "Model: YOLOv8n trained on the shezhenv3 COCO tongue dataset. "
            "Overall test-set mAP50 = 0.325. Per-class accuracy varies widely — "
            "each detection below is labelled with its validated reliability."
        )
        lines.append(f"Detected {len(detections)} tongue feature(s):\n")

        for det in detections:
            rel = det.get("reliability", DEFAULT_RELIABILITY)
            label = det.get("reliability_label", "")
            lines.append(
                f"  [{det['confidence']:.0f}% conf | class reliability {rel:.2f} — {label}] "
                f"{det['zh']} ({det['class_name']}) — {det['meaning']} | "
                f"TCM: {det['tcm_significance']}"
            )

        lines.append("\nSynthesised TCM Patterns (rule-based from detections):")
        for pat in patterns[:3]:
            lines.append(
                f"  [{pat['confidence']:.0f}% | {pat.get('evidence_strength','?')} evidence] "
                f"{pat['pattern']}  (triggered by: {', '.join(pat.get('triggers', []))})"
            )

        lines.append(f"\nRule-based constitution estimate: {constitution}")
        lines.append("\n=== END YOLO DETECTIONS ===")
        lines.append(
            "HOW TO USE THIS: Detections marked 'validated' (reliability >= 0.6) are "
            "trustworthy objective evidence — the white-coating and yellow-coating "
            "classes in particular are well validated. Detections marked 'low "
            "confidence class' come from classes that performed poorly in validation; "
            "treat those as weak hints only and do NOT build a primary diagnosis on "
            "them alone. If the detector reports nothing, that is meaningful evidence "
            "of a normal tongue, not a reason to invent findings."
        )

        return "\n".join(lines)


# ── Singleton (auto-loaded once per Streamlit session) ────────────────────────
_detector_instance = None

def get_detector() -> TongueDetector:
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = TongueDetector()
    return _detector_instance
