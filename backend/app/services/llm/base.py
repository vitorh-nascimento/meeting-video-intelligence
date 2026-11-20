"""
Base e utilitários compartilhados para provedores de LLM plugáveis:
- Prompts estruturados por template (Reunião Corporativa, Aula/Vídeo Técnico, Discovery/Cliente)
- Validação estrita com Pydantic v2 (StructuredAnalysis)
- Gerador determinístico de Ata / Relatório em Markdown pronto para Teams/Slack/Confluence/Jira
"""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from app.schemas import (
    ChatAnswerResponse,
    ChatCitation,
    DocumentMetadata,
    ExecutiveSummary,
    KeyKnowledge,
    StructuredAnalysis,
)


TEMPLATE_GUIDANCE: Dict[str, str] = {
    "Reunião Corporativa": (
        "Foque fortemente em decisões aprovadas, pendências/bloqueios em aberto, donos (responsáveis), "
        "prazos explícitos ou implícitos, prioridades, riscos de negócio e alinhamentos entre áreas."
    ),
    "Aula/Vídeo Técnico": (
        "Foque fortemente em aprendizados técnicos, conceitos arquiteturais, boas práticas, "
        "ferramentas/tecnologias citadas, métricas/benchmarks e próximos passos práticos de estudo/implementação."
    ),
    "Discovery/Cliente": (
        "Foque fortemente em dores do cliente, requisitos funcionais e não-funcionais, restrições, "
        "dúvidas em aberto (pendências), compromissos assumidos, riscos de escopo e plano de ação de proposta/POC."
    ),
}


def build_analysis_prompt(
    *,
    transcript_text: str,
    title: str,
    template: str,
    categories: List[str],
    glossary: List[str],
    language: str,
    duration_seconds: int,
    duration_formatted: str,
    word_count: int,
) -> str:
    guidance = TEMPLATE_GUIDANCE.get(template, TEMPLATE_GUIDANCE["Reunião Corporativa"])
    cats_str = ", ".join(categories)
    glossary_str = ", ".join(glossary[:80]) if glossary else "N/A"
    # Limite seguro de caracteres para suportar vídeos longos sem estourar janelas menores
    max_chars = 180_000
    clipped_text = transcript_text[:max_chars]

    return f"""Você é um especialista sênior em Engenharia de Dados, Gestão de Projetos e Síntese Executiva.
Analise a transcrição abaixo usando o perfil/template: "{template}".
Diretriz do perfil: {guidance}

Contexto conhecido:
- Título sugerido: {title}
- Idioma: {language}
- Duração estimada: {duration_formatted} ({duration_seconds}s)
- Contagem aproximada de palavras: {word_count}
- Categorias temáticas permitidas (escolha a mais aderente): [{cats_str}]
- Glossário técnico de referência: [{glossary_str}]

Retorne EXCLUSIVAMENTE um objeto JSON válido seguindo exatamente esta estrutura:
{{
  "metadados": {{
    "titulo": "Título claro e descritivo",
    "tipo_midia": "Reunião | Vídeo Técnico/Aula | Áudio/Podcast | Entrevista | Outro",
    "idioma": "{language}",
    "duracao_estimada_segundos": {duration_seconds},
    "duracao_formatada": "{duration_formatted}",
    "contagem_palavras": {word_count},
    "categoria_tematica": "Uma das categorias permitidas"
  }},
  "resumo_executivo": {{
    "resumo_curto": "Parágrafo executivo objetivo (3 a 5 frases) sintetizando o propósito e resultado principal.",
    "topicos_principais": ["Tópico 1", "Tópico 2", "Tópico 3"]
  }},
  "decisoes": [
    {{
      "decisao": "Descrição clara da decisão tomada",
      "contexto": "Por que essa decisão foi tomada",
      "impacto": "Impacto esperado em custo, prazo, arquitetura ou negócio",
      "participantes_envolvidos": ["Nome ou Área"]
    }}
  ],
  "pendencias": [
    {{
      "descricao": "Bloqueio, dúvida em aberto ou dependência pendente",
      "responsavel_ou_area": "Responsável ou área (ou 'A definir')",
      "impacto": "Alto | Médio | Baixo",
      "status": "Pendente"
    }}
  ],
  "action_items": [
    {{
      "tarefa": "Ação concreta a ser executada",
      "responsavel": "Pessoa ou equipe (ou 'A definir')",
      "prazo": "Data ou marco citado (ou 'A definir')",
      "prioridade": "Alta | Média | Baixa",
      "status": "Pendente"
    }}
  ],
  "informacoes_chave": {{
    "insights": ["Principais insights e conclusões"],
    "aprendizados_tecnicos": ["Conceitos, arquiteturas e boas práticas explicadas"],
    "metricas_citadas": ["Números, percentuais, valores, SLAs ou metas mencionados"],
    "riscos": ["Riscos levantados durante a conversa"],
    "ferramentas_tecnologias": ["Tecnologias, plataformas e ferramentas citadas"]
  }},
  "ata_markdown": "Versão completa da Ata/Relatório em Markdown bem formatado pronto para copiar e colar em e-mail, Teams, Slack, Jira ou Confluence."
}}

Regras:
- Responda em Português do Brasil (a menos que a transcrição seja integralmente em outro idioma e faça sentido manter termos técnicos).
- Nunca invente informações ausentes da transcrição; se uma lista não tiver ocorrências reais, retorne [].
- Retorne SOMENTE o JSON válido, sem texto fora do JSON.

TRANSCRIÇÃO:
{clipped_text}
"""


