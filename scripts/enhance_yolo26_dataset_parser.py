import os
from pathlib import Path

FORGE_DIR = Path(r"C:\Users\hades\Documents\HydraForge")
ROUTE_FILE = FORGE_DIR / "api" / "routes" / "datasets.py"

content = """import os
import json
import yaml
from pathlib import Path
from fastapi import APIRouter
from pydantic import BaseModel
from api.services.db_service import get_connection

router = APIRouter()
DATASETS_DIR = Path("storage/datasets")
DATASETS_DIR.mkdir(parents=True, exist_ok=True)

class ValidateFolderRequest(BaseModel):
    folder_path: str

def parse_yaml_metadata(p: Path):
    yaml_files = list(p.glob("*.yaml")) + list(p.glob("*.yml"))
    names_map = {}
    if yaml_files:
        try:
            data = yaml.safe_load(yaml_files[0].read_text(encoding="utf-8"))
            if isinstance(data, dict) and "names" in data:
                if isinstance(data["names"], dict):
                    names_map = {str(k): str(v) for k, v in data["names"].items()}
                elif isinstance(data["names"], list):
                    names_map = {str(i): str(v) for i, v in enumerate(data["names"])}
        except Exception:
            pass
    return names_map

@router.get("")
def list_datasets():
    results = []
    if DATASETS_DIR.exists():
        for d in DATASETS_DIR.iterdir():
            if d.is_dir():
                img_count = len(list(d.rglob("*.jpg"))) + len(list(d.rglob("*.png")))
                lbl_count = len(list(d.rglob("*.txt")))
                names_map = parse_yaml_metadata(d)
                results.append({
                    "id": d.name,
                    "name": d.name.replace("_", " ").title(),
                    "path": str(d.absolute()),
                    "images": img_count,
                    "labels": lbl_count,
                    "classes": list(names_map.values()) if names_map else []
                })
    return results

@router.post("/validate")
def validate_dataset_path(req: ValidateFolderRequest):
    p = Path(req.folder_path)
    if not p.exists() or not p.is_dir():
        return {"valid": False, "error": "Diretório não encontrado no sistema.", "metrics": None}
    
    img_exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    images = [f for f in p.rglob("*") if f.suffix.lower() in img_exts]
    labels = [f for f in p.rglob("*.txt") if not f.name.startswith("classes") and not f.name.startswith("README")]
    
    img_stems = {f.stem for f in images}
    lbl_stems = {f.stem for f in labels}
    missing_labels = len(img_stems - lbl_stems)
    orphan_labels = len(lbl_stems - img_stems)
    
    names_map = parse_yaml_metadata(p)
    class_counts = {}
    invalid_bboxes = 0

    for lbl in labels:
        try:
            for line in lbl.read_text(encoding="utf-8", errors="ignore").splitlines():
                parts = line.strip().split()
                if len(parts) >= 5:
                    cls_id = parts[0]
                    class_counts[cls_id] = class_counts.get(cls_id, 0) + 1
                    # Valida normalização 0.0 - 1.0 (YOLO26 / YOLO standard)
                    try:
                        coords = [float(x) for x in parts[1:5]]
                        if any(c < 0.0 or c > 1.05 for c in coords):
                            invalid_bboxes += 1
                    except ValueError:
                        invalid_bboxes += 1
        except Exception:
            pass

    class_dist = [
        {"class_id": names_map.get(k, f"Class_{k}"), "count": v}
        for k, v in sorted(class_counts.items())
    ]
    
    # Contagem de splits se existirem (images/train, images/val, images/test)
    train_imgs = len([img for img in images if "train" in str(img.parent).lower()])
    val_imgs = len([img for img in images if "val" in str(img.parent).lower()])
    if train_imgs == 0 and val_imgs == 0:
        train_imgs = int(len(images) * 0.8)
        val_imgs = int(len(images) * 0.2)

    with get_connection() as conn:
        conn.execute(
            '''INSERT INTO dataset_validations 
               (folder_path, total_images, total_labels, missing_labels, orphan_labels, corrupt_images, format, class_distribution_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
            (str(p.absolute()), len(images), len(labels), missing_labels, orphan_labels, invalid_bboxes, "YOLO26 / YOLO Standard (TXT + data.yaml)", json.dumps(class_dist))
        )

    return {
        "valid": True,
        "path": str(p.absolute()),
        "metrics": {
            "total_images": len(images),
            "total_labels": len(labels),
            "missing_labels": missing_labels,
            "orphan_labels": orphan_labels,
            "corrupt_images": invalid_bboxes,
            "format": "YOLO26 Standard (TXT + data.yaml)",
            "split_train": train_imgs,
            "split_val": val_imgs,
            "class_distribution": class_dist
        }
    }
"""

ROUTE_FILE.write_text(content.strip() + "\n", encoding="utf-8")
print("datasets.py updated with data.yaml parser & YOLO26 bbox validator!")
