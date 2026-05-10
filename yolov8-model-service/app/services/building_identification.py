from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class Identification:
    object: str
    material: str
    age_period: str
    note: Optional[str] = None  # e.g. "вероятно"


def _has(defect_classes: set[str], cls: str) -> bool:
    return cls in defect_classes


def infer_identification_from_defects(detections: List[Dict[str, Any]]) -> Identification:
    """
    Fallback идентификация (когда модель не даёт element/material/age классов).
    Это эвристика по признакам дефектов и типичным сочетаниям.
    """
    classes = {str(d.get("class")) for d in detections if d.get("class")}

    # Material heuristics
    if _has(classes, "rebar_exposed"):
        material = "железобетон (вероятно)"
    elif _has(classes, "mortar_joint_damage") or _has(classes, "brick_fallout"):
        material = "кирпич / кладка (вероятно)"
    elif _has(classes, "plaster_delamination"):
        material = "штукатурка (по внешним признакам)"
    elif _has(classes, "metal_corrosion"):
        material = "металл (по коррозии элементов)"
    else:
        material = "не определено (недостаточно признаков)"

    # Object / element heuristics (best-effort)
    # В вашем UX чаще всего анализируют стену/фасад; используем это как default.
    if any(c.startswith("crack_") for c in classes) or _has(classes, "plaster_delamination") or _has(classes, "efflorescence_leaks"):
        obj = "наружная несущая стена / фасад (вероятно)"
    elif _has(classes, "beam_sagging"):
        obj = "перекрытие / балка (вероятно)"
    elif _has(classes, "surface_bulging"):
        obj = "стена / фасад (вероятно)"
    else:
        obj = "фасад / стена (вероятно)"

    # Age heuristics
    # Очень приблизительно: сочетание кладки/штукатурки + признаки хронической влаги часто встречаются в более старом фонде.
    if ("кирпич" in material) and (_has(classes, "efflorescence_leaks") or _has(classes, "damp_spots")):
        age = "1950–1970-е (вероятно)"
    elif ("железобетон" in material) and (_has(classes, "rebar_exposed") or _has(classes, "wall_out_of_plumb")):
        age = "1960–1990-е (вероятно)"
    else:
        age = "после 1990-х (предположительно)"

    return Identification(object=obj, material=material, age_period=age, note="fallback-heuristic")

