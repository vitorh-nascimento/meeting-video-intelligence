"""
Rotas da Biblioteca de Documentos:
- Listagem filtrável (busca textual, tipo de mídia, categoria, intervalo de datas)
- Detalhe completo (Resumo, Ata, Decisões, Pendências, Action Items, Conhecimento, Transcrição)
- Checklist interativo de Action Items e Pendências
- Chat Q&A sobre a transcrição com citações de timestamp
- Exportação (.srt, .txt, .md, .json)
- Envio sob demanda para Volume do Databricks + trigger da pipeline Lakeflow
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse

from app.db import db
from app.schemas import (
    ActionItemUpdateRequest,
    ChatAnswerResponse,
    ChatQuestionRequest,
    DatabricksPushRequest,
    PendingUpdateRequest,
)
from app.services.databricks_sync import sanitize_filename
from app.services.llm import get_llm_provider
from app.services.pipeline import pipeline

router = APIRouter(prefix="/api/documents", tags=["Documentos"])


@router.get("")
def list_documents(
    search: Optional[str] = Query(default=None),
    media_type: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    date_from: Optional[str] = Query(default=None),
    date_to: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
) -> List[Dict[str, Any]]:
    return db.list_documents(
        search=search,
        media_type=media_type,
        category=category,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )


@router.get("/{doc_id}")
def get_document(doc_id: str) -> Dict[str, Any]:
    doc = db.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado.")
    return doc


@router.delete("/{doc_id}")
def delete_document(doc_id: str) -> Dict[str, Any]:
    deleted = db.delete_document(doc_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Documento não encontrado.")
    return {"deleted": True, "id": doc_id}


@router.patch("/{doc_id}/action-items/{item_id}")
def update_action_item(doc_id: str, item_id: int, payload: ActionItemUpdateRequest) -> Dict[str, Any]:
    updated = db.update_action_item(doc_id, item_id, payload.model_dump(exclude_none=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Action Item não encontrado.")
    return updated


@router.patch("/{doc_id}/pendings/{item_id}")
def update_pending_item(doc_id: str, item_id: int, payload: PendingUpdateRequest) -> Dict[str, Any]:
    updated = db.update_pending_item(doc_id, item_id, payload.model_dump(exclude_none=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Pendência não encontrada.")
    return updated


@router.post("/{doc_id}/chat", response_model=ChatAnswerResponse)
def chat_with_document(doc_id: str, payload: ChatQuestionRequest) -> ChatAnswerResponse:
    doc = db.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado.")

    settings = db.get_settings(masked=False)
    llm = get_llm_provider(settings, allow_heuristic_fallback=True)

    db.add_chat_message(doc_id, "user", payload.question)
    answer = llm.answer_question(
        question=payload.question,
        segments=doc.get("segments") or [],
        summary_short=doc.get("summary_short") or "",
    )
    db.add_chat_message(
        doc_id,
        "assistant",
        answer.answer,
        citations=[c.model_dump() for c in answer.citations],
    )
    return answer


@router.get("/{doc_id}/export/{fmt}")
def export_document(doc_id: str, fmt: str) -> PlainTextResponse:
    doc = db.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado.")

    fmt_lower = fmt.lower()
    base_name = sanitize_filename(doc["title"])

    if fmt_lower == "srt":
        content = doc.get("raw_srt") or ""
        media_type = "application/x-subrip; charset=utf-8"
        ext = "srt"
    elif fmt_lower == "txt":
        content = doc.get("clean_text") or ""
        media_type = "text/plain; charset=utf-8"
        ext = "txt"
    elif fmt_lower == "md":
        content = doc.get("ata_markdown") or ""
        media_type = "text/markdown; charset=utf-8"
        ext = "md"
    elif fmt_lower == "json":
        content = json.dumps(doc.get("analysis") or {}, ensure_ascii=False, indent=2)
        media_type = "application/json; charset=utf-8"
        ext = "json"
    else:
        raise HTTPException(status_code=400, detail="Formato inválido. Use: srt, txt, md ou json.")

    return PlainTextResponse(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{base_name}.{ext}"'},
    )


@router.post("/{doc_id}/push-databricks")
def push_to_databricks(doc_id: str, payload: DatabricksPushRequest) -> Dict[str, Any]:
    try:
        return pipeline.push_document_to_databricks(doc_id, run_pipeline=payload.run_pipeline)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
