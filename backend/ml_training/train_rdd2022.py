from __future__ import annotations

import argparse
import random
import shutil
import subprocess
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter, defaultdict
from collections.abc import Sequence
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
    country: str
    image_path: Path
    xml_path: Path


def resolve_device(requested: str) -> str:
    requested = requested.strip()
    if requested and requested.lower() != "auto":
        return requested
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
        candidates = sorted(path for path in RAW_DIR.rglob(country) if path.is_dir())
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


def collect_samples(
    country_dirs: Sequence[Path],
    *,
    max_samples_per_country: int | None = None,
) -> list[Sample]:
    samples: list[Sample] = []
    for country_dir in country_dirs:
        images_dir = country_dir / "train" / "images"
        xmls_dir = country_dir / "train" / "annotations" / "xmls"
        if not images_dir.exists() or not xmls_dir.exists():
            raise FileNotFoundError(f"Expected training folders were not found under {country_dir}")

        country_samples: list[Sample] = []
        for image_path in sorted(images_dir.glob("*.jpg")):
            xml_path = xmls_dir / f"{image_path.stem}.xml"
            if xml_path.exists():
                country_samples.append(
                    Sample(country=country_dir.name, image_path=image_path, xml_path=xml_path)
                )

        if not country_samples:
            raise RuntimeError(f"No paired training samples were found in {country_dir}")

        if max_samples_per_country is not None:
            country_samples = country_samples[:max_samples_per_country]

        samples.extend(country_samples)
        print(f"Collected {len(country_samples)} samples from {country_dir.name}")

    return samples


def write_yolo_labels(labels_path: Path, labels: list[tuple[int, float, float, float, float]]) -> None:
    labels_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"{class_id} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}"
        for class_id, cx, cy, bw, bh in labels
    ]
    labels_path.write_text("\n".join(lines), encoding="utf-8")


