import { useEffect, memo } from "react";
import { useContainedImageLayout } from "@/shared/useContainedImageLayout";

interface SafeImageProps {
  src: string;
  alt: string;
  className?: string;
  containerClassName?: string;
  style?: React.CSSProperties;
  onLoad?: () => void;
}

/** Изображение через background-image — без <img>, чтобы Яндекс.Браузер не показывал панель поиска. */
function SafeImage({
  src,
  alt,
  className = "",
  containerClassName = "relative flex h-full w-full max-h-full max-w-full items-center justify-center",
  style,
  onLoad,
}: SafeImageProps) {
  const { containerRef, layout, naturalSize } = useContainedImageLayout(src);

  useEffect(() => {
    if (naturalSize.width > 0 && layout.width > 0) {
      onLoad?.();
    }
  }, [naturalSize.width, naturalSize.height, layout.width, onLoad]);

  return (
    <div ref={containerRef} className={containerClassName}>
      {layout.width > 0 && (
        <div
          role="img"
          aria-label={alt}
          className={`absolute shrink-0 bg-contain bg-center bg-no-repeat pointer-events-none ${className}`}
          style={{
            left: layout.offsetX,
            top: layout.offsetY,
            width: layout.width,
            height: layout.height,
            backgroundImage: `url("${src}")`,
            ...style,
          }}
        />
      )}
    </div>
  );
}

export default memo(SafeImage);
