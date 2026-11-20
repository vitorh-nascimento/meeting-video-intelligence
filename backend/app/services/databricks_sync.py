"""
Integração opcional com Databricks Lakehouse:
- Upload da transcrição (.srt/.txt) para um Volume do Unity Catalog via REST Files API (Host + Token)
  ou via Databricks CLI (`databricks fs cp ... --profile ...`).
- Acionamento opcional da Lakeflow Spark Declarative Pipeline.
Zero valores pessoais ou IDs fixos hardcoded.
"""

from __future__ import annotations

import json
import re
import subprocess
import unicodedata
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional


def sanitize_filename(name: str) -> str:
    ascii_name = (
        unicodedata.normalize("NFKD", name or "transcript")
        .encode("ascii", "ignore")
        .decode("ascii")
    )
    clean = re.sub(r"[^A-Za-z0-9\-]+", "_", ascii_name.strip())
    return clean.strip("_")[:80] or "transcript"


def build_volume_dest_path(settings: Dict[str, Any], filename: str) -> str:
    catalog = str(settings.get("databricks_catalog", "")).strip()
    schema = str(settings.get("databricks_schema", "")).strip()
    volume = str(settings.get("databricks_volume_name", "raw_transcripts")).strip() or "raw_transcripts"
    if not catalog or not schema:
        raise ValueError(
            "Configure `databricks_catalog` e `databricks_schema` em Configurações (ou .env) antes de enviar para o Databricks."
        )
    return f"/Volumes/{catalog}/{schema}/{volume}/{filename}"


def upload_to_unity_catalog_volume(
    *,
    local_file: Path,
    settings: Dict[str, Any],
    dest_filename: Optional[str] = None,
) -> Dict[str, Any]:
    filename = dest_filename or local_file.name
    volume_path = build_volume_dest_path(settings, filename)

    host = str(settings.get("databricks_host", "")).strip().rstrip("/")
    token = str(settings.get("databricks_token", "")).strip()
    profile = str(settings.get("databricks_profile", "")).strip()

    # 1. Preferência: REST Files API (funciona sem CLI instalado)
    if host and token:
        url = f"{host}/api/2.0/fs/files{volume_path}?overwrite=true"
        req = urllib.request.Request(
            url,
            data=local_file.read_bytes(),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/octet-stream",
            },
            method="PUT",
        )
        try:
            with urllib.request.urlopen(req, timeout=120):
                return {"method": "rest_api", "volume_path": volume_path, "uploaded": True}
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:400]
            raise RuntimeError(f"Erro HTTP {exc.code} ao enviar para Volume UC via REST: {detail}") from exc

    # 2. Fallback: Databricks CLI (`dbfs:/Volumes/...`)
    cmd = ["databricks", "fs", "cp", str(local_file), f"dbfs:{volume_path}", "--overwrite"]
    if profile:
        cmd.extend(["--profile", profile])
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return {
            "method": "databricks_cli",
            "volume_path": volume_path,
            "uploaded": True,
            "stdout": res.stdout.strip(),
        }
    except FileNotFoundError as exc:
        raise RuntimeError(
            "Databricks CLI não encontrado e DATABRICKS_HOST/DATABRICKS_TOKEN não configurados."
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"Erro ao enviar via Databricks CLI: {exc.stderr or exc.stdout}") from exc


def trigger_lakeflow_pipeline(settings: Dict[str, Any]) -> Dict[str, Any]:
    pipeline_id = str(settings.get("databricks_pipeline_id", "")).strip()
    if not pipeline_id:
        raise ValueError("Configure `databricks_pipeline_id` em Configurações (ou .env) para acionar a pipeline.")

    host = str(settings.get("databricks_host", "")).strip().rstrip("/")
    token = str(settings.get("databricks_token", "")).strip()
    profile = str(settings.get("databricks_profile", "")).strip()

    if host and token:
        url = f"{host}/api/2.0/pipelines/{pipeline_id}/updates"
        req = urllib.request.Request(
            url,
            data=json.dumps({}).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return {
                    "triggered": True,
                    "method": "rest_api",
                    "pipeline_id": pipeline_id,
                    "update_id": data.get("update_id"),
                }
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:400]
            raise RuntimeError(f"Erro HTTP {exc.code} ao acionar pipeline Lakeflow: {detail}") from exc

    cmd = ["databricks", "pipelines", "start-update", pipeline_id]
    if profile:
        cmd.extend(["--profile", profile])
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(res.stdout) if res.stdout.strip() else {}
        return {
            "triggered": True,
            "method": "databricks_cli",
            "pipeline_id": pipeline_id,
            "update_id": data.get("update_id"),
        }
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"Erro ao acionar pipeline via Databricks CLI: {exc.stderr or exc.stdout}") from exc
