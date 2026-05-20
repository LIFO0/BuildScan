# BuildScan

**BuildScan** — веб-приложение для технической диагностики зданий с использованием искусственного интеллекта. Система на основе нейронной сети **YOLOv8** анализирует фотографии строительных конструкций и автоматически выявляет дефекты: трещины, отслоение штукатурки, коррозию, плесень и деформации. По результатам анализа приложение присваивает объекту **категорию технического состояния** согласно российскому стандарту **ГОСТ 31937-2011** и формирует готовый **акт осмотра** в формате PDF.

**Целевая аудитория:** жители, управляющие компании и технические инспекторы.

**Эффект:** сокращение времени первичной диагностики с нескольких недель до **~30 секунд** на снимок.

---

## Возможности

- Детекция дефектов на фото фасадов и несущих стен (YOLOv8)
- Оценка категории состояния по **ГОСТ 31937-2011** (эвристика на основе найденных дефектов)
- Структурированный отчёт: идентификация объекта, описание повреждений, рекомендации
- Пакетная загрузка и история анализов
- Визуализация bounding boxes и метрик по каждому снимку
- Проверка сцены (CLIP): отсечение снимков, не относящихся к зданию
- Веб-интерфейс на React + TypeScript

---

## Архитектура

```
┌─────────────────────┐
│  Frontend (Vite)    │  React + TypeScript, порт 5173
│  frontend-service   │
└──────────┬──────────┘
           │ HTTP /api, WebSocket
┌──────────▼──────────┐
│  Django API         │  Задачи анализа, файлы, история, порт 8000
│  backend-django     │
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│  YOLOv8 Service     │  Детекция + отчёт ГОСТ, порт 8001
│  yolov8-model-service│
└─────────────────────┘
```

Дополнительно в репозитории:

| Компонент | Назначение |
|-----------|------------|
| **auth-service** | JWT-аутентификация (опционально) |
| **annotation-service** | Разметка и аннотации изображений |
| **training/** | Обучение модели на датасете дефектов зданий |

---

## Детектируемые классы дефектов

| Класс | Описание |
|-------|----------|
| `crack_diagonal` | Диагональная трещина |
| `crack_vertical` | Вертикальная трещина |
| `crack_horizontal` | Горизонтальная трещина |
| `crack_hairline` | Волосяная трещина |
| `plaster_peeling` | Отслоение штукатурки |
| `brick_damage` | Разрушение кирпичной кладки |
| `corrosion` | Коррозия металлических элементов |
| `mold` | Плесень и грибок |
| `moisture_stain` | Следы замокания и высолы |
| `concrete_spalling` | Скол бетона / обнажение арматуры |
| `deformation` | Прогиб / деформация конструкции |

Маппинг классов настраивается в `yolov8-model-service/app/services/predictor.py`.

---

## Структура проекта

```
BuildScan/
├── frontend-service/          # UI (React, Vite, HeroUI)
├── backend-django/            # API, задачи, медиа, WebSocket
├── yolov8-model-service/      # YOLOv8 + CLIP + отчёт ГОСТ
├── auth-service/              # Аутентификация
├── annotation-service/        # Сервис аннотаций
├── training/                  # Обучение YOLO (dataset.yaml)
├── models/                    # Веса best.pt
├── tools/launcher/            # Альтернативный лаунчер
├── run.bat                    # Быстрый старт на Windows
└── README.md
```

---

## Быстрый старт (Windows)

### Требования

- **Node.js** 18+ и npm
- **Python 3.14** (`py -3.14`)
- Файл модели: `models/best.pt` (обученная YOLOv8)

### Запуск всех сервисов

```bat
run.bat
```

или:

```bat
run.bat start
```

Откройте в браузере:

| Сервис | URL |
|--------|-----|
| Интерфейс | http://127.0.0.1:5173 |
| API (Django) | http://127.0.0.1:8000/api/ |
| YOLOv8 | http://127.0.0.1:8001/health |

Остановка процессов по портам:

```bat
run.bat stop
```

Запуск отдельного сервиса:

```bat
run.bat frontend
run.bat django
run.bat yolo
```

### Ручной запуск

**Frontend:**

```powershell
cd frontend-service
npm install
npm run dev
```

**Backend (Django):**

```powershell
cd backend-django
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
uvicorn lineguard.asgi:application --host 127.0.0.1 --port 8000
```

**YOLOv8:**

```powershell
cd yolov8-model-service
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:MODEL_PATH = "..\models\best.pt"
$env:PORT = "8001"
python -m app.main
```

Прокси API на фронте: `frontend-service/vite.config.ts` → `http://localhost:8000`.

---

## Обучение модели

Конфигурация датасета: `training/dataset.yaml`.

```bash
cd training
python train_yolo.py
```

Подготовка данных: `prepare_dataset.py`, разметка — `annotation-service`.

После обучения поместите `best.pt` в каталог `models/`.

---

## Переменные окружения (YOLOv8)

| Переменная | Описание |
|------------|----------|
| `MODEL_PATH` | Путь к весам YOLO (по умолчанию `models/best.pt`) |
| `PORT` | Порт сервиса (по умолчанию `8001`) |
| `DISABLE_CLIP_SCENE` | `1` — отключить CLIP-проверку «это здание» |

---

## Технологии

| Слой | Стек |
|------|------|
| Frontend | React 18, TypeScript, Vite, HeroUI, Framer Motion, TanStack Query |
| Backend | Django, Django REST, Channels (WebSocket), SQLite (dev) |
| ML | YOLOv8 (Ultralytics), PyTorch, CLIP (transformers) |
| Инфра | `run.bat`, SQLite, локальные venv |

---

## Troubleshooting

**Модель не найдена**

```powershell
Test-Path models\best.pt
```

**Порты заняты**

```bat
run.bat stop
```

**Ошибки зависимостей YOLO (torch)**

`run.bat` при неудачной установке pinned torch пробует совместимую CPU-сборку автоматически.

---

## Лицензия

Укажите лицензию проекта при публикации.

---

## Авторы

- German Mironchuc
