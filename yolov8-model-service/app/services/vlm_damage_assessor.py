from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from PIL import Image


@dataclass(frozen=True)
class VlmResult:
    label: str
    score: float


class ClipZeroShotAssessor:
    """
    Zero-shot fallback using CLIP.
    Loads lazily once per process.
    """

    def __init__(self, model_id: str = "openai/clip-vit-base-patch32") -> None:
        from transformers import CLIPModel, CLIPProcessor  # type: ignore

        self.model_id = model_id
        self.processor = CLIPProcessor.from_pretrained(model_id)
        self.model = CLIPModel.from_pretrained(model_id)

    def rank(self, image: Image.Image, labels: List[str]) -> List[VlmResult]:
        import torch

        inputs = self.processor(text=labels, images=image, return_tensors="pt", padding=True)
        with torch.no_grad():
            outputs = self.model(**inputs)
            logits = outputs.logits_per_image[0]  # (len(labels),)
            probs = logits.softmax(dim=0).cpu().numpy().tolist()
        scored = [VlmResult(label=l, score=float(p)) for l, p in zip(labels, probs)]
        scored.sort(key=lambda x: x.score, reverse=True)
        return scored


_assessor: ClipZeroShotAssessor | None = None


def get_assessor() -> ClipZeroShotAssessor:
    global _assessor
    if _assessor is None:
        _assessor = ClipZeroShotAssessor()
    return _assessor


def assess_damage_and_context(image: Image.Image) -> Dict[str, Any]:
    """
    Returns:
      - damage_level: 1..4 (gost category proxy)
      - damage_label_ru
      - confidence (0..1)
      - material_guess_ru
      - object_guess_ru
    """
    assessor = get_assessor()

    # Damage severity (very important)
    damage_labels = [
        "фото аварийного здания, есть обрушение, разрушенные этажи, крупные трещины",
        "фото здания с сильными повреждениями, глубокие трещины, частичное разрушение",
        "фото здания с умеренными дефектами, трещины и отслоение штукатурки",
        "фото здания без видимых дефектов, фасад в норме",
    ]
    damage_ranked = assessor.rank(image, damage_labels)
    top = damage_ranked[0]

    # Map to category (proxy for ГОСТ 31937-2011)
    # Order above is from worst->best.
    if top.label == damage_labels[0]:
        category = 4
        damage_ru = "АВАРИЙНОЕ (обрушение/угроза безопасности)"
    elif top.label == damage_labels[1]:
        category = 3
        damage_ru = "ОГРАНИЧЕННО РАБОТОСПОСОБНОЕ (сильные повреждения)"
    elif top.label == damage_labels[2]:
        category = 2
        damage_ru = "РАБОТОСПОСОБНОЕ (умеренные дефекты)"
    else:
        category = 1
        damage_ru = "НОРМАТИВНОЕ (дефекты не выражены)"

    # Object element guess
    obj_labels = [
        "фото фасада многоквартирного дома",
        "фото несущей стены здания",
        "фото перекрытия или балок здания",
        "фото фундамента здания",
        "фото кровли здания",
        "фото балкона здания",
    ]
    obj_top = assessor.rank(image, obj_labels)[0]
    obj_map = {
        obj_labels[0]: "фасад",
        obj_labels[1]: "несущая стена",
        obj_labels[2]: "перекрытие/балки",
        obj_labels[3]: "фундамент",
        obj_labels[4]: "кровля",
        obj_labels[5]: "балкон",
    }

    # Material guess
    mat_labels = [
        "кирпичное здание, кирпичная кладка",
        "панельное здание, железобетонные панели",
        "железобетонная конструкция",
        "деревянная конструкция здания",
        "металлические конструкции здания",
        "оштукатуренный фасад здания",
    ]
    mat_top = assessor.rank(image, mat_labels)[0]
    mat_map = {
        mat_labels[0]: "кирпич",
        mat_labels[1]: "панель",
        mat_labels[2]: "железобетон",
        mat_labels[3]: "дерево",
        mat_labels[4]: "металл",
        mat_labels[5]: "штукатурка",
    }

    return {
        "damage_category": category,
        "damage_label_ru": damage_ru,
        "confidence": round(top.score, 4),
        "object_guess_ru": obj_map.get(obj_top.label, "фасад/стена"),
        "material_guess_ru": mat_map.get(mat_top.label, "не определено"),
    }

