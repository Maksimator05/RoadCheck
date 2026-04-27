from __future__ import annotations

import argparse
import random
import shutil
import subprocess
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from pathlib import Path

import torch
import yaml
from ultralytics import YOLO

BASE_DIR = Path(__file__).resolve().parent
BACKEND_DIR = BASE_DIR.parent
DOWNLOADS_DIR = BASE_DIR / "downloads"
RAW_DIR = BASE_DIR / "rdd2022_raw"
DATASET_DIR = BASE_DIR / "dataset_yolo"
RUNS_DIR = BASE_DIR / "runs"
WEIGHTS_DST = BACKEND_DIR / "app" / "ml" / "weights"

CLASS_MAP = {
    "D00": 0,
    "D10": 1,
    "D20": 2,
    "D40": 3,
}
CLASS_NAMES = ["D00", "D10", "D20", "D40"]

COUNTRY_URLS = {
    "Czech": "https://bigdatacup.s3.ap-northeast-1.amazonaws.com/2022/CRDDC2022/RDD2022/Country_Specific_Data_CRDDC2022/RDD2022_Czech.zip",
    "India": "https://bigdatacup.s3.ap-northeast-1.amazonaws.com/2022/CRDDC2022/RDD2022/Country_Specific_Data_CRDDC2022/RDD2022_India.zip",
    "Japan": "https://bigdatacup.s3.ap-northeast-1.amazonaws.com/2022/CRDDC2022/RDD2022/Country_Specific_Data_CRDDC2022/RDD2022_Japan.zip",
    "Norway": "https://bigdatacup.s3.ap-northeast-1.amazonaws.com/2022/CRDDC2022/RDD2022/Country_Specific_Data_CRDDC2022/RDD2022_Norway.zip",
    "United_States": "https://bigdatacup.s3.ap-northeast-1.amazonaws.com/2022/CRDDC2022/RDD2022/Country_Specific_Data_CRDDC2022/RDD2022_United_States.zip",
    "China_MotorBike": "https://bigdatacup.s3.ap-northeast-1.amazonaws.com/2022/CRDDC2022/RDD2022/Country_Specific_Data_CRDDC2022/RDD2022_China_MotorBike.zip",
    "China_Drone": "https://bigdatacup.s3.ap-northeast-1.amazonaws.com/2022/CRDDC2022/RDD2022/Country_Specific_Data_CRDDC2022/RDD2022_China_Drone.zip",
}


@dataclass(frozen=True)
class Sample:
    image_path: Path
    xml_path: Path


def resolve_device() -> str:
    if torch.cuda.is_available():
        return "0"
    if getattr(torch.backends, "mps", None) is not None and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def download_country_zip(country: str) -> Path:
    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
    url = COUNTRY_URLS[country]
    zip_path = DOWNLOADS_DIR / f"RDD2022_{country}.zip"
    def _download() -> None:
        print(f"Downloading {country} dataset from official source with curl...")
        subprocess.run(
            ["curl", "-L", "-k", "-C", "-", "-o", str(zip_path), url],
            check=True,
        )

    if zip_path.exists():
        try:
            with zipfile.ZipFile(zip_path) as archive:
                archive.testzip()
            print(f"Archive already present: {zip_path}")
            return zip_path
        except zipfile.BadZipFile:
            print(f"Found a partial or corrupted archive, resuming download: {zip_path}")
            _download()
    else:
        _download()

    print(f"Downloaded: {zip_path}")
    return zip_path


def ensure_country_extracted(country: str, zip_path: Path) -> Path:
    country_dir = RAW_DIR / country
    if country_dir.exists():
        print(f"Raw dataset already extracted: {country_dir}")
        return country_dir

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Extracting archive to: {RAW_DIR}")
    with zipfile.ZipFile(zip_path) as archive:
        archive.extractall(RAW_DIR)

    if not country_dir.exists():
        candidates = sorted(p for p in RAW_DIR.rglob(country) if p.is_dir())
        if candidates:
            return candidates[0]
        raise FileNotFoundError(f"Extracted archive, but country directory '{country}' was not found.")

    return country_dir


def parse_voc_xml(xml_path: Path) -> list[tuple[int, float, float, float, float]]:
    tree = ET.parse(xml_path)
    root = tree.getroot()
    size = root.find("size")
    if size is None:
        return []

    width = int(size.findtext("width", default="0"))
    height = int(size.findtext("height", default="0"))
    if width <= 0 or height <= 0:
        return []

    labels: list[tuple[int, float, float, float, float]] = []
    for obj in root.findall("object"):
        name = (obj.findtext("name", default="")).strip()
        if name not in CLASS_MAP:
            continue

        bbox = obj.find("bndbox")
        if bbox is None:
            continue

        xmin = max(0, int(float(bbox.findtext("xmin", default="0"))))
        ymin = max(0, int(float(bbox.findtext("ymin", default="0"))))
        xmax = min(width, int(float(bbox.findtext("xmax", default="0"))))
        ymax = min(height, int(float(bbox.findtext("ymax", default="0"))))
        if xmax <= xmin or ymax <= ymin:
            continue

        cx = ((xmin + xmax) / 2) / width
        cy = ((ymin + ymax) / 2) / height
        bw = (xmax - xmin) / width
        bh = (ymax - ymin) / height
        labels.append((CLASS_MAP[name], cx, cy, bw, bh))

    return labels


