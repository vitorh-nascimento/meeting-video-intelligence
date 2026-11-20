"""
Transcritor 100% Offline via faster-whisper para reuniões corporativas confidenciais.
Nenhum dado de áudio ou texto sai da máquina local.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from app.services.parser import TranscriptParser, format_timestamp_srt
from app.services.transcribers.base import BaseTranscriber, ProgressCallback


class LocalWhisperTranscriber(BaseTranscriber):
    provider_name = "local_whisper"

    def __init__(
        self,
        model_size: str = "small",
        device: str = "auto",
        compute_type: str = "int8",
    ) -> None:
        self.model_size = model_size or "small"
        self.device = device or "auto"
        self.compute_type = compute_type or "int8"

    def transcribe(
        self,
        media_path: Path,
        *,
        glossary: Optional[List[str]] = None,
        language: Optional[str] = None,
        progress_cb: Optional[ProgressCallback] = None,
    ) -> Dict[str, Any]:
        try:
            from faster_whisper import WhisperModel  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError(
                "Pacote `faster-whisper` não instalado. Para transcrição 100% offline, "
                "instale com `pip install faster-whisper`."
            ) from exc

        if progress_cb:
            progress_cb(f"Carregando modelo Whisper offline ({self.model_size})...", 38)

        model = WhisperModel(self.model_size, device=self.device, compute_type=self.compute_type)
        initial_prompt = None
        if glossary:
            initial_prompt = "Vocabulário técnico: " + ", ".join(glossary[:80])

        lang_code = None
        if language:
            lang_code = language.split("-")[0].lower()

        if progress_cb:
            progress_cb("Transcrevendo áudio localmente com faster-whisper (100% offline)...", 48)

        segments_iter, info = model.transcribe(
            str(media_path),
            language=lang_code,
            initial_prompt=initial_prompt,
            vad_filter=True,
            beam_size=5,
        )

        normalized: List[Dict[str, Any]] = []
        for idx, seg in enumerate(segments_iter, start=1):
            text = (seg.text or "").strip()
            if not text:
                continue
            start_s = float(seg.start)
            end_s = float(seg.end)
            normalized.append(
                {
                    "index": idx,
                    "inicio": format_timestamp_srt(start_s),
                    "fim": format_timestamp_srt(end_s),
                    "start_seconds": round(start_s, 3),
                    "end_seconds": round(end_s, 3),
                    "speaker": None,
                    "texto": text,
                }
            )

        parsed = TranscriptParser._build_payload("srt", normalized)
        parsed["idioma"] = getattr(info, "language", language or "pt")
        return parsed
