"""
Gerenciamento de configurações da aplicação.
Prioridade:
1. Configurações salvas pelo usuário em SQLite (tabela app_settings)
2. Variáveis de ambiente / .env
3. Padrões seguros e genéricos (ZERO credenciais ou caminhos pessoais hardcoded)
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv

# Carrega .env da raiz do projeto se existir
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

DEFAULT_CATEGORIES: List[str] = [
    "Engenharia de Dados & Lakehouse",
    "Arquitetura Cloud & Infraestrutura",
    "Produto & Discovery de Cliente",
    "Alinhamento & Gestão de Equipe",
    "Treinamento & Aula Técnica",
    "Governança, Segurança & FinOps",
    "Geral / Outros",
]

DEFAULT_GLOSSARY: List[str] = [
    "Databricks",
    "Unity Catalog",
    "Lakeflow",
    "Delta Lake",
    "Spark",
    "Auto Loader",
    "AI Functions",
    "Genie Space",
    "BigQuery",
    "Dataflow",
    "FastAPI",
    "FinOps",
    "SLA",
    "KPI",
    "ETL",
    "ELT",
]

SECRET_FIELDS = {
    "gemini_api_key",
    "openai_api_key",
    "azure_openai_api_key",
    "databricks_token",
}


def get_data_dir() -> Path:
    raw = os.environ.get("DATA_DIR", "").strip()
    if raw:
        p = Path(raw)
        if not p.is_absolute():
            p = PROJECT_ROOT / p
    else:
        p = PROJECT_ROOT / "data"
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_db_path() -> Path:
    custom = os.environ.get("DATABASE_PATH", "").strip()
    if custom:
        p = Path(custom)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p
    return get_data_dir() / "meeting_intelligence.db"


def get_uploads_dir() -> Path:
    d = get_data_dir() / "uploads"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_exports_dir() -> Path:
    d = get_data_dir() / "exports"
    d.mkdir(parents=True, exist_ok=True)
    return d


DEFAULT_APP_HOST = "127.0.0.1"
DEFAULT_APP_PORT = 8185


def get_app_host() -> str:
    return os.environ.get("APP_HOST", DEFAULT_APP_HOST).strip() or DEFAULT_APP_HOST


def get_app_port() -> int:
    raw = os.environ.get("APP_PORT", str(DEFAULT_APP_PORT)).strip()
    try:
        return int(raw)
    except ValueError:
        return DEFAULT_APP_PORT


def get_cors_origins() -> List[str]:
    raw = os.environ.get(
        "CORS_ORIGINS",
        "http://mvi.localhost:5185,http://localhost:5185,http://127.0.0.1:5185,"
        "http://mvi.localhost:8185,http://localhost:8185,http://127.0.0.1:8185",
    )
    return [o.strip() for o in raw.split(",") if o.strip()]


def get_env_defaults() -> Dict[str, Any]:
    """Retorna os valores padrão lidos do ambiente (.env)."""
    return {
        "transcriber_provider": os.environ.get("TRANSCRIBER_PROVIDER", "gemini"),
        "gemini_transcription_model": os.environ.get("GEMINI_TRANSCRIPTION_MODEL", "gemini-2.5-flash"),
        "audio_chunk_minutes": int(os.environ.get("AUDIO_CHUNK_MINUTES", "20")),
        "whisper_model_size": os.environ.get("WHISPER_MODEL_SIZE", "small"),
        "whisper_device": os.environ.get("WHISPER_DEVICE", "auto"),
        "whisper_compute_type": os.environ.get("WHISPER_COMPUTE_TYPE", "int8"),
        "llm_provider": os.environ.get("LLM_PROVIDER", "gemini"),
        "gemini_api_key": os.environ.get("GEMINI_API_KEY", ""),
        "gemini_llm_model": os.environ.get("GEMINI_LLM_MODEL", "gemini-2.5-flash"),
        "openai_api_key": os.environ.get("OPENAI_API_KEY", ""),
        "openai_model": os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        "openai_base_url": os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        "azure_openai_endpoint": os.environ.get("AZURE_OPENAI_ENDPOINT", ""),
        "azure_openai_api_key": os.environ.get("AZURE_OPENAI_API_KEY", ""),
        "azure_openai_deployment": os.environ.get("AZURE_OPENAI_DEPLOYMENT", ""),
        "azure_openai_api_version": os.environ.get("AZURE_OPENAI_API_VERSION", "2024-10-21"),
        "ollama_base_url": os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
        "ollama_model": os.environ.get("OLLAMA_MODEL", "llama3.1:8b"),
        "databricks_host": os.environ.get("DATABRICKS_HOST", ""),
        "databricks_token": os.environ.get("DATABRICKS_TOKEN", ""),
        "databricks_profile": os.environ.get("DATABRICKS_PROFILE", ""),
        "databricks_catalog": os.environ.get("DATABRICKS_CATALOG", ""),
        "databricks_schema": os.environ.get("DATABRICKS_SCHEMA", ""),
        "databricks_volume_name": os.environ.get("DATABRICKS_VOLUME_NAME", "raw_transcripts"),
        "databricks_pipeline_id": os.environ.get("DATABRICKS_PIPELINE_ID", ""),
        "databricks_llm_endpoint": os.environ.get(
            "DATABRICKS_LLM_ENDPOINT",
            "system.ai.databricks-meta-llama-3-3-70b-instruct",
        ),
        "glossary_terms": DEFAULT_GLOSSARY.copy(),
        "categories": DEFAULT_CATEGORIES.copy(),
    }


def mask_secret(value: str) -> str:
    """Mascara chaves sensíveis para exibição segura na UI."""
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}{'*' * (len(value) - 8)}{value[-4:]}"


def parse_setting_value(raw_value: str) -> Any:
    try:
        return json.loads(raw_value)
    except Exception:
        return raw_value
