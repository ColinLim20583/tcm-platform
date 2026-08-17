"""
train_yolo.py — Train YOLOv8 on Shezhen (舌诊) Tongue Diagnosis Dataset
------------------------------------------------------------------------
Run AFTER setup_dataset.py:
    python train_yolo.py

Options:
    python train_yolo.py --model yolov8n   # nano (fastest, CPU-friendly)
    python train_yolo.py --model yolov8s   # small (better accuracy, needs GPU)
    python train_yolo.py --model yolov8m   # medium (best accuracy, GPU required)
    python train_yolo.py --epochs 100      # default 80
    python train_yolo.py --resume          # resume interrupted training

Output:
    models/tongue_yolo_best.pt   ← use this for inference
    models/tongue_yolo_last.pt   ← last checkpoint
    runs/shezhen_train/          ← full training artifacts
"""

import argparse
import shutil
import random
from pathlib import Path


def fix_dataset_paths(base: Path) -> Path:
    """
    Regenerate list files and dataset.yaml with correct local paths.
    Needed because the files were originally created on a different machine.
    Returns the path to the validated/fixed dataset.yaml.
    """
    yolo_dir = base / "shezhen_data" / "yolo"
    yaml_path = yolo_dir / "dataset.yaml"

    # Find the actual shezhen source data root (handles any nesting)
    coco_root = None
    for p in (base / "shezhen_data").rglob("train"):
        if (p / "annotations" / "train.json").exists():
            coco_root = p.parent
            break

    if coco_root is None:
        print("⚠ shezhen_data not found — run setup_dataset.py first, or ensure zip was extracted")
        return yaml_path

    print(f"  Dataset root: {coco_root}")

    train_img_dir = coco_root / "train" / "images"
    train_lbl_dir = coco_root / "train" / "labels"
    test_img_dir  = coco_root / "test"  / "images"
    test_lbl_dir  = coco_root / "test"  / "labels"

    img_exts = {".jpg", ".jpeg", ".png"}

    # ── Convert COCO→YOLO labels if not yet done ──────────────────────────────
    if not train_lbl_dir.exists() or len(list(train_lbl_dir.glob("*.txt"))) < 10:
        print("  Converting COCO→YOLO labels for train split...")
        import json
        from collections import defaultdict
        train_lbl_dir.mkdir(exist_ok=True)
        with open(coco_root / "train" / "annotations" / "train.json") as f:
            coco = json.load(f)
        img_info = {img["id"]: img for img in coco["images"]}
        cat_to_idx = {cat["id"]: i for i, cat in enumerate(coco["categories"])}
        ann_by_img = defaultdict(list)
        for ann in coco["annotations"]:
            ann_by_img[ann["image_id"]].append(ann)
        existing_stems = {p.stem for p in train_img_dir.iterdir() if p.suffix.lower() in img_exts}
        written = 0
        for img_id, anns in ann_by_img.items():
            info = img_info.get(img_id)
            if not info: continue
            stem = Path(info["file_name"]).stem
            if stem not in existing_stems: continue
            W, H = info["width"], info["height"]
            lines = []
            for ann in anns:
                cls_idx = cat_to_idx.get(ann["category_id"])
                if cls_idx is None: continue
                x, y, w, h = ann["bbox"]
                cx=(x+w/2)/W; cy=(y+h/2)/H; nw=w/W; nh=h/H
                lines.append(f"{cls_idx} {cx:.6f} {cy:.6f} {nw:.6f} {nh:.6f}")
            if lines:
                (train_lbl_dir / f"{stem}.txt").write_text("\n".join(lines))
                written += 1
        print(f"  ✓ Wrote {written} YOLO label files")

    # ── Build image lists ──────────────────────────────────────────────────────
    labelled_stems = {p.stem for p in train_lbl_dir.glob("*.txt")}
    all_train = [p for p in train_img_dir.iterdir()
                 if p.suffix.lower() in img_exts and p.stem in labelled_stems]

    random.seed(42); random.shuffle(all_train)
    n_val = max(1, int(len(all_train) * 0.15))
    val_imgs   = all_train[:n_val]
    train_imgs = all_train[n_val:]
    test_imgs  = [p for p in test_img_dir.iterdir() if p.suffix.lower() in img_exts]

    yolo_dir.mkdir(parents=True, exist_ok=True)
    (yolo_dir / "train_list.txt").write_text("\n".join(str(p) for p in train_imgs))
    (yolo_dir / "val_list.txt"  ).write_text("\n".join(str(p) for p in val_imgs))
    (yolo_dir / "test_list.txt" ).write_text("\n".join(str(p) for p in test_imgs))

    CLASS_NAMES = [
        "jiankangshe","botaishe","hongshe","zishe","pangdashe","shoushe",
        "hongdianshe","liewenshe","chihenshe","baitaishe","huangtaishe","heitaishe",
        "huataishe","shenquao","shenqutu","gandanao","gandantu","piweiao",
        "piweitu","xinfeiao","xinfeitu"
    ]
    total = len(train_imgs) + len(val_imgs) + len(test_imgs)
    yaml_path.write_text(
        f"# Shezhen Tongue Dataset — YOLOv8\n"
        f"# {total} labelled images | 21 classes\n\n"
        f"train: {yolo_dir / 'train_list.txt'}\n"
        f"val:   {yolo_dir / 'val_list.txt'}\n"
        f"test:  {yolo_dir / 'test_list.txt'}\n\n"
        f"nc: {len(CLASS_NAMES)}\n"
        f"names: {CLASS_NAMES}\n"
    )
    print(f"  ✓ dataset.yaml: {len(train_imgs)} train | {len(val_imgs)} val | {len(test_imgs)} test")
    return yaml_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model",  default="yolov8n", help="YOLOv8 model size: yolov8n/s/m/l/x")
    parser.add_argument("--epochs", type=int, default=80)
    parser.add_argument("--batch",  type=int, default=16, help="Batch size (reduce to 8 if OOM)")
    parser.add_argument("--imgsz",  type=int, default=640)
    parser.add_argument("--device", default="", help="'' for auto, '0' for GPU 0, 'cpu' for CPU")
    parser.add_argument("--resume", action="store_true", help="Resume from last.pt")
    parser.add_argument("--data",   default="shezhen_data/yolo/dataset.yaml")
    args = parser.parse_args()

    try:
        from ultralytics import YOLO
    except ImportError:
        print("❌ ultralytics not installed. Run:")
        print("   pip install ultralytics")
        return

    base = Path(__file__).parent
    models_dir = base / "models"
    models_dir.mkdir(exist_ok=True)

    # ── Auto-fix dataset paths (sandbox → local machine) ─────────────────────
    print("\n▶ Checking / rebuilding dataset paths for this machine...")
    yaml_path = fix_dataset_paths(base)

    if not yaml_path.exists():
        print(f"❌ dataset.yaml not found at {yaml_path}")
        print("   Ensure shezhen_datasets1.zip was extracted to tcm_platform/shezhen_data/")
        return

    print("=" * 60)
    print("  ChemiGran Tongue Diagnosis — YOLOv8 Training")
    print("=" * 60)
    print(f"  Model   : {args.model}")
    print(f"  Epochs  : {args.epochs}")
    print(f"  Batch   : {args.batch}")
    print(f"  ImgSize : {args.imgsz}")
    print(f"  Device  : {'auto' if not args.device else args.device}")
    print(f"  Dataset : {yaml_path}")
    print("=" * 60)

    # Load model
    if args.resume:
        last_pt = base / "runs" / "shezhen_train" / "weights" / "last.pt"
        if last_pt.exists():
            print(f"\n▶ Resuming from {last_pt}")
            model = YOLO(str(last_pt))
        else:
            print(f"❌ No last.pt found at {last_pt}")
            return
    else:
        model_file = f"{args.model}.pt"
        print(f"\n▶ Loading {model_file} (downloads if not cached)...")
        model = YOLO(model_file)

    # Training configuration
    print(f"\n▶ Starting training...\n")
    results = model.train(
        data=str(yaml_path),
        epochs=args.epochs,
        batch=args.batch,
        imgsz=args.imgsz,
        device=args.device if args.device else None,
        project=str(base / "runs"),
        name="shezhen_train",
        exist_ok=True,

        # Augmentation (good for tongue images)
        hsv_h=0.015,      # Hue shift — handles lighting variation
        hsv_s=0.5,        # Saturation — tongue colour variation
        hsv_v=0.4,        # Value/brightness
        degrees=10,       # Slight rotation
        translate=0.1,
        scale=0.3,
        flipud=0.1,
        fliplr=0.3,
        mosaic=0.8,
        mixup=0.1,

        # Optimizer
        optimizer="AdamW",
        lr0=0.001,
        lrf=0.01,
        weight_decay=0.0005,
        warmup_epochs=3,

        # Patience & saving
        patience=20,
        save=True,
        save_period=10,
        val=True,
        plots=True,
        verbose=True,
    )

    # ── Copy best weights to models/ ─────────────────────────────────────────
    best_src = base / "runs" / "shezhen_train" / "weights" / "tongue_yolo_best.pt"
    last_src = base / "runs" / "shezhen_train" / "weights" / "last.pt"

    if best_src.exists():
        best_dst = models_dir / "tongue_yolo_best.pt"
        shutil.copy2(best_src, best_dst)
        print(f"\n✅ Best model saved: {best_dst}")

    if last_src.exists():
        last_dst = models_dir / "tongue_yolo_last.pt"
        shutil.copy2(last_src, last_dst)
        print(f"   Last model saved: {last_dst}")

    # ── Quick validation on test set ─────────────────────────────────────────
    print("\n▶ Running validation on test set...")
    try:
        from ultralytics import YOLO as _YOLO
        best_model = _YOLO(str(best_dst))
        metrics = best_model.val(
            data=str(yaml_path),
            split="test",
            imgsz=args.imgsz,
        )
        print(f"\n📊 Test Set Results:")
        print(f"   mAP50     : {metrics.box.map50:.3f}")
        print(f"   mAP50-95  : {metrics.box.map:.3f}")
        print(f"   Precision : {metrics.box.mp:.3f}")
        print(f"   Recall    : {metrics.box.mr:.3f}")
    except Exception as e:
        print(f"   Validation skipped: {e}")

    print("\n" + "=" * 60)
    print("  Training Complete!")
    print(f"  Best model: models/tongue_yolo_best.pt")
    print(f"  Run the Streamlit app — it will auto-detect the model.")
    print("=" * 60)


if __name__ == "__main__":
    main()
