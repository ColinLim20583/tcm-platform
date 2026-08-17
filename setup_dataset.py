"""
setup_dataset.py — Prepare Shezhen (舌诊) Dataset for YOLOv8 Training
----------------------------------------------------------------------
Run ONCE before training:
    python setup_dataset.py --zip path/to/shezhen_datasets1.zip

What it does:
  1. Extracts the zip into tcm_platform/shezhen_data/
  2. Converts COCO bbox annotations → YOLO .txt label files
  3. Writes shezhen_data/dataset.yaml for ultralytics
"""

import os
import json
import shutil
import zipfile
import argparse
from pathlib import Path

# ── 21 class names (order matches category_id 0-20) ──────────────────────────
CLASS_NAMES = [
    "jiankangshe",   # 0  健康舌  Healthy tongue
    "botaishe",      # 1  薄苔舌  Thin coating
    "hongshe",       # 2  红舌    Red tongue — Heat
    "zishe",         # 3  紫舌    Purple tongue — Blood stasis
    "pangdashe",     # 4  胖大舌  Swollen tongue — Spleen Qi def / Damp
    "shoushe",       # 5  瘦舌    Thin tongue — Blood/Yin def
    "hongdianshe",   # 6  红点舌  Red dots — Heat toxin
    "liewenshe",     # 7  裂纹舌  Cracked — Yin def
    "chihenshe",     # 8  齿痕舌  Teeth-marked — Spleen Qi def
    "baitaishe",     # 9  白苔舌  White coating — Cold/Normal
    "huangtaishe",   # 10 黄苔舌  Yellow coating — Heat/Damp-Heat
    "heitaishe",     # 11 黑苔舌  Black coating — Extreme Cold/Heat
    "huataishe",     # 12 花苔舌  Peeled coating — Yin def
    "shenquao",      # 13 肾区凹  Kidney zone concave — Kidney def
    "shenqutu",      # 14 肾区凸  Kidney zone convex
    "gandanao",      # 15 肝胆区凹 Liver/GB zone concave — Liver def
    "gandantu",      # 16 肝胆区凸 Liver/GB zone convex
    "piweiao",       # 17 脾胃区凹 Spleen/ST zone concave — Spleen def
    "piweitu",       # 18 脾胃区凸 Spleen/ST zone convex
    "xinfeiao",      # 19 心肺区凹 Heart/Lung zone concave — Heart/Lung def
    "xinfeitu",      # 20 心肺区凸 Heart/Lung zone convex
]

# ── TCM meaning map (used by tongue_detector.py) ─────────────────────────────
TCM_MEANING = {
    "jiankangshe":  {"zh": "健康舌", "meaning": "Healthy tongue", "tcm": "Balanced constitution"},
    "botaishe":     {"zh": "薄苔舌", "meaning": "Thin coating", "tcm": "Normal or mild exterior pattern"},
    "hongshe":      {"zh": "红舌",   "meaning": "Red tongue body", "tcm": "Heat pattern; Yin deficiency"},
    "zishe":        {"zh": "紫舌",   "meaning": "Purple tongue", "tcm": "Blood stasis; Cold obstructing vessels"},
    "pangdashe":    {"zh": "胖大舌", "meaning": "Swollen/enlarged tongue", "tcm": "Spleen Qi deficiency; Damp; Yang deficiency"},
    "shoushe":      {"zh": "瘦舌",   "meaning": "Thin/lean tongue", "tcm": "Blood deficiency; Yin deficiency"},
    "hongdianshe":  {"zh": "红点舌", "meaning": "Red dots on tongue", "tcm": "Heat toxin; Blood Heat"},
    "liewenshe":    {"zh": "裂纹舌", "meaning": "Cracked tongue", "tcm": "Yin deficiency; Heat consuming fluids; chronic Blood deficiency"},
    "chihenshe":    {"zh": "齿痕舌", "meaning": "Teeth-marked edges", "tcm": "Spleen Qi deficiency with Damp retention"},
    "baitaishe":    {"zh": "白苔舌", "meaning": "White coating", "tcm": "Cold pattern; Normal (thin white); Cold-Damp (thick white)"},
    "huangtaishe":  {"zh": "黄苔舌", "meaning": "Yellow coating", "tcm": "Heat; Damp-Heat; interior Heat accumulation"},
    "heitaishe":    {"zh": "黑苔舌", "meaning": "Black/grey coating", "tcm": "Extreme Cold (moist) or extreme Heat (dry)"},
    "huataishe":    {"zh": "花苔舌", "meaning": "Peeled/geographic coating", "tcm": "Stomach Yin deficiency; chronic illness"},
    "shenquao":     {"zh": "肾区凹", "meaning": "Kidney zone concave", "tcm": "Kidney deficiency (Yin or Yang)"},
    "shenqutu":     {"zh": "肾区凸", "meaning": "Kidney zone convex", "tcm": "Kidney excess pattern"},
    "gandanao":     {"zh": "肝胆区凹","meaning": "Liver/GB zone concave", "tcm": "Liver Blood or Yin deficiency"},
    "gandantu":     {"zh": "肝胆区凸","meaning": "Liver/GB zone convex", "tcm": "Liver Qi stagnation; Liver Fire"},
    "piweiao":      {"zh": "脾胃区凹","meaning": "Spleen/Stomach zone concave", "tcm": "Spleen Qi or Yang deficiency"},
    "piweitu":      {"zh": "脾胃区凸","meaning": "Spleen/Stomach zone convex", "tcm": "Food stagnation; Stomach excess"},
    "xinfeiao":     {"zh": "心肺区凹","meaning": "Heart/Lung zone concave", "tcm": "Heart or Lung Qi/Blood deficiency"},
    "xinfeitu":     {"zh": "心肺区凸","meaning": "Heart/Lung zone convex", "tcm": "Heart Fire; Lung Heat or Phlegm"},
}