def build_qa_prompt(
    *,
    question: str,
    segments: List[Dict[str, Any]],
    summary_short: str,
) -> str:
    lines: List[str] = []
    for seg in segments[:450]:
        ts = seg.get("inicio", "00:00:00,000").split(",")[0]
        speaker = seg.get("speaker")
        txt = seg.get("texto", "").strip()
        if not txt:
            continue
        prefix = f"[{ts}] {speaker}: " if speaker else f"[{ts}] "
        lines.append(f"{prefix}{txt}")

    transcript_with_ts = "\n".join(lines)[:120_000]
    return f"""Você é um assistente de Q&A especializado em analisar transcrições de reuniões e vídeos técnicos.
Responda à pergunta do usuário baseando-se EXCLUSIVAMENTE na transcrição com timestamps fornecida.
Sempre cite os trechos e timestamps [HH:MM:SS] que fundamentam sua resposta. Se a informação não estiver na transcrição, diga claramente que não foi mencionada.

Resumo do conteúdo: {summary_short}

Retorne EXCLUSIVAMENTE um JSON válido no formato:
{{
  "answer": "Resposta clara, direta e bem estruturada em português.",
  "citations": [
    {{"timestamp": "HH:MM:SS", "trecho": "Trecho relevante da transcrição"}}
  ]
}}

PERGUNTA DO USUÁRIO:
{question}

TRANSCRIÇÃO COM TIMESTAMPS:
{transcript_with_ts}
"""


def extract_json_object(raw_text: str) -> Dict[str, Any]:
    """Extrai objeto JSON mesmo se envolto em cercas ```json ... ``` ou texto auxiliar."""
    cleaned = raw_text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        obj = json.loads(cleaned)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = cleaned[start : end + 1]
        obj = json.loads(candidate)
        if isinstance(obj, dict):
            return obj
    raise ValueError("Não foi possível extrair um JSON válido da resposta da LLM.")


def render_ata_markdown(analysis: StructuredAnalysis) -> str:
    """Gera Ata / Relatório executivo em Markdown pronto para compartilhar."""
    m = analysis.metadados
    r = analysis.resumo_executivo
    k = analysis.informacoes_chave

    parts: List[str] = [
        f"# {m.titulo}",
        "",
        f"**Tipo:** {m.tipo_midia} | **Categoria:** {m.categoria_tematica} | **Duração:** {m.duracao_formatada} | **Palavras:** {m.contagem_palavras}",
        "",
        "## Resumo Executivo",
        r.resumo_curto or "_Sem resumo disponível._",
        "",
    ]

    if r.topicos_principais:
        parts.append("### Principais Tópicos Discutidos")
        for topic in r.topicos_principais:
            parts.append(f"- {topic}")
        parts.append("")

    if analysis.decisoes:
        parts.append("## Decisões Tomadas")
        for idx, d in enumerate(analysis.decisoes, start=1):
            who = f" _({', '.join(d.participantes_envolvidos)})_" if d.participantes_envolvidos else ""
            parts.append(f"{idx}. **{d.decisao}**{who}")
            if d.contexto:
                parts.append(f"   - Contexto: {d.contexto}")
            if d.impacto:
                parts.append(f"   - Impacto: {d.impacto}")
        parts.append("")

    if analysis.action_items:
        parts.append("## Action Items (Plano de Ação)")
        parts.append("| Tarefa | Responsável | Prazo | Prioridade | Status |")
        parts.append("|---|---|---|---|---|")
        for a in analysis.action_items:
            parts.append(f"| {a.tarefa} | {a.responsavel} | {a.prazo} | {a.prioridade} | {a.status} |")
        parts.append("")

    if analysis.pendencias:
        parts.append("## Pendências & Bloqueios em Aberto")
        for p in analysis.pendencias:
            parts.append(f"- **[{p.status}]** {p.descricao} — *Responsável/Área:* {p.responsavel_ou_area} (*Impacto:* {p.impacto})")
        parts.append("")

    has_knowledge = any(
        [k.insights, k.aprendizados_tecnicos, k.metricas_citadas, k.riscos, k.ferramentas_tecnologias]
    )
    if has_knowledge:
        parts.append("## Informações-Chave & Conhecimento")
        if k.insights:
            parts.append("### Insights")
            parts.extend([f"- {x}" for x in k.insights])
        if k.aprendizados_tecnicos:
            parts.append("### Aprendizados Técnicos")
            parts.extend([f"- {x}" for x in k.aprendizados_tecnicos])
        if k.metricas_citadas:
            parts.append("### Métricas & Números Citados")
            parts.extend([f"- {x}" for x in k.metricas_citadas])
        if k.riscos:
            parts.append("### Riscos Levantados")
            parts.extend([f"- {x}" for x in k.riscos])
        if k.ferramentas_tecnologias:
            parts.append("### Ferramentas & Tecnologias")
            parts.append(", ".join(f"`{t}`" for t in k.ferramentas_tecnologias))
        parts.append("")

    return "\n".join(parts).strip()


