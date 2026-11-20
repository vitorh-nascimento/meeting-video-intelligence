"""Testes do fluxo de ingestão unificada, fallback YouTube -> yt-dlp -> IA e vídeos locais."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db import Database
from app.services.media import extract_youtube_video_id
from app.services.pipeline import IngestionPipeline


def test_extract_youtube_video_id_variants():
    assert extract_youtube_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert extract_youtube_video_id("https://youtu.be/dQw4w9WgXcQ?t=30") == "dQw4w9WgXcQ"
    assert extract_youtube_video_id("https://www.youtube.com/shorts/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert extract_youtube_video_id("https://vimeo.com/123456789") is None


def test_url_fallback_when_youtube_has_no_captions(tmp_path: Path):
    test_db = Database(tmp_path / "test.db")
    test_db.update_settings({"llm_provider": "heuristic", "transcriber_provider": "gemini"})
    pipe = IngestionPipeline(database=test_db)

    fake_audio = tmp_path / "fake_audio.m4a"
    fake_audio.write_bytes(b"FAKEAUDIO")

    mock_transcriber = MagicMock()
    mock_transcriber.provider_name = "gemini"
    mock_transcriber.transcribe.return_value = {
        "formato": "srt",
        "total_segmentos": 2,
        "total_palavras": 24,
        "duracao_segundos": 3620,
        "duracao_formatada": "01:00:20",
        "texto_completo": (
            "Ana: Decidimos adotar Databricks Lakeflow para o pipeline de eventos. "
            "Carlos vai entregar o protótipo até sexta-feira com redução de 25% em custos."
        ),
        "conteudo_srt": "1\n00:00:01,000 --> 01:00:20,000\nAna: Decidimos adotar Databricks Lakeflow.",
        "segmentos": [
            {
                "index": 1,
                "inicio": "00:00:01,000",
                "fim": "01:00:20,000",
                "start_seconds": 1.0,
                "end_seconds": 3620.0,
                "speaker": "Ana",
                "texto": "Decidimos adotar Databricks Lakeflow para o pipeline de eventos.",
            }
        ],
        "idioma": "pt-BR",
    }

    with (
        patch("app.services.pipeline.download_youtube_transcript", side_effect=RuntimeError("No captions")),
        patch("app.services.pipeline.download_audio_from_url", return_value=(fake_audio, {"title": "Aula Longa Lakehouse"})),
        patch("app.services.pipeline.get_transcriber", return_value=mock_transcriber),
    ):
        doc = pipe.process_url(
            url="https://www.youtube.com/watch?v=abc12345678",
            template="Aula/Vídeo Técnico",
        )

    assert doc["title"] == "Aula Longa Lakehouse"
    assert doc["transcriber_provider"] == "gemini"
    assert doc["duration_seconds"] == 3620
    assert len(doc["decisions"]) >= 1
    assert len(doc["action_items"]) >= 1
    mock_transcriber.transcribe.assert_called_once()


def test_local_video_upload_extracts_audio_and_transcribes(tmp_path: Path):
    test_db = Database(tmp_path / "test_video.db")
    test_db.update_settings({"llm_provider": "heuristic"})
    pipe = IngestionPipeline(database=test_db)

    fake_video = tmp_path / "reuniao_privada_teams.mp4"
    fake_video.write_bytes(b"FAKEVIDEO")
    fake_extracted_audio = tmp_path / "extracted.mp3"
    fake_extracted_audio.write_bytes(b"FAKEAUDIO")

    mock_transcriber = MagicMock()
    mock_transcriber.provider_name = "local_whisper"
    mock_transcriber.transcribe.return_value = {
        "formato": "srt",
        "total_segmentos": 1,
        "total_palavras": 18,
        "duracao_segundos": 900,
        "duracao_formatada": "00:15:00",
        "texto_completo": "Mariana: Ficou pendente validar o acesso ao Unity Catalog. João vai enviar o documento amanhã.",
        "conteudo_srt": "1\n00:00:00,000 --> 00:15:00,000\nMariana: Ficou pendente validar o acesso.",
        "segmentos": [
            {
                "index": 1,
                "inicio": "00:00:00,000",
                "fim": "00:15:00,000",
                "start_seconds": 0.0,
                "end_seconds": 900.0,
                "speaker": "Mariana",
                "texto": "Ficou pendente validar o acesso ao Unity Catalog. João vai enviar o documento amanhã.",
            }
        ],
        "idioma": "pt-BR",
    }

    with (
        patch("app.services.pipeline.extract_and_compress_audio", return_value=fake_extracted_audio) as mock_ext,
        patch("app.services.pipeline.get_transcriber", return_value=mock_transcriber),
    ):
        doc = pipe.process_file(file_path=fake_video, template="Reunião Corporativa")

    mock_ext.assert_called_once()
    assert doc["transcriber_provider"] == "local_whisper"
    assert doc["llm_provider"] == "heuristic"
    assert len(doc["pendings"]) >= 1 or len(doc["action_items"]) >= 1
