# MusicForge — AI Music Generation Platform
## Claude Code Project Prompt

---

## 🎯 Цель проекта

Локальная платформа для генерации музыки на базе **ACE-Step v1.5** с REST API, веб-интерфейсом и архитектурой для GPU farm интеграции. Проект демонстрирует fine-tuning под стиль конкретного исполнителя и динамическое распределение задач по GPU воркерам.

---

## 📁 Структура проекта

```
musicforge/
├── CLAUDE.md                  # этот файл
├── docker-compose.yml         # оркестрация всех сервисов
├── .env.example               # переменные окружения
├── README.md                  # документация
│
├── backend/                   # FastAPI сервер
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                # точка входа, монтирование роутеров
│   ├── config.py              # настройки через pydantic-settings
│   │
│   ├── api/
│   │   ├── routes/
│   │   │   ├── generate.py    # POST /generate, GET /generate/{task_id}
│   │   │   ├── tasks.py       # GET /tasks, DELETE /tasks/{task_id}
│   │   │   ├── models.py      # GET /models, GET /models/{id}/status
│   │   │   └── health.py      # GET /health, GET /metrics
│   │   └── middleware.py      # CORS, logging, error handling
│   │
│   ├── core/
│   │   ├── acestep_client.py  # HTTP клиент к ACE-Step API (localhost:8001)
│   │   ├── queue.py           # Celery app + task definitions
│   │   ├── gpu_manager.py     # менеджер GPU воркеров (мок + реальный)
│   │   └── storage.py         # сохранение аудио файлов, метаданных
│   │
│   └── schemas/
│       ├── generate.py        # GenerateRequest, GenerateResponse
│       ├── task.py            # TaskStatus, TaskResult
│       └── worker.py          # WorkerInfo, GPUStats
│
├── worker/                    # Celery воркер (отдельный контейнер)
│   ├── Dockerfile
│   ├── requirements.txt
│   └── tasks.py               # generate_music task
│
├── acestep/                   # ACE-Step обёртка
│   ├── Dockerfile             # на базе ACE-Step-1.5
│   ├── start.sh               # запуск acestep-api на порту 8001
│   └── lora/                  # обученные LoRA адаптеры
│       └── README.md          # как добавить свой LoRA
│
├── frontend/                  # React + Vite
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.ts
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── components/
│       │   ├── GenerateForm/  # форма генерации (промпт, жанр, длина, LoRA)
│       │   ├── AudioPlayer/   # кастомный плеер с визуализацией
│       │   ├── TaskQueue/     # лента задач и их статусы
│       │   ├── GPUDashboard/  # статус GPU воркеров (realtime)
│       │   └── TrackHistory/  # история генераций
│       ├── hooks/
│       │   ├── useGenerate.ts # мутация + polling статуса
│       │   ├── useGPUStats.ts # WebSocket или polling метрик
│       │   └── useAudio.ts    # Web Audio API визуализация
│       ├── stores/
│       │   └── musicStore.ts  # Zustand store
│       └── api/
│           └── client.ts      # axios инстанс с типами
│
├── scripts/
│   ├── train_lora.sh          # запуск fine-tuning через ACE-Step
│   ├── download_models.sh     # предзагрузка весов
│   └── seed_artist.sh         # подготовка датасета исполнителя
│
└── docs/
    ├── api.md                 # REST API документация
    ├── gpu_farm_arch.md       # архитектура GPU farm
    └── lora_training.md       # гайд по fine-tuning
```

---

## 🔧 Технический стек

| Слой | Технология |
|------|-----------|
| Модель | ACE-Step v1.5 (локально, порт 8001) |
| API | FastAPI + Uvicorn |
| Очередь | Celery + Redis |
| Хранилище | локальная FS + SQLite (через SQLModel) |
| Фронт | React + Vite + TypeScript + TailwindCSS |
| Состояние | Zustand |
| HTTP клиент | Axios + React Query |
| Аудио | Web Audio API |
| Деплой | Docker Compose |

