import { useState, useEffect, useCallback, useMemo, useRef, memo } from "react";
import { createPortal } from "react-dom";
import { motion, AnimatePresence } from "framer-motion";
import ImageWithDefectOverlay, { type OverlayDetection } from "./ImageWithDefectOverlay";
import { getDefectMetadata } from "@/types/metrics";

type DetectionWithConfidence = OverlayDetection & { confidence?: number };

export type { DetectionWithConfidence };

interface DefectListItem {
  sourceIndex: number;
  label: string;
  confidence: number;
  severity?: string;
  isDefect: boolean;
}

interface DefectResultModalProps {
  isOpen: boolean;
  onClose: () => void;
  imageUrl: string;
  fileName: string;
  detections: DetectionWithConfidence[];
}

interface PanState {
  x: number;
  y: number;
}

function isDefectDetection(detection: OverlayDetection): boolean {
  const summary = detection.defect_summary || {};
  const severity = summary.severity;
  if (severity === "none" || severity === null || severity === undefined) {
    const type = (summary.type || "").toLowerCase();
    return type !== "" && type !== "норма" && type !== "normal";
  }
  return severity !== "none";
}

function buildDefectList(detections: DetectionWithConfidence[]): DefectListItem[] {
  const items = detections.map((detection, sourceIndex) => {
    const summary = detection.defect_summary || {};
    return {
      sourceIndex,
      label: detection.class_ru || detection.class || "Объект",
      confidence: detection.confidence ?? 0,
      severity: summary.severity,
      isDefect: isDefectDetection(detection),
    };
  });

  return items.sort((a, b) => {
    if (a.isDefect && !b.isDefect) return -1;
    if (!a.isDefect && b.isDefect) return 1;
    if (a.isDefect && b.isDefect) {
      const rank = (s?: string) =>
        s === "critical" || s === "high" || s === "критическая" ? 0 : 1;
      return rank(a.severity) - rank(b.severity);
    }
    return 0;
  });
}

const ZOOM_MIN = 1;
const ZOOM_MAX = 4;
const ZOOM_STEP = 0.25;

