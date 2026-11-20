"""Provedor LLM Google Gemini API com Structured JSON Output."""

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


class GeminiLLMProvider(BaseLLMProvider):
    provider_name = "gemini"

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash") -> None:
        self.api_key = api_key
        self.model = model or "gemini-2.5-flash"

    def _generate_json(self, prompt: str) -> str:
        if not self.api_key:
            raise ValueError("Chave GEMINI_API_KEY não configurada.")
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent?key={self.api_key}"
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json",
                "maxOutputTokens": 16384,
            },
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                candidates = data.get("candidates", [])
                if not candidates:
                    raise RuntimeError("Resposta vazia do Google Gemini.")
                return str(candidates[0].get("content", {}).get("parts", [{}])[0].get("text", ""))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise RuntimeError(f"Erro HTTP {exc.code} na Gemini API: {detail}") from exc

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
        raw_text = self._generate_json(prompt)
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
        raw_text = self._generate_json(prompt)
        return self._parse_qa_json(raw_text)
