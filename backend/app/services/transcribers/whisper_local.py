"""
Transcritor 100% Offline via faster-whisper para reuniões corporativas confidenciais
e gravações longas (> 1h / > 2h) com progresso em tempo real e filtro de silêncio (VAD).
Decodifica o áudio diretamente via ffmpeg (16 kHz mono float32) para evitar incompatibilidades
com versões recentes do PyAV (ex.: `av>=14` sem argumento `metadata_errors`) e suportar
qualquer formato (.mp4, .mkv, .m4a, .webm, .opus, .mp3, .wav).
Nenhum dado de áudio ou texto sai da máquina local.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from app.services.media import find_ffmpeg_executable
from app.services.parser import TranscriptParser, format_timestamp_srt
from app.services.transcribers.base import BaseTranscriber, ProgressCallback


def _decode_audio_to_16k_float32(media_path: Path) -> Union[Any, str]:
    """
    Decodifica áudio/vídeo para array NumPy float32 mono 16 kHz via ffmpeg.
    Se ffmpeg não estiver disponível, faz fallback para o caminho do arquivo.
    """
    ffmpeg = find_ffmpeg_executable()
    if not ffmpeg:
        return str(media_path)

    import numpy as np

    cmd = [
        ffmpeg,
        "-nostdin",
        "-threads",
        "0",
        "-i",
        str(media_path),
        "-f",
        "s16le",
        "-ac",
        "1",
        "-acodec",
        "pcm_s16le",
        "-ar",
        "16000",
        "-",
    ]
    res = subprocess.run(cmd, capture_output=True)
    if res.returncode != 0 or not res.stdout:
        stderr_tail = (res.stderr or b"").decode("utf-8", errors="replace")[-400:]
        raise RuntimeError(f"Falha ao decodificar áudio via ffmpeg: {stderr_tail}")

    return np.frombuffer(res.stdout, dtype=np.int16).astype(np.float32) / 32768.0


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
            progress_cb(
                f"Carregando modelo Whisper offline ({self.model_size}, {self.compute_type})...",
                36,
            )

        cpu_threads = max(2, min(8, (os.cpu_count() or 4)))
        model = WhisperModel(
            self.model_size,
            device=self.device,
            compute_type=self.compute_type,
            cpu_threads=cpu_threads,
        )
        initial_prompt = None
        if glossary:
            initial_prompt = "Vocabulário técnico: " + ", ".join(glossary[:80])

        lang_code = None
        if language:
            lang_code = language.split("-")[0].lower()

        if progress_cb:
            progress_cb("Decodificando faixa de áudio (16 kHz mono) via ffmpeg...", 38)

        audio_input = _decode_audio_to_16k_float32(media_path)

        if progress_cb:
            progress_cb("Transcrevendo áudio localmente com faster-whisper (100% offline)...", 40)

        segments_iter, info = model.transcribe(
            audio_input,
            language=lang_code,
            initial_prompt=initial_prompt,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 500},
            beam_size=5,
            condition_on_previous_text=True,
        )

        total_duration = float(getattr(info, "duration", 0.0) or 0.0)
        total_fmt = format_timestamp_srt(total_duration).split(",")[0] if total_duration > 0 else "??:??:??"

        normalized: List[Dict[str, Any]] = []
        last_reported_pct = 40
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
            if progress_cb and total_duration > 0:
                ratio = min(1.0, end_s / total_duration)
                pct = 40 + int(ratio * 35)  # 40% -> 75%
                if pct >= last_reported_pct + 2 or idx == 1:
                    last_reported_pct = pct
                    cur_fmt = format_timestamp_srt(end_s).split(",")[0]
                    progress_cb(
                        f"Transcrevendo offline ({cur_fmt} / {total_fmt} • {len(normalized)} trechos)...",
                        pct,
                    )

        parsed = TranscriptParser._build_payload("srt", normalized)
        parsed["idioma"] = getattr(info, "language", language or "pt")
        return parsed
