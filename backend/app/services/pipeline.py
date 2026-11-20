"""
Orquestrador Unificado de Ingestão, Transcrição e Análise Estruturada via LLM.
Suporta os 3 fluxos de entrada:
1. Transcrições prontas (.srt, .vtt, .txt, .json) ou texto colado
2. URL de vídeo (YouTube com legendas -> fallback automático yt-dlp áudio -> transcrição IA)
3. Upload manual de vídeo/áudio local (.mp4, .mkv, .mov, .webm, .avi, .mp3, .wav, .m4a, .ogg, .aac)

Atualiza o progresso do job em tempo real no SQLite:
Recebido -> Extraindo Áudio -> Transcrevendo -> Analisando com LLM -> Concluído
"""

from __future__ import annotations

import tempfile
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from app.db import Database, db as default_db
from app.schemas import JobStage, MediaType
from app.services.databricks_sync import (
    sanitize_filename,
    trigger_lakeflow_pipeline,
    upload_to_unity_catalog_volume,
)
from app.services.llm import get_llm_provider
from app.services.media import (
    MEDIA_EXTENSIONS,
    TRANSCRIPT_EXTENSIONS,
    VIDEO_EXTENSIONS,
    download_audio_from_url,
    download_youtube_transcript,
    extract_and_compress_audio,
    extract_youtube_video_id,
    fetch_url_title,
)
from app.services.parser import TranscriptParser
from app.services.transcribers import get_transcriber


def _infer_media_type(source_type: str, template: str, ref: str) -> str:
    lower_ref = (ref or "").lower()
    if "aula" in template.lower() or "youtube" in lower_ref or "youtu.be" in lower_ref:
        return MediaType.VIDEO_TECNICO.value
    if any(ext in lower_ref for ext in [".mp3", ".m4a", ".wav", ".ogg", ".aac"]):
        return MediaType.AUDIO_PODCAST.value
    if "entrevista" in lower_ref:
        return MediaType.ENTREVISTA.value
    return MediaType.REUNIAO.value


