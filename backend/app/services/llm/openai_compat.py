"""
Provedores compatíveis com Chat Completions:
- OpenAI API
- Azure OpenAI
- Ollama (100% local)
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
    ) -> None:
        self.provider_name = provider_name
        self.endpoint_url = endpoint_url
        self.headers = headers
        self.model = model
        self.use_json_mode = use_json_mode

    @classmethod
    def for_openai(cls, api_key: str, model: str = "gpt-4o-mini", base_url: str = "https://api.openai.com/v1") -> "OpenAICompatLLMProvider":
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
            raise ValueError("Configure AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY e AZURE_OPENAI_DEPLOYMENT.")
        url = f"{endpoint.rstrip('/')}/openai/deployments/{deployment}/chat/completions?api-version={api_version}"
        return cls(
            provider_name="azure_openai",
            endpoint_url=url,
            headers={"api-key": api_key, "Content-Type": "application/json"},
            model=deployment,
            use_json_mode=True,
        )

    @classmethod
    def for_ollama(cls, base_url: str = "http://127.0.0.1:11434", model: str = "llama3.1:8b") -> "OpenAICompatLLMProvider":
        url = f"{base_url.rstrip('/')}/v1/chat/completions"
        return cls(
            provider_name="ollama",
            endpoint_url=url,
            headers={"Content-Type": "application/json"},
            model=model or "llama3.1:8b",
            use_json_mode=True,
        )

    def _call_chat(self, prompt: str) -> str:
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
            with urllib.request.urlopen(req, timeout=240) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return str(data["choices"][0]["message"]["content"])
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise RuntimeError(f"Erro HTTP {exc.code} no provedor {self.provider_name}: {detail}") from exc

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
