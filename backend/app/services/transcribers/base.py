"""Interface abstrata para provedores de transcrição."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

ProgressCallback = Callable[[str, int], None]


class BaseTranscriber(ABC):
    provider_name: str = "base"

    @abstractmethod
    def transcribe(
        self,
        media_path: Path,
        *,
        glossary: Optional[List[str]] = None,
        language: Optional[str] = None,
        progress_cb: Optional[ProgressCallback] = None,
    ) -> Dict[str, Any]:
        """
        Transcreve o arquivo de áudio/vídeo e retorna o dicionário normalizado do TranscriptParser:
        `{formato, total_segmentos, total_palavras, duracao_segundos, duracao_formatada, texto_completo, conteudo_srt, segmentos}`.
        """
        raise NotImplementedError
