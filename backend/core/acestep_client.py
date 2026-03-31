import httpx
import asyncio
import uuid
import os
from typing import Optional, Dict, Any
from config import settings


class ACEStepClient:
    """Async HTTP client to ACE-Step API."""

    def __init__(self):
        self.base_url = settings.acestep_api_url
        self.api_key = settings.acestep_api_key
        self.mock_mode = settings.mock_acestep
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=300.0,
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def health_check(self) -> Dict[str, Any]:
        if self.mock_mode:
            return {"status": "ok", "model": "mock-acestep-v1.5"}
        client = await self._get_client()
        resp = await client.get("/health")
        resp.raise_for_status()
        return resp.json()

    async def generate(
        self,
        prompt: str,
        lyrics: Optional[str] = None,
        duration: int = 60,
        lora_name: Optional[str] = None,
        style_preset: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Submit a generation task via POST /release_task, returns {task_id}."""
        if self.mock_mode:
            task_id = str(uuid.uuid4())
            return {"task_id": task_id}

        client = await self._get_client()
        payload: Dict[str, Any] = {
            "prompt": prompt,
            "duration": duration,
        }
        if lyrics:
            payload["lyrics"] = lyrics
        if lora_name:
            payload["lora_name"] = lora_name

        resp = await client.post("/release_task", json=payload)
        resp.raise_for_status()
        return resp.json()  # {"task_id": "uuid"}

    async def get_task_status(self, acestep_task_id: str) -> Dict[str, Any]:
        """Poll via POST /query_result.

        Returns normalised dict:
          {"task_id": ..., "status": 0|1|2, "audio_path": str|None}

        ACE-Step statuses: 0=pending, 1=success, 2=failed
        """
        if self.mock_mode:
            return {"task_id": acestep_task_id, "status": 1, "audio_path": None}

        client = await self._get_client()
        resp = await client.post("/query_result", json={"task_id_list": [acestep_task_id]})
        resp.raise_for_status()
        data = resp.json()

        # data = {"data": [{"task_id": ..., "status": 0|1|2, "result": "<json str>"}]}
        items = data.get("data", [])
        if not items:
            return {"task_id": acestep_task_id, "status": 0, "audio_path": None}

        item = items[0]
        audio_path: Optional[str] = None
        if item.get("status") == 1:
            import json as _json
            try:
                result = _json.loads(item.get("result", "{}"))
                audio_path = result.get("file")
            except (ValueError, TypeError):
                audio_path = item.get("result")

        return {
            "task_id": item.get("task_id", acestep_task_id),
            "status": item.get("status", 0),
            "audio_path": audio_path,
        }

    async def download_audio(self, audio_path: str, dest_path: str) -> str:
        """Copy/download audio from ACE-Step host to local dest_path.

        audio_path is the file path returned by query_result (absolute on the
        ACE-Step host). We try GET /audio?path=<audio_path> first; if ACE-Step
        serves the file directly via that route, great. Otherwise the worker
        can map the path via a shared volume.
        """
        if self.mock_mode:
            _write_mock_wav(dest_path)
            return dest_path

        client = await self._get_client()
        resp = await client.get("/audio", params={"path": audio_path})
        resp.raise_for_status()
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        with open(dest_path, "wb") as f:
            f.write(resp.content)
        return dest_path

    async def list_loras(self):
        if self.mock_mode:
            return [
                {"name": "artist_lora_v1", "description": "Demo LoRA adapter"},
                {"name": "zemfira_lora_v1", "description": "Zemfira style"},
            ]
        client = await self._get_client()
        resp = await client.get("/loras")
        resp.raise_for_status()
        return resp.json()


def _write_mock_wav(dest_path: str, duration_seconds: int = 5, sample_rate: int = 44100):
    """Write a minimal silent WAV file for mock/dev mode."""
    import struct
    import math

    num_samples = sample_rate * duration_seconds
    num_channels = 2
    bits_per_sample = 16
    byte_rate = sample_rate * num_channels * bits_per_sample // 8
    block_align = num_channels * bits_per_sample // 8
    data_size = num_samples * block_align
    chunk_size = 36 + data_size

    os.makedirs(os.path.dirname(dest_path), exist_ok=True)

    with open(dest_path, "wb") as f:
        # RIFF header
        f.write(b"RIFF")
        f.write(struct.pack("<I", chunk_size))
        f.write(b"WAVE")
        # fmt sub-chunk
        f.write(b"fmt ")
        f.write(struct.pack("<I", 16))  # sub-chunk size
        f.write(struct.pack("<H", 1))   # PCM
        f.write(struct.pack("<H", num_channels))
        f.write(struct.pack("<I", sample_rate))
        f.write(struct.pack("<I", byte_rate))
        f.write(struct.pack("<H", block_align))
        f.write(struct.pack("<H", bits_per_sample))
        # data sub-chunk
        f.write(b"data")
        f.write(struct.pack("<I", data_size))
        # Generate a simple sine wave tone instead of silence
        for i in range(num_samples):
            val = int(32767 * 0.1 * math.sin(2 * math.pi * 440 * i / sample_rate))
            sample = struct.pack("<h", val)
            f.write(sample * num_channels)


# Singleton
acestep_client = ACEStepClient()
