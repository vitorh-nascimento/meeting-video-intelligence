"""Rotas de Configurações locais (API Keys, provedores, glossário, categorias e Databricks)."""

from __future__ import annotations

import shutil
from typing import Any, Dict

from fastapi import APIRouter

from app.db import db
from app.schemas import SettingsUpdateRequest
from app.services.media import find_ffmpeg_executable

router = APIRouter(prefix="/api/settings", tags=["Configurações"])


@router.get("")
def get_settings() -> Dict[str, Any]:
    return db.get_settings(masked=True)


@router.put("")
def update_settings(payload: SettingsUpdateRequest) -> Dict[str, Any]:
    return db.update_settings(payload.settings)


@router.get("/capabilities")
def get_capabilities() -> Dict[str, Any]:
    """Informa à UI quais ferramentas opcionais estão disponíveis no ambiente local."""
    def _has_module(mod: str) -> bool:
        try:
            __import__(mod)
            return True
        except Exception:
            return False

    return {
        "ffmpeg_available": bool(find_ffmpeg_executable()),
        "yt_dlp_available": _has_module("yt_dlp"),
        "youtube_transcript_api_available": _has_module("youtube_transcript_api"),
        "faster_whisper_available": _has_module("faster_whisper"),
        "databricks_cli_available": bool(shutil.which("databricks")),
    }
