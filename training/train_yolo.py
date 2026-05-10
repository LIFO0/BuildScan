"""
Train YOLOv8 on building defects dataset.

Requirements:
  - Python 3.11/3.12 recommended (Windows wheels availability).
  - ultralytics installed (already used by yolov8-model-service).

Usage examples:
  py -3.12 training\\train_yolo.py --data training\\dataset.yaml --model yolov8n.pt --epochs 100 --imgsz 1024
  py -3.12 training\\train_yolo.py --data training\\dataset.yaml --model yolov8s.pt --epochs 200 --imgsz 1280
"""

from __future__ import annotations

import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--data", default=str(Path("training") / "dataset.yaml"))
    p.add_argument("--model", default="yolov8n.pt", help="Base model: yolov8n.pt|yolov8s.pt|... or a path to .pt")
    p.add_argument("--epochs", type=int, default=120)
    p.add_argument("--imgsz", type=int, default=1024)
    p.add_argument("--batch", type=int, default=8)
    p.add_argument("--device", default="cpu", help="cpu or 0 (CUDA GPU id). Example: --device 0")
    p.add_argument("--project", default="runs_building_defects")
    p.add_argument("--name", default="yolov8_building_defects")
    p.add_argument("--seed", type=int, default=42)
    return p.parse_args()


def main() -> int:
    args = parse_args()

    from ultralytics import YOLO

    model = YOLO(args.model)
    model.train(
        data=args.data,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        project=args.project,
        name=args.name,
        seed=args.seed,
        pretrained=True,  # keep backbone pretraining (recommended when dataset is small)
        cache=False,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

