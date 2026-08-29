import uuid
from dataclasses import dataclass
from pathlib import Path

import av
from fastapi import UploadFile

from app.errors import UnsupportedFormatError, UploadTooLargeError

ALLOWED_EXTENSIONS = {".mp4", ".mov", ".webm", ".mkv", ".m4a", ".mp3"}
_CHUNK_SIZE = 1024 * 1024  # 1 MB


@dataclass
class MediaProbe:
    duration_seconds: float
    has_audio: bool


async def save_upload(file: UploadFile, dest_dir: Path, max_upload_mb: int) -> Path:
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise UnsupportedFormatError(f"Unsupported extension: {ext}")

    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / f"{uuid.uuid4()}{ext}"
    max_bytes = max_upload_mb * 1024 * 1024

    written = 0
    with open(dest_path, "wb") as out:
        while chunk := await file.read(_CHUNK_SIZE):
            written += len(chunk)
            if written > max_bytes:
                out.close()
                dest_path.unlink(missing_ok=True)
                raise UploadTooLargeError(f"Upload exceeds {max_upload_mb}MB")
            out.write(chunk)

    return dest_path


def probe_media(path: Path) -> MediaProbe:
    try:
        with av.open(str(path)) as container:
            duration = float(container.duration or 0) / 1_000_000
            has_audio = len(container.streams.audio) > 0
    except Exception as e:
        raise UnsupportedFormatError(str(e)) from e

    if not has_audio:
        raise UnsupportedFormatError("File has no audio track.")

    return MediaProbe(duration_seconds=duration, has_audio=has_audio)
