# MusicForge (Local Suno-like Demo)

Music generation platform with:
- FastAPI backend (`/api/*`)
- Celery worker + Redis queue
- ACE-Step wrapper service (mock or real)
- React frontend demo UI

## Quick Start

1. Copy env file (already done once):

```bash
cp .env.example .env
```

2. Adjust ports in `.env` if needed:

- `FRONTEND_PORT` (default `3000`)
- `FLOWER_HOST_PORT` (default `5555`)
- `BACKEND_PORT` (default `8000`)
- `ACESTEP_PORT` (default `8001`)

3. Start everything:

```bash
docker compose up --build -d
```

## URLs

Current local defaults from `.env` in this repo:

- Frontend: `http://localhost:3001`
- API docs: `http://localhost:8000/docs`
- Backend health: `http://localhost:8000/health`
- Flower: `http://localhost:5556`
- ACE-Step wrapper: `http://localhost:8001`

## Lyrics Requirement

`POST /api/generate` requires lyrics with song structure tags:
- `[verse]`
- `[chorus]`

Requests without these sections are rejected with `422`.

## Example Request

```json
{
  "prompt": "indie pop, female vocals, dreamy atmosphere",
  "lyrics": "[verse]\nLine 1\nLine 2\n\n[chorus]\nHook line\nHook line",
  "duration": 60,
  "style_preset": "indie_pop"
}
```

## Real GPU / Real ACE-Step

For local UI/backend development without model inference, use mock mode:
- `MOCK_GPU=true`
- `MOCK_ACESTEP=true`

For real inference:
- set `MOCK_ACESTEP=false`
- point `ACESTEP_API_URL` to a real ACE-Step API
- keep worker connected to Redis and mounted output dir

## Stop

```bash
docker compose down
```
