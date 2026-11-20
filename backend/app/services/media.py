"""
Serviço de Mídia:
- Detecção de URLs do YouTube e demais URLs suportadas por yt-dlp
- Obtenção de legendas oficiais/automáticas (YouTube Transcript API)
- Fallback automático para download da faixa de áudio otimizada via yt-dlp
- Extração/compressão de áudio de vídeos locais (.mp4, .mkv, .mov, .webm, .avi) via ffmpeg
- Segmentação automática de áudios longos (> 1h / > 2h) em chunks com offset exato
"""

from __future__ import annotations

import math
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.services.parser import TranscriptParser, format_timestamp_srt

TRANSCRIPT_EXTENSIONS = {".srt", ".vtt", ".txt", ".json"}
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".mov", ".webm", ".avi"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".aac", ".opus", ".flac"}
MEDIA_EXTENSIONS = VIDEO_EXTENSIONS | AUDIO_EXTENSIONS


@dataclass
class AudioChunk:
    path: Path
    offset_seconds: float
    duration_seconds: float


def extract_youtube_video_id(url_or_id: str) -> Optional[str]:
    """Extrai o ID do vídeo do YouTube (11 caracteres) ou retorna None."""
    s = (url_or_id or "").strip()
    if re.match(r"^[a-zA-Z0-9_-]{11}$", s) and "/" not in s and "." not in s:
        return s

    lower = s.lower()
    if "youtube.com" not in lower and "youtu.be" not in lower:
        return None

    patterns = [
        r"[?&]v=([a-zA-Z0-9_-]{11})",
        r"youtu\.be\/([a-zA-Z0-9_-]{11})",
        r"youtube\.com\/shorts\/([a-zA-Z0-9_-]{11})",
        r"youtube\.com\/embed\/([a-zA-Z0-9_-]{11})",
        r"youtube\.com\/live\/([a-zA-Z0-9_-]{11})",
        r"youtube\.com\/v\/([a-zA-Z0-9_-]{11})",
    ]
    for pattern in patterns:
        m = re.search(pattern, s)
        if m:
            return m.group(1)
    return None


def find_ffmpeg_executable() -> Optional[str]:
    """Localiza ffmpeg no PATH do sistema ou via pacote opcional imageio-ffmpeg."""
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg
    try:
        import imageio_ffmpeg  # type: ignore[import-not-found]

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def find_ffprobe_executable() -> Optional[str]:
    return shutil.which("ffprobe")