def validate_and_normalize_analysis(
    raw_obj: Dict[str, Any],
    *,
    title: str,
    language: str,
    duration_seconds: int,
    duration_formatted: str,
    word_count: int,
    default_media_type: str,
) -> StructuredAnalysis:
    """Valida o JSON retornado pela LLM contra Pydantic v2 e completa campos obrigatórios."""
    meta = dict(raw_obj.get("metadados") or {})
    meta.setdefault("titulo", title)
    meta.setdefault("tipo_midia", default_media_type)
    meta["idioma"] = meta.get("idioma") or language
    meta["duracao_estimada_segundos"] = int(meta.get("duracao_estimada_segundos") or duration_seconds)
    meta["duracao_formatada"] = meta.get("duracao_formatada") or duration_formatted
    meta["contagem_palavras"] = int(meta.get("contagem_palavras") or word_count)
    meta["categoria_tematica"] = meta.get("categoria_tematica") or "Geral / Outros"

    resumo = dict(raw_obj.get("resumo_executivo") or {})
    resumo.setdefault("resumo_curto", "")
    resumo.setdefault("topicos_principais", [])

    knowledge = dict(raw_obj.get("informacoes_chave") or {})

    normalized_payload = {
        "metadados": DocumentMetadata.model_validate(meta).model_dump(),
        "resumo_executivo": ExecutiveSummary.model_validate(resumo).model_dump(),
        "decisoes": raw_obj.get("decisoes") or [],
        "pendencias": raw_obj.get("pendencias") or [],
        "action_items": raw_obj.get("action_items") or [],
        "informacoes_chave": KeyKnowledge.model_validate(knowledge).model_dump(),
        "ata_markdown": str(raw_obj.get("ata_markdown") or "").strip(),
    }

    analysis = StructuredAnalysis.model_validate(normalized_payload)
    if len(analysis.ata_markdown) < 40:
        analysis.ata_markdown = render_ata_markdown(analysis)
    return analysis


class BaseLLMProvider(ABC):
    provider_name: str = "base"

    @abstractmethod
    def analyze_transcript(
        self,
        *,
        transcript_text: str,
        title: str,
        template: str,
        categories: List[str],
        glossary: List[str],
        language: str,
        duration_seconds: int,
        duration_formatted: str,
        word_count: int,
        default_media_type: str,
    ) -> StructuredAnalysis:
        raise NotImplementedError

    @abstractmethod
    def answer_question(
        self,
        *,
        question: str,
        segments: List[Dict[str, Any]],
        summary_short: str,
    ) -> ChatAnswerResponse:
        raise NotImplementedError

    def _parse_qa_json(self, raw_text: str) -> ChatAnswerResponse:
        try:
            obj = extract_json_object(raw_text)
            cits = [
                ChatCitation(
                    timestamp=str(c.get("timestamp", "00:00:00")),
                    trecho=str(c.get("trecho", "")),
                )
                for c in (obj.get("citations") or [])
                if isinstance(c, dict) and c.get("trecho")
            ]
            return ChatAnswerResponse(
                answer=str(obj.get("answer") or raw_text).strip(),
                citations=cits,
                provider=self.provider_name,
            )
        except Exception:
            return ChatAnswerResponse(
                answer=raw_text.strip(),
                citations=[],
                provider=self.provider_name,
            )
