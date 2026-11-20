"""
Provedor LLM Databricks Model Serving / Foundation Model APIs.
Suporta tanto endpoints Unity Gateway (ex.: system.ai.*) quanto endpoints customizados.
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


class DatabricksLLMProvider(BaseLLMProvider):
    provider_name = "databricks"

    def __init__(self, host: str, token: str, endpoint_name: str) -> None:
        self.host = host.rstrip("/")
        self.token = token
        self.endpoint_name = endpoint_name or "system.ai.databricks-meta-llama-3-3-70b-instruct"

    def _call_serving(self, prompt: str) -> str:
        if not (self.host and self.token):
            raise ValueError("Configure DATABRICKS_HOST e DATABRICKS_TOKEN para usar o provedor Databricks LLM.")

        # Endpoints Unity Catalog / Foundation Models usam /serving-endpoints/{name}/invocations
        url = f"{self.host}/serving-endpoints/{self.endpoint_name}/invocations"
        payload = {
            "messages": [
                {
                    "role": "system",
                    "content": "Retorne estritamente um JSON válido seguindo o schema solicitado.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "max_tokens": 8192,
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=240) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if "choices" in data:
                    return str(data["choices"][0]["message"]["content"])
                if "predictions" in data and data["predictions"]:
                    return str(data["predictions"][0])
                return json.dumps(data, ensure_ascii=False)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise RuntimeError(f"Erro HTTP {exc.code} no Databricks Model Serving: {detail}") from exc

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
        raw_text = self._call_serving(prompt)
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
        raw_text = self._call_serving(prompt)
        return self._parse_qa_json(raw_text)
