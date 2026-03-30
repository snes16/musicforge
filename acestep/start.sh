#!/bin/bash
set -e

MOCK_ACESTEP="${MOCK_ACESTEP:-true}"
PORT="${PORT:-8001}"

if [ "$MOCK_ACESTEP" = "true" ]; then
  echo "[acestep] Running in MOCK mode on port $PORT"
  # Start a minimal mock FastAPI server
  pip install --quiet fastapi uvicorn 2>/dev/null || true

  python3 - <<'PYEOF'
import os
import uuid
import time
import asyncio
from fastapi import FastAPI
import uvicorn

app = FastAPI(title="ACE-Step Mock API", version="1.5.0-mock")

tasks = {}

@app.get("/health")
def health():
    return {"status": "ok", "model": "acestep-v1.5-mock"}

@app.post("/generate")
async def generate(request: dict):
    task_id = str(uuid.uuid4())
    tasks[task_id] = {"task_id": task_id, "status": "processing", "created_at": time.time()}
    # Simulate async processing
    asyncio.create_task(_process_task(task_id, request))
    return {"task_id": task_id, "status": "processing"}

async def _process_task(task_id: str, request: dict):
    await asyncio.sleep(5)
    tasks[task_id]["status"] = "completed"
    tasks[task_id]["audio_url"] = f"/audio/{task_id}.wav"

@app.get("/tasks/{task_id}")
def get_task(task_id: str):
    if task_id not in tasks:
        return {"task_id": task_id, "status": "not_found"}
    return tasks[task_id]

@app.get("/loras")
def list_loras():
    return [
        {"name": "artist_lora_v1", "description": "Demo LoRA"},
        {"name": "zemfira_lora_v1", "description": "Zemfira style"},
    ]

@app.get("/docs-link")
def docs_link():
    return {"message": "See ACE-Step docs at https://github.com/ACE-Step/ACE-Step"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)
PYEOF

else
  echo "[acestep] Starting real ACE-Step API on port $PORT"
  echo "[acestep] Checkpoints: /app/checkpoints"
  echo "[acestep] LoRA dir: /app/lora"

  # Real ACE-Step startup
  # Requires ACE-Step to be installed: pip install acestep
  # or cloned to /app and run via uv
  if command -v acestep-api &>/dev/null; then
    acestep-api --port "$PORT" --checkpoint-dir /app/checkpoints --lora-dir /app/lora
  else
    uv run acestep-api --port "$PORT" --checkpoint-dir /app/checkpoints --lora-dir /app/lora
  fi
fi