def _split_samples_by_country(samples: Sequence[Sample], val_ratio: float, seed: int) -> dict[str, list[Sample]]:
    rng = random.Random(seed)
    train_samples: list[Sample] = []
    val_samples: list[Sample] = []
    grouped: dict[str, list[Sample]] = defaultdict(list)
    for sample in samples:
        grouped[sample.country].append(sample)

    for country, country_samples in sorted(grouped.items()):
        shuffled = list(country_samples)
        rng.shuffle(shuffled)
        val_count = max(1, int(len(shuffled) * val_ratio))
        if len(shuffled) <= val_count:
            val_count = max(1, len(shuffled) // 5)
        val_samples.extend(shuffled[:val_count])
        train_samples.extend(shuffled[val_count:])

    return {"train": train_samples, "val": val_samples}


def _dataset_filename(sample: Sample) -> str:
    return f"{sample.country}__{sample.image_path.name}"


def build_yolo_dataset(samples: list[Sample], val_ratio: float, seed: int) -> Path:
    if DATASET_DIR.exists():
        shutil.rmtree(DATASET_DIR)

    split_map = _split_samples_by_country(samples, val_ratio=val_ratio, seed=seed)
    class_counts = Counter()

    for split_name, split_samples in split_map.items():
        for sample in split_samples:
            labels = parse_voc_xml(sample.xml_path)
            for class_id, *_ in labels:
                class_counts[CLASS_NAMES[class_id]] += 1

            target_name = _dataset_filename(sample)
            target_image = DATASET_DIR / "images" / split_name / target_name
            target_label = DATASET_DIR / "labels" / split_name / f"{Path(target_name).stem}.txt"
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
    print(f"Class distribution: {dict(class_counts)}")
    return data_yaml_path


def train_model(data_yaml_path: Path, args: argparse.Namespace, device: str) -> Path:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    model = YOLO(args.model)
    print(
        f"Starting training: model={args.model} countries={','.join(args.countries)} "
        f"epochs={args.epochs} imgsz={args.imgsz} batch={args.batch} device={device}"
    )

    train_kwargs: dict[str, object] = {
        "data": str(data_yaml_path),
        "epochs": args.epochs,
        "imgsz": args.imgsz,
        "batch": args.batch,
        "device": device,
        "project": str(RUNS_DIR),
        "name": args.run_name,
        "exist_ok": True,
        "workers": args.workers,
        "patience": args.patience,
        "optimizer": args.optimizer,
        "save": True,
        "plots": True,
        "verbose": True,
        "cos_lr": args.cos_lr,
        "close_mosaic": args.close_mosaic,
        "hsv_h": args.hsv_h,
        "hsv_s": args.hsv_s,
        "hsv_v": args.hsv_v,
        "fliplr": args.fliplr,
        "flipud": args.flipud,
        "translate": args.translate,
        "scale": args.scale,
        "mosaic": args.mosaic,
        "mixup": args.mixup,
        "copy_paste": args.copy_paste,
        "seed": args.seed,
        "deterministic": True,
        "rect": args.rect,
        "single_cls": False,
        # ── новые параметры ──────────────────────────────────────────────
        "lr0": args.lr0,
        "lrf": args.lrf,
        "warmup_epochs": args.warmup_epochs,
        "cls_pw": args.cls_pw,
    }
    if args.cache:
        train_kwargs["cache"] = args.cache

    model.train(**train_kwargs)

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
    parser = argparse.ArgumentParser(description="Prepare and train YOLO on RDD2022 road damage data.")

    # --country (одна страна, для обратной совместимости) и --countries (список)
    parser.add_argument("--country", choices=sorted(COUNTRY_URLS), default=None,
                        help="Single country (legacy alias; use --countries instead).")
    parser.add_argument(
        "--countries",
        nargs="+",
        choices=sorted(COUNTRY_URLS),
        help="One or more RDD2022 countries to combine into a single training dataset.",
    )

    parser.add_argument("--epochs", type=int, default=60)
    parser.add_argument("--imgsz", type=int, default=960)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--val-ratio", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--model", default="yolov8s.pt")
    parser.add_argument("--run-name", default=None)

    # Поддержка обоих вариантов написания: --max-samples и --max-samples-per-country
    parser.add_argument("--max-samples-per-country", "--max-samples",
                        type=int, default=None, dest="max_samples_per_country",
                        help="Limit samples per country (useful for quick debug runs).")

    parser.add_argument("--device", default="auto")
    parser.add_argument("--workers", type=int, default=0)
    parser.add_argument("--patience", type=int, default=20)
    parser.add_argument("--optimizer", default="AdamW")
    parser.add_argument("--cache", choices=["ram", "disk"], default=None)
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--skip-copy-weights", action="store_true")
    parser.add_argument("--rect", action="store_true")
    parser.add_argument("--cos-lr", action="store_true")
    parser.add_argument("--close-mosaic", type=int, default=10)
    parser.add_argument("--hsv-h", type=float, default=0.015)
    parser.add_argument("--hsv-s", type=float, default=0.7)
    parser.add_argument("--hsv-v", type=float, default=0.4)
    parser.add_argument("--fliplr", type=float, default=0.5)
    parser.add_argument("--flipud", type=float, default=0.0)
    parser.add_argument("--translate", type=float, default=0.05)
    parser.add_argument("--scale", type=float, default=0.30)
    parser.add_argument("--mosaic", type=float, default=1.0)
    parser.add_argument("--mixup", type=float, default=0.10)
    parser.add_argument("--copy-paste", type=float, default=0.0)
    # ── новые аргументы ──────────────────────────────────────────────────
    parser.add_argument("--lr0", type=float, default=0.01,
                        help="Initial learning rate (default 0.01; recommended 0.001 for AdamW).")
    parser.add_argument("--lrf", type=float, default=0.01,
                        help="Final learning rate as a fraction of lr0 (used with cos-lr).")
    parser.add_argument("--warmup-epochs", type=float, default=3.0,
                        help="Number of warmup epochs (default 3; try 5 for mixed datasets).")
    parser.add_argument("--cls-pw", type=float, default=0.0,
                        help="BCE class-weight power for imbalanced datasets (e.g. 0.5).")

    args = parser.parse_args()

    # Разрешаем конфликт --country / --countries
    if args.countries:
        args.countries = list(dict.fromkeys(args.countries))  # убираем дубликаты, сохраняем порядок
    elif args.country:
        args.countries = [args.country]
    else:
        args.countries = ["India"]

    # Авто-генерация имени запуска
    if args.run_name is None:
        countries_slug = "-".join(c.lower().replace("_", "-") for c in args.countries)
        model_slug = Path(args.model).stem.lower()
        args.run_name = f"roadcheck-{countries_slug}-{model_slug}"

    return args


def main() -> None:
    args = parse_args()
    random.seed(args.seed)
    device = resolve_device(args.device)

    country_dirs: list[Path] = []
    for country in args.countries:
        zip_path = download_country_zip(country)
        country_dirs.append(ensure_country_extracted(country, zip_path))

    samples = collect_samples(
        country_dirs,
        max_samples_per_country=args.max_samples_per_country,
    )
    data_yaml_path = build_yolo_dataset(samples, val_ratio=args.val_ratio, seed=args.seed)

    if args.prepare_only:
        print(f"Dataset prepared only. data.yaml: {data_yaml_path}")
        return

    best_pt = train_model(data_yaml_path, args, device=device)
    if args.skip_copy_weights:
        print(f"Training complete. Best weights: {best_pt}")
        return

    dst = copy_weights(best_pt)
    print(f"Training complete. Best weights: {best_pt}")
    print(f"Weights copied to backend: {dst}")


if __name__ == "__main__":
    main()