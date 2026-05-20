"""
Модуль для инференса YOLOv8 модели
"""
import os
import torch

# КРИТИЧНО: Установить переменную окружения ДО импорта ultralytics
# PyTorch 2.6+ требует weights_only=False для загрузки YOLOv8 моделей
os.environ['TORCH_ALLOW_UNSAFE_LOAD'] = '1'

# Monkey patch для torch.load (на случай если переменная окружения не сработает)
_original_torch_load = torch.load
def _patched_torch_load(*args, **kwargs):
    if 'weights_only' not in kwargs:
        kwargs['weights_only'] = False
    return _original_torch_load(*args, **kwargs)
torch.load = _patched_torch_load

from ultralytics import YOLO
from PIL import Image
import numpy as np
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

# Fallback identification when model doesn't output element/material/age classes
from app.services.building_identification import infer_identification_from_defects
from app.services.vlm_damage_assessor import assess_building_scene, _MSG_NOT_BUILDING_FALLBACK

# Маппинг классов (домен: дефекты зданий)
# ВАЖНО: если ваша YOLO-модель имеет другие id/названия, достаточно поменять этот маппинг.
CLASS_NAMES = {
    0: "crack_diagonal",
    1: "crack_vertical",
    2: "crack_horizontal",
    3: "crack_hairline",
    4: "plaster_peeling",
    5: "brick_damage",
    6: "corrosion",
    7: "mold",
    8: "moisture_stain",
    9: "concrete_spalling",
    10: "deformation",
}

CLASS_NAMES_RU = {
    "crack_diagonal": "Диагональная трещина",
    "crack_vertical": "Вертикальная трещина",
    "crack_horizontal": "Горизонтальная трещина",
    "crack_hairline": "Волосяная трещина (до 0.1 мм)",
    "plaster_peeling": "Отслоение штукатурки",
    "brick_damage": "Разрушение кирпичной кладки",
    "corrosion": "Коррозия металлических элементов",
    "mold": "Плесень и грибок",
    "moisture_stain": "Следы замокания и высолы",
    "concrete_spalling": "Скол бетона / обнажение арматуры",
    "deformation": "Прогиб / деформация конструкции",
    "no_defect": "Дефектов не обнаружено",
}

DEFECT_CLASSES = [
    "crack_diagonal",
    "crack_vertical",
    "crack_horizontal",
    "crack_hairline",
    "plaster_peeling",
    "brick_damage",
    "corrosion",
    "mold",
    "moisture_stain",
    "concrete_spalling",
    "deformation",
]

DEFECT_FEATURES = {
    "crack_vertical": {
        "type": "трещина",
        "severity": "medium",
        "description": "Вертикальные трещины часто связаны с осадкой основания/фундамента."
    },
    "crack_horizontal": {
        "type": "трещина",
        "severity": "medium",
        "description": "Горизонтальные трещины могут указывать на сдвиги/деформации перекрытий."
    },
    "crack_diagonal": {
        "type": "трещина",
        "severity": "high",
        "description": "Диагональные трещины часто связаны с неравномерной осадкой."
    },
    "crack_hairline": {
        "type": "трещина",
        "severity": "low",
        "description": "Волосяные трещины могут быть усадочными/температурными; требуют наблюдения."
    },
    "plaster_peeling": {
        "type": "разрушение покрытий",
        "severity": "medium",
        "description": "Отслоение штукатурки, риск потери защитного слоя и дальнейшего разрушения."
    },
    "brick_damage": {
        "type": "разрушение кладки",
        "severity": "high",
        "description": "Разрушение кирпичной кладки снижает несущую способность и устойчивость."
    },
    "corrosion": {
        "type": "коррозия",
        "severity": "medium",
        "description": "Коррозия металлических элементов может ускорять деградацию конструкции."
    },
    "mold": {
        "type": "влажностное повреждение",
        "severity": "high",
        "description": "Плесень/грибок — признак хронической влажности и неблагоприятных условий."
    },
    "moisture_stain": {
        "type": "влажностное повреждение",
        "severity": "medium",
        "description": "Следы замокания/высолы обычно связаны с протечками или нарушением гидроизоляции."
    },
    "concrete_spalling": {
        "type": "разрушение бетона",
        "severity": "critical",
        "description": "Скол бетона/обнажение арматуры — высокий риск коррозии и потери несущей способности."
    },
    "deformation": {
        "type": "деформация",
        "severity": "critical",
        "description": "Прогиб/деформация конструкции может указывать на перегрузку или критическое состояние."
    },
}