---

## 📋 Задачи для реализации (в приоритете)

### 1. ACE-Step обёртка (`/acestep`)
- Dockerfile на базе Python 3.11
- `start.sh` запускает `uv run acestep-api --port 8001`
- volume mount для `./checkpoints` (модели уже скачаны локально)
- volume mount для `./acestep/lora` (LoRA адаптеры)
- healthcheck на `/health`

### 2. Backend API (`/backend`)

**`POST /api/generate`**
```json
// Request
{
  "prompt": "indie pop, female vocals, dreamy atmosphere",
  "lyrics": "[verse]\nOptional lyrics here\n[chorus]\nChorus text",
  "duration": 60,
  "lora_name": "artist_lora_v1",  // null = base model
  "style_preset": "indie_pop"
}

// Response (async — возвращает task_id сразу)
{
  "task_id": "uuid",
  "status": "queued",
  "estimated_seconds": 15,
  "position_in_queue": 1
}
```

**`GET /api/generate/{task_id}`**
```json
{
  "task_id": "uuid",
  "status": "completed",  // queued | processing | completed | failed
  "audio_url": "/audio/uuid.wav",
  "duration": 60,
  "metadata": {
    "model": "acestep-v15-turbo",
    "lora": "artist_lora_v1",
    "generation_time": 9.2,
    "gpu": "RTX 5070"
  }
}
```

**`GET /api/workers`** — статус GPU воркеров
```json
{
  "workers": [
    {
      "id": "worker-gpu0",
      "gpu": "RTX 5070",
      "vram_total": 16384,
      "vram_used": 3800,
      "status": "idle",  // idle | busy | offline
      "tasks_completed": 42
    }
  ]
}
```

**`GET /api/models`** — список доступных LoRA и пресетов

**`GET /health`** — healthcheck

### 3. Celery воркер (`/worker`)
- Подключается к ACE-Step API через HTTP
- Обновляет статус задачи в Redis
- Сохраняет аудио в `./audio_output/`
- Эмитирует прогресс (0% → 50% → 100%)

### 4. GPU Manager (`core/gpu_manager.py`)
- Абстракция над воркерами
- `get_available_worker()` — выбирает воркер с минимальной нагрузкой
- `get_all_stats()` — VRAM usage, температура, очередь
- Моковый режим (`MOCK_GPU=true`) для разработки без GPU
- Реальный режим через `nvidia-smi` + subprocess

### 5. Frontend

**Дизайн**: тёмная тема, аудио-волновая эстетика. Вдохновение — профессиональные DAW (dark, precise, technical). Цвета: почти-чёрный фон `#0a0a0f`, акцент — электрический синий `#3b82f6` или фиолетовый `#8b5cf6`. Шрифт для UI — что-то техническое (JetBrains Mono для лейблов, современный sans для текста).

**Главная страница:**
- Большая форма генерации слева (промпт, лирика, жанр, длина, выбор LoRA)
- Кастомный аудио плеер с визуализацией waveform (Web Audio API + Canvas)
- Лента задач справа с realtime статусами
- GPU Dashboard внизу — карточки воркеров с VRAM bar

**Компоненты:**
- `GenerateForm` — textarea для промпта и лирики, sliders, select для LoRA
- `AudioPlayer` — кастомный плеер: waveform визуализация, play/pause/seek, download
- `TaskCard` — статус задачи, прогресс бар, время генерации
- `GPUCard` — имя GPU, VRAM usage bar, статус (idle/busy/offline)

### 6. LoRA Fine-tuning скрипт (`scripts/train_lora.sh`)
```bash
# Использование:
# ./scripts/train_lora.sh --artist "Земфира" --songs-dir ./data/zemfira --output lora_zemfira_v1
```
- Принимает директорию с mp3/wav треками
- Запускает препроцессинг через ACE-Step
- Обучает LoRA (~1 час на RTX 5070, 8 треков)
- Сохраняет в `./acestep/lora/`

