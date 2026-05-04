# RoadCheck Training Guide

## What is wrong with the current training baseline

- Only `India` is currently unpacked in `backend/ml_training/rdd2022_raw`.
- In the current India-only labels, class balance is weak:
  - `D40` pothole: `3187`
  - `D20` alligator crack: `2021`
  - `D00` longitudinal crack: `1555`
  - `D10` transverse crack: `68`
- The last saved run in `backend/ml_training/runs/roadcheck-japan-cpu/results.csv` has only `8` epochs and very low quality:
  - best `recall`: `0.17355`
  - best `mAP50`: `0.15941`
  - best `mAP50-95`: `0.06408`

This means the current model is both undertrained and trained on too narrow a slice of the dataset.

## Recommended strategy

1. Train on all available RDD2022 countries, not only India.
2. Use `yolov8s.pt` as the baseline model.
3. Train with larger images: `imgsz 960` or `1024`.
4. Train longer: `80-120` epochs, not `8-25`.
5. Use cosine LR and close mosaic near the end of training.
6. Keep `AdamW`.

## Environment

From the project root:

```powershell
.\.venv\Scripts\python.exe -m pip install torch torchvision ultralytics pyyaml
```

If `curl` is available in PowerShell, the dataset downloader inside the script will use it automatically.

## Updated script

The project script now supports:

- multiple countries at once via `--countries`
- dataset preparation without training via `--prepare-only`
- choosing device, optimizer, cache mode, augmentation settings
- unique filenames when merging countries

Script path:

`backend/ml_training/train_rdd2022.py`

## 1. Quick sanity run on current local India data

This does not aim for the best model. It is only for checking that the pipeline works:

```powershell
.\.venv\Scripts\python.exe backend\ml_training\train_rdd2022.py `
  --countries India `
  --epochs 40 `
  --imgsz 896 `
  --batch 8 `
  --model yolov8s.pt `
  --cos-lr `
  --close-mosaic 10 `
  --optimizer AdamW `
  --cache disk
```

## 2. Recommended full RDD2022 training

This is the main command I recommend for better generalization:

```powershell
.\.venv\Scripts\python.exe backend\ml_training\train_rdd2022.py `
  --countries India Japan Czech Norway United_States China_MotorBike China_Drone `
  --epochs 100 `
  --imgsz 960 `
  --batch 8 `
  --model yolov8s.pt `
  --cos-lr `
  --close-mosaic 10 `
  --optimizer AdamW `
  --cache disk `
  --patience 25
```

Notes:

- If some countries are not downloaded yet, the script will download and unpack them.
- The merged YOLO dataset will be rebuilt in `backend/ml_training/dataset_yolo`.
- Best weights will be copied automatically to `backend/app/ml/weights/best.pt`.

## 3. If you have a stronger GPU

For `12-16 GB` VRAM:

```powershell
.\.venv\Scripts\python.exe backend\ml_training\train_rdd2022.py `
  --countries India Japan Czech Norway United_States China_MotorBike China_Drone `
  --epochs 120 `
  --imgsz 1024 `
  --batch 6 `
  --model yolov8m.pt `
  --cos-lr `
  --close-mosaic 10 `
  --optimizer AdamW `
  --cache disk `
  --patience 30
```

For CPU-only training, lower expectations and use:

```powershell
.\.venv\Scripts\python.exe backend\ml_training\train_rdd2022.py `
  --countries India Japan Czech Norway United_States China_MotorBike China_Drone `
  --epochs 60 `
  --imgsz 768 `
  --batch 4 `
  --model yolov8n.pt `
  --device cpu `
  --optimizer AdamW `
  --close-mosaic 10 `
  --patience 15
```

## 4. Prepare dataset only

If you want to inspect the merged dataset before training:

```powershell
.\.venv\Scripts\python.exe backend\ml_training\train_rdd2022.py `
  --countries India Japan Czech Norway United_States China_MotorBike China_Drone `
  --prepare-only
```

This will rebuild:

- `backend/ml_training/dataset_yolo/images/train`
- `backend/ml_training/dataset_yolo/images/val`
- `backend/ml_training/dataset_yolo/labels/train`
- `backend/ml_training/dataset_yolo/labels/val`
- `backend/ml_training/dataset_yolo/data.yaml`

## 5. Parameters that matter most

### `--countries`

Most important for your case. India-only data is not enough, especially for cracks.

### `--imgsz`

For road damage, small cracks and distant potholes are easy to lose after resize.
Use:

- `960` as the default good choice
- `1024` if GPU allows
- `768` if hardware is weak

### `--model`

- `yolov8s.pt`: best default balance
- `yolov8m.pt`: better if you have enough VRAM
- `yolov8n.pt`: only if hardware is weak

### `--epochs`

Use `80-120`. The current run with `8` epochs is not enough.

### `--close-mosaic 10`

Good practice for detection training. Mosaic is useful early, but should be reduced near the end.

### `--cos-lr`

Safer LR decay for longer runs.

## 6. What result to expect

The main expected improvements are:

- better recall on multiple potholes in one frame
- fewer misses on medium and far defects
- better generalization across road texture, camera height and country

What this will not solve fully by itself:

- defects that are not annotated in RDD2022 classes
- very domain-specific road scenes from your own users

## 7. Best next step after RDD2022

After the full RDD2022 training, add your own real project photos with markup and run a short fine-tune from the new `best.pt`.

That is usually the step that gives the biggest jump for your actual product images.
