import logging
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

import imageio_ffmpeg
import yt_dlp

from app.errors import (
    DownloadFailedError,
    InvalidURLError,
    PrivateVideoError,
    VideoTooLongError,
    VideoUnavailableError,
)

logger = logging.getLogger(__name__)

# TikTok's anti-bot challenge is solved probabilistically by yt-dlp (native JS
# challenge solver) — it fails intermittently even for a valid, public video.
# Retrying a few times resolves most of these transient failures.
_CHALLENGE_RETRY_MARKERS = (
    "unable to extract",
    "unexpected response from webpage request",
)
_MAX_ATTEMPTS = 4
_RETRY_DELAY_SECONDS = 2


@dataclass
class DownloadResult:
    video_path: Path
    duration_seconds: float
    title: str


def _ydl_opts(out_dir: Path) -> dict:
    return {
        "ffmpeg_location": imageio_ffmpeg.get_ffmpeg_exe(),
        "noplaylist": True,
        # "best" (not "mp4/best"): some TikTok posts are audio+image slideshows
        # with no video stream at all — we only ever need the audio track for
        # transcription, so any best-available format works.
        "format": "best",
        "quiet": True,
        "no_warnings": True,
        "retries": 3,
        "socket_timeout": 30,
        "outtmpl": str(out_dir / "%(id)s.%(ext)s"),
    }


def _map_download_error(e: Exception) -> Exception:
    msg = str(e).lower()
    if "unsupported url" in msg or "is not a valid url" in msg:
        return InvalidURLError(str(e))
    if "private video" in msg:
        return PrivateVideoError(str(e))
    if "unavailable" in msg or "not available" in msg or "removed" in msg:
        return VideoUnavailableError(str(e))
    return DownloadFailedError(str(e))


def _is_transient_challenge_error(e: Exception) -> bool:
    msg = str(e).lower()
    return any(marker in msg for marker in _CHALLENGE_RETRY_MARKERS)


def _extract_with_retry(ydl: yt_dlp.YoutubeDL, url: str) -> dict:
    last_error: Exception | None = None
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            return ydl.extract_info(url, download=True)
        except yt_dlp.utils.DownloadError as e:
            last_error = e
            if attempt < _MAX_ATTEMPTS and _is_transient_challenge_error(e):
                logger.info(
                    "TikTok bot-check challenge failed (attempt %d/%d), retrying...",
                    attempt,
                    _MAX_ATTEMPTS,
                )
                time.sleep(_RETRY_DELAY_SECONDS)
                continue
            raise
    raise last_error  # pragma: no cover - loop always returns or raises above


def download_tiktok_video(
    url: str, out_dir: Path, max_duration_seconds: int
) -> DownloadResult:
    out_dir.mkdir(parents=True, exist_ok=True)
    opts = _ydl_opts(out_dir)

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = _extract_with_retry(ydl, url)
            video_path = Path(ydl.prepare_filename(info))
    except yt_dlp.utils.DownloadError as e:
        raise _map_download_error(e) from e

    if not video_path.exists():
        candidates = list(out_dir.glob(f"{info.get('id', '')}.*"))
        if not candidates:
            raise DownloadFailedError("Downloaded file not found on disk.")
        video_path = candidates[0]

    duration = float(info.get("duration") or 0)
    if duration and duration > max_duration_seconds:
        video_path.unlink(missing_ok=True)
        raise VideoTooLongError(duration, max_duration_seconds)

    return DownloadResult(
        video_path=video_path,
        duration_seconds=duration,
        title=info.get("title") or str(uuid.uuid4()),
    )
