"""
Ponto de entrada da API REST FastAPI — Meeting & Video Intelligence.
Execução local:
  uvicorn app.main:app --app-dir backend --reload --port 8000
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.config import PROJECT_ROOT, get_cors_origins
from app.routers import documents, ingest, settings

app = FastAPI(
    title="Meeting & Video Intelligence API",
    version=__version__,
    description=(
        "Plataforma standalone de ingestão, transcrição multimodal (Gemini / Whisper offline), "
        "extração estruturada via LLM e sincronização com Databricks Lakehouse."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest.router)
app.include_router(documents.router)
app.include_router(settings.router)


@app.get("/api/health", tags=["Sistema"])
def health_check() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


# Serve o build do frontend automaticamente caso exista `frontend/dist`
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"
if FRONTEND_DIST.exists() and (FRONTEND_DIST / "index.html").exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")
