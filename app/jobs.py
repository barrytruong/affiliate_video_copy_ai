import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Callable

from app.models import Job, JobStatus


class JobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()

    def create(self, source_type: str, source: str, target_language: str = "en") -> Job:
        job = Job(
            id=str(uuid.uuid4()),
            source_type=source_type,
            source=source,
            target_language=target_language,
        )
        with self._lock:
            self._jobs[job.id] = job
        return job

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def update(self, job_id: str, **fields) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            for key, value in fields.items():
                setattr(job, key, value)
            job.updated_at = datetime.now()


# Single worker: Whisper and Ollama both use the same local GPU, and this is a
# single-user local tool, so jobs are processed one at a time rather than in
# parallel (avoids VRAM contention/OOM for no real benefit).
_executor = ThreadPoolExecutor(max_workers=1)

store = JobStore()


def submit_job(job_id: str, run_fn: Callable[[str], None]) -> None:
    _executor.submit(run_fn, job_id)