---

## 🌐 GPU Farm архитектура (документировать, частично реализовать)

```
                    ┌─────────────────────┐
                    │   FastAPI Gateway   │
                    │   (порт 8000)       │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │    Redis Queue      │
                    │  (Celery broker)    │
                    └──────┬──────┬───────┘
                           │      │
              ┌────────────▼──┐ ┌─▼────────────┐
              │  Worker GPU0  │ │  Worker GPU1  │
              │  RTX 5070     │ │  RTX 5060 Ti  │
              │  ACE-Step :8001│ │  ACE-Step :8002│
              └───────────────┘ └───────────────┘
```

- Каждый воркер — отдельный Docker контейнер с `CUDA_VISIBLE_DEVICES`
- Задачи роутятся в очередь `gpu0` или `gpu1` в зависимости от нагрузки
- GPU Manager опрашивает воркеры каждые 2 сек
- При добавлении новой GPU — добавить контейнер в docker-compose + воркер

---

## ⚙️ Переменные окружения (`.env`)

```env
# ACE-Step
ACESTEP_API_URL=http://acestep:8001
ACESTEP_API_KEY=local-dev-key

# Redis / Celery
REDIS_URL=redis://redis:6379/0

# Storage
AUDIO_OUTPUT_DIR=./audio_output
MAX_AUDIO_SIZE_MB=50

# GPU
MOCK_GPU=false               # true для разработки без GPU
GPU_POLL_INTERVAL=2          # секунды

# API
API_SECRET_KEY=change-me-in-production
CORS_ORIGINS=http://localhost:3000

# Frontend
VITE_API_URL=http://localhost:8000
```

---

## 🚀 Запуск

```bash
# 1. Клонировать ACE-Step и скачать модели
git clone https://github.com/ACE-Step/ACE-Step-1.5.git
cd ACE-Step-1.5 && uv run acestep-download && cd ..

# 2. Запустить платформу
docker-compose up --build

# 3. Открыть
# Фронт:     http://localhost:3000
# API docs:  http://localhost:8000/docs
# ACE-Step:  http://localhost:8001
# Flower:    http://localhost:5555  (мониторинг Celery)
```

---

## ✅ Definition of Done

- [ ] `POST /api/generate` принимает запрос и возвращает task_id
- [ ] Polling `GET /api/generate/{task_id}` показывает прогресс
- [ ] Аудио доступно по URL после завершения
- [ ] Фронт отображает форму, плеер, очередь задач
- [ ] GPU Dashboard показывает статус воркеров
- [ ] Swagger доки доступны на `/docs`
- [ ] LoRA скрипт задокументирован
- [ ] docker-compose поднимает всё одной командой
- [ ] README с архитектурой GPU farm

---

## 📌 Приоритет реализации

1. `docker-compose.yml` + базовая конфигурация
2. `backend/main.py` + роутеры generate, health
3. `core/acestep_client.py` — HTTP клиент к ACE-Step
4. `core/queue.py` + `worker/tasks.py` — Celery
5. `core/gpu_manager.py` — моковый + реальный режим
6. Фронт — GenerateForm + AudioPlayer + TaskQueue
7. GPUDashboard + история
8. Скрипты fine-tuning + документация

---

## 🗒️ Заметки

- ACE-Step API уже имеет встроенную документацию на `:8001/docs` — не дублировать, линковать
- Для мока GPU использовать `MOCK_GPU=true`, чтобы разрабатывать фронт без запущенной модели
- LoRA fine-tuning запускается отдельно через скрипт, не через API (слишком долго для HTTP request)
- Аудио файлы отдавать через FastAPI `FileResponse` или nginx static в проде
- WebSocket для realtime статуса задач — опционально, polling каждые 2 сек достаточно
