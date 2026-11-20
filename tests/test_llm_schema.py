"""Testes de validação Pydantic do JSON estruturado extraído pela LLM e renderização da Ata."""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.schemas import StructuredAnalysis
from app.services.llm.base import extract_json_object, validate_and_normalize_analysis
from app.services.llm.heuristic import HeuristicLLMProvider


def test_extract_json_object_handles_markdown_fences():
    raw = """```json
    {
      "metadados": {"titulo": "Comitê Cloud"},
      "resumo_executivo": {"resumo_curto": "Discussão de FinOps.", "topicos_principais": ["FinOps"]},
      "decisoes": [{"decisao": "Adotar Serverless", "participantes_envolvidos": "Ana, Carlos"}],
      "pendencias": [{"descricao": "Aguardando aprovação de segurança"}],
      "action_items": [{"tarefa": "Criar dashboard", "prioridade": "HIGH", "status": "pending"}],
      "informacoes_chave": {"ferramentas_tecnologias": ["Databricks", "BigQuery"]}
    }
    ```"""
    obj = extract_json_object(raw)
    analysis = validate_and_normalize_analysis(
        obj,
        title="Fallback Title",
        language="pt-BR",
        duration_seconds=1800,
        duration_formatted="00:30:00",
        word_count=420,
        default_media_type="Reunião",
    )
    assert isinstance(analysis, StructuredAnalysis)
    assert analysis.metadados.titulo == "Comitê Cloud"
    assert analysis.decisoes[0].participantes_envolvidos == ["Ana", "Carlos"]
    assert analysis.action_items[0].prioridade == "Alta"
    assert analysis.action_items[0].status == "Pendente"
    assert "## Decisões Tomadas" in analysis.ata_markdown
    assert "## Action Items (Plano de Ação)" in analysis.ata_markdown


def test_heuristic_provider_extracts_entities_and_qa():
    provider = HeuristicLLMProvider()
    transcript = (
        "Ana: Decidimos migrar os jobs noturnos para Databricks Serverless com economia de 20% em DBU. "
        "Carlos: Ficou pendente a revisão das permissões no Unity Catalog pela equipe de Segurança. "
        "Pedro: Vou criar o relatório de FinOps até 30/11/2026 com prioridade urgente. "
        "Ana: Atenção ao risco de atraso se o acesso não for liberado."
    )
    analysis = provider.analyze_transcript(
        transcript_text=transcript,
        title="Alinhamento FinOps",
        template="Reunião Corporativa",
        categories=["Governança, Segurança & FinOps", "Geral / Outros"],
        glossary=["Databricks", "Unity Catalog", "FinOps"],
        language="pt-BR",
        duration_seconds=600,
        duration_formatted="00:10:00",
        word_count=len(transcript.split()),
        default_media_type="Reunião",
    )
    assert analysis.metadados.categoria_tematica == "Governança, Segurança & FinOps"
    assert len(analysis.decisoes) >= 1
    assert len(analysis.pendencias) >= 1
    assert len(analysis.action_items) >= 1
    assert "Databricks" in analysis.informacoes_chave.ferramentas_tecnologias
    assert any("20%" in m for m in analysis.informacoes_chave.metricas_citadas)

    qa = provider.answer_question(
        question="Qual foi a economia decidida no Databricks?",
        segments=[{"inicio": "00:01:15,000", "speaker": "Ana", "texto": "Decidimos migrar para Databricks com economia de 20%."}],
        summary_short=analysis.resumo_executivo.resumo_curto,
    )
    assert len(qa.citations) == 1
    assert qa.citations[0].timestamp == "00:01:15"
