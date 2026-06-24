from __future__ import annotations

import re
import uuid
from pathlib import Path
from typing import List, Literal

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile

from app.core.config import settings
from app.models.schemas import UploadJob, UploadResponse
from app.services.container import ingestion_service, job_store
from app.services.identity import now_utc
from app.services.ingestion_service import save_upload_file

router = APIRouter(prefix="/uploads", tags=["uploads"])


def safe_filename(filename: str) -> str:
    name = Path(filename or "upload").name
    name = re.sub(r"[^\w.\-\u4e00-\u9fff()（）]+", "_", name)
    return name[:180] or "upload"


@router.post("", response_model=UploadResponse)
def upload_docs(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    mode: Literal["incremental", "rebuild"] = "incremental",
) -> UploadResponse:
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")
    job_id = "upload_" + now_utc().strftime("%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:8]
    job_dir = settings.upload_dir / job_id
    saved_paths: list[Path] = []
    for item in files:
        extension = Path(item.filename or "").suffix.lower()
        if extension not in {".dts", ".json"}:
            raise HTTPException(status_code=400, detail=f"Unsupported file extension: {extension}")
        destination = job_dir / safe_filename(item.filename or f"file{extension}")
        save_upload_file(item.file, destination)
        saved_paths.append(destination)

    job = UploadJob(job_id=job_id, status="queued", total_files=len(saved_paths), mode=mode)
    job_store.create(job)
    background_tasks.add_task(ingestion_service.process_files, job_id, saved_paths, mode)
    return UploadResponse(job_id=job_id, status=job.status, total_files=job.total_files)


@router.get("/{job_id}", response_model=UploadJob)
def get_upload_job(job_id: str) -> UploadJob:
    job = job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Upload job not found")
    return job


@router.get("", response_model=list[UploadJob])
def list_upload_jobs(limit: int = 20) -> list[UploadJob]:
    return job_store.list_recent(limit=limit)