def probe_media_duration_seconds(media_path: Path) -> Optional[float]:
    """Obtém a duração do áudio/vídeo em segundos via ffprobe ou ffmpeg."""
    ffprobe = find_ffprobe_executable()
    if ffprobe:
        try:
            res = subprocess.run(
                [
                    ffprobe,
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    str(media_path),
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            return float(res.stdout.strip())
        except Exception:
            pass

    ffmpeg = find_ffmpeg_executable()
    if ffmpeg:
        try:
            res = subprocess.run(
                [ffmpeg, "-i", str(media_path)],
                capture_output=True,
                text=True,
            )
            m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", res.stderr or "")
            if m:
                return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
        except Exception:
            pass

    return None


def extract_and_compress_audio(input_path: Path, output_dir: Path) -> Path:
    """
    Extrai e comprime a faixa de áudio para mono 16kHz 48kbps (.mp3) usando ffmpeg.
    Ideal para reduzir vídeos pesados (.mp4/.mkv/.mov) de centenas de MB para poucos MB.
    Se ffmpeg não estiver disponível e o arquivo já for áudio, retorna o arquivo original.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    ext = input_path.suffix.lower()
    ffmpeg = find_ffmpeg_executable()

    if not ffmpeg:
        if ext in AUDIO_EXTENSIONS:
            return input_path
        # Ainda permite enviar vídeos pequenos diretamente ao Gemini, mas alerta se muito grande
        size_mb = input_path.stat().st_size / (1024 * 1024)
        if size_mb > 450:
            raise RuntimeError(
                "Arquivo de vídeo muito grande sem ffmpeg instalado. Instale o ffmpeg ou o pacote "
                "`imageio-ffmpeg` para extrair a faixa de áudio automaticamente."
            )
        return input_path

    out_path = output_dir / f"{input_path.stem}_audio_16k.mp3"
    cmd = [
        ffmpeg,
        "-y",
        "-i",
        str(input_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-b:a",
        "48k",
        str(out_path),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0 or not out_path.exists():
        if ext in AUDIO_EXTENSIONS:
            return input_path
        raise RuntimeError(f"Falha ao extrair áudio com ffmpeg: {res.stderr[-400:]}")
    return out_path


def split_audio_into_chunks(
    audio_path: Path,
    output_dir: Path,
    chunk_minutes: int = 20,
) -> List[AudioChunk]:
    """
    Divide áudios longos (> chunk_minutes) em fatias de `chunk_minutes` minutos via ffmpeg
    para evitar truncamento de saída em transcrições de vídeos de 1h, 2h ou mais.
    Caso o áudio seja menor que o limite ou ffmpeg não esteja disponível, retorna 1 chunk.
    """
    chunk_sec = max(5, int(chunk_minutes)) * 60
    duration = probe_media_duration_seconds(audio_path)
    ffmpeg = find_ffmpeg_executable()

    if not ffmpeg or duration is None or duration <= chunk_sec + 30:
        return [AudioChunk(path=audio_path, offset_seconds=0.0, duration_seconds=duration or 0.0)]

    output_dir.mkdir(parents=True, exist_ok=True)
    num_chunks = math.ceil(duration / chunk_sec)
    chunks: List[AudioChunk] = []

    for idx in range(num_chunks):
        start_sec = idx * chunk_sec
        this_dur = min(chunk_sec, duration - start_sec)
        chunk_file = output_dir / f"{audio_path.stem}_chunk_{idx + 1:03d}.mp3"
        cmd = [
            ffmpeg,
            "-y",
            "-ss",
            str(start_sec),
            "-t",
            str(this_dur),
            "-i",
            str(audio_path),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-b:a",
            "48k",
            str(chunk_file),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0 or not chunk_file.exists():
            # Se falhar segmentação, faz fallback para o arquivo inteiro
            return [AudioChunk(path=audio_path, offset_seconds=0.0, duration_seconds=duration)]
        chunks.append(AudioChunk(path=chunk_file, offset_seconds=float(start_sec), duration_seconds=float(this_dur)))

    return chunks


def download_youtube_transcript(
    video_id: str,
    languages: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Busca legendas oficiais ou automáticas já existentes no YouTube.
    Compatível com youtube-transcript-api v0.6.x e v1.x.
    """
    langs = languages or ["pt", "pt-BR", "en", "es"]
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError as exc:
        raise RuntimeError(
            "Pacote `youtube-transcript-api` não instalado. Instale com `pip install youtube-transcript-api`."
        ) from exc

    detected_lang = langs[0]
    raw_items: List[Dict[str, Any]] = []

    # Suporta API v1.x (instância) e v0.6.x (métodos de classe)
    if hasattr(YouTubeTranscriptApi, "list_transcripts"):
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        try:
            transcript = transcript_list.find_transcript(langs)
        except Exception:
            transcript = transcript_list.find_generated_transcript(langs)
        fetched = transcript.fetch()
        detected_lang = getattr(transcript, "language_code", langs[0])
    else:
        api = YouTubeTranscriptApi()
        transcript_list = api.list(video_id)
        try:
            transcript = transcript_list.find_transcript(langs)
        except Exception:
            transcript = transcript_list.find_generated_transcript(langs)
        fetched = transcript.fetch()
        detected_lang = getattr(transcript, "language_code", langs[0])

    for item in fetched:
        if isinstance(item, dict):
            start = float(item.get("start", 0.0))
            duration = float(item.get("duration", 2.0))
            text = str(item.get("text", "")).replace("\n", " ").strip()
        else:
            start = float(getattr(item, "start", 0.0))
            duration = float(getattr(item, "duration", 2.0))
            text = str(getattr(item, "text", "")).replace("\n", " ").strip()
        if text:
            raw_items.append(
                {
                    "inicio": format_timestamp_srt(start),
                    "fim": format_timestamp_srt(start + duration),
                    "start_seconds": round(start, 3),
                    "end_seconds": round(start + duration, 3),
                    "speaker": None,
                    "texto": text,
                }
            )

    if not raw_items:
        raise RuntimeError("Nenhuma legenda com conteúdo encontrada para este vídeo.")

    parsed = TranscriptParser._build_payload("srt", raw_items)
    parsed["video_id"] = video_id
    parsed["idioma"] = detected_lang
    return parsed


def download_audio_from_url(url: str, output_dir: Path) -> Tuple[Path, Dict[str, Any]]:
    """
    Baixa apenas a faixa de áudio otimizada de qualquer URL suportada pelo yt-dlp.
    Retorna `(caminho_do_audio, metadados_extraidos)`.
    """
    try:
        import yt_dlp
    except ImportError as exc:
        raise RuntimeError(
            "Pacote `yt-dlp` não instalado. Instale com `pip install yt-dlp` para baixar áudio de URLs."
        ) from exc

    output_dir.mkdir(parents=True, exist_ok=True)
    video_id = extract_youtube_video_id(url) or "remote_media"
    target_pattern = str(output_dir / f"audio_{video_id}.%(ext)s")

    ydl_opts = {
        "format": "bestaudio[ext=m4a]/bestaudio/best",
        "outtmpl": target_pattern,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        audio_path = Path(filename)
        metadata = {
            "title": info.get("title") or f"Vídeo {video_id}",
            "duration": info.get("duration") or 0,
            "uploader": info.get("uploader") or "",
            "webpage_url": info.get("webpage_url") or url,
        }
        return audio_path, metadata


def fetch_url_title(url: str) -> Optional[str]:
    """Tenta obter rapidamente o título do vídeo via yt-dlp sem baixar mídia."""
    try:
        import yt_dlp

        with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "skip_download": True}) as ydl:
            info = ydl.extract_info(url, download=False)
            return info.get("title") if isinstance(info, dict) else None
    except Exception:
        return None