def coco_to_yolo(json_path: Path, images_dir: Path, labels_dir: Path):
    """Convert a COCO annotation JSON to YOLO .txt label files."""
    labels_dir.mkdir(parents=True, exist_ok=True)

    with open(json_path) as f:
        data = json.load(f)

    # Build image_id → {width, height, filename} map
    img_info = {img["id"]: img for img in data["images"]}

    # Group annotations by image_id
    from collections import defaultdict
    ann_by_img = defaultdict(list)
    for ann in data["annotations"]:
        ann_by_img[ann["image_id"]].append(ann)

    converted = 0
    for img_id, anns in ann_by_img.items():
        info = img_info.get(img_id)
        if not info:
            continue
        W, H = info["width"], info["height"]
        fname = Path(info["file_name"]).stem  # e.g. "10001"
        label_file = labels_dir / f"{fname}.txt"

        lines = []
        for ann in anns:
            cat_id = ann["category_id"]
            if cat_id >= len(CLASS_NAMES):
                continue
            x, y, w, h = ann["bbox"]  # COCO: top-left x,y + w,h
            # Convert to YOLO normalised cx, cy, w, h
            cx = (x + w / 2) / W
            cy = (y + h / 2) / H
            nw = w / W
            nh = h / H
            lines.append(f"{cat_id} {cx:.6f} {cy:.6f} {nw:.6f} {nh:.6f}")

        with open(label_file, "w") as lf:
            lf.write("\n".join(lines))
        converted += 1

    print(f"  ✓ Converted {converted} images → {labels_dir}")
    return converted


def main():
    parser = argparse.ArgumentParser(description="Setup shezhen dataset for YOLOv8")
    parser.add_argument("--zip", required=True, help="Path to shezhen_datasets1.zip")
    parser.add_argument("--out", default="shezhen_data", help="Output folder name (inside tcm_platform)")
    args = parser.parse_args()

    base = Path(__file__).parent
    out_dir = base / args.out
    zip_path = Path(args.zip)

    if not zip_path.exists():
        print(f"❌ Zip not found: {zip_path}")
        return

    # ── Step 1: Extract ───────────────────────────────────────────────────────
    print(f"\n1️⃣  Extracting {zip_path.name} → {out_dir} ...")
    out_dir.mkdir(exist_ok=True)

    with zipfile.ZipFile(zip_path) as zf:
        members = zf.namelist()
        total = len(members)
        for i, member in enumerate(members):
            zf.extract(member, out_dir)
            if i % 1000 == 0:
                print(f"   {i}/{total} files extracted...", end="\r")
    print(f"\n   ✓ Extracted {total} files")

    # Locate the actual dataset root (handles nested folder in zip)
    coco_root = None
    for p in out_dir.rglob("train"):
        if (p / "annotations" / "train.json").exists():
            coco_root = p.parent
            break

    if not coco_root:
        print("❌ Could not find dataset root with train/val/test structure")
        return

    print(f"   Dataset root: {coco_root}")

    # ── Step 2: Convert COCO → YOLO ───────────────────────────────────────────
    print("\n2️⃣  Converting COCO annotations → YOLO format ...")
    yolo_dir = out_dir / "yolo"
    splits = {
        "train": coco_root / "train",
        "val":   coco_root / "val",
        "test":  coco_root / "test",
    }

    total_imgs = 0
    for split, split_path in splits.items():
        json_file = split_path / "annotations" / f"{split}.json"
        images_src = split_path / "images"
        yolo_split = yolo_dir / split

        if not json_file.exists():
            print(f"   ⚠ Skipping {split} — no annotation file found")
            continue

        # Copy images
        img_dst = yolo_split / "images"
        img_dst.mkdir(parents=True, exist_ok=True)
        imgs = list(images_src.glob("*.jpg")) + list(images_src.glob("*.png"))
        for img in imgs:
            dst = img_dst / img.name
            if not dst.exists():
                shutil.copy2(img, dst)
        print(f"   Copied {len(imgs)} {split} images")
        total_imgs += len(imgs)

        # Convert labels
        lbl_dst = yolo_split / "labels"
        coco_to_yolo(json_file, img_dst, lbl_dst)

    # ── Step 3: Write dataset.yaml ────────────────────────────────────────────
    print("\n3️⃣  Writing dataset.yaml ...")
    yaml_path = yolo_dir / "dataset.yaml"
    yaml_content = f"""# Shezhen (舌诊) Tongue Diagnosis Dataset — YOLOv8
# 21 TCM tongue feature classes | {total_imgs} images

path: {yolo_dir.resolve()}
train: train/images
val:   val/images
test:  test/images

nc: {len(CLASS_NAMES)}
names: {CLASS_NAMES}
"""
    yaml_path.write_text(yaml_content)
    print(f"   ✓ Saved: {yaml_path}")

    # Save TCM meaning map for tongue_detector.py
    import json as _json
    meaning_path = yolo_dir / "tcm_meaning.json"
    meaning_path.write_text(_json.dumps(TCM_MEANING, ensure_ascii=False, indent=2))

    print(f"\n✅ Dataset ready!")
    print(f"   Images: {total_imgs}")
    print(f"   Classes: {len(CLASS_NAMES)}")
    print(f"   YAML: {yaml_path}")
    print(f"\n▶  Next step: python train_yolo.py")


if __name__ == "__main__":
    main()