class IngestionPipeline:
    """Pipeline reutilizável pela API REST (em background) e pela CLI."""

    def __init__(self, database: Optional[Database] = None) -> None:
        self.db = database or default_db

    def _set_stage(self, job_id: Optional[str], stage: JobStage, progress: int, message: str, **extra: Any) -> None:
        if not job_id:
            return
        self.db.update_job(job_id, stage=stage.value, progress=progress, message=message, **extra)

    def _run_llm_and_persist(
        self,
        *,
        job_id: Optional[str],
        parsed: Dict[str, Any],
        title: str,
        source_type: str,
        source_ref: str,
        template: str,
        transcriber_provider: str,
        language: Optional[str],
        push_to_databricks: bool = False,
        run_databricks_pipeline: bool = False,
    ) -> Dict[str, Any]:
        settings = self.db.get_settings(masked=False)
        self._set_stage(job_id, JobStage.ANALISANDO_LLM, 78, "Extraindo resumo, decisões, pendências e action items...")

        clean_text = parsed.get("texto_completo", "").strip()
        if not clean_text:
            raise ValueError("A transcrição obtida está vazia. Verifique o arquivo ou a fonte informada.")

        llm = get_llm_provider(settings, allow_heuristic_fallback=True)
        resolved_lang = language or parsed.get("idioma") or "pt-BR"
        default_media_type = _infer_media_type(source_type, template, source_ref)

        analysis = llm.analyze_transcript(
            transcript_text=clean_text,
            title=title,
            template=template,
            categories=settings.get("categories") or [],
            glossary=settings.get("glossary_terms") or [],
            language=resolved_lang,
            duration_seconds=int(parsed.get("duracao_segundos", 0) or 0),
            duration_formatted=str(parsed.get("duracao_formatada", "00:00:00")),
            word_count=int(parsed.get("total_palavras", 0) or 0),
            default_media_type=default_media_type,
        )

        doc_id = str(uuid.uuid4())
        doc = self.db.save_document(
            doc_id=doc_id,
            source_type=source_type,
            source_ref=source_ref,
            template=template,
            transcriber_provider=transcriber_provider,
            llm_provider=llm.provider_name,
            transcript_format=parsed.get("formato", "srt"),
            raw_srt=parsed.get("conteudo_srt", ""),
            clean_text=clean_text,
            segments=parsed.get("segmentos", []),
            analysis=analysis.model_dump(),
        )

        if push_to_databricks:
            self._set_stage(job_id, JobStage.ANALISANDO_LLM, 92, "Enviando transcrição para Volume no Databricks...")
            self.push_document_to_databricks(doc_id, run_pipeline=run_databricks_pipeline)
            doc = self.db.get_document(doc_id) or doc

        self._set_stage(
            job_id,
            JobStage.CONCLUIDO,
            100,
            "Processamento concluído com sucesso!",
            status="completed",
            document_id=doc_id,
            title=doc["title"],
        )
        return doc

    def process_text(
        self,
        *,
        text: str,
        title: str,
        format_hint: str = "auto",
        template: str = "Reunião Corporativa",
        language: Optional[str] = "pt-BR",
        job_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        try:
            self._set_stage(job_id, JobStage.TRANSCREVENDO, 45, "Normalizando transcrição colada...")
            parsed = TranscriptParser.parse_content(text, format_hint=format_hint)
            return self._run_llm_and_persist(
                job_id=job_id,
                parsed=parsed,
                title=title or "Transcrição Colada",
                source_type="text",
                source_ref="texto_colado",
                template=template,
                transcriber_provider="direct_transcript",
                language=language,
            )
        except Exception as exc:
            if job_id:
                self.db.update_job(
                    job_id,
                    status="failed",
                    stage=JobStage.ERRO.value,
                    message=str(exc),
                    error=str(exc),
                )
            raise

    def process_file(
        self,
        *,
        file_path: Path,
        original_filename: Optional[str] = None,
        title: Optional[str] = None,
        template: str = "Reunião Corporativa",
        language: Optional[str] = None,
        push_to_databricks: bool = False,
        run_databricks_pipeline: bool = False,
        job_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        try:
            path = Path(file_path)
            if not path.exists():
                raise FileNotFoundError(f"Arquivo não encontrado: {path}")

            display_name = original_filename or path.name
            ext = Path(display_name).suffix.lower() or path.suffix.lower()
            resolved_title = (title or Path(display_name).stem.replace("_", " ")).strip()
            settings = self.db.get_settings(masked=False)

            if ext in TRANSCRIPT_EXTENSIONS or ext == "":
                self._set_stage(job_id, JobStage.TRANSCREVENDO, 40, f"Lendo e normalizando legenda ({ext or 'txt'})...")
                parsed = TranscriptParser.parse_file(path)
                provider_used = "direct_transcript"
            elif ext in MEDIA_EXTENSIONS:
                with tempfile.TemporaryDirectory(prefix="mvi_audio_") as tmp_dir:
                    if ext in VIDEO_EXTENSIONS:
                        self._set_stage(
                            job_id,
                            JobStage.EXTRAINDO_AUDIO,
                            20,
                            f"Extraindo e comprimindo faixa de áudio do vídeo ({display_name})...",
                        )
                        audio_path = extract_and_compress_audio(path, Path(tmp_dir))
                    else:
                        self._set_stage(
                            job_id,
                            JobStage.EXTRAINDO_AUDIO,
                            20,
                            f"Preparando arquivo de áudio ({display_name})...",
                        )
                        audio_path = path

                    transcriber = get_transcriber(settings)
                    provider_used = transcriber.provider_name
                    self._set_stage(
                        job_id,
                        JobStage.TRANSCREVENDO,
                        35,
                        f"Transcrevendo áudio via {provider_used}...",
                    )
                    parsed = transcriber.transcribe(
                        audio_path,
                        glossary=settings.get("glossary_terms") or [],
                        language=language,
                        progress_cb=lambda msg, pct: self._set_stage(job_id, JobStage.TRANSCREVENDO, pct, msg),
                    )
            else:
                # Tenta ler como texto simples
                self._set_stage(job_id, JobStage.TRANSCREVENDO, 40, "Lendo arquivo como texto...")
                parsed = TranscriptParser.parse_file(path)
                provider_used = "direct_transcript"

            return self._run_llm_and_persist(
                job_id=job_id,
                parsed=parsed,
                title=resolved_title,
                source_type="file",
                source_ref=display_name,
                template=template,
                transcriber_provider=provider_used,
                language=language,
                push_to_databricks=push_to_databricks,
                run_databricks_pipeline=run_databricks_pipeline,
            )
        except Exception as exc:
            if job_id:
                self.db.update_job(
                    job_id,
                    status="failed",
                    stage=JobStage.ERRO.value,
                    message=str(exc),
                    error=str(exc),
                )
            raise

    def process_url(
        self,
        *,
        url: str,
        title: Optional[str] = None,
        template: str = "Aula/Vídeo Técnico",
        force_ai_transcription: bool = False,
        language: Optional[str] = None,
        push_to_databricks: bool = False,
        run_databricks_pipeline: bool = False,
        job_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        try:
            settings = self.db.get_settings(masked=False)
            video_id = extract_youtube_video_id(url)
            parsed: Optional[Dict[str, Any]] = None
            provider_used = "youtube_captions"
            resolved_title = (title or "").strip()

            if video_id and not force_ai_transcription:
                self._set_stage(job_id, JobStage.TRANSCREVENDO, 25, "Buscando legendas existentes no YouTube...")
                try:
                    langs = [language] if language else ["pt", "pt-BR", "en", "es"]
                    parsed = download_youtube_transcript(video_id, languages=langs)
                    if not resolved_title:
                        resolved_title = fetch_url_title(url) or f"YouTube {video_id}"
                except Exception:
                    parsed = None

            if parsed is None:
                with tempfile.TemporaryDirectory(prefix="mvi_url_") as tmp_dir:
                    self._set_stage(
                        job_id,
                        JobStage.EXTRAINDO_AUDIO,
                        20,
                        "Sem legenda pronta (ou transcrição IA forçada). Baixando faixa de áudio via yt-dlp...",
                    )
                    audio_path, meta = download_audio_from_url(url, Path(tmp_dir))
                    if not resolved_title:
                        resolved_title = meta.get("title") or f"Vídeo {video_id or 'Remoto'}"

                    transcriber = get_transcriber(settings)
                    provider_used = transcriber.provider_name
                    self._set_stage(
                        job_id,
                        JobStage.TRANSCREVENDO,
                        35,
                        f"Transcrevendo áudio baixado via {provider_used}...",
                    )
                    parsed = transcriber.transcribe(
                        audio_path,
                        glossary=settings.get("glossary_terms") or [],
                        language=language,
                        progress_cb=lambda msg, pct: self._set_stage(job_id, JobStage.TRANSCREVENDO, pct, msg),
                    )

            return self._run_llm_and_persist(
                job_id=job_id,
                parsed=parsed,
                title=resolved_title or "Vídeo Online",
                source_type="url",
                source_ref=url,
                template=template,
                transcriber_provider=provider_used,
                language=language,
                push_to_databricks=push_to_databricks,
                run_databricks_pipeline=run_databricks_pipeline,
            )
        except Exception as exc:
            if job_id:
                self.db.update_job(
                    job_id,
                    status="failed",
                    stage=JobStage.ERRO.value,
                    message=str(exc),
                    error=str(exc),
                )
            raise

    def push_document_to_databricks(self, doc_id: str, run_pipeline: bool = False) -> Dict[str, Any]:
        doc = self.db.get_document(doc_id)
        if not doc:
            raise FileNotFoundError(f"Documento {doc_id} não encontrado.")
        settings = self.db.get_settings(masked=False)

        safe_name = sanitize_filename(doc["title"])
        ext = ".srt" if doc.get("raw_srt") else ".txt"
        content = doc.get("raw_srt") or doc.get("clean_text") or ""

        with tempfile.TemporaryDirectory(prefix="mvi_dbx_") as tmp_dir:
            tmp_file = Path(tmp_dir) / f"{safe_name}_{doc_id[:8]}{ext}"
            tmp_file.write_text(content, encoding="utf-8")
            upload_res = upload_to_unity_catalog_volume(
                local_file=tmp_file,
                settings=settings,
                dest_filename=tmp_file.name,
            )

        self.db.mark_databricks_synced(doc_id, upload_res["volume_path"])
        result: Dict[str, Any] = {"upload": upload_res, "pipeline": None}
        if run_pipeline:
            result["pipeline"] = trigger_lakeflow_pipeline(settings)
        return result


pipeline = IngestionPipeline()
