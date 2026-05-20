import { Link } from "react-router-dom";
import { Button } from "@heroui/react";
import { motion } from "framer-motion";
import { ScanSearch } from "lucide-react";

/** Горизонт колец — как в оригинале (scope/grid по центру на 65% экрана) */
const HORIZON = "65%";
/** Масштаб полукруга колец относительно исходного scope.svg */
const SCOPE_SCALE = 1.15;

export default function HomePage() {
  return (
    <div
      className="h-screen text-white relative overflow-hidden"
      style={{ backgroundColor: "#0A0A0A" }}
    >
      {/* Фон: сетка, луч, полукруги — как в фиолетовом макете */}
      <div
        className="fixed inset-0 pointer-events-none"
        style={{ overflow: "visible", zIndex: 0, background: "transparent" }}
      >
        <img
          src="/images/grid.svg"
          alt=""
          className="absolute left-1/2"
          style={{
            top: HORIZON,
            transform: "translateX(-50%) translateY(-50%)",
            width: "100%",
            height: "100%",
            objectFit: "cover",
            opacity: 0.12,
            zIndex: 1,
          }}
        />

        <img
          src="/images/ray.svg"
          alt=""
          className="absolute top-0 left-12"
          style={{
            width: "200%",
            height: "200%",
            objectFit: "none",
            objectPosition: "top left",
            mixBlendMode: "screen",
            opacity: 0.35,
            zIndex: 1,
          }}
        />

        <div
          className="absolute left-1/2 pointer-events-none"
          style={{
            top: HORIZON,
            transform: `translateX(-50%) translateY(-50%) scale(${SCOPE_SCALE})`,
            zIndex: 2,
            clipPath: "inset(0 0 50% 0)",
            WebkitClipPath: "inset(0 0 50% 0)",
            WebkitMaskImage:
              "linear-gradient(to bottom, black 60%, transparent 100%)",
            maskImage:
              "linear-gradient(to bottom, black 60%, transparent 100%)",
            WebkitMaskSize: "100% 50%",
            maskSize: "100% 50%",
            WebkitMaskPosition: "top",
            maskPosition: "top",
            WebkitMaskRepeat: "no-repeat",
            maskRepeat: "no-repeat",
          }}
        >
          <img
            src="/images/scope.svg"
            alt=""
            className="block bg-transparent"
            style={{
              background: "transparent",
              filter:
                "drop-shadow(0 0 4px rgba(245, 158, 11, 0.45)) drop-shadow(0 0 8px rgba(245, 158, 11, 0.2))",
            }}
          />
        </div>
      </div>

      <div className="relative z-10" style={{ padding: "40px" }}>
        {/* Навбар */}
        <div className="w-full flex items-center justify-between">
          <div className="flex items-center gap-3">
            <img
              src="/images/magnifier_logo.png"
              alt="BuildScan"
              className="h-8 w-8 object-contain"
            />
            <span className="text-white text-xl font-bold">BuildScan</span>
          </div>

          <div
            className="hidden sm:flex gap-[42px] border border-white/10 pl-[24px] pt-[18px] pb-[18px] pr-[24px] ml-[120px] rounded-[8px]"
            style={{
              textShadow:
                "0 0 10px rgba(255, 255, 255, 0.5), 0 0 20px rgba(255, 255, 255, 0.7)",
            }}
          >
            <Link to="/" className="text-white font-medium">
              Главная
            </Link>
            <Link
              to="/panel?model=analysis"
              className="transition-colors font-medium hover:!text-white"
              style={{ color: "rgba(255, 255, 255, 0.6)" }}
            >
              Анализ
            </Link>
            <Link
              to="/panel?model=history"
              className="transition-colors font-medium hover:!text-white"
              style={{ color: "rgba(255, 255, 255, 0.6)" }}
            >
              История
            </Link>
          </div>

          <div className="flex items-center gap-4">
            <Button
              as={Link}
              variant="bordered"
              className="pt-[8px] pb-[8px] pl-[26px] pr-[26px]"
              style={{
                backgroundColor: "transparent",
                borderRadius: "8px",
                border: "1px solid #F59E0B",
                color: "#F59E0B",
                fontWeight: 550,
              }}
              radius="full"
            >
              Войти
            </Button>
            <Button
              as={Link}
              variant="bordered"
              className="text-white pt-[6px] pb-[8px] pl-[11px] pr-[12px]"
              style={{
                border: "1px solid #FFFFFF",
                borderRadius: "8px",
                color: "#FFFFFF",
                fontWeight: 650,
              }}
              radius="full"
            >
              Зарегистрироваться
            </Button>
          </div>
        </div>

        {/* Hero: иконка на горизонте 65%, текст строго ниже */}
        <div className="flex flex-col items-center justify-center h-[calc(100vh-120px)] px-4">
          <div className="max-w-6xl mx-auto flex flex-col items-center">
            <motion.div
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 1, ease: "easeOut" }}
              className="flex justify-center mb-9"
              style={{ marginTop: "28vh" }}
            >
              <div className="relative flex items-center justify-center">
                <div
                  aria-hidden
                  className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 pointer-events-none"
                  style={{
                    width: 320,
                    height: 320,
                    borderRadius: "50%",
                    background:
                      "radial-gradient(circle, rgba(245, 158, 11, 0.4) 0%, rgba(245, 158, 11, 0.15) 35%, rgba(245, 158, 11, 0.05) 55%, transparent 72%)",
                    zIndex: 0,
                  }}
                />
                <div
                  className="relative z-[1] flex items-center justify-center h-[128px] w-[128px]"
                  style={{
                    borderRadius: "28px",
                    background: "rgba(10, 10, 10, 0.6)",
                    border: "1px solid rgba(245, 158, 11, 0.35)",
                  }}
                >
                  <ScanSearch
                    size={72}
                    strokeWidth={1.25}
                    color="#F59E0B"
                    aria-hidden
                  />
                </div>
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 0 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.3 }}
              className="text-center mb-8"
            >
              <h1
                className="text-6xl md:text-7xl mb-4"
                style={{ fontWeight: 400, color: "#FFFFFF" }}
              >
                Диагностика, которая <br /> видит больше
              </h1>
              <p
                className="max-w-3xl mx-auto leading-relaxed mb-6 w-[516px]"
                style={{ fontSize: "16px", color: "#9CA3AF" }}
              >
                Искусственный интеллект для точного анализа дефектов зданий и
                автоматического формирования актов технического осмотра по ГОСТ
                31937-2011
              </p>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.6 }}
              className="flex justify-center"
              style={{ marginTop: "-40px" }}
            >
              <Button
                as={Link}
                to="/panel?model=analysis"
                size="lg"
                className="font-bold text-lg rounded-full hover:scale-105 transition-all duration-300 flex items-center justify-center h-[42px]"
                radius="full"
                style={{
                  padding: "13px 12px",
                  backgroundColor: "#F59E0B",
                  color: "#0A0A0A",
                  border: "1px solid #F59E0B",
                  fontWeight: 500,
                }}
              >
                <ScanSearch size={18} strokeWidth={2} color="#0A0A0A" aria-hidden />
                Начать диагностику
              </Button>
            </motion.div>
          </div>
        </div>
      </div>
    </div>
  );
}
