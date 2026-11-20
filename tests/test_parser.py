"""Testes unitários do TranscriptParser (.srt, .vtt Teams/Zoom, .txt, .json e merge de chunks)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.parser import (
    TranscriptParser,
    format_timestamp_srt,
    parse_timestamp_to_seconds,
)


def test_parse_srt_with_html_and_speakers():
    srt = """1
00:00:01,000 --> 00:00:05,500
<i>Ana:</i> Decidimos migrar para Serverless Compute.

2
00:00:06,000 --> 00:00:11,250
Carlos: Vou configurar o alerta de custos até sexta-feira.
"""
    parsed = TranscriptParser.parse_srt(srt)
    assert parsed["formato"] == "srt"
    assert parsed["total_segmentos"] == 2
    assert parsed["segmentos"][0]["speaker"] == "Ana"
    assert "migrar para Serverless" in parsed["segmentos"][0]["texto"]
    assert parsed["segmentos"][1]["speaker"] == "Carlos"
    assert parsed["duracao_segundos"] == 11
    assert "00:00:06,000 --> 00:00:11,250" in parsed["conteudo_srt"]


def test_parse_vtt_teams_format():
    vtt = """WEBVTT
Kind: captions
Language: pt-BR

00:00:02.000 --> 00:00:07.500
<v Maria Silva>Aprovamos o orçamento de FinOps para o Q4.</v>

00:01:05.200 --> 00:01:12.000
<v João Pereira>Ficou pendente a liberação do Unity Catalog pela área de Segurança.</v>
"""
    parsed = TranscriptParser.parse_vtt(vtt)
    assert parsed["formato"] == "vtt"
    assert parsed["total_segmentos"] == 2
    assert parsed["segmentos"][0]["speaker"] == "Maria Silva"
    assert parsed["segmentos"][1]["speaker"] == "João Pereira"
    assert parsed["duracao_segundos"] == 72


def test_parse_json_whisper_style():
    payload = json.dumps(
        [
            {"start": 0.0, "end": 4.2, "text": "Bem-vindos à aula de Databricks Lakeflow."},
            {"start": 4.5, "end": 9.8, "text": "Hoje veremos Auto Loader e AI Functions."},
        ]
    )
    parsed = TranscriptParser.parse_content(payload, format_hint="auto")
    assert parsed["formato"] == "json"
    assert parsed["total_segmentos"] == 2
    assert parsed["duracao_segundos"] == 10
    assert "Auto Loader" in parsed["texto_completo"]


def test_merge_srt_chunks_applies_offset_for_long_videos():
    chunk_1 = """1
00:00:10,000 --> 00:00:20,000
Início da primeira hora de treinamento.
"""
    chunk_2 = """1
00:00:05,000 --> 00:00:15,000
Conteúdo após 20 minutos de vídeo.
"""
    merged = TranscriptParser.merge_srt_chunks([(chunk_1, 0.0), (chunk_2, 1200.0)])
    assert merged["total_segmentos"] == 2
    assert merged["segmentos"][0]["inicio"] == "00:00:10,000"
    assert merged["segmentos"][1]["inicio"] == "00:20:05,000"
    assert merged["segmentos"][1]["fim"] == "00:20:15,000"
    assert merged["duracao_segundos"] == 1215


def test_timestamp_roundtrip():
    sec = parse_timestamp_to_seconds("01:23:45,678")
    assert round(sec, 3) == 5025.678
    assert format_timestamp_srt(sec) == "01:23:45,678"