def collect_samples(country_dir: Path, max_samples: int | None = None) -> list[Sample]:
    images_dir = country_dir / "train" / "images"
    xmls_dir = country_dir / "train" / "annotations" / "xmls"
    if not images_dir.exists() or not xmls_dir.exists():
        raise FileNotFoundError(f"Expected training folders were not found under {country_dir}")

    samples: list[Sample] = []
    for image_path in sorted(images_dir.glob("*.jpg")):
        xml_path = xmls_dir / f"{image_path.stem}.xml"
        if xml_path.exists():
            samples.append(Sample(image_path=image_path, xml_path=xml_path))

    if not samples:
        raise RuntimeError(f"No paired training samples were found in {country_dir}")
    if max_samples is not None:
        samples = samples[:max_samples]
    return samples


def write_yolo_labels(labels_path: Path, labels: list[tuple[int, float, float, float, float]]) -> None:
    labels_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"{class_id} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}"
        for class_id, cx, cy, bw, bh in labels
    ]
    labels_path.write_text("\n".join(lines), encoding="utf-8")


def build_yolo_dataset(samples: list[Sample], val_ratio: float, seed: int) -> Path:
    if DATASET_DIR.exists():
        shutil.rmtree(DATASET_DIR)

    random.Random(seed).shuffle(samples)
    val_count = max(1, int(len(samples) * val_ratio))
    split_map = {
        "val": samples[:val_count],
        "train": samples[val_count:],
    }

    for split_name, split_samples in split_map.items():
        for sample in split_samples:
            labels = parse_voc_xml(sample.xml_path)
            target_image = DATASET_DIR / "images" / split_name / sample.image_path.name
            target_label = DATASET_DIR / "labels" / split_name / f"{sample.image_path.stem}.txt"
            target_image.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(sample.image_path, target_image)
            write_yolo_labels(target_label, labels)

    data_yaml = {
        "path": str(DATASET_DIR.resolve()),
        "train": "images/train",
        "val": "images/val",
        "names": CLASS_NAMES,
    }
    data_yaml_path = DATASET_DIR / "data.yaml"
    data_yaml_path.write_text(yaml.safe_dump(data_yaml, sort_keys=False), encoding="utf-8")
    print(f"YOLO dataset prepared at: {DATASET_DIR}")
    print(f"Train samples: {len(split_map['train'])}")
    print(f"Val samples: {len(split_map['val'])}")
    return data_yaml_path


def train_model(data_yaml_path: Path, args: argparse.Namespace, device: str) -> Path:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    model = YOLO(args.model)
    print(
        f"Starting training: model={args.model} country={args.country} epochs={args.epochs} "
        f"imgsz={args.imgsz} batch={args.batch} device={device}"
    )
    model.train(
        data=str(data_yaml_path),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=device,
        project=str(RUNS_DIR),
        name=args.run_name,
        exist_ok=True,
        workers=0,
        patience=max(3, min(args.epochs, 10)),
        optimizer="auto",
        hsv_h=0.015,
        hsv_s=0.7,
        hsv_v=0.4,
        fliplr=0.5,
        flipud=0.0,
        mosaic=1.0,
        save=True,
        plots=True,
        verbose=True,
    )
    best_pt = RUNS_DIR / args.run_name / "weights" / "best.pt"
    if not best_pt.exists():
        raise FileNotFoundError(f"Training finished, but best.pt was not found at {best_pt}")
    return best_pt


def copy_weights(best_pt: Path) -> Path:
    WEIGHTS_DST.mkdir(parents=True, exist_ok=True)
    dst = WEIGHTS_DST / "best.pt"
    shutil.copy2(best_pt, dst)
    return dst


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train a lightweight YOLOv8 model on RDD2022.")
    parser.add_argument("--country", choices=sorted(COUNTRY_URLS), default="Japan")
    parser.add_argument("--epochs", type=int, default=25)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=4)
    parser.add_argument("--val-ratio", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--model", default="yolov8n.pt")
    parser.add_argument("--run-name", default="roadcheck-japan-cpu")
    parser.add_argument("--max-samples", type=int, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    random.seed(args.seed)
    device = resolve_device()
    zip_path = download_country_zip(args.country)
    country_dir = ensure_country_extracted(args.country, zip_path)
    samples = collect_samples(country_dir, max_samples=args.max_samples)
    data_yaml_path = build_yolo_dataset(samples, val_ratio=args.val_ratio, seed=args.seed)
    best_pt = train_model(data_yaml_path, args, device=device)
    dst = copy_weights(best_pt)
    print(f"Training complete. Best weights: {best_pt}")
    print(f"Weights copied to backend: {dst}")


if __name__ == "__main__":
    main()
