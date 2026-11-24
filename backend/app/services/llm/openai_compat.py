"""
Provedores compatíveis com Chat Completions:
- OpenAI API
- Azure OpenAI
- Ollama (100% local, com suporte nativo a janela expandida num_ctx e Map-Reduce para vídeos > 1h/2h)
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Dict, List

from app.schemas import ChatAnswerResponse, StructuredAnalysis
from app.services.llm.base import (
    BaseLLMProvider,
    build_analysis_prompt,
    build_qa_prompt,
    extract_json_object,
    validate_and_normalize_analysis,
)


def _split_text_chunks(text: str, max_chars: int = 16_000, overlap: int = 600) -> List[str]:
    """Divide transcrições longas (>1h/2h) em blocos alinhados por quebra de linha/frase."""
    clean = (text or "").strip()
    if len(clean) <= max_chars:
        return [clean] if clean else []

    chunks: List[str] = []
    start = 0
    n = len(clean)
    while start < n:
        end = min(n, start + max_chars)
        if end < n:
            split_pos = clean.rfind("\n", start + max_chars // 2, end)
            if split_pos == -1:
                split_pos = clean.rfind(". ", start + max_chars // 2, end)
            if split_pos != -1 and split_pos > start:
                end = split_pos + 1
        part = clean[start:end].strip()
        if part:
            chunks.append(part)
        if end >= n:
            break
        start = max(end - overlap, start + 1)
    return chunks


class OpenAICompatLLMProvider(BaseLLMProvider):
    """Suporta OpenAI, Azure OpenAI e Ollama via API HTTP padrão (sem SDK obrigatório)."""

    def __init__(
        self,
        *,
        provider_name: str,
        endpoint_url: str,
        headers: Dict[str, str],
        model: str,
        use_json_mode: bool = True,
        ollama_native_chat_url: str = "",
        timeout_seconds: int = 240,
    ) -> None:
        self.provider_name = provider_name
        self.endpoint_url = endpoint_url
        self.headers = headers
        self.model = model
        self.use_json_mode = use_json_mode
        self.ollama_native_chat_url = ollama_native_chat_url
        self.timeout_seconds = timeout_seconds

    @classmethod
    def for_openai(
        cls, api_key: str, model: str = "gpt-4o-mini", base_url: str = "https://api.openai.com/v1"
    ) -> "OpenAICompatLLMProvider":
        if not api_key:
            raise ValueError("Chave OPENAI_API_KEY não configurada.")
        url = f"{base_url.rstrip('/')}/chat/completions"
        return cls(
            provider_name="openai",
            endpoint_url=url,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            model=model or "gpt-4o-mini",
            use_json_mode=True,
        )

    @classmethod
    def for_azure_openai(
        cls,
        endpoint: str,
        api_key: str,
        deployment: str,
        api_version: str = "2024-10-21",
    ) -> "OpenAICompatLLMProvider":
        if not (endpoint and api_key and deployment):
            raise ValueError(
                "Configure AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY e AZURE_OPENAI_DEPLOYMENT."
            )
        url = f"{endpoint.rstrip('/')}/openai/deployments/{deployment}/chat/completions?api-version={api_version}"
        return cls(
            provider_name="azure_openai",
            endpoint_url=url,
            headers={"api-key": api_key, "Content-Type": "application/json"},
            model=deployment,
            use_json_mode=True,
        )

    @classmethod
    def for_ollama(
        cls, base_url: str = "http://127.0.0.1:11434", model: str = "qwen2.5:7b"
    ) -> "OpenAICompatLLMProvider":
        root = base_url.rstrip("/")
        return cls(
            provider_name="ollama",
            endpoint_url=f"{root}/v1/chat/completions",
            ollama_native_chat_url=f"{root}/api/chat",
            headers={"Content-Type": "application/json"},
            model=model or "qwen2.5:7b",
            use_json_mode=True,
            timeout_seconds=600,
        )

    def _call_chat(self, prompt: str) -> str:
        # Para Ollama, usa /api/chat nativo para garantir num_ctx=16384 (evita truncar reuniões longas no default 4k)
        if self.provider_name == "ollama" and self.ollama_native_chat_url:
            native_payload: Dict[str, Any] = {
                "model": self.model,
                "stream": False,
                "format": "json",
                "options": {
                    "temperature": 0.2,
                    "num_ctx": 16384,
                },
                "messages": [
                    {
                        "role": "system",
                        "content": "Você responde sempre com um objeto JSON válido seguindo exatamente o schema solicitado, em Português do Brasil.",
                    },
                    {"role": "user", "content": prompt},
                ],
            }
            req = urllib.request.Request(
                self.ollama_native_chat_url,
                data=json.dumps(native_payload).encode("utf-8"),
                headers=self.headers,
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    return str(data["message"]["content"])
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")[:500]
                raise RuntimeError(f"Erro HTTP {exc.code} no Ollama ({self.model}): {detail}") from exc
            except urllib.error.URLError as exc:
                raise RuntimeError(
                    f"Não foi possível conectar ao Ollama em {self.ollama_native_chat_url}. "
                    f"Verifique se o serviço está rodando (`ollama serve`). Detalhe: {exc}"
                ) from exc

        payload: Dict[str, Any] = {
            "model": self.model,
            "temperature": 0.2,
            "messages": [
                {
                    "role": "system",
                    "content": "Você responde sempre com um objeto JSON válido seguindo exatamente o schema solicitado.",
                },
                {"role": "user", "content": prompt},
            ],
        }
        if self.use_json_mode:
            payload["response_format"] = {"type": "json_object"}

        req = urllib.request.Request(
            self.endpoint_url,
            data=json.dumps(payload).encode("utf-8"),
            headers=self.headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return str(data["choices"][0]["message"]["content"])
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise RuntimeError(f"Erro HTTP {exc.code} no provedor {self.provider_name}: {detail}") from exc

    def _analyze_long_transcript_map_reduce(
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
        """
        Estratégia Map-Reduce para vídeos longos (> 1h / > 2h) em modelos locais (Ollama):
        1. Extrai pontos estruturados de cada bloco (~16k chars / ~20 min) sem estourar num_ctx.
        2. Consolida todos os blocos em uma única ata estruturada sem duplicidades.
        """
        chunks = _split_text_chunks(transcript_text, max_chars=16_000, overlap=600)
        partials: List[Dict[str, Any]] = []

        for idx, chunk in enumerate(chunks, start=1):
            map_prompt = f"""Analise o BLOCO {idx} de {len(chunks)} da transcrição "{title}" (template: {template}).
