import { useState, useRef, useEffect, useCallback, memo } from "react";
import { getDefectMetadata } from "@/types/metrics";

export interface OverlayDetection {
  bbox: number[];
  class?: string;
  class_ru?: string;
  defect_summary?: {
    type?: string;
    severity?: string;
  };
  is_manual?: boolean;
}

interface ImageWithDefectOverlayProps {
  src: string;
  alt: string;
  detections?: OverlayDetection[];
  showOverlay?: boolean;
  highlightedIndex?: number | null;
  imageStyle?: React.CSSProperties;
}

interface DisplayRect {
  x: number;
  y: number;
  width: number;
  height: number;
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

function getStrokeColor(severity: string | undefined, isDefect: boolean): string {
  if (!isDefect) {
    return "rgba(96, 165, 250, 0.85)";
  }
  return getDefectMetadata(severity, true).iconColor;
}

function bboxToDisplayRect(
  bbox: number[],
  naturalWidth: number,
  naturalHeight: number,
  displayWidth: number,
  displayHeight: number
): DisplayRect | null {
  if (bbox.length !== 4 || naturalWidth <= 0 || naturalHeight <= 0) {
    return null;
  }

  const [x1, y1, x2, y2] = bbox;
  const scaleX = displayWidth / naturalWidth;
  const scaleY = displayHeight / naturalHeight;

  return {
    x: x1 * scaleX,
    y: y1 * scaleY,
    width: (x2 - x1) * scaleX,
    height: (y2 - y1) * scaleY,
  };
}

function ImageWithDefectOverlay({
  src,
  alt,
  detections = [],
  showOverlay = false,
  highlightedIndex = null,
  imageStyle,
}: ImageWithDefectOverlayProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const imageRef = useRef<HTMLImageElement>(null);
  const [layout, setLayout] = useState({ width: 0, height: 0, offsetX: 0, offsetY: 0 });
  const [naturalSize, setNaturalSize] = useState({ width: 0, height: 0 });

  const updateLayout = useCallback(() => {
    const container = containerRef.current;
    const image = imageRef.current;
    if (!container || !image || !image.complete || image.naturalWidth === 0) {
      return;
    }

    const containerRect = container.getBoundingClientRect();
    const imageRect = image.getBoundingClientRect();

    setLayout({
      width: imageRect.width,
      height: imageRect.height,
      offsetX: imageRect.left - containerRect.left,
      offsetY: imageRect.top - containerRect.top,
    });
    setNaturalSize({
      width: image.naturalWidth,
      height: image.naturalHeight,
    });
  }, []);

  useEffect(() => {
    updateLayout();
    const container = containerRef.current;
    if (!container) return;

    const observer = new ResizeObserver(updateLayout);
    observer.observe(container);
    window.addEventListener("resize", updateLayout);

    return () => {
      observer.disconnect();
      window.removeEventListener("resize", updateLayout);
    };
  }, [updateLayout, src, showOverlay]);

  const overlayRects = showOverlay
    ? detections
        .map((detection, index) => {
          const rect = bboxToDisplayRect(
            detection.bbox,
            naturalSize.width,
            naturalSize.height,
            layout.width,
            layout.height
          );
          if (!rect || rect.width < 2 || rect.height < 2) {
            return null;
          }

          const isDefect = isDefectDetection(detection);
          const severity = detection.defect_summary?.severity;
          const stroke = getStrokeColor(severity, isDefect);
          const isHighlighted = highlightedIndex === index;

          return {
            index,
            rect,
            stroke,
            isDefect,
            label: detection.class_ru || detection.class || "",
            isHighlighted,
            isManual: detection.is_manual,
          };
        })
        .filter((item): item is NonNullable<typeof item> => item !== null)
    : [];

  return (
    <div
      ref={containerRef}
      className="relative flex h-full w-full max-h-full max-w-full items-center justify-center"
    >
      <img
        ref={imageRef}
        src={src}
        alt={alt}
        className="block max-h-full max-w-full object-contain"
        style={{
          width: "auto",
          height: "auto",
          ...imageStyle,
        }}
        onLoad={updateLayout}
      />

      {showOverlay && layout.width > 0 && overlayRects.length > 0 && (
        <svg
          className="absolute pointer-events-none"
          style={{
            left: layout.offsetX,
            top: layout.offsetY,
            width: layout.width,
            height: layout.height,
          }}
          aria-hidden
        >
          {overlayRects.map((item) => (
            <g key={item.index}>
              <rect
                x={item.rect.x}
                y={item.rect.y}
                width={item.rect.width}
                height={item.rect.height}
                fill={
                  item.isHighlighted
                    ? "rgba(239, 68, 68, 0.25)"
                    : item.isDefect
                      ? "rgba(239, 68, 68, 0.12)"
                      : "rgba(59, 130, 246, 0.08)"
                }
                stroke={item.stroke}
                strokeWidth={item.isHighlighted ? 3 : 2}
                rx={2}
              />
              {item.label && item.isDefect && (
                <>
                  <rect
                    x={item.rect.x}
                    y={Math.max(0, item.rect.y - 22)}
                    width={Math.min(item.label.length * 7 + 12, layout.width - item.rect.x)}
                    height={20}
                    fill="rgba(0, 0, 0, 0.75)"
                    rx={3}
                  />
                  <text
                    x={item.rect.x + 6}
                    y={Math.max(14, item.rect.y - 8)}
                    fill="#FFFFFF"
                    fontSize={11}
                    fontWeight={600}
                  >
                    {item.label.length > 28 ? `${item.label.slice(0, 28)}…` : item.label}
                  </text>
                </>
              )}
              {item.isManual && (
                <circle
                  cx={item.rect.x + item.rect.width - 6}
                  cy={item.rect.y + 6}
                  r={5}
                  fill="#F59E0B"
                  stroke="#0A0A0A"
                  strokeWidth={1}
                />
              )}
            </g>
          ))}
        </svg>
      )}
    </div>
  );
}

export default memo(ImageWithDefectOverlay);
