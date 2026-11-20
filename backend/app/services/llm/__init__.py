"""Fábrica plugável de provedores LLM com fallback seguro para modo heurístico."""

from __future__ import annotations

from typing import Any, Dict

from app.services.llm.base import BaseLLMProvider
from app.services.llm.databricks import DatabricksLLMProvider
from app.services.llm.gemini import GeminiLLMProvider
from app.services.llm.heuristic import HeuristicLLMProvider
from app.services.llm.openai_compat import OpenAICompatLLMProvider


def get_llm_provider(settings: Dict[str, Any], allow_heuristic_fallback: bool = True) -> BaseLLMProvider:
    provider = str(settings.get("llm_provider", "gemini")).strip().lower()

    if provider == "heuristic":
        return HeuristicLLMProvider()

    if provider == "gemini":
        api_key = str(settings.get("gemini_api_key", "")).strip()
        if api_key:
            return GeminiLLMProvider(
                api_key=api_key,
                model=str(settings.get("gemini_llm_model", "gemini-2.5-flash")).strip(),
            )

    elif provider == "openai":
        api_key = str(settings.get("openai_api_key", "")).strip()
        if api_key:
            return OpenAICompatLLMProvider.for_openai(
                api_key=api_key,
                model=str(settings.get("openai_model", "gpt-4o-mini")).strip(),
                base_url=str(settings.get("openai_base_url", "https://api.openai.com/v1")).strip(),
            )

    elif provider == "azure_openai":
        ep = str(settings.get("azure_openai_endpoint", "")).strip()
        key = str(settings.get("azure_openai_api_key", "")).strip()
        dep = str(settings.get("azure_openai_deployment", "")).strip()
        ver = str(settings.get("azure_openai_api_version", "2024-10-21")).strip()
        if ep and key and dep:
            return OpenAICompatLLMProvider.for_azure_openai(ep, key, dep, ver)

    elif provider == "databricks":
        host = str(settings.get("databricks_host", "")).strip()
        token = str(settings.get("databricks_token", "")).strip()
        ep = str(settings.get("databricks_llm_endpoint", "")).strip()
        if host and token:
            return DatabricksLLMProvider(host=host, token=token, endpoint_name=ep)

    elif provider == "ollama":
        return OpenAICompatLLMProvider.for_ollama(
            base_url=str(settings.get("ollama_base_url", "http://127.0.0.1:11434")).strip(),
            model=str(settings.get("ollama_model", "llama3.1:8b")).strip(),
        )

    if allow_heuristic_fallback:
        return HeuristicLLMProvider()

    raise ValueError(
        f"Credenciais ausentes para o provedor LLM '{provider}'. Configure em Configurações ou no arquivo .env."
    )


__all__ = [
    "BaseLLMProvider",
    "DatabricksLLMProvider",
    "GeminiLLMProvider",
    "HeuristicLLMProvider",
    "OpenAICompatLLMProvider",
    "get_llm_provider",
]
