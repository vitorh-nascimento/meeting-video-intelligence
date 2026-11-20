"""
Provedor Heurístico Offline (Fallback Determinístico).
Permite testar, demonstrar e executar a aplicação 100% offline mesmo sem API Keys,
produzindo JSON estruturado válido, Ata Markdown e Q&A com citações por timestamp.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

from app.schemas import ChatAnswerResponse, ChatCitation, StructuredAnalysis
from app.services.llm.base import BaseLLMProvider, render_ata_markdown, validate_and_normalize_analysis

DECISION_RE = re.compile(r"\b(decidimos|aprovado|aprovamos|definimos|ficou definido|escolhemos|vamos adotar|decisão)\b", re.IGNORECASE)
PENDING_RE = re.compile(r"\b(pendência|pendencia|pendente|pendentes|bloqueio|bloqueado|aguardando|dúvida|duvida|em aberto|depende de)\b", re.IGNORECASE)
ACTION_RE = re.compile(r"\b(action item|vai entregar|vai fazer|precisa|responsável|responsavel|configurar|criar|enviar|implementar|validar|até dia|prazo)\b", re.IGNORECASE)
RISK_RE = re.compile(r"\b(risco|atenção|cuidado|alerta|custo alto|atraso|falha|limitação)\b", re.IGNORECASE)
METRIC_RE = re.compile(r"(\d+(?:[.,]\d+)?\s*(?:%|mil|milhões|milhoes|horas|dias|ms|gb|mb|tb|dbu|r\$|usd|\$))", re.IGNORECASE)
DEADLINE_RE = re.compile(r"\b(\d{1,2}/\d{1,2}(?:/\d{2,4})?|sexta(?:-feira)?|segunda(?:-feira)?|amanhã|próxima semana|fim da sprint|fim do mês)\b", re.IGNORECASE)
SPEAKER_RE = re.compile(r"^([A-ZÀ-Ú][a-zà-ú]+(?:\s+[A-ZÀ-Ú][a-zà-ú]+)?):\s*")


class HeuristicLLMProvider(BaseLLMProvider):
    provider_name = "heuristic"

    def _split_sentences(self, text: str) -> List[str]:
        parts = re.split(r"(?<=[\.\!\?\n])\s+", text.strip())
        return [p.strip() for p in parts if len(p.strip()) >= 15]

    def _pick_category(self, text: str, categories: List[str]) -> str:
        lower = text.lower()
        keyword_map = [
            (["finops", "custo", "dbu", "governança", "segurança", "lgpd", "permissões"], "Governança, Segurança & FinOps"),
            (["databricks", "lakehouse", "spark", "delta", "unity catalog", "dlt", "etl"], "Engenharia de Dados & Lakehouse"),
            (["gcp", "aws", "azure", "cloud", "bigquery", "dataflow", "kubernetes"], "Arquitetura Cloud & Infraestrutura"),
            (["cliente", "discovery", "requisito", "proposta", "escopo"], "Produto & Discovery de Cliente"),
            (["aula", "curso", "treinamento", "exame", "conceito", "tutorial"], "Treinamento & Aula Técnica"),
            (["sprint", "equipe", "reunião", "alinhamento", "roadmap"], "Alinhamento & Gestão de Equipe"),
        ]
        best_cat: str | None = None
        best_score = 0
        for kws, preferred in keyword_map:
            score = sum(1 for kw in kws if kw in lower)
            if score <= 0:
                continue
            matched = next(
                (cat for cat in categories if preferred.lower() in cat.lower() or cat.lower() in preferred.lower()),
                None,
            )
            if matched and score > best_score:
                best_score = score
                best_cat = matched
        if best_cat:
            return best_cat
        return categories[-1] if categories else "Geral / Outros"

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
        sentences = self._split_sentences(transcript_text)
        summary_short = " ".join(sentences[:3]) if sentences else transcript_text[:400]
        if len(summary_short) > 650:
            summary_short = summary_short[:647].rstrip() + "..."

        topicos: List[str] = []
        decisoes: List[Dict[str, Any]] = []
        pendencias: List[Dict[str, Any]] = []
        action_items: List[Dict[str, Any]] = []
        riscos: List[str] = []
        insights: List[str] = []

        for sent in sentences:
            sp_match = SPEAKER_RE.match(sent)
            speaker = sp_match.group(1) if sp_match else "A definir"
            clean_sent = SPEAKER_RE.sub("", sent).strip()

            if DECISION_RE.search(clean_sent) and len(decisoes) < 8:
                decisoes.append(
                    {
                        "decisao": clean_sent,
                        "contexto": f"Identificado no contexto de {template}.",
                        "impacto": "Direcionamento acordado na discussão.",
                        "participantes_envolvidos": [speaker] if speaker != "A definir" else [],
                    }
                )
            elif PENDING_RE.search(clean_sent) and len(pendencias) < 8:
                pendencias.append(
                    {
                        "descricao": clean_sent,
                        "responsavel_ou_area": speaker,
                        "impacto": "Médio",
                        "status": "Pendente",
                    }
                )
            elif ACTION_RE.search(clean_sent) and len(action_items) < 10:
                dl_match = DEADLINE_RE.search(clean_sent)
                prazo = dl_match.group(1) if dl_match else "A definir"
                prioridade = "Alta" if re.search(r"urgente|crític|imediato|hoje|amanhã", clean_sent, re.IGNORECASE) else "Média"
                action_items.append(
                    {
                        "tarefa": clean_sent,
                        "responsavel": speaker,
                        "prazo": prazo,
                        "prioridade": prioridade,
                        "status": "Pendente",
                    }
                )

            if RISK_RE.search(clean_sent) and len(riscos) < 6:
                riscos.append(clean_sent)

            if len(topicos) < 5 and len(clean_sent) <= 180:
                topicos.append(clean_sent)

        if not insights and sentences:
            insights = sentences[:3]

        # Tecnologias encontradas a partir do glossário + vocabulário comum
        tech_pool = list(dict.fromkeys(glossary + ["Python", "SQL", "FastAPI", "React", "Docker", "Kubernetes", "Power BI", "Apache Beam", "Spark", "Databricks", "BigQuery", "AWS", "Azure", "GCP"]))
        found_techs = [
            term for term in tech_pool if re.search(rf"\b{re.escape(term)}\b", transcript_text, re.IGNORECASE)
        ][:15]

        metrics = list(dict.fromkeys(m.group(1).strip() for m in METRIC_RE.finditer(transcript_text)))[:10]
        category = self._pick_category(transcript_text, categories)

        raw_obj = {
            "metadados": {
                "titulo": title,
                "tipo_midia": default_media_type,
                "idioma": language,
                "duracao_estimada_segundos": duration_seconds,
                "duracao_formatada": duration_formatted,
                "contagem_palavras": word_count,
                "categoria_tematica": category,
            },
            "resumo_executivo": {
                "resumo_curto": summary_short,
                "topicos_principais": topicos[:5],
            },
            "decisoes": decisoes,
            "pendencias": pendencias,
            "action_items": action_items,
            "informacoes_chave": {
                "insights": insights[:5],
                "aprendizados_tecnicos": insights[:3] if "Aula" in template else [],
                "metricas_citadas": metrics,
                "riscos": riscos,
                "ferramentas_tecnologias": found_techs,
            },
            "ata_markdown": "",
        }
        analysis = validate_and_normalize_analysis(
            raw_obj,
            title=title,
            language=language,
            duration_seconds=duration_seconds,
            duration_formatted=duration_formatted,
            word_count=word_count,
            default_media_type=default_media_type,
        )
        analysis.ata_markdown = render_ata_markdown(analysis)
        return analysis

    def answer_question(
        self,
        *,
        question: str,
        segments: List[Dict[str, Any]],
        summary_short: str,
    ) -> ChatAnswerResponse:
        stop_words = {"como", "qual", "quais", "para", "sobre", "quem", "onde", "quando", "porque", "isso", "essa", "este", "esta", "foram", "foi", "uma", "uns", "das", "dos", "que", "com", "por"}
        tokens = [
            t.lower()
            for t in re.findall(r"[a-zA-ZÀ-ÿ0-9]{3,}", question)
            if t.lower() not in stop_words
        ]

        scored: List[tuple[int, Dict[str, Any]]] = []
        for seg in segments:
            text = str(seg.get("texto", ""))
            lower = text.lower()
            score = sum(1 for tok in tokens if tok in lower)
            if score > 0:
                scored.append((score, seg))

        scored.sort(key=lambda item: item[0], reverse=True)
        top_matches = [seg for _, seg in scored[:4]]

        if not top_matches:
            return ChatAnswerResponse(
                answer=(
                    "Não encontrei trechos diretos correspondentes à sua pergunta no modo offline heurístico. "
                    f"Resumo disponível: {summary_short}"
                ),
                citations=[],
                provider=self.provider_name,
            )

        citations = [
            ChatCitation(
                timestamp=str(seg.get("inicio", "00:00:00,000")).split(",")[0],
                trecho=(
                    f"{seg['speaker']}: {seg['texto']}"
                    if seg.get("speaker")
                    else str(seg.get("texto", ""))
                ),
            )
            for seg in top_matches
        ]
        bullet_lines = "\n".join(f"- [{c.timestamp}] {c.trecho}" for c in citations)
        answer = (
            "Com base nos trechos mais relevantes encontrados na transcrição:\n\n"
            f"{bullet_lines}\n\n"
            "*(Resposta gerada em modo offline heurístico; configure Gemini, OpenAI, Databricks ou Ollama em Configurações para síntese generativa avançada.)*"
        )
        return ChatAnswerResponse(answer=answer, citations=citations, provider=self.provider_name)
