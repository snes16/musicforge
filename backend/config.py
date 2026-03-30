from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # ACE-Step
    acestep_api_url: str = "http://localhost:8001"
    acestep_api_key: str = "local-dev-key"
    mock_acestep: bool = True

    # Redis / Celery
    redis_url: str = "redis://redis:6379/0"

    # Storage
    audio_output_dir: str = "./audio_output"
    max_audio_size_mb: int = 50

    # GPU
    mock_gpu: bool = True
    gpu_poll_interval: int = 2

    # API
    api_secret_key: str = "change-me-in-production"
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
