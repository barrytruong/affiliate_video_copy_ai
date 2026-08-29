import logging
import shutil
from pathlib import Path

from app.config import DOWNLOADS_DIR, settings
from app.errors import PipelineError, VideoTooLongError
from app.jobs import store
from app.models import JobStatus
from app.ollama_client import check_ollama_health
from app.pipeline import downloader, ingest, scriptwriter, transcriber

logger = logging.getLogger(__name__)


def run_job(job_id: str) -> None:
    job = store.get(job_id)
    if job is None:
        return

    job_download_dir = DOWNLOADS_DIR / job_id
    video_path: Path | None = None
    try:
        if job.source_type == "url":
            store.update(
                job_id,
                status=JobStatus.DOWNLOADING,
                stage_message="Đang tải video từ TikTok...",
            )
            result = downloader.download_tiktok_video(
                job.source, job_download_dir, settings.max_video_seconds
            )
            video_path = result.video_path
        else:
            video_path = Path(job.source)
            store.update(
                job_id,
                status=JobStatus.INGESTING,
                stage_message="Đang kiểm tra video...",
            )
            probe = ingest.probe_media(video_path)
            if probe.duration_seconds > settings.max_video_seconds:
                raise VideoTooLongError(
                    probe.duration_seconds, settings.max_video_seconds
                )

        store.update(
            job_id,
            status=JobStatus.TRANSCRIBING,
            stage_message="Đang chuyển giọng nói thành văn bản...",
        )
        transcript = transcriber.transcribe(
            video_path,
            model_size=settings.whisper_model_size,
            device=settings.whisper_device,
            compute_type=settings.whisper_compute_type,
        )

        check_ollama_health(settings.ollama_host, settings.ollama_model)

        stage_label = "tiếng Anh" if job.target_language == "en" else "tiếng Việt"
        store.update(
            job_id,
            status=JobStatus.WRITING,
            stage_message=f"Đang viết kịch bản {stage_label} tự nhiên...",
        )
        script = scriptwriter.generate_script(
            transcript,
            model=settings.ollama_model,
            base_url=settings.ollama_host,
            target_language=job.target_language,
        )

        store.update(
            job_id,
            status=JobStatus.DONE,
            script=script,
            transcript=transcript,
            stage_message="Hoàn tất!",
        )
    except PipelineError as e:
        store.update(
            job_id,
            status=JobStatus.ERROR,
            error=e.user_message_vi,
            stage_message=e.user_message_vi,
        )
    except Exception:
        logger.exception("Job %s failed with an unexpected error", job_id)
        store.update(
            job_id,
            status=JobStatus.ERROR,
            error="internal_error",
            stage_message="Đã có lỗi xảy ra, vui lòng thử lại.",
        )
    finally:
        shutil.rmtree(job_download_dir, ignore_errors=True)
        if job.source_type == "upload" and video_path is not None:
            video_path.unlink(missing_ok=True)
