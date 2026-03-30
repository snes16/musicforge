import subprocess
import json
import random
import time
from typing import List, Optional
from config import settings
from schemas.worker import WorkerInfo, WorkerStatus


class MockGPUManager:
    """Fake GPU manager for development without actual GPU hardware."""

    def __init__(self):
        self._workers = [
            {
                "id": "worker-gpu0",
                "gpu": "RTX 5070 (Mock)",
                "vram_total": 16384,
                "vram_used": 0,
                "status": WorkerStatus.idle,
                "tasks_completed": 0,
                "temperature": 35.0,
                "current_task": None,
            }
        ]
        self._task_assignments: dict = {}

    def get_all_stats(self) -> List[WorkerInfo]:
        workers = []
        for w in self._workers:
            # Simulate some random variation
            w["vram_used"] = random.randint(1000, 4000) if w["status"] != WorkerStatus.idle else random.randint(500, 1200)
            w["temperature"] = round(random.uniform(32.0, 75.0), 1)
            workers.append(WorkerInfo(**w))
        return workers

    def get_available_worker(self) -> Optional[WorkerInfo]:
        workers = self.get_all_stats()
        idle_workers = [w for w in workers if w.status == WorkerStatus.idle]
        if idle_workers:
            return idle_workers[0]
        # Pick worker with lowest VRAM usage
        if workers:
            return min(workers, key=lambda w: w.vram_used)
        return None

    def mark_busy(self, worker_id: str, task_id: str):
        for w in self._workers:
            if w["id"] == worker_id:
                w["status"] = WorkerStatus.busy
                w["current_task"] = task_id
                self._task_assignments[task_id] = worker_id
                break

    def mark_idle(self, worker_id: str):
        for w in self._workers:
            if w["id"] == worker_id:
                w["status"] = WorkerStatus.idle
                w["current_task"] = None
                w["tasks_completed"] = w.get("tasks_completed", 0) + 1
                break


class RealGPUManager:
    """Real GPU manager using nvidia-smi."""

    def get_all_stats(self) -> List[WorkerInfo]:
        try:
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=name,memory.total,memory.used,temperature.gpu,utilization.gpu",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            workers = []
            for i, line in enumerate(result.stdout.strip().splitlines()):
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 4:
                    name, mem_total, mem_used, temp = parts[:4]
                    vram_total = int(mem_total)
                    vram_used = int(mem_used)
                    usage_ratio = vram_used / vram_total if vram_total > 0 else 0
                    if usage_ratio > 0.8:
                        status = WorkerStatus.busy
                    else:
                        status = WorkerStatus.idle
                    workers.append(
                        WorkerInfo(
                            id=f"worker-gpu{i}",
                            gpu=name,
                            vram_total=vram_total,
                            vram_used=vram_used,
                            status=status,
                            tasks_completed=0,
                            temperature=float(temp),
                        )
                    )
            return workers
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            return []

    def get_available_worker(self) -> Optional[WorkerInfo]:
        workers = self.get_all_stats()
        if not workers:
            return None
        idle_workers = [w for w in workers if w.status == WorkerStatus.idle]
        if idle_workers:
            return min(idle_workers, key=lambda w: w.vram_used)
        return min(workers, key=lambda w: w.vram_used)

    def mark_busy(self, worker_id: str, task_id: str):
        pass  # No state in real mode; rely on nvidia-smi polling

    def mark_idle(self, worker_id: str):
        pass


def get_gpu_manager():
    if settings.mock_gpu:
        return MockGPUManager()
    return RealGPUManager()


gpu_manager = get_gpu_manager()