# Описание состояния по умолчанию (когда дефектов нет)
NORMAL_STATE = {
    "type": "норма",
    "severity": "none",
    "description": "Признаков дефекта не обнаружено"
}

def _severity_rank(severity: str) -> int:
    return {"none": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}.get(str(severity).lower(), 2)


def _build_report(detections: List[dict]) -> Dict[str, Any]:
    """
    Собирает карточку анализа в формате из ТЗ (6 блоков) на основе детекций.
    Это эвристика: точность зависит от того, какие классы выдаёт модель.
    """
    # --- Block 1: Identification (если модель умеет) ---
    element = None
    material = None
    age = None

    for d in detections:
        c = d.get("class")
        if c and c.startswith("element_") and element is None:
            element = CLASS_NAMES_RU.get(c, c)
        if c and c.startswith("material_") and material is None:
            material = CLASS_NAMES_RU.get(c, c)
        if c and c.startswith("age_") and age is None:
            age = CLASS_NAMES_RU.get(c, c)

    identification = {
        "object": element or "не определено (нужна модель/классы для идентификации элемента)",
        "material": material or "не определено (нужна модель/классы для материала)",
        "age_period": age or "не определено (нужна модель/классы для периода постройки)",
    }

    # Эвристика infer_identification_from_defects задаёт «фасад» даже при пустых / нерелевантных
    # детекциях — это вводит в заблуждение на фото «не здание». Используем её только если
    # модель реально что-то нашла из классов дефектов.
    defect_for_id = [d for d in detections if d.get("class") in DEFECT_CLASSES]
    if (element is None) and (material is None) and (age is None):
        if defect_for_id:
            inferred = infer_identification_from_defects(detections)
            identification = {
                "object": inferred.object,
                "material": inferred.material,
                "age_period": inferred.age_period,
            }
        else:
            identification = {
                "object": (
                    "На фотографии не распознан фрагмент наружного фасада или несущей стены здания "
                    "(не найдено детекций по целевым классам дефектов). Если на снимке нет здания, "
                    "загрузите крупный план стены; если это фасад — попробуйте другой ракурс или освещение."
                ),
                "material": "не определено (нет признаков дефектов по целевым классам)",
                "age_period": "не определено",
            }

    # --- Block 2: Defects list ---
    defect_detections = [d for d in detections if d.get("class") in DEFECT_CLASSES]
    defect_items = []
    max_sev = "none"
    for idx, d in enumerate(defect_detections, start=1):
        summary = d.get("defect_summary", {}) or {}
        c = d.get("class")
        class_ru = d.get("class_ru") or CLASS_NAMES_RU.get(c, c)
        sev = str(summary.get("severity", "medium")).lower()
        if _severity_rank(sev) > _severity_rank(max_sev):
            max_sev = sev

        # Эвристики ширины раскрытия/протяжённости — грубо по bbox.
        bbox = d.get("bbox") or [0, 0, 0, 0]
        w = (bbox[2] - bbox[0]) if len(bbox) == 4 else 0
        h = (bbox[3] - bbox[1]) if len(bbox) == 4 else 0
        length_hint = "значительная (более 1 м)" if max(w, h) >= 600 else "умеренная" if max(w, h) >= 250 else "локальная"
        crack_width_hint = None
        if c in ("crack_hairline",):
            crack_width_hint = "до 0.1 мм (волосяная)"
        elif c in ("crack_vertical", "crack_horizontal"):
            crack_width_hint = "0.1–0.3 мм (развитая)"
        elif c in ("crack_diagonal",):
            crack_width_hint = "2–4 мм (широкая)" if max(w, h) >= 400 else "0.3–2 мм"

        item = {
            "index": idx,
            "title": class_ru,
            "severity": sev,
            "confidence": d.get("confidence"),
            "description": summary.get("description", ""),
            "details": {
                "length": length_hint,
                **({"estimated_crack_width": crack_width_hint} if crack_width_hint else {}),
            },
        }
        defect_items.append(item)

    # --- Block 3: GOST category (heuristic) ---
    # 1: normative; 2: workable; 3: limited workable; 4: emergency
    category = 1
    status = "НОРМАТИВНОЕ"
    reasons = []
    if defect_items:
        category = 2
        status = "РАБОТОСПОСОБНОЕ"
        reasons.append("Обнаружены дефекты, требующие наблюдения/ремонта.")

    if max_sev in ("high", "critical"):
        category = 3
        status = "ОГРАНИЧЕННО РАБОТОСПОСОБНОЕ"
        reasons.append("Обнаружены выраженные дефекты (высокая/критическая степень).")
    if max_sev == "critical" and any(d.get("class") in ("beam_sagging", "wall_out_of_plumb", "brick_fallout", "rebar_exposed") for d in defect_detections):
        category = 4
        status = "АВАРИЙНОЕ"
        reasons.append("Есть признаки, потенциально указывающие на угрозу безопасности/устойчивости.")

    gost = {
        "category": category,
        "status": status,
        "basis": reasons,
        "normative": "ГОСТ 31937-2011 (эвристическая оценка по результатам ИИ-детекции)",
    }

    # Note: VLM fallback is applied in YOLOPredictor.predict (where we have access to the image).

    # --- Block 4: Causes (templated) ---
    causes = []
    if any(d.get("class") in ("crack_diagonal", "crack_vertical") for d in defect_detections):
        causes.append("Неравномерная осадка основания/фундамента (возможна из-за изменения уровня грунтовых вод или подмыва).")
    if any(d.get("class") in ("efflorescence_leaks", "damp_spots", "mold_fungus") for d in defect_detections):
        causes.append("Хроническое увлажнение из-за нарушения гидроизоляции/протечек/конденсации.")
    if any(d.get("class") in ("plaster_delamination", "mortar_joint_damage", "brick_fallout") for d in defect_detections):
        causes.append("Старение/деградация материалов и отсутствие своевременного ремонта защитных слоёв.")
    if not causes:
        causes.append("Вероятные причины не определены (недостаточно признаков на фото).")

    # --- Block 5: Urgency & recommendations ---
    urgency_map = {
        1: ("🟢", "НИЗКАЯ"),
        2: ("🟡", "СРЕДНЯЯ"),
        3: ("🟠", "ВЫСОКАЯ"),
        4: ("🔴", "КРИТИЧЕСКАЯ"),
    }
    urgency_level = 1 if category == 1 else 2 if category == 2 else 3 if category == 3 else 4
    urgency = {"level": urgency_level, "label": urgency_map[urgency_level][1], "indicator": urgency_map[urgency_level][0]}

    recommendations = []
    if urgency_level >= 3:
        recommendations.extend([
            "Установить маяки на трещины для контроля динамики раскрытия.",
            "Заказать инструментальное обследование у сертифицированного специалиста.",
        ])
    if any(d.get("class") in ("efflorescence_leaks", "damp_spots", "mold_fungus") for d in defect_detections):
        recommendations.append("Проверить источники влаги и восстановить гидроизоляцию/водоотвод.")
    if urgency_level == 4:
        recommendations.insert(0, "Немедленные меры безопасности: ограждение зоны, ограничение нагрузок/доступа.")

    # --- Block 6: Final card text ---
    final_lines = []
    final_lines.append("АКТ ТЕХНИЧЕСКОГО ОСМОТРА (черновик ИИ)")
    final_lines.append(f"Обследуемый элемент: {identification['object']}")
    final_lines.append("")
    if defect_items:
        final_lines.append("ВЫЯВЛЕННЫЕ ДЕФЕКТЫ:")
        for it in defect_items[:10]:
            line = f"- {it['title']}"
            if it["details"].get("estimated_crack_width"):
                line += f", раскрытие {it['details']['estimated_crack_width']}"
            final_lines.append(line)
    else:
        final_lines.append("ВЫЯВЛЕННЫЕ ДЕФЕКТЫ: не обнаружены")
    final_lines.append("")
    final_lines.append(f"КАТЕГОРИЯ СОСТОЯНИЯ (ГОСТ 31937-2011): {gost['category']} — {gost['status']}")
    final_lines.append(f"СРОЧНОСТЬ: {urgency['label']}")
    final_lines.append("")
    final_lines.append("ВАЖНО: результат является предварительной ИИ-диагностикой и не заменяет заключение эксперта.")

    return {
        "block1_identification": identification,
        "block2_defects": defect_items,
        "block3_gost_31937_2011": gost,
        "block4_causes": causes,
        "block5_urgency": urgency,
        "block5_recommendations": recommendations,
        "block6_final_card_text": "\n".join(final_lines),
    }


