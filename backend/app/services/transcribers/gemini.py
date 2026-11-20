"""
Transcritor Google Gemini Multimodal com:
- Suporte a áudios/vídeos longos (> 1h / > 2h) via segmentação automática (chunking) + merge de timestamps SRT
- Upload resumable via Google AI Files API para arquivos grandes + remoção do arquivo remoto após uso
- maxOutputTokens elevado (65536) para evitar truncamento da transcrição
- Injeção de glossário técnico configurável
"""

from __future__ import annotations

import base64
import json
import re
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.services.media import AudioChunk, split_audio_into_chunks
from app.services.parser import TranscriptParser
from app.services.transcribers.base import BaseTranscriber, ProgressCallback

MIME_BY_EXT = {
    ".mp3": "audio/mp3",
    ".wav": "audio/wav",
    ".m4a": "audio/mp4",
    ".aac": "audio/aac",
    ".ogg": "audio/ogg",
    ".opus": "audio/ogg",
    ".flac": "audio/flac",
    ".mp4": "video/mp4",
    ".mkv": "video/x-matroska",
    ".mov": "video/quicktime",
    ".webm": "video/webm",
    ".avi": "video/x-msvideo",
}


class GeminiTranscriber(BaseTranscriber):
    provider_name = "gemini"

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.5-flash",
        chunk_minutes: int = 20,
    ) -> None:
        self.api_key = api_key
        self.model = model or "gemini-2.5-flash"
        self.chunk_minutes = max(5, int(chunk_minutes or 20))

    def _build_prompt(self, glossary: Optional[List[str]], language: Optional[str]) -> str:
        glossary_block = ""
        if glossary:
            terms = ", ".join(glossary[:80])
            glossary_block = (
                f"5. Preserve rigorosamente a grafia destes termos técnicos/glossário do projeto: {terms}.\n"
            )
        lang_hint = (
            f"Idioma esperado predominante: {language}. Mantenha termos técnicos originais.\n"
            if language
            else "Transcreva no idioma original falado no áudio.\n"
        )
        return (
            "Você é um transcritor profissional de reuniões corporativas, aulas técnicas e vídeos.\n"
            f"{lang_hint}"
            "Transcreva INTEGRALMENTE o áudio a seguir no formato SubRip (.srt), sem resumir e sem omitir trechos.\n"
            "Regras Obrigatórias:\n"
            "1. Utilize numeração sequencial (1, 2, 3...) e timestamps no formato exato: HH:MM:SS,mmm --> HH:MM:SS,mmm.\n"
            "2. Os timestamps devem começar em 00:00:00,000 relativos ao início deste arquivo de áudio.\n"
            "3. Segmente as falas em blocos legíveis de 3 a 12 segundos. Quando houver troca clara de locutor, prefixe com 'Participante 1:', 'Participante 2:' ou o nome citado.\n"
            "4. Retorne EXCLUSIVAMENTE o conteúdo em formato .srt puro, sem comentários nem cercas markdown.\n"
            f"{glossary_block}"
        )

    def _upload_to_files_api(self, media_path: Path, mime_type: str) -> Tuple[str, str]:
        file_size = media_path.stat().st_size
        init_url = f"https://generativelanguage.googleapis.com/upload/v1beta/files?key={self.api_key}"

        init_headers = {
            "X-Goog-Upload-Protocol": "resumable",
            "X-Goog-Upload-Command": "start",
            "X-Goog-Upload-Header-Content-Length": str(file_size),
            "X-Goog-Upload-Header-Content-Type": mime_type,
            "Content-Type": "application/json",
        }
        init_body = json.dumps({"file": {"display_name": media_path.stem}}).encode("utf-8")
        req_init = urllib.request.Request(init_url, data=init_body, headers=init_headers, method="POST")

        with urllib.request.urlopen(req_init, timeout=60) as resp:
            upload_url = resp.headers.get("x-goog-upload-url")
            if not upload_url:
                raise RuntimeError("Não foi possível iniciar sessão resumable na Gemini Files API.")

        upload_headers = {
            "Content-Length": str(file_size),
            "X-Goog-Upload-Offset": "0",
            "X-Goog-Upload-Command": "upload, finalize",
        }
        with open(media_path, "rb") as fh:
            data = fh.read()
        req_up = urllib.request.Request(upload_url, data=data, headers=upload_headers, method="POST")
        with urllib.request.urlopen(req_up, timeout=300) as resp_up:
            file_info = json.loads(resp_up.read().decode("utf-8"))

        file_uri = file_info["file"]["uri"]
        file_name = file_info["file"]["name"]

        # Aguarda estado ACTIVE
        for _ in range(60):
            get_url = f"https://generativelanguage.googleapis.com/v1beta/{file_name}?key={self.api_key}"
            with urllib.request.urlopen(urllib.request.Request(get_url), timeout=30) as resp_get:
                info = json.loads(resp_get.read().decode("utf-8"))
                state = info.get("state", "ACTIVE")
                if state == "ACTIVE":
                    return file_uri, file_name
                if state == "FAILED":
                    raise RuntimeError("Falha ao processar arquivo de mídia na Gemini Files API.")
            time.sleep(2)
        return file_uri, file_name

    def _delete_remote_file(self, file_name: str) -> None:
        try:
            del_url = f"https://generativelanguage.googleapis.com/v1beta/{file_name}?key={self.api_key}"
            req = urllib.request.Request(del_url, method="DELETE")
            urllib.request.urlopen(req, timeout=15).close()
        except Exception:
            pass

    def _transcribe_single_file(self, chunk_path: Path, prompt: str) -> str:
        ext = chunk_path.suffix.lower()
        mime_type = MIME_BY_EXT.get(ext, "audio/mp3")
        size_mb = chunk_path.stat().st_size / (1024 * 1024)

        remote_file_name: Optional[str] = None
        try:
            if size_mb > 15.0:
                file_uri, remote_file_name = self._upload_to_files_api(chunk_path, mime_type)
                parts = [
                    {"file_data": {"mime_type": mime_type, "file_uri": file_uri}},
                    {"text": prompt},
                ]
            else:
                b64 = base64.b64encode(chunk_path.read_bytes()).decode("utf-8")
                parts = [
                    {"inline_data": {"mime_type": mime_type, "data": b64}},
                    {"text": prompt},
                ]

            url = (
                f"https://generativelanguage.googleapis.com/v1beta/models/"
                f"{self.model}:generateContent?key={self.api_key}"
            )
            payload = {
                "contents": [{"parts": parts}],
                "generationConfig": {
                    "temperature": 0.1,
                    "maxOutputTokens": 65536,
                },
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=600) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                candidates = res.get("candidates", [])
                if not candidates:
                    raise RuntimeError("Gemini não retornou candidatos de transcrição.")
                text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                cleaned = re.sub(r"^```(?:srt)?\s*", "", text.strip(), flags=re.IGNORECASE)
                cleaned = re.sub(r"\s*```$", "", cleaned.strip())
                return cleaned
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")[:500]
            raise RuntimeError(f"Erro HTTP {e.code} na Gemini API durante transcrição: {detail}") from e
        finally:
            if remote_file_name:
                self._delete_remote_file(remote_file_name)

    def transcribe(
        self,
        media_path: Path,
        *,
        glossary: Optional[List[str]] = None,
        language: Optional[str] = None,
        progress_cb: Optional[ProgressCallback] = None,
    ) -> Dict[str, Any]:
        if not self.api_key:
            raise ValueError(
                "Chave GEMINI_API_KEY não configurada. Informe em Configurações ou .env, "
                "ou altere o transcritor para `local_whisper` (100% offline)."
            )

        prompt = self._build_prompt(glossary, language)
        with tempfile.TemporaryDirectory(prefix="mvi_chunks_") as tmp_dir:
            chunks: List[AudioChunk] = split_audio_into_chunks(
                media_path,
                Path(tmp_dir),
                chunk_minutes=self.chunk_minutes,
            )
            chunk_results: List[Tuple[str, float]] = []
            total = len(chunks)
            for idx, chunk in enumerate(chunks, start=1):
                if progress_cb:
                    pct = 35 + int((idx - 1) / max(1, total) * 35)
                    progress_cb(f"Transcrevendo bloco {idx}/{total} via Google Gemini...", pct)
                srt_text = self._transcribe_single_file(chunk.path, prompt)
                chunk_results.append((srt_text, chunk.offset_seconds))

        parsed = TranscriptParser.merge_srt_chunks(chunk_results)
        parsed["idioma"] = language or "pt-BR"
        return parsed
