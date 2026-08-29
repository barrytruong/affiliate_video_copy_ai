import logging
from pathlib import Path

from app.config import ensure_cuda_dlls_on_path
from app.errors import NoSpeechDetectedError
from app.models import TranscriptResult, TranscriptSegment

logger = logging.getLogger(__name__)

ensure_cuda_dlls_on_path()

_model_cache: dict[tuple[str, str, str], "WhisperModel"] = {}
_cuda_unavailable = False


def _load_model(model_size: str, device: str, compute_type: str):
    from faster_whisper import WhisperModel

    key = (model_size, device, compute_type)
    if key not in _model_cache:
        _model_cache[key] = WhisperModel(
            model_size, device=device, compute_type=compute_type
        )
    return _model_cache[key]


def get_model(model_size: str, device: str, compute_type: str):
    global _cuda_unavailable

    if device == "cuda" and not _cuda_unavailable:
        try:
            return _load_model(model_size, "cuda", compute_type)
        except Exception:
            logger.warning(
                "CUDA unavailable for faster-whisper, falling back to CPU.",
                exc_info=True,
            )
            _cuda_unavailable = True

    return _load_model(model_size, "cpu", "int8")


def transcribe(
    media_path: Path,
    model_size: str = "medium",
    device: str = "cuda",
    compute_type: str = "float16",
) -> TranscriptResult:
    model = get_model(model_size, device, compute_type)

    raw_segments, info = model.transcribe(
        str(media_path),
        beam_size=5,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 500},
    )

    segments = [
        TranscriptSegment(start=s.start, end=s.end, text=s.text.strip())
        for s in raw_segments
    ]
    full_text = " ".join(s.text for s in segments).strip()

    if not full_text:
        raise NoSpeechDetectedError()

    return TranscriptResult(
        language=info.language,
        language_probability=info.language_probability,
        duration=info.duration,
        segments=segments,
        full_text=full_text,
    )