def _build_report_scene_rejected(message_ru: str) -> Dict[str, Any]:
    """Карточка, когда снимок не относится к фасаду здания (CLIP или fallback по пустым детекциям)."""
    identification = {
        "object": message_ru,
        "material": "—",
        "age_period": "—",
    }
    gost = {
        "category": 1,
        "status": "АНАЛИЗ НЕ ПРИМЕНИМ",
        "basis": ["Снимок не относится к целевому типу для поиска дефектов фасада."],
        "normative": "—",
    }
    urgency = {"level": 1, "label": "НИЗКАЯ", "indicator": "🟢"}
    recommendations = [
        "Сделайте фото крупным планом наружного фасада или несущей стены здания.",
        "Избегайте сильной засветки и сильного наклона; фрагмент стены должен занимать большую часть кадра.",
    ]
    final_lines = [
        "АКТ ТЕХНИЧЕСКОГО ОСМОТРА (черновик ИИ)",
        message_ru,
        "",
        "Анализ дефектов не выполнялся: изображение не классифицировано как фасад здания.",
        "",
        "ВАЖНО: результат не заменяет заключение эксперта.",
    ]
    return {
        "block1_identification": identification,
        "block2_defects": [],
        "block3_gost_31937_2011": gost,
        "block4_causes": ["Неприменимость связана с типом сцены на фотографии, а не с состоянием конструкции."],
        "block5_urgency": urgency,
        "block5_recommendations": recommendations,
        "block6_final_card_text": "\n".join(final_lines),
    }


