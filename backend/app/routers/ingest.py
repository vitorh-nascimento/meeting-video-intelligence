"""
Rotas de Ingestão Unificada (Arquivo de mídia/transcrição, URL de vídeo, Texto colado)
e consulta de progresso de jobs assíncronos.
"""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile

from app.config import get_uploads_dir
from app.db import db
from app.schemas import IngestTextRequest, IngestUrlRequest, JobResponse
from app.services.pipeline import pipeline

router = APIRouter(prefix="/api", tags=["Ingestão & Jobs"])


def _run_file_job(
    job_id: str,
    saved_path: Path,
    original_filename: str,
    title: Optional[str],
    template: str,
    language: Optional[str],
    push_to_databricks: bool,
    run_databricks_pipeline: bool,
) -> None:
    try:
        pipeline.process_file(
            file_path=saved_path,
            original_filename=original_filename,
            title=title,
            template=template,
            language=language,
            push_to_databricks=push_to_databricks,
            run_databricks_pipeline=run_databricks_pipeline,
            job_id=job_id,
        )
    except Exception:
        # O erro já foi gravado no job dentro do pipeline
        pass
    finally:
        # Remove arquivo bruto temporário de upload após processamento para economizar disco
        try:
            saved_path.unlink(missing_ok=True)
        except Exception:
            pass


def _run_url_job(job_id: str, payload: IngestUrlRequest) -> None:
    try:
        pipeline.process_url(
            url=payload.url,
            title=payload.title,
            template=payload.template,
            force_ai_transcription=payload.force_ai_transcription,
            language=payload.language,
            push_to_databricks=payload.push_to_databricks,
            run_databricks_pipeline=payload.run_databricks_pipeline,
            job_id=job_id,
        )
    except Exception:
        pass


def _run_text_job(job_id: str, payload: IngestTextRequest) -> None:
    try:
        pipeline.process_text(
            text=payload.text,
            title=payload.title,
            format_hint=payload.format_hint,
            template=payload.template,
            language=payload.language,
            job_id=job_id,
        )
    except Exception:
        pass


@router.post("/ingest/file", response_model=JobResponse)
async def ingest_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: Optional[str] = Form(default=None),
    template: str = Form(default="Reunião Corporativa"),
    language: Optional[str] = Form(default=None),
    push_to_databricks: bool = Form(default=False),
    run_databricks_pipeline: bool = Form(default=False),
) -> JobResponse:
    original_name = file.filename or "upload.txt"
    ext = Path(original_name).suffix.lower()
    job_id = str(uuid.uuid4())
    dest_path = get_uploads_dir() / f"{job_id}{ext}"

    with open(dest_path, "wb") as out:
        shutil.copyfileobj(file.file, out)

    resolved_title = (title or Path(original_name).stem.replace("_", " ")).strip()
    job = db.create_job(
        job_id=job_id,
        source_type="file",
        source_ref=original_name,
        title=resolved_title,
        template=template,
    )

    background_tasks.add_task(
        _run_file_job,
        job_id,
        dest_path,
        original_name,
        title,
        template,
        language,
        push_to_databricks,
        run_databricks_pipeline,
    )
    return JobResponse(**job)


@router.post("/ingest/url", response_model=JobResponse)
async def ingest_url(payload: IngestUrlRequest, background_tasks: BackgroundTasks) -> JobResponse:
    job_id = str(uuid.uuid4())
    job = db.create_job(
        job_id=job_id,
        source_type="url",
        source_ref=payload.url,
        title=payload.title or payload.url,
        template=payload.template,
    )
    background_tasks.add_task(_run_url_job, job_id, payload)
    return JobResponse(**job)


@router.post("/ingest/text", response_model=JobResponse)
async def ingest_text(payload: IngestTextRequest, background_tasks: BackgroundTasks) -> JobResponse:
    job_id = str(uuid.uuid4())
    job = db.create_job(
        job_id=job_id,
        source_type="text",
        source_ref="texto_colado",
        title=payload.title,
        template=payload.template,
    )
    background_tasks.add_task(_run_text_job, job_id, payload)
    return JobResponse(**job)


@router.get("/jobs", response_model=List[JobResponse])
def list_jobs(limit: int = 20) -> List[JobResponse]:
    return [JobResponse(**j) for j in db.list_jobs(limit=limit)]


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str) -> JobResponse:
    job = db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado.")
    return JobResponse(**job)
