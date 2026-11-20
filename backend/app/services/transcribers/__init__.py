"""Provider Pattern para motores de transcrição de áudio/vídeo."""

from __future__ import annotations

from typing import Any, Dict

from app.services.transcribers.base import BaseTranscriber
from app.services.transcribers.gemini import GeminiTranscriber
from app.services.transcribers.whisper_local import LocalWhisperTranscriber


def get_transcriber(settings: Dict[str, Any]) -> BaseTranscriber:
    provider = str(settings.get("transcriber_provider", "gemini")).strip().lower()
    if provider == "local_whisper":
        return LocalWhisperTranscriber(
            model_size=str(settings.get("whisper_model_size", "small")),
            device=str(settings.get("whisper_device", "auto")),
            compute_type=str(settings.get("whisper_compute_type", "int8")),
        )
    return GeminiTranscriber(
        api_key=str(settings.get("gemini_api_key", "")).strip(),
        model=str(settings.get("gemini_transcription_model", "gemini-2.5-flash")).strip(),
        chunk_minutes=int(settings.get("audio_chunk_minutes", 20) or 20),
    )


__all__ = [
    "BaseTranscriber",
    "GeminiTranscriber",
    "LocalWhisperTranscriber",
    "get_transcriber",
]
