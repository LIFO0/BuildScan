"""
Скрипт подготовки датасета для обучения YOLOv8.
Создаёт папку valid, переносит туда 20% данных из train,
и генерирует правильный data.yaml.
"""

import os
import shutil
import random
import yaml
from pathlib import Path

# ============================================================
#  ПУТЬ К ДАТАСЕТУ — меняй только эту строку если нужно
# ============================================================
DATASET_PATH = Path(r"C:\Users\user\Desktop\MPIT-2026-Okrug-main\training\data\building_defects")

# Откуда берём данные
TRAIN_IMAGES = DATASET_PATH / "train" / "images"
TRAIN_LABELS = DATASET_PATH / "train" / "labels"

# Куда кладём validation
VALID_IMAGES = DATASET_PATH / "valid" / "images"
VALID_LABELS = DATASET_PATH / "valid" / "labels"

# Сколько процентов отдаём в valid
VAL_SPLIT = 0.2

# ============================================================

def main():
    print("=" * 50)
    print("  Подготовка датасета для YOLOv8")
    print("=" * 50)

    # --- Проверяем что train существует ---
    if not TRAIN_IMAGES.exists():
        print(f"❌ Папка не найдена: {TRAIN_IMAGES}")
        print("   Проверь путь к датасету в переменной DATASET_PATH")
        return

    # --- Получаем список всех изображений ---
    extensions = [".jpg", ".jpeg", ".png", ".bmp", ".webp"]
    all_images = []
    for ext in extensions:
        all_images.extend(list(TRAIN_IMAGES.glob(f"*{ext}")))
        all_images.extend(list(TRAIN_IMAGES.glob(f"*{ext.upper()}")))

    if not all_images:
        print(f"❌ Изображения не найдены в {TRAIN_IMAGES}")
        return

    print(f"\n✅ Найдено изображений в train: {len(all_images)}")

    # --- Проверяем есть ли уже valid ---
    if VALID_IMAGES.exists() and len(list(VALID_IMAGES.glob("*"))) > 0:
        print(f"⚠️  Папка valid уже существует и не пустая.")
        answer = input("   Пересоздать? (да/нет): ").strip().lower()
        if answer not in ("да", "д", "y", "yes"):
            print("   Пропускаем создание valid.")
        else:
            shutil.rmtree(DATASET_PATH / "valid")
            _create_valid(all_images)
    else:
        _create_valid(all_images)

    # --- Генерируем data.yaml ---
    _create_yaml()

    # --- Итоговая статистика ---
    print("\n" + "=" * 50)
    print("  Готово! Статистика датасета:")
    print("=" * 50)
    _print_stats()
    print("\n✅ Датасет готов к обучению!")
    print("\nЗапусти обучение командой:")
    print(f'   python training\\train_yolo.py --data training\\data\\building_defects\\data.yaml --model yolov8n.pt --epochs 50 --imgsz 640 --batch 4 --device cpu')


def _create_valid(all_images):
    """Создаёт папку valid и переносит туда 20% изображений."""

    # Создаём папки
    VALID_IMAGES.mkdir(parents=True, exist_ok=True)
    VALID_LABELS.mkdir(parents=True, exist_ok=True)

    # Перемешиваем и делим
    random.seed(42)  # для воспроизводимости
    random.shuffle(all_images)
    val_count = max(1, int(len(all_images) * VAL_SPLIT))
    val_images = all_images[:val_count]

    print(f"📂 Переносим в valid: {val_count} изображений ({VAL_SPLIT*100:.0f}%)")

    moved = 0
    no_label = 0

    for img_path in val_images:
        # Копируем изображение
        shutil.copy2(img_path, VALID_IMAGES / img_path.name)

        # Копируем соответствующий label файл
        label_path = TRAIN_LABELS / (img_path.stem + ".txt")
        if label_path.exists():
            shutil.copy2(label_path, VALID_LABELS / label_path.name)
            moved += 1
        else:
            # Создаём пустой label (изображение без дефектов)
            (VALID_LABELS / (img_path.stem + ".txt")).touch()
            no_label += 1

    print(f"   ✅ С разметкой: {moved}")
    if no_label:
        print(f"   ⚠️  Без разметки (создан пустой файл): {no_label}")


def _create_yaml():
    """Создаёт data.yaml для обучения."""

    yaml_path = DATASET_PATH / "data.yaml"

    # Используем прямые пути
    data = {
        "path": str(DATASET_PATH).replace("\\", "/"),
        "train": "train/images",
        "val": "valid/images",
        "test": "test/images",
        "nc": 1,
        "names": ["crack"],
    }

    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False)

    print(f"\n✅ Создан data.yaml: {yaml_path}")
    print(f"   Классы: crack (1 класс)")


def _print_stats():
    """Выводит статистику по папкам."""
    folders = {
        "train/images": TRAIN_IMAGES,
        "train/labels": TRAIN_LABELS,
        "valid/images": VALID_IMAGES,
        "valid/labels": VALID_LABELS,
    }
    for name, path in folders.items():
        if path.exists():
            count = len(list(path.glob("*")))
            print(f"   {name}: {count} файлов")
        else:
            print(f"   {name}: ❌ не найдена")


if __name__ == "__main__":
    main()
