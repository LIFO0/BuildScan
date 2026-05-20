/**
 * Данные с бэкенда (yolov8 + Django): проверка сцены «фасад здания» vs прочее.
 */
export type ImageSummaryLike = {
  scene?: {
    skipped?: boolean;
    is_building_facade?: boolean | null;
    message_ru?: string;
    method?: string;
  } | null;
  report?: {
    block1_identification?: { object?: string };
    block3_gost_31937_2011?: { status?: string };
  } | null;
};

export function getNotBuildingMessage(
  summary: ImageSummaryLike | null | undefined
): string | null {
  if (!summary) return null;

  const scene = summary.scene;
  if (scene && scene.is_building_facade === false && scene.message_ru?.trim()) {
    return scene.message_ru.trim();
  }

  const obj = summary.report?.block1_identification?.object;
  if (typeof obj === "string" && obj.trim()) {
    const s = obj.trim();
    if (
      s.includes("не здание") ||
      s.includes("не фрагмент наружного фасада") ||
      s.includes("нет фасада здания")
    ) {
      return s;
    }
    if (
      s.includes("Если на снимке нет здания") ||
      s.includes("не распознан типичный фрагмент наружного фасада")
    ) {
      return s;
    }
  }

  if (
    summary.report?.block3_gost_31937_2011?.status === "АНАЛИЗ НЕ ПРИМЕНИМ" &&
    typeof obj === "string" &&
    obj.trim()
  ) {
    return obj.trim();
  }

  return null;
}

export function isNotBuildingPhoto(
  summary: ImageSummaryLike | null | undefined
): boolean {
  return getNotBuildingMessage(summary) !== null;
}

/** Короткий заголовок для баннера: жёсткий отказ CLIP vs мягкая подсказка по отчёту */
export function getNotBuildingBannerTitle(message: string): string {
  if (
    message.includes("На фотографии не здание") ||
    message.includes("нет фасада здания")
  ) {
    return "На фотографии не здание";
  }
  return "Снимок, вероятно, не для анализа фасада";
}