class YOLOPredictor:
    """Класс для предсказаний YOLOv8 модели"""

    def __init__(self, model_path: str, conf_threshold: float = 0.25):
        """
        Инициализация предиктора

        Args:
            model_path: путь к файлу модели .pt
            conf_threshold: порог уверенности для детекций
        """
        self.model = YOLO(model_path)
        self.conf_threshold = conf_threshold
        logger.info(f"✅ Модель загружена: {model_path}")

    def predict(self, image: Image.Image, return_visualization: bool = False) -> Dict[str, Any]:
        """
        Предсказание на изображении

        Args:
            image: PIL Image
            return_visualization: вернуть визуализацию с bbox (опционально)

        Returns:
            Словарь с результатами детекции
        """
        scene = assess_building_scene(image)
        empty_stats = {name: 0 for name in CLASS_NAMES.values()}

        if (not scene.get("skipped")) and scene.get("is_building_facade") is False:
            report = _build_report_scene_rejected(scene["message_ru"])
            return {
                "detections": [],
                "statistics": empty_stats,
                "total_objects": 0,
                "defects_count": 0,
                "has_defects": False,
                "report": report,
                "scene": scene,
            }

        # Предсказание YOLO (сцена допустима или CLIP недоступен)
        results = self.model(image, conf=self.conf_threshold)

        # Парсинг результатов
        detections = []
        statistics = {name: 0 for name in CLASS_NAMES.values()}
        defects_count = 0

        # Визуализация (если нужно)
        annotated_image = None
        if return_visualization:
            annotated_image = results[0].plot()  # YOLOv8 автоматически рисует bbox
            annotated_image = Image.fromarray(annotated_image)

        for result in results:
            boxes = result.boxes

            for box in boxes:
                # Координаты bbox
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()

                # Класс и уверенность
                cls_id = int(box.cls[0].cpu().numpy())
                conf = float(box.conf[0].cpu().numpy())

                # Название класса
                class_name = CLASS_NAMES.get(cls_id, f"unknown_{cls_id}")

                # Размер объекта (для определения малых объектов <30px)
                bbox_width = int(x2 - x1)
                bbox_height = int(y2 - y1)
                bbox_area = bbox_width * bbox_height
                is_small_object = bbox_width < 30 or bbox_height < 30

                # Признаки дефекта (для удовлетворения требований ТЗ)
                if class_name in DEFECT_CLASSES:
                    defect_info = DEFECT_FEATURES.get(class_name, {})
                else:
                    defect_info = NORMAL_STATE

                # Детекция
                detection = {
                    "class": class_name,
                    "class_ru": CLASS_NAMES_RU.get(class_name, class_name),
                    "confidence": round(conf, 4),
                    "bbox": [int(x1), int(y1), int(x2), int(y2)],
                    "bbox_size": {
                        "width": bbox_width,
                        "height": bbox_height,
                        "area": bbox_area,
                        "is_small": is_small_object
                    },
                    "defect_summary": {
                        "type": defect_info.get("type", "норма"),
                        "severity": defect_info.get("severity", "none"),
                        "description": defect_info.get("description", "")
                    }
                }

                # Добавляем признаки дефекта для дефектных классов
                if class_name in DEFECT_CLASSES:
                    detection["defect_features"] = {
                        "type": defect_info.get("type", "неизвестно"),
                        "severity": defect_info.get("severity", "medium"),
                        "description": defect_info.get("description", ""),
                        "confidence_level": "high" if conf > 0.7 else "medium" if conf > 0.5 else "low"
                    }

                detections.append(detection)

                # Обновляем статистику
                statistics[class_name] += 1

                # Подсчет дефектов
                if class_name in DEFECT_CLASSES:
                    defects_count += 1

        # Шумовые боксы (не дефекты и низкая уверенность) не должны блокировать ветку «нет фасада»
        if defects_count == 0 and detections:
            max_conf = max(float(d.get("confidence") or 0) for d in detections)
            try:
                noise_max = float(os.getenv("YOLO_NOISE_MAX_CONF", "0.45"))
            except ValueError:
                noise_max = 0.45
            if max_conf < noise_max:
                detections = []
                statistics = {name: 0 for name in CLASS_NAMES.values()}

        report = _build_report(detections)
        scene_out: Dict[str, Any] = dict(scene)

        # CLIP недоступен и YOLO пустой: не подменяем «фасад», но и не утверждаем «не здание»
        # (на ровном фасаде модель тоже может ничего не найти).
        if scene.get("skipped") and len(detections) == 0:
            scene_out["is_building_facade"] = None
            scene_out["message_ru"] = ""
            scene_out["method"] = "yolo_empty_no_clip"
        elif scene.get("skipped") and len(detections) > 0:
            # Есть только нерелевантные/не-дефектные срабатывания — не помечаем как «точно здание»
            scene_out["is_building_facade"] = None
            scene_out.setdefault("message_ru", "")

        result_dict: Dict[str, Any] = {
            "detections": detections,
            "statistics": statistics,
            "total_objects": len(detections),
            "defects_count": defects_count,
            "has_defects": defects_count > 0,
            "report": report,
            "scene": scene_out,
        }

        if return_visualization and annotated_image:
            result_dict["visualization"] = annotated_image

        return result_dict