Extraia APENAS o que aparece neste bloco em JSON válido:
{{
  "resumo_bloco": "Resumo objetivo deste trecho (2 a 4 frases)",
  "topicos": ["Tópico"],
  "decisoes": [{{"decisao": "...", "contexto": "...", "impacto": "...", "participantes_envolvidos": []}}],
  "pendencias": [{{"descricao": "...", "responsavel_ou_area": "A definir", "impacto": "Médio", "status": "Pendente"}}],
  "action_items": [{{"tarefa": "...", "responsavel": "A definir", "prazo": "A definir", "prioridade": "Média", "status": "Pendente"}}],
  "insights": [],
  "aprendizados_tecnicos": [],
  "metricas_citadas": [],
  "riscos": [],
  "ferramentas_tecnologias": []
}}

BLOCO {idx}/{len(chunks)}:
{chunk}
"""
            raw_part = self._call_chat(map_prompt)
            try:
                partials.append(extract_json_object(raw_part))
            except Exception:
                partials.append({"resumo_bloco": raw_part[:800]})

        consolidated_source = (
            f"CONSOLIDAÇÃO DE {len(chunks)} BLOCOS DE UMA GRAVAÇÃO LONGA ({duration_formatted}):\n"
            + json.dumps(partials, ensure_ascii=False, indent=2)
        )
        reduce_prompt = build_analysis_prompt(
            transcript_text=consolidated_source,
            title=title,
            template=template,
            categories=categories,
            glossary=glossary,
            language=language,
            duration_seconds=duration_seconds,
            duration_formatted=duration_formatted,
            word_count=word_count,
        )
        raw_final = self._call_chat(reduce_prompt)
        parsed = extract_json_object(raw_final)
        return validate_and_normalize_analysis(
            parsed,
            title=title,
            language=language,
            duration_seconds=duration_seconds,
            duration_formatted=duration_formatted,
            word_count=word_count,
            default_media_type=default_media_type,
        )

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
        # Vídeos longos (> 1h / > 20k caracteres) no Ollama usam Map-Reduce para não estourar contexto local
        if self.provider_name == "ollama" and len(transcript_text) > 20_000:
            return self._analyze_long_transcript_map_reduce(
                transcript_text=transcript_text,
                title=title,
                template=template,
                categories=categories,
                glossary=glossary,
                language=language,
                duration_seconds=duration_seconds,
                duration_formatted=duration_formatted,
                word_count=word_count,
                default_media_type=default_media_type,
            )

        prompt = build_analysis_prompt(
            transcript_text=transcript_text,
            title=title,
            template=template,
            categories=categories,
            glossary=glossary,
            language=language,
            duration_seconds=duration_seconds,
            duration_formatted=duration_formatted,
            word_count=word_count,
        )
        raw_text = self._call_chat(prompt)
        parsed = extract_json_object(raw_text)
        return validate_and_normalize_analysis(
            parsed,
            title=title,
            language=language,
            duration_seconds=duration_seconds,
            duration_formatted=duration_formatted,
            word_count=word_count,
            default_media_type=default_media_type,
        )

    def answer_question(
        self,
        *,
        question: str,
        segments: List[Dict[str, Any]],
        summary_short: str,
    ) -> ChatAnswerResponse:
        prompt = build_qa_prompt(question=question, segments=segments, summary_short=summary_short)
        raw_text = self._call_chat(prompt)
        return self._parse_qa_json(raw_text)
