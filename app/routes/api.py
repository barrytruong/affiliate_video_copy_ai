from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import PlainTextResponse

from app.config import UPLOADS_DIR, settings
from app.errors import PipelineError
from app.jobs import store, submit_job
from app.models import HealthResponse, JobCreateResponse, JobStatusResponse
from app.ollama_client import check_ollama_health
from app.pipeline import ingest
from app.pipeline.pipeline import run_job

router = APIRouter(prefix="/api")


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    try:
        check_ollama_health(settings.ollama_host, settings.ollama_model)
        return HealthResponse(
            ollama_ok=True,
            model_ok=True,
            ollama_model=settings.ollama_model,
            whisper_device=settings.whisper_device,
        )
    except PipelineError as e:
        return HealthResponse(
            ollama_ok=False,
            model_ok=False,
            ollama_model=settings.ollama_model,
            whisper_device=settings.whisper_device,
            detail=e.user_message_vi,
        )


@router.post("/jobs", response_model=JobCreateResponse)
async def create_job(
    url: str | None = Form(None),
    file: UploadFile | None = File(None),
    language: str = Form("en"),
) -> JobCreateResponse:
    has_url = bool(url and url.strip())
    has_file = file is not None and bool(file.filename)

    if has_url == has_file:
        raise HTTPException(
            status_code=400,
            detail="Vui lòng chỉ chọn một trong hai: dán link TikTok hoặc tải file lên.",
        )

    if language not in ("en", "vi"):
        raise HTTPException(status_code=400, detail="Ngôn ngữ không hợp lệ.")

    if has_url:
        job = store.create(source_type="url", source=url.strip(), target_language=language)
    else:
        try:
            saved_path = await ingest.save_upload(file, UPLOADS_DIR, settings.max_upload_mb)
        except PipelineError as e:
            raise HTTPException(status_code=400, detail=e.user_message_vi) from e
        job = store.create(source_type="upload", source=str(saved_path), target_language=language)

    submit_job(job.id, run_job)
    return JobCreateResponse(job_id=job.id)


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
def get_job(job_id: str) -> JobStatusResponse:
    job = store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy công việc này.")
    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        stage_message=job.stage_message,
        script=job.script,
        error=job.error,
    )


@router.get("/jobs/{job_id}/script")
def download_script(job_id: str) -> PlainTextResponse:
    job = store.get(job_id)
    if job is None or job.script is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy kịch bản.")
    return PlainTextResponse(
        job.script,
        headers={"Content-Disposition": f'attachment; filename="script-{job_id}.txt"'},
    )
