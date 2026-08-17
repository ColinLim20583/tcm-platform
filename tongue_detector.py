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

# ── Pattern synthesis rules ───────────────────────────────────────────────────
# Maps combinations of detected features to consolidated TCM patterns
PATTERN_RULES = [
    # (required_features_any_of, pattern, confidence_bonus)
    ({"pangdashe", "chihenshe"},    "Spleen Qi Deficiency with Phlegm-Damp", 15),
    ({"liewenshe", "shoushe"},      "Yin Deficiency with Empty Heat",         15),
    ({"hongshe", "huangtaishe"},    "Excess Heat / Liver Fire",               15),
    ({"zishe"},                     "Blood Stasis",                           10),
    ({"hongshe", "liewenshe"},      "Yin Deficiency with Heat",               12),
    ({"pangdashe", "baitaishe"},    "Spleen Yang Deficiency with Cold-Damp",  12),
    ({"huangtaishe", "chihenshe"},  "Damp-Heat accumulation",                 12),
    ({"huataishe"},                 "Stomach Yin Deficiency",                 10),
    ({"heitaishe"},                 "Extreme pattern (Cold or Heat)",         10),
    ({"hongdianshe"},               "Heat Toxin / Blood Heat",                10),
    ({"shenquao", "shoushe"},       "Kidney Yin Deficiency",                  12),
    ({"shenquao", "pangdashe"},     "Kidney Yang Deficiency",                 12),
    ({"gandantu", "hongshe"},       "Liver Fire Rising",                      12),
    ({"xinfeiao"},                  "Heart-Lung Qi Deficiency",               10),
    ({"piweiao"},                   "Spleen-Stomach Deficiency",              10),
]

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


class TongueDetector:
    def __init__(self, model_path: str = None):
        """
        Load the trained YOLOv8 model.
        Falls back to None if model not yet trained — vision_engine uses
        Claude-only analysis in that case.
        """
        self.model = None
        self.model_path = None

        if model_path is None:
            # Auto-discover model
            base = Path(__file__).parent / "models"
            candidates = ["tongue_yolo_best.pt", "tongue_yolo_last.pt"]
            for c in candidates:
                p = base / c
                if p.exists():
                    model_path = str(p)
                    break

        if model_path and Path(model_path).exists():
            try:
                from ultralytics import YOLO
                self.model = YOLO(model_path)
                self.model_path = model_path
                print(f"✓ TongueDetector loaded: {model_path}")
            except ImportError:
                print("⚠ ultralytics not installed — YOLO detection disabled")
            except Exception as e:
                print(f"⚠ Could not load model: {e}")
        else:
            print("ℹ TongueDetector: no trained model found — using Claude Vision only")

    @property
    def is_ready(self) -> bool:
        return self.model is not None

    def detect(self, image_bytes: bytes, conf_threshold: float = 0.25) -> dict:
        """
        Run YOLOv8 detection on image bytes.
        Returns structured detection results ready for Claude synthesis.
        """
        if not self.is_ready:
            return {"detections": [], "yolo_available": False}

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
        """Synthesise TCM patterns from detected feature combinations."""
        detected_set = {d["class_name"] for d in detections}
        patterns = []

        for required, pattern, bonus in PATTERN_RULES:
            if required & detected_set:  # any overlap
                # Base confidence = avg confidence of matching features
                matching = [d["confidence"] for d in detections if d["class_name"] in required]
                base_conf = sum(matching) / len(matching) if matching else 50
                total_conf = min(95, base_conf + bonus)
                patterns.append({"pattern": pattern, "confidence": round(total_conf, 1),
                                  "triggers": list(required & detected_set)})

        # Fallback: individual feature patterns
        if not patterns:
            for det in detections[:3]:
                meaning = TCM_MEANING.get(det["class_name"], {})
                tcm = meaning.get("tcm", "")
                if tcm:
                    patterns.append({"pattern": tcm.split(";")[0].strip(),
                                     "confidence": det["confidence"],
                                     "triggers": [det["class_name"]]})

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

        lines = ["=== YOLOv8 TONGUE FEATURE DETECTIONS ==="]
        lines.append(f"Model: Trained on 12,889 tongue images (shezhenv3 COCO dataset)")
        lines.append(f"Detected {len(detections)} tongue feature(s):\n")

        for det in detections:
            lines.append(
                f"  [{det['confidence']:.0f}%] {det['zh']} ({det['class_name']}) — "
                f"{det['meaning']} | TCM: {det['tcm_significance']}"
            )

        lines.append(f"\nSynthesised TCM Patterns:")
        for pat in patterns[:3]:
            lines.append(f"  [{pat['confidence']:.0f}%] {pat['pattern']}")

        lines.append(f"\nConstitution: {constitution}")
        lines.append("\n=== END YOLO DETECTIONS ===")
        lines.append("Please synthesise the above objective detections with your visual assessment to produce the final TCM diagnosis.")

        return "\n".join(lines)


# ── Singleton (auto-loaded once per Streamlit session) ────────────────────────
_detector_instance = None

def get_detector() -> TongueDetector:
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = TongueDetector()
    return _detector_instance
