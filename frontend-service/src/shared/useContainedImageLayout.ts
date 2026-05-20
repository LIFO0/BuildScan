import { useState, useRef, useEffect, useCallback } from "react";

export interface ContainedImageLayout {
  width: number;
  height: number;
  offsetX: number;
  offsetY: number;
}

/** Загрузка и расчёт object-contain без тега <img> (не триггерит панель Яндекс.Браузера). */
export function useContainedImageLayout(src: string) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [naturalSize, setNaturalSize] = useState({ width: 0, height: 0 });
  const [layout, setLayout] = useState<ContainedImageLayout>({
    width: 0,
    height: 0,
    offsetX: 0,
    offsetY: 0,
  });

  const updateLayout = useCallback(() => {
    const container = containerRef.current;
    if (!container || naturalSize.width === 0 || naturalSize.height === 0) {
      return;
    }

    const { width: cw, height: ch } = container.getBoundingClientRect();
    const scale = Math.min(cw / naturalSize.width, ch / naturalSize.height);
    const width = naturalSize.width * scale;
    const height = naturalSize.height * scale;

    setLayout({
      width,
      height,
      offsetX: (cw - width) / 2,
      offsetY: (ch - height) / 2,
    });
  }, [naturalSize]);

  useEffect(() => {
    setNaturalSize({ width: 0, height: 0 });
    const loader = new Image();
    loader.onload = () => {
      setNaturalSize({
        width: loader.naturalWidth,
        height: loader.naturalHeight,
      });
    };
    loader.src = src;
  }, [src]);

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
  }, [updateLayout, src]);

  return { containerRef, layout, naturalSize, updateLayout };
}
