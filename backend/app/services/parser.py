"""
Parser e Normalizador de Transcrições (.srt, .vtt, .txt, .json).
Evoluído para suportar:
- Legendas SubRip (.srt) e WebVTT (.vtt), incluindo marcações de locutor (<v Nome> do Teams/Zoom/Meet)
- Arquivos JSON estruturados (saídas Whisper, YouTube Transcript API ou formato interno)
- Texto puro (.txt) com detecção de speakers (ex.: "Maria: Vamos aprovar...")
- Conversão precisa de timestamps <-> segundos, cálculo de duração e merge com offset de chunks (> 1h)
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


TIME_SRT_RE = re.compile(
    r"(\d{1,2}:\d{2}:\d{2}[,\.]\d{3})\s*-->\s*(\d{1,2}:\d{2}:\d{2}[,\.]\d{3})"
)
TIME_VTT_RE = re.compile(
    r"((?:\d{1,2}:)?\d{2}:\d{2}[,\.]\d{3})\s*-->\s*((?:\d{1,2}:)?\d{2}:\d{2}[,\.]\d{3})"
)
VTT_VOICE_TAG_RE = re.compile(r"<v(?:\.[^>\s]+)?\s+([^>]+)>", flags=re.IGNORECASE)
SPEAKER_PREFIX_RE = re.compile(r"^([A-ZÀ-Úa-zà-ú0-9_\.\- ]{2,40}):\s+(.+)$")


def parse_timestamp_to_seconds(ts: str) -> float:
    """Converte HH:MM:SS,mmm ou MM:SS.mmm em segundos."""
    if not ts:
        return 0.0
    clean = ts.strip().replace(",", ".")
    parts = clean.split(":")
    try:
        if len(parts) == 3:
            h, m, s = int(parts[0]), int(parts[1]), float(parts[2])
            return h * 3600 + m * 60 + s
        if len(parts) == 2:
            m, s = int(parts[0]), float(parts[1])
            return m * 60 + s
        return float(clean)
    except ValueError:
        return 0.0


def format_timestamp_srt(seconds: float) -> str:
    """Converte segundos em HH:MM:SS,mmm."""
    seconds = max(0.0, float(seconds))
    total_ms = int(round(seconds * 1000))
    ms = total_ms % 1000
    total_sec = total_ms // 1000
    h = total_sec // 3600
    m = (total_sec % 3600) // 60
    s = total_sec % 60
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def format_duration_hms(seconds: float) -> str:
    """Converte segundos em HH:MM:SS."""
    total_sec = max(0, int(round(seconds)))
    h = total_sec // 3600
    m = (total_sec % 3600) // 60
    s = total_sec % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def _extract_speaker_and_clean_text(raw_text: str) -> Tuple[Optional[str], str]:
    speaker: Optional[str] = None
    voice_match = VTT_VOICE_TAG_RE.search(raw_text)
    if voice_match:
        speaker = voice_match.group(1).strip()

    cleaned = re.sub(r"<[^>]+>", "", raw_text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    if not speaker:
        sp_match = SPEAKER_PREFIX_RE.match(cleaned)
        if sp_match:
            candidate = sp_match.group(1).strip()
            # Evita confundir horários ou URLs com nome de speaker
            if len(candidate.split()) <= 4 and not candidate.lower().startswith(("http", "obs", "nota")):
                speaker = candidate
                cleaned = sp_match.group(2).strip()

    return speaker, cleaned


class TranscriptParser:
    """Parser e normalizador unificado de transcrições de reuniões e vídeos."""

    @staticmethod
    def segments_to_srt(segments: List[Dict[str, Any]]) -> str:
        """Reconstrói conteúdo .srt válido a partir da lista de segmentos normalizados."""
        lines: List[str] = []
        for idx, seg in enumerate(segments, start=1):
            start_s = seg.get("start_seconds")
            end_s = seg.get("end_seconds")
            inicio = seg.get("inicio") or format_timestamp_srt(float(start_s or 0.0))
            fim = seg.get("fim") or format_timestamp_srt(float(end_s or 0.0))
            inicio = inicio.replace(".", ",")
            fim = fim.replace(".", ",")
            speaker = seg.get("speaker")
            texto = str(seg.get("texto", "")).strip()
            if not texto:
                continue
            rendered_text = f"{speaker}: {texto}" if speaker and not texto.startswith(f"{speaker}:") else texto
            lines.append(f"{idx}\n{inicio} --> {fim}\n{rendered_text}\n")
        return "\n".join(lines).strip()

    @classmethod
    def shift_segments(cls, segments: List[Dict[str, Any]], offset_seconds: float) -> List[Dict[str, Any]]:
        """Aplica offset em segundos a todos os segmentos (usado ao unir chunks de vídeos longos)."""
        shifted: List[Dict[str, Any]] = []
        for seg in segments:
            s_sec = float(seg.get("start_seconds", parse_timestamp_to_seconds(seg.get("inicio", "")))) + offset_seconds
            e_sec = float(seg.get("end_seconds", parse_timestamp_to_seconds(seg.get("fim", "")))) + offset_seconds
            if e_sec < s_sec:
                e_sec = s_sec + 2.0
            shifted.append(
                {
                    "index": seg.get("index", 1),
                    "inicio": format_timestamp_srt(s_sec),
                    "fim": format_timestamp_srt(e_sec),
                    "start_seconds": round(s_sec, 3),
                    "end_seconds": round(e_sec, 3),
                    "speaker": seg.get("speaker"),
                    "texto": seg.get("texto", ""),
                }
            )
        return shifted

    @classmethod
    def merge_srt_chunks(cls, chunk_results: List[Tuple[str, float]]) -> Dict[str, Any]:
        """
        Combina múltiplos blocos SRT gerados por chunking de áudio.
        Cada item de `chunk_results` é `(srt_content, chunk_start_offset_seconds)`.
        """
        merged_segments: List[Dict[str, Any]] = []
        next_idx = 1

        for raw_srt, offset_sec in chunk_results:
            parsed = cls.parse_srt(raw_srt)
            if not parsed["segmentos"] and raw_srt.strip():
                # Fallback caso a LLM devolva texto contínuo sem timestamps em algum chunk
                parsed = cls.parse_plain_text(raw_srt, base_offset_seconds=offset_sec)
                shifted = parsed["segmentos"]
            else:
                shifted = cls.shift_segments(parsed["segmentos"], offset_sec)

            for seg in shifted:
                seg["index"] = next_idx
                next_idx += 1
                merged_segments.append(seg)

        return cls._build_payload("srt", merged_segments)

    @classmethod
    def _build_payload(cls, fmt: str, segments: List[Dict[str, Any]]) -> Dict[str, Any]:
        full_parts: List[str] = []
        max_end = 0.0
        for idx, seg in enumerate(segments, start=1):
            seg["index"] = idx
            max_end = max(max_end, float(seg.get("end_seconds", 0.0)))
            speaker = seg.get("speaker")
            texto = str(seg.get("texto", "")).strip()
            if texto:
                full_parts.append(f"{speaker}: {texto}" if speaker else texto)

        full_text = " ".join(full_parts).strip()
        word_count = len(full_text.split()) if full_text else 0
        # Se não houver timestamps confiáveis (ex.: .txt puro), estima ~145 palavras/minuto
        if max_end <= 0.0 and word_count > 0:
            max_end = round((word_count / 145.0) * 60.0, 1)

        return {
            "formato": fmt,
            "total_segmentos": len(segments),
            "total_palavras": word_count,
            "duracao_segundos": int(round(max_end)),
            "duracao_formatada": format_duration_hms(max_end),
            "texto_completo": full_text,
            "conteudo_srt": cls.segments_to_srt(segments),
            "segmentos": segments,
        }

    @classmethod
    def parse_srt(cls, content: str) -> Dict[str, Any]:
        content = content.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
        blocks = re.split(r"\n\s*\n", content.strip())
        segments: List[Dict[str, Any]] = []

        for block in blocks:
            lines = [line.strip() for line in block.split("\n") if line.strip()]
            if not lines:
                continue

            time_match = None
            text_lines: List[str] = []
            for line in lines:
                m = TIME_SRT_RE.search(line)
                if m:
                    time_match = m
                elif not line.isdigit():
                    text_lines.append(line)

            raw_text = " ".join(text_lines).strip()
            speaker, cleaned = _extract_speaker_and_clean_text(raw_text)
            if not cleaned:
                continue

            start_raw = time_match.group(1) if time_match else "00:00:00,000"
            end_raw = time_match.group(2) if time_match else start_raw
            start_s = parse_timestamp_to_seconds(start_raw)
            end_s = parse_timestamp_to_seconds(end_raw)

            segments.append(
                {
                    "index": len(segments) + 1,
                    "inicio": format_timestamp_srt(start_s),
                    "fim": format_timestamp_srt(end_s),
                    "start_seconds": round(start_s, 3),
                    "end_seconds": round(end_s, 3),
                    "speaker": speaker,
                    "texto": cleaned,
                }
            )

        return cls._build_payload("srt", segments)

    @classmethod
    def parse_vtt(cls, content: str) -> Dict[str, Any]:
        content = content.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
        # Remove cabeçalho WEBVTT e eventuais metadados iniciais
        content = re.sub(r"^WEBVTT[^\n]*\n(?:(?:Kind|Language|Style|Region):[^\n]*\n)*", "", content, flags=re.IGNORECASE)
        blocks = re.split(r"\n\s*\n", content.strip())
        segments: List[Dict[str, Any]] = []

        for block in blocks:
            lines = [line.strip() for line in block.split("\n") if line.strip()]
            if not lines:
                continue
            if lines[0].startswith(("NOTE", "STYLE", "REGION")):
                continue

            time_match = None
            text_lines: List[str] = []
            for line in lines:
                m = TIME_VTT_RE.search(line)
                if m:
                    time_match = m
                elif not line.isdigit() and not re.match(r"^[0-9a-f\-]{8,}/\d+-\d+$", line, flags=re.IGNORECASE):
                    text_lines.append(line)

            if not text_lines:
                continue

            raw_text = " ".join(text_lines).strip()
            speaker, cleaned = _extract_speaker_and_clean_text(raw_text)
            if not cleaned:
                continue

            start_raw = time_match.group(1) if time_match else "00:00:00.000"
            end_raw = time_match.group(2) if time_match else start_raw
            start_s = parse_timestamp_to_seconds(start_raw)
            end_s = parse_timestamp_to_seconds(end_raw)

            segments.append(
                {
                    "index": len(segments) + 1,
                    "inicio": format_timestamp_srt(start_s),
                    "fim": format_timestamp_srt(end_s),
                    "start_seconds": round(start_s, 3),
                    "end_seconds": round(end_s, 3),
                    "speaker": speaker,
                    "texto": cleaned,
                }
            )

        return cls._build_payload("vtt", segments)

    @classmethod
    def parse_plain_text(cls, content: str, base_offset_seconds: float = 0.0) -> Dict[str, Any]:
        content = content.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n").strip()
        if not content:
            return cls._build_payload("txt", [])

        # Divide em parágrafos ou linhas não vazias para preservar turnos de fala
        raw_lines = [line.strip() for line in content.split("\n") if line.strip()]
        segments: List[Dict[str, Any]] = []
        cursor = base_offset_seconds

        for line in raw_lines:
            speaker, cleaned = _extract_speaker_and_clean_text(line)
            if not cleaned:
                continue
            words = max(1, len(cleaned.split()))
            est_dur = max(2.0, round((words / 2.4), 2))
            segments.append(
                {
                    "index": len(segments) + 1,
                    "inicio": format_timestamp_srt(cursor),
                    "fim": format_timestamp_srt(cursor + est_dur),
                    "start_seconds": round(cursor, 3),
                    "end_seconds": round(cursor + est_dur, 3),
                    "speaker": speaker,
                    "texto": cleaned,
                }
            )
            cursor += est_dur

        return cls._build_payload("txt", segments)

    @classmethod
    def parse_json(cls, content: str) -> Dict[str, Any]:
        try:
            data = json.loads(content)
        except Exception:
            return cls.parse_plain_text(content)

        raw_segments: Optional[List[Any]] = None
        if isinstance(data, list):
            raw_segments = data
        elif isinstance(data, dict):
            if isinstance(data.get("segmentos"), list):
                raw_segments = data["segmentos"]
            elif isinstance(data.get("segments"), list):
                raw_segments = data["segments"]
            elif isinstance(data.get("texto_completo"), str):
                return cls.parse_plain_text(data["texto_completo"])
            elif isinstance(data.get("text"), str):
                return cls.parse_plain_text(data["text"])

        if raw_segments is not None:
            segments: List[Dict[str, Any]] = []
            for item in raw_segments:
                if not isinstance(item, dict):
                    continue
                raw_text = str(item.get("texto") or item.get("text") or "").strip()
                if not raw_text:
                    continue
                speaker = item.get("speaker")
                if not speaker:
                    speaker, cleaned = _extract_speaker_and_clean_text(raw_text)
                else:
                    cleaned = raw_text

                if "start" in item:
                    s_sec = float(item["start"])
                    e_sec = float(item.get("end", s_sec + float(item.get("duration", 3.0))))
                elif "start_seconds" in item:
                    s_sec = float(item["start_seconds"])
                    e_sec = float(item.get("end_seconds", s_sec + 3.0))
                else:
                    s_sec = parse_timestamp_to_seconds(str(item.get("inicio", "")))
                    e_sec = parse_timestamp_to_seconds(str(item.get("fim", "")))

                segments.append(
                    {
                        "index": len(segments) + 1,
                        "inicio": format_timestamp_srt(s_sec),
                        "fim": format_timestamp_srt(e_sec),
                        "start_seconds": round(s_sec, 3),
                        "end_seconds": round(e_sec, 3),
                        "speaker": speaker,
                        "texto": cleaned,
                    }
                )
            return cls._build_payload("json", segments)

        return cls.parse_plain_text(json.dumps(data, ensure_ascii=False))

    @classmethod
    def parse_content(cls, content: str, format_hint: str = "auto") -> Dict[str, Any]:
        fmt = (format_hint or "auto").lower().lstrip(".")
        stripped = content.lstrip("\ufeff").strip()

        if fmt == "auto":
            if stripped.upper().startswith("WEBVTT"):
                fmt = "vtt"
            elif TIME_SRT_RE.search(stripped[:2000]):
                fmt = "srt"
            elif TIME_VTT_RE.search(stripped[:2000]):
                fmt = "vtt"
            elif (stripped.startswith("{") and stripped.endswith("}")) or (
                stripped.startswith("[") and stripped.endswith("]")
            ):
                fmt = "json"
            else:
                fmt = "txt"

        if fmt == "srt":
            return cls.parse_srt(content)
        if fmt == "vtt":
            return cls.parse_vtt(content)
        if fmt == "json":
            return cls.parse_json(content)
        return cls.parse_plain_text(content)

    @classmethod
    def parse_file(cls, filepath: Path) -> Dict[str, Any]:
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {filepath}")
        raw_content = filepath.read_text(encoding="utf-8", errors="replace")
        ext = filepath.suffix.lower().lstrip(".")
        parsed = cls.parse_content(raw_content, format_hint=ext or "auto")
        parsed["arquivo_origem"] = filepath.name
        return parsed
