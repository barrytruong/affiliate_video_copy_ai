import os
import sys
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = BASE_DIR / "storage"
UPLOADS_DIR = STORAGE_DIR / "uploads"
DOWNLOADS_DIR = STORAGE_DIR / "downloads"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    ollama_host: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5:7b"

    whisper_model_size: str = "medium"
    whisper_device: str = "cuda"
    whisper_compute_type: str = "float16"

    max_video_seconds: int = 600
    max_upload_mb: int = 300


settings = Settings()

UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)


def ensure_cuda_dlls_on_path() -> None:
    """On Windows, ctranslate2 (used by faster-whisper) links against cuBLAS/cuDNN
    but does not bundle them or add them to PATH itself. If those libraries were
    installed via the `nvidia-cublas-cu12` / `nvidia-cudnn-cu12` pip packages,
    their bin directories must be added to PATH before any CUDA model load."""
    if sys.platform != "win32":
        return
    try:
        import nvidia.cublas
        import nvidia.cudnn
    except ImportError:
        return

    extra_dirs = [
        str(Path(next(iter(nvidia.cublas.__path__))) / "bin"),
        str(Path(next(iter(nvidia.cudnn.__path__))) / "bin"),
    ]
    existing = os.environ.get("PATH", "")
    for d in extra_dirs:
        if d not in existing and Path(d).is_dir():
            existing = d + os.pathsep + existing
    os.environ["PATH"] = existing