function DefectResultModal({
  isOpen,
  onClose,
  imageUrl,
  fileName,
  detections,
}: DefectResultModalProps) {
  const [highlightedIndex, setHighlightedIndex] = useState<number | null>(null);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState<PanState>({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);
  const panStartRef = useRef({ clientX: 0, clientY: 0, panX: 0, panY: 0 });

  const defectList = useMemo(() => buildDefectList(detections), [detections]);
  const defectCount = defectList.filter((d) => d.isDefect).length;

  const resetView = useCallback(() => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
    setHighlightedIndex(null);
  }, []);

  useEffect(() => {
    if (!isOpen) {
      resetView();
      return;
    }
    const firstDefect = defectList.find((d) => d.isDefect);
    setHighlightedIndex(firstDefect ? firstDefect.sourceIndex : null);
    setZoom(1);
    setPan({ x: 0, y: 0 });

    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, [isOpen, resetView, defectList]);

  useEffect(() => {
    if (!isOpen) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [isOpen, onClose]);

  useEffect(() => {
    if (!isPanning) return;

    const onMouseMove = (e: MouseEvent) => {
      setPan({
        x: panStartRef.current.panX + e.clientX - panStartRef.current.clientX,
        y: panStartRef.current.panY + e.clientY - panStartRef.current.clientY,
      });
    };

    const endPan = () => setIsPanning(false);

    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", endPan);

    return () => {
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", endPan);
    };
  }, [isPanning]);

  const handleSelectDefect = (sourceIndex: number) => {
    setHighlightedIndex(sourceIndex);
  };

  const handleZoomIn = () => setZoom((z) => Math.min(ZOOM_MAX, z + ZOOM_STEP));
  const handleZoomOut = () => setZoom((z) => Math.max(ZOOM_MIN, z - ZOOM_STEP));

  const handleViewportMouseDown = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.button !== 1) return;
    e.preventDefault();
    setIsPanning(true);
    panStartRef.current = {
      clientX: e.clientX,
      clientY: e.clientY,
      panX: pan.x,
      panY: pan.y,
    };
  };

  const handleAuxClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.button === 1) e.preventDefault();
  };

  if (typeof document === "undefined") return null;

  return createPortal(
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2 }}
          className="fixed inset-0 z-[200] flex items-center justify-center p-4 md:p-8"
          role="dialog"
          aria-modal="true"
          aria-labelledby="defect-result-modal-title"
        >
          <button
            type="button"
            className="absolute inset-0 bg-black/85 backdrop-blur-sm"
            onClick={onClose}
            aria-label="Закрыть"
          />

          <motion.div
            initial={{ opacity: 0, scale: 0.96, y: 12 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: 12 }}
            transition={{ duration: 0.25 }}
            className="relative z-10 flex h-[min(92vh,900px)] w-full max-w-[1400px] flex-col overflow-hidden rounded-2xl border border-white/15 bg-[#111111] shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Шапка */}
            <div className="flex shrink-0 items-center justify-between gap-4 border-b border-white/10 px-5 py-4">
              <div className="min-w-0">
                <h2
                  id="defect-result-modal-title"
                  className="truncate text-lg font-semibold text-white"
                >
                  Результат анализа
                </h2>
                <p className="truncate text-sm text-white/50">{fileName}</p>
              </div>

              <div className="flex items-center gap-2 shrink-0">
                <span className="hidden sm:inline text-xs text-white/40 mr-1">
                  {defectCount > 0
                    ? `${defectCount} дефект${defectCount === 1 ? "" : defectCount < 5 ? "а" : "ов"}`
                    : "Детекции"}
                </span>
                <button
                  type="button"
                  onClick={handleZoomOut}
                  disabled={zoom <= ZOOM_MIN}
                  className="rounded-lg border border-white/15 px-3 py-1.5 text-sm text-white/80 hover:bg-white/10 disabled:opacity-30"
                  aria-label="Уменьшить"
                >
                  −
                </button>
                <span className="min-w-[3rem] text-center text-sm text-white/70">
                  {Math.round(zoom * 100)}%
                </span>
                <button
                  type="button"
                  onClick={handleZoomIn}
                  disabled={zoom >= ZOOM_MAX}
                  className="rounded-lg border border-white/15 px-3 py-1.5 text-sm text-white/80 hover:bg-white/10 disabled:opacity-30"
                  aria-label="Увеличить"
                >
                  +
                </button>
                <button
                  type="button"
                  onClick={resetView}
                  className="rounded-lg border border-white/15 px-3 py-1.5 text-sm text-white/60 hover:bg-white/10"
                >
                  Сброс
                </button>
                <button
                  type="button"
                  onClick={onClose}
                  className="ml-1 rounded-lg p-2 text-white/70 hover:bg-white/10 hover:text-white"
                  aria-label="Закрыть окно"
                >
                  <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M6 18L18 6M6 6l12 12"
                    />
                  </svg>
                </button>
              </div>
            </div>

            {/* Контент */}
            <div className="flex min-h-0 flex-1 flex-col md:flex-row">
              {/* Изображение */}
              <div className="relative min-h-0 flex-1 overflow-hidden bg-black/40">
                <div
                  className={`absolute inset-0 overflow-hidden select-none ${
                    isPanning ? "cursor-grabbing" : "cursor-default"
                  }`}
                  onMouseDown={handleViewportMouseDown}
                  onAuxClick={handleAuxClick}
                  style={{ touchAction: "none" }}
                >
                  <div className="flex h-full w-full items-center justify-center">
                    <div
                      className="will-change-transform"
                      style={{
                        transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
                        transformOrigin: "center center",
                        transition: isPanning ? "none" : "transform 0.2s ease-out",
                      }}
                    >
                      <div className="relative flex h-[min(70vh,720px)] w-[min(85vw,1000px)] max-h-full max-w-full items-center justify-center">
                        <ImageWithDefectOverlay
                          src={imageUrl}
                          alt={fileName}
                          detections={detections}
                          showOverlay
                          highlightedIndex={highlightedIndex}
                        />
                      </div>
                    </div>
                  </div>
                </div>
                <p className="pointer-events-none absolute bottom-3 left-4 text-xs text-white/40">
                  Зажмите колёсико мыши для перемещения · +/- для масштаба
                </p>
              </div>

              {/* Список дефектов */}
              <div className="flex w-full shrink-0 flex-col border-t border-white/10 md:w-[300px] md:border-t-0 md:border-l">
                <p className="shrink-0 px-4 py-3 text-xs font-semibold uppercase tracking-wide text-white/50">
                  Обнаружено на фото
                </p>
                <div className="min-h-0 flex-1 overflow-y-auto px-3 pb-4 space-y-2">
                  {defectList.length === 0 ? (
                    <p className="px-2 text-sm text-white/50">Детекции отсутствуют</p>
                  ) : (
                    defectList.map((item) => {
                      const isActive = highlightedIndex === item.sourceIndex;
                      const meta = getDefectMetadata(
                        item.severity,
                        item.isDefect
                      );
                      const confidencePct = Math.round(item.confidence * 100);

                      return (
                        <button
                          key={item.sourceIndex}
                          type="button"
                          onClick={() => handleSelectDefect(item.sourceIndex)}
                          className={`w-full rounded-xl border p-3 text-left transition-all ${
                            isActive
                              ? "border-[#F59E0B] bg-[rgba(245,158,11,0.15)]"
                              : "border-white/10 bg-white/5 hover:border-white/25 hover:bg-white/10"
                          }`}
                        >
                          <div className="flex items-start gap-2">
                            <span
                              className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full"
                              style={{ backgroundColor: meta.iconBgColor }}
                            >
                              {item.isDefect ? (
                                <svg
                                  className="h-4 w-4"
                                  fill={meta.iconColor}
                                  viewBox="0 0 20 20"
                                >
                                  <path
                                    fillRule="evenodd"
                                    d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                                    clipRule="evenodd"
                                  />
                                </svg>
                              ) : (
                                <svg
                                  className="h-4 w-4"
                                  fill="none"
                                  stroke={meta.iconColor}
                                  viewBox="0 0 24 24"
                                  strokeWidth={2}
                                >
                                  <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                                  />
                                </svg>
                              )}
                            </span>
                            <div className="min-w-0 flex-1">
                              <p className="truncate text-sm font-medium text-white">
                                {item.label}
                              </p>
                              {item.isDefect && confidencePct > 0 && (
                                <p className="mt-0.5 text-xs text-white/50">
                                  Уверенность: {confidencePct}%
                                </p>
                              )}
                            </div>
                          </div>
                        </button>
                      );
                    })
                  )}
                </div>
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>,
    document.body
  );
}

export default memo(DefectResultModal);
