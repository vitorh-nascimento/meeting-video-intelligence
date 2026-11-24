"""
Camada de persistência SQLite (WAL mode) para histórico de documentos,
jobs assíncronos, decisões, pendências, action items, chat Q&A e configurações.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from app.config import SECRET_FIELDS, get_db_path, get_env_defaults, mask_secret, parse_setting_value


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


class Database:
    """Gerenciador SQLite thread-safe em WAL mode."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path = Path(db_path) if db_path else get_db_path()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=30.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        conn = self._connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init_schema(self) -> None:
        with self.transaction() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    progress INTEGER NOT NULL DEFAULT 0,
                    message TEXT NOT NULL DEFAULT '',
                    source_type TEXT NOT NULL,
                    source_ref TEXT NOT NULL DEFAULT '',
                    title TEXT NOT NULL DEFAULT '',
                    template TEXT NOT NULL DEFAULT 'Reunião Corporativa',
                    document_id TEXT,
                    error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    source_ref TEXT NOT NULL DEFAULT '',
                    media_type TEXT NOT NULL DEFAULT 'Reunião',
                    template TEXT NOT NULL DEFAULT 'Reunião Corporativa',
                    category TEXT NOT NULL DEFAULT 'Geral / Outros',
                    language TEXT NOT NULL DEFAULT 'pt-BR',
                    duration_seconds INTEGER NOT NULL DEFAULT 0,
                    duration_formatted TEXT NOT NULL DEFAULT '00:00:00',
                    word_count INTEGER NOT NULL DEFAULT 0,
                    transcriber_provider TEXT NOT NULL DEFAULT 'native',
                    llm_provider TEXT NOT NULL DEFAULT 'heuristic',
                    transcript_format TEXT NOT NULL DEFAULT 'srt',
                    raw_srt TEXT NOT NULL DEFAULT '',
                    clean_text TEXT NOT NULL DEFAULT '',
                    segments_json TEXT NOT NULL DEFAULT '[]',
                    summary_short TEXT NOT NULL DEFAULT '',
                    summary_bullets_json TEXT NOT NULL DEFAULT '[]',
                    knowledge_json TEXT NOT NULL DEFAULT '{}',
                    ata_markdown TEXT NOT NULL DEFAULT '',
                    analysis_json TEXT NOT NULL DEFAULT '{}',
                    databricks_synced_at TEXT,
                    databricks_volume_path TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id TEXT NOT NULL,
                    decisao TEXT NOT NULL,
                    contexto TEXT NOT NULL DEFAULT '',
                    impacto TEXT NOT NULL DEFAULT '',
                    participantes_json TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS pendings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id TEXT NOT NULL,
                    descricao TEXT NOT NULL,
                    responsavel_ou_area TEXT NOT NULL DEFAULT 'A definir',
                    impacto TEXT NOT NULL DEFAULT 'Médio',
                    status TEXT NOT NULL DEFAULT 'Pendente',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS action_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id TEXT NOT NULL,
                    tarefa TEXT NOT NULL,
                    responsavel TEXT NOT NULL DEFAULT 'A definir',
                    prazo TEXT NOT NULL DEFAULT 'A definir',
                    prioridade TEXT NOT NULL DEFAULT 'Média',
                    status TEXT NOT NULL DEFAULT 'Pendente',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS chat_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    citations_json TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS app_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents(created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_documents_category ON documents(category);
                CREATE INDEX IF NOT EXISTS idx_documents_media_type ON documents(media_type);
                CREATE INDEX IF NOT EXISTS idx_action_items_doc ON action_items(document_id);
                CREATE INDEX IF NOT EXISTS idx_pendings_doc ON pendings(document_id);
                CREATE INDEX IF NOT EXISTS idx_decisions_doc ON decisions(document_id);
                """
            )

    # --- Settings ---

    def get_settings(self, masked: bool = False) -> Dict[str, Any]:
        defaults = get_env_defaults()
        with self.transaction() as conn:
            rows = conn.execute("SELECT key, value FROM app_settings").fetchall()
            for row in rows:
                defaults[row["key"]] = parse_setting_value(row["value"])

        if masked:
            out: Dict[str, Any] = {}
            for k, v in defaults.items():
                if k in SECRET_FIELDS:
                    out[k] = mask_secret(str(v or ""))
                    out[f"{k}_configured"] = bool(str(v or "").strip())
                else:
                    out[k] = v
            return out
        return defaults

    def update_settings(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        now = utc_now_iso()
        current = self.get_settings(masked=False)
        with self.transaction() as conn:
            for k, v in updates.items():
                if k.endswith("_configured"):
                    continue
                # Se a UI enviar valor mascarado contendo ****, preserva o segredo atual
                if k in SECRET_FIELDS and isinstance(v, str) and "****" in v:
                    continue
                if k not in current:
                    continue
                conn.execute(
                    """
                    INSERT INTO app_settings (key, value, updated_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at
                    """,
                    (k, json.dumps(v, ensure_ascii=False), now),
                )
        return self.get_settings(masked=True)

    # --- Jobs ---

    def create_job(
        self,
        job_id: str,
        source_type: str,
        source_ref: str,
        title: str,
        template: str,
    ) -> Dict[str, Any]:
        now = utc_now_iso()
        with self.transaction() as conn:
            conn.execute(
                """
                INSERT INTO jobs (id, status, stage, progress, message, source_type, source_ref, title, template, created_at, updated_at)
                VALUES (?, 'running', 'Recebido', 5, 'Solicitação recebida para processamento', ?, ?, ?, ?, ?, ?)
                """,
                (job_id, source_type, source_ref, title, template, now, now),
            )
        return self.get_job(job_id)  # type: ignore[return-value]

    def update_job(
        self,
        job_id: str,
        *,
        status: Optional[str] = None,
        stage: Optional[str] = None,
        progress: Optional[int] = None,
        message: Optional[str] = None,
        document_id: Optional[str] = None,
        error: Optional[str] = None,
        title: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        fields: List[str] = []
        values: List[Any] = []
        if status is not None:
            fields.append("status = ?")
            values.append(status)
        if stage is not None:
            fields.append("stage = ?")
            values.append(stage)
        if progress is not None:
            fields.append("progress = ?")
            values.append(progress)
        if message is not None:
            fields.append("message = ?")
            values.append(message)
        if document_id is not None:
            fields.append("document_id = ?")
            values.append(document_id)
        if error is not None:
            fields.append("error = ?")
            values.append(error)
        if title is not None:
            fields.append("title = ?")
            values.append(title)
        fields.append("updated_at = ?")
        values.append(utc_now_iso())
        values.append(job_id)

        with self.transaction() as conn:
            conn.execute(f"UPDATE jobs SET {', '.join(fields)} WHERE id = ?", values)
        return self.get_job(job_id)

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self.transaction() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
            return dict(row) if row else None

    def list_jobs(self, limit: int = 30) -> List[Dict[str, Any]]:
        with self.transaction() as conn:
            rows = conn.execute(
                "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]

    # --- Documents ---

    def save_document(
        self,
        *,
        doc_id: str,
        source_type: str,
        source_ref: str,
        template: str,
        transcriber_provider: str,
        llm_provider: str,
        transcript_format: str,
        raw_srt: str,
        clean_text: str,
        segments: List[Dict[str, Any]],
        analysis: Dict[str, Any],
    ) -> Dict[str, Any]:
        now = utc_now_iso()
        meta = analysis.get("metadados", {})
        resumo = analysis.get("resumo_executivo", {})
        knowledge = analysis.get("informacoes_chave", {})
        ata_md = analysis.get("ata_markdown", "")

        with self.transaction() as conn:
            conn.execute(
                """
                INSERT INTO documents (
                    id, title, source_type, source_ref, media_type, template, category,
                    language, duration_seconds, duration_formatted, word_count,
                    transcriber_provider, llm_provider, transcript_format,
                    raw_srt, clean_text, segments_json,
                    summary_short, summary_bullets_json, knowledge_json,
                    ata_markdown, analysis_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    doc_id,
                    meta.get("titulo", "Sem título"),
                    source_type,
                    source_ref,
                    meta.get("tipo_midia", "Reunião"),
                    template,
                    meta.get("categoria_tematica", "Geral / Outros"),
                    meta.get("idioma", "pt-BR"),
                    int(meta.get("duracao_estimada_segundos", 0) or 0),
                    meta.get("duracao_formatada", "00:00:00"),
                    int(meta.get("contagem_palavras", 0) or 0),
                    transcriber_provider,
                    llm_provider,
                    transcript_format,
                    raw_srt,
                    clean_text,
                    json.dumps(segments, ensure_ascii=False),
                    resumo.get("resumo_curto", ""),
                    json.dumps(resumo.get("topicos_principais", []), ensure_ascii=False),
                    json.dumps(knowledge, ensure_ascii=False),
                    ata_md,
                    json.dumps(analysis, ensure_ascii=False),
                    now,
                    now,
                ),
            )

            for d in analysis.get("decisoes", []):
                conn.execute(
                    """
                    INSERT INTO decisions (document_id, decisao, contexto, impacto, participantes_json, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        doc_id,
                        d.get("decisao", ""),
                        d.get("contexto", ""),
                        d.get("impacto", ""),
                        json.dumps(d.get("participantes_envolvidos", []), ensure_ascii=False),
                        now,
                    ),
                )

            for p in analysis.get("pendencias", []):
                conn.execute(
                    """
                    INSERT INTO pendings (document_id, descricao, responsavel_ou_area, impacto, status, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        doc_id,
                        p.get("descricao", ""),
                        p.get("responsavel_ou_area", "A definir"),
                        p.get("impacto", "Médio"),
                        p.get("status", "Pendente"),
                        now,
                        now,
                    ),
                )

            for a in analysis.get("action_items", []):
                conn.execute(
                    """
                    INSERT INTO action_items (document_id, tarefa, responsavel, prazo, prioridade, status, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        doc_id,
                        a.get("tarefa", ""),
                        a.get("responsavel", "A definir"),
                        a.get("prazo", "A definir"),
                        a.get("prioridade", "Média"),
                        a.get("status", "Pendente"),
                        now,
                        now,
                    ),
                )

        return self.get_document(doc_id)  # type: ignore[return-value]

    def update_document_analysis(
        self,
        doc_id: str,
        *,
        template: str,
        llm_provider: str,
        analysis: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Atualiza apenas a análise LLM (metadados, resumo, decisões, pendências, action items e ata) preservando a transcrição."""
        existing = self.get_document(doc_id)
        if not existing:
            return None

        now = utc_now_iso()
        meta = analysis.get("metadados", {})
        resumo = analysis.get("resumo_executivo", {})
        knowledge = analysis.get("informacoes_chave", {})
        ata_md = analysis.get("ata_markdown", "")

        with self.transaction() as conn:
            conn.execute(
                """
                UPDATE documents
                SET title = ?, media_type = ?, template = ?, category = ?,
                    llm_provider = ?, summary_short = ?, summary_bullets_json = ?,
                    knowledge_json = ?, ata_markdown = ?, analysis_json = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    meta.get("titulo", existing["title"]),
                    meta.get("tipo_midia", existing["media_type"]),
                    template,
                    meta.get("categoria_tematica", existing["category"]),
                    llm_provider,
                    resumo.get("resumo_curto", ""),
                    json.dumps(resumo.get("topicos_principais", []), ensure_ascii=False),
                    json.dumps(knowledge, ensure_ascii=False),
                    ata_md,
                    json.dumps(analysis, ensure_ascii=False),
                    now,
                    doc_id,
                ),
            )
            conn.execute("DELETE FROM decisions WHERE document_id = ?", (doc_id,))
            conn.execute("DELETE FROM pendings WHERE document_id = ?", (doc_id,))
            conn.execute("DELETE FROM action_items WHERE document_id = ?", (doc_id,))

            for d in analysis.get("decisoes", []):
                conn.execute(
                    """
                    INSERT INTO decisions (document_id, decisao, contexto, impacto, participantes_json, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        doc_id,
                        d.get("decisao", ""),
                        d.get("contexto", ""),
                        d.get("impacto", ""),
                        json.dumps(d.get("participantes_envolvidos", []), ensure_ascii=False),
                        now,
                    ),
                )

            for p in analysis.get("pendencias", []):
                conn.execute(
                    """
                    INSERT INTO pendings (document_id, descricao, responsavel_ou_area, impacto, status, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        doc_id,
                        p.get("descricao", ""),
                        p.get("responsavel_ou_area", "A definir"),
                        p.get("impacto", "Médio"),
                        p.get("status", "Pendente"),
                        now,
                        now,
                    ),
                )

            for a in analysis.get("action_items", []):
                conn.execute(
                    """
                    INSERT INTO action_items (document_id, tarefa, responsavel, prazo, prioridade, status, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        doc_id,
                        a.get("tarefa", ""),
                        a.get("responsavel", "A definir"),
                        a.get("prazo", "A definir"),
                        a.get("prioridade", "Média"),
                        a.get("status", "Pendente"),
                        now,
                        now,
                    ),
                )

        return self.get_document(doc_id)

    def list_documents(
        self,
        *,
        search: Optional[str] = None,
        media_type: Optional[str] = None,
        category: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        clauses: List[str] = []
        params: List[Any] = []

        if search and search.strip():
            q = f"%{search.strip()}%"
            clauses.append(
                "(d.title LIKE ? OR d.summary_short LIKE ? OR d.clean_text LIKE ? OR d.category LIKE ?)"
            )
            params.extend([q, q, q, q])
        if media_type and media_type.strip() and media_type != "Todos":
            clauses.append("d.media_type = ?")
            params.append(media_type.strip())
        if category and category.strip() and category != "Todas":
            clauses.append("d.category = ?")
            params.append(category.strip())
        if date_from and date_from.strip():
            clauses.append("substr(d.created_at, 1, 10) >= ?")
            params.append(date_from.strip())
        if date_to and date_to.strip():
            clauses.append("substr(d.created_at, 1, 10) <= ?")
            params.append(date_to.strip())

        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(limit)

        query = f"""
            SELECT
                d.id, d.title, d.source_type, d.source_ref, d.media_type, d.template,
                d.category, d.language, d.duration_seconds, d.duration_formatted,
                d.word_count, d.transcriber_provider, d.llm_provider,
                d.summary_short, d.databricks_synced_at, d.created_at, d.updated_at,
                (SELECT COUNT(*) FROM decisions dec WHERE dec.document_id = d.id) AS decisions_count,
                (SELECT COUNT(*) FROM pendings pen WHERE pen.document_id = d.id) AS pendings_count,
                (SELECT COUNT(*) FROM action_items act WHERE act.document_id = d.id) AS action_items_count,
                (SELECT COUNT(*) FROM action_items act WHERE act.document_id = d.id AND act.status = 'Concluído') AS action_items_done
            FROM documents d
            {where_sql}
            ORDER BY d.created_at DESC
            LIMIT ?
        """
        with self.transaction() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        with self.transaction() as conn:
            row = conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
            if not row:
                return None

            doc = dict(row)
            doc["segments"] = json.loads(doc.pop("segments_json", "[]") or "[]")
            doc["summary_bullets"] = json.loads(doc.pop("summary_bullets_json", "[]") or "[]")
            doc["knowledge"] = json.loads(doc.pop("knowledge_json", "{}") or "{}")
            doc["analysis"] = json.loads(doc.pop("analysis_json", "{}") or "{}")

            dec_rows = conn.execute(
                "SELECT * FROM decisions WHERE document_id = ? ORDER BY id ASC", (doc_id,)
            ).fetchall()
            doc["decisions"] = [
                {
                    "id": r["id"],
                    "decisao": r["decisao"],
                    "contexto": r["contexto"],
                    "impacto": r["impacto"],
                    "participantes_envolvidos": json.loads(r["participantes_json"] or "[]"),
                }
                for r in dec_rows
            ]

            pen_rows = conn.execute(
                "SELECT * FROM pendings WHERE document_id = ? ORDER BY id ASC", (doc_id,)
            ).fetchall()
            doc["pendings"] = [dict(r) for r in pen_rows]

            act_rows = conn.execute(
                "SELECT * FROM action_items WHERE document_id = ? ORDER BY id ASC", (doc_id,)
            ).fetchall()
            doc["action_items"] = [dict(r) for r in act_rows]

            chat_rows = conn.execute(
                "SELECT * FROM chat_messages WHERE document_id = ? ORDER BY id ASC", (doc_id,)
            ).fetchall()
            doc["chat_history"] = [
                {
                    "id": r["id"],
                    "role": r["role"],
                    "content": r["content"],
                    "citations": json.loads(r["citations_json"] or "[]"),
                    "created_at": r["created_at"],
                }
                for r in chat_rows
            ]
            return doc

    def delete_document(self, doc_id: str) -> bool:
        with self.transaction() as conn:
            cur = conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
            return cur.rowcount > 0

    def update_action_item(self, doc_id: str, item_id: int, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        allowed = {"status", "responsavel", "prazo", "prioridade", "tarefa"}
        fields: List[str] = []
        values: List[Any] = []
        for k, v in updates.items():
            if k in allowed and v is not None:
                fields.append(f"{k} = ?")
                values.append(v)
        if not fields:
            return None
        fields.append("updated_at = ?")
        values.append(utc_now_iso())
        values.extend([item_id, doc_id])
        with self.transaction() as conn:
            conn.execute(
                f"UPDATE action_items SET {', '.join(fields)} WHERE id = ? AND document_id = ?",
                values,
            )
            row = conn.execute(
                "SELECT * FROM action_items WHERE id = ? AND document_id = ?",
                (item_id, doc_id),
            ).fetchone()
            return dict(row) if row else None

    def update_pending_item(self, doc_id: str, item_id: int, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        allowed = {"status", "responsavel_ou_area", "impacto", "descricao"}
        fields: List[str] = []
        values: List[Any] = []
        for k, v in updates.items():
            if k in allowed and v is not None:
                fields.append(f"{k} = ?")
                values.append(v)
        if not fields:
            return None
        fields.append("updated_at = ?")
        values.append(utc_now_iso())
        values.extend([item_id, doc_id])
        with self.transaction() as conn:
            conn.execute(
                f"UPDATE pendings SET {', '.join(fields)} WHERE id = ? AND document_id = ?",
                values,
            )
            row = conn.execute(
                "SELECT * FROM pendings WHERE id = ? AND document_id = ?",
                (item_id, doc_id),
            ).fetchone()
            return dict(row) if row else None

    def mark_databricks_synced(self, doc_id: str, volume_path: str) -> None:
        now = utc_now_iso()
        with self.transaction() as conn:
            conn.execute(
                "UPDATE documents SET databricks_synced_at = ?, databricks_volume_path = ?, updated_at = ? WHERE id = ?",
                (now, volume_path, now, doc_id),
            )

    def add_chat_message(
        self,
        doc_id: str,
        role: str,
        content: str,
        citations: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        now = utc_now_iso()
        citations_list = citations or []
        with self.transaction() as conn:
            cur = conn.execute(
                """
                INSERT INTO chat_messages (document_id, role, content, citations_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (doc_id, role, content, json.dumps(citations_list, ensure_ascii=False), now),
            )
            return {
                "id": cur.lastrowid,
                "role": role,
                "content": content,
                "citations": citations_list,
                "created_at": now,
            }


# Instância singleton padrão
db = Database()
