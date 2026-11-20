"""Testes ponta a ponta dos endpoints FastAPI (ingestão, jobs, biblioteca, checklist, Q&A, exportação e settings)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db import Database
from app.main import app
from app.routers import documents as doc_router
from app.routers import ingest as ingest_router
from app.routers import settings as settings_router
from app.services.pipeline import IngestionPipeline


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    isolated_db = Database(tmp_path / "api_test.db")
    isolated_db.update_settings({"llm_provider": "heuristic"})
    isolated_pipeline = IngestionPipeline(database=isolated_db)

    monkeypatch.setattr(ingest_router, "db", isolated_db)
    monkeypatch.setattr(ingest_router, "pipeline", isolated_pipeline)
    monkeypatch.setattr(doc_router, "db", isolated_db)
    monkeypatch.setattr(doc_router, "pipeline", isolated_pipeline)
    monkeypatch.setattr(settings_router, "db", isolated_db)

    return TestClient(app)


def test_full_api_lifecycle_text_and_file_ingest(client: TestClient):
    # Health
    assert client.get("/api/health").status_code == 200

    # 1. Ingestão de texto colado
    resp = client.post(
        "/api/ingest/text",
        json={
            "title": "Reunião Arquitetura Lakehouse",
            "text": (
                "Ana: Decidimos padronizar a camada Gold com Materialized Views no Databricks.\n"
                "Lucas: Ficou pendente definir o SLA de atualização com o time de BI.\n"
                "Carla: Vou configurar o alerta de custos até sexta-feira com prioridade urgente."
            ),
            "format_hint": "txt",
            "template": "Reunião Corporativa",
        },
    )
    assert resp.status_code == 200
    job_id = resp.json()["id"]

    # BackgroundTasks roda de forma síncrona no TestClient antes do retorno
    job_resp = client.get(f"/api/jobs/{job_id}")
    assert job_resp.status_code == 200
    job_data = job_resp.json()
    assert job_data["status"] == "completed"
    doc_id = job_data["document_id"]
    assert doc_id

    # 2. Listagem e busca na biblioteca
    lib = client.get("/api/documents", params={"search": "Lakehouse"})
    assert lib.status_code == 200
    assert len(lib.json()) == 1

    # 3. Detalhe do documento + checklist interativo de Action Item
    detail = client.get(f"/api/documents/{doc_id}").json()
    assert detail["title"] == "Reunião Arquitetura Lakehouse"
    assert len(detail["action_items"]) >= 1
    first_action_id = detail["action_items"][0]["id"]

    patch_resp = client.patch(
        f"/api/documents/{doc_id}/action-items/{first_action_id}",
        json={"status": "Concluído"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["status"] == "Concluído"

    # 4. Chat Q&A com citação
    chat_resp = client.post(
        f"/api/documents/{doc_id}/chat",
        json={"question": "O que foi decidido sobre Databricks?"},
    )
    assert chat_resp.status_code == 200
    assert len(chat_resp.json()["citations"]) >= 1

    # 5. Exportações (.md, .srt, .txt, .json)
    for fmt in ("md", "srt", "txt", "json"):
        exp = client.get(f"/api/documents/{doc_id}/export/{fmt}")
        assert exp.status_code == 200
        assert len(exp.text) > 10

    # 6. Upload de arquivo .vtt
    vtt_bytes = (
        "WEBVTT\n\n00:00:01.000 --> 00:00:05.000\n"
        "<v Pedro>Aprovamos o escopo da POC com GCP BigQuery.</v>\n"
    ).encode("utf-8")
    up = client.post(
        "/api/ingest/file",
        files={"file": ("reuniao_teams.vtt", vtt_bytes, "text/vtt")},
        data={"template": "Discovery/Cliente"},
    )
    assert up.status_code == 200
    assert client.get(f"/api/jobs/{up.json()['id']}").json()["status"] == "completed"

    # 7. Configurações (mascaramento de segredos)
    upd = client.put(
        "/api/settings",
        json={"settings": {"gemini_api_key": "AIzaSecretTestKey123456", "audio_chunk_minutes": 25}},
    )
    assert upd.status_code == 200
    assert "****" in upd.json()["gemini_api_key"]
    assert upd.json()["audio_chunk_minutes"] == 25
