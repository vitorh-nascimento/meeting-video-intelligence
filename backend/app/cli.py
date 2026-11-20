"""
CLI oficial do Meeting & Video Intelligence.
Exemplos:
  python -m app.cli ingest "https://www.youtube.com/watch?v=..." --template "Aula/Vídeo Técnico"
  python -m app.cli ingest "./reuniao_teams.vtt" --title "Daily Engenharia" --push-databricks
  python -m app.cli list
  python -m app.cli show <doc_id>
  python -m app.cli export <doc_id> --format md --output ./ata.md
  python -m app.cli push-databricks <doc_id> --run-pipeline
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from app.db import db
from app.services.pipeline import pipeline


def _is_url(source: str) -> bool:
    s = source.strip().lower()
    return s.startswith(("http://", "https://")) or "youtube.com" in s or "youtu.be" in s


def cmd_ingest(args: argparse.Namespace) -> int:
    source = args.source
    if _is_url(source):
        doc = pipeline.process_url(
            url=source,
            title=args.title,
            template=args.template,
            force_ai_transcription=args.force_ai,
            language=args.language,
            push_to_databricks=args.push_databricks,
            run_databricks_pipeline=args.run_pipeline,
        )
    else:
        doc = pipeline.process_file(
            file_path=Path(source),
            title=args.title,
            template=args.template,
            language=args.language,
            push_to_databricks=args.push_databricks,
            run_databricks_pipeline=args.run_pipeline,
        )

    print(f"\n[OK] Documento processado e salvo: {doc['id']}")
    print(f"Titulo:     {doc['title']}")
    print(f"Categoria:  {doc['category']} | Tipo: {doc['media_type']} | Duracao: {doc['duration_formatted']}")
    print(f"Provedores: transcritor={doc['transcriber_provider']} | llm={doc['llm_provider']}")
    print(
        f"Extraidos:  {len(doc['decisions'])} decisoes | "
        f"{len(doc['pendings'])} pendencias | {len(doc['action_items'])} action items"
    )
    if args.output_md:
        Path(args.output_md).write_text(doc["ata_markdown"], encoding="utf-8")
        print(f"Ata Markdown salva em: {args.output_md}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    docs = db.list_documents(search=args.search, limit=args.limit)
    if not docs:
        print("Nenhum documento encontrado.")
        return 0
    for d in docs:
        print(
            f"{d['id']} | {d['created_at']} | [{d['category']}] {d['title']} "
            f"(Decisoes:{d['decisions_count']} Pend:{d['pendings_count']} Acoes:{d['action_items_done']}/{d['action_items_count']})"
        )
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    doc = db.get_document(args.doc_id)
    if not doc:
        print(f"Documento não encontrado: {args.doc_id}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(doc["analysis"], ensure_ascii=False, indent=2))
    else:
        print(doc["ata_markdown"])
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    doc = db.get_document(args.doc_id)
    if not doc:
        print(f"Documento não encontrado: {args.doc_id}", file=sys.stderr)
        return 1

    fmt = args.format.lower()
    if fmt == "srt":
        content = doc["raw_srt"]
    elif fmt == "txt":
        content = doc["clean_text"]
    elif fmt == "json":
        content = json.dumps(doc["analysis"], ensure_ascii=False, indent=2)
    else:
        content = doc["ata_markdown"]

    out_path = Path(args.output) if args.output else Path(f"{doc['id'][:8]}.{fmt}")
    out_path.write_text(content, encoding="utf-8")
    print(f"Arquivo exportado com sucesso: {out_path}")
    return 0


def cmd_push_databricks(args: argparse.Namespace) -> int:
    res = pipeline.push_document_to_databricks(args.doc_id, run_pipeline=args.run_pipeline)
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.cli",
        description="Meeting & Video Intelligence CLI — Ingestão, Transcrição, Sumarização LLM e Sync Databricks",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_ing = sub.add_parser("ingest", help="Ingere URL de vídeo ou arquivo local (vídeo, áudio ou legenda)")
    p_ing.add_argument("source", help="URL (YouTube/yt-dlp) ou caminho de arquivo (.mp4, .mp3, .srt, .vtt, .txt, .json)")
    p_ing.add_argument("--title", "-t", default=None, help="Título customizado")
    p_ing.add_argument(
        "--template",
        default="Reunião Corporativa",
        choices=["Reunião Corporativa", "Aula/Vídeo Técnico", "Discovery/Cliente"],
        help="Perfil de extração LLM",
    )
    p_ing.add_argument("--language", "-l", default=None, help="Idioma (ex.: pt-BR, en)")
    p_ing.add_argument("--force-ai", "-f", action="store_true", help="Força transcrição por IA mesmo se houver legenda")
    p_ing.add_argument("--push-databricks", action="store_true", help="Envia transcrição ao Volume UC após processar")
    p_ing.add_argument("--run-pipeline", action="store_true", help="Aciona a pipeline Lakeflow após o upload")
    p_ing.add_argument("--output-md", default=None, help="Salva a Ata Markdown gerada neste caminho")
    p_ing.set_defaults(func=cmd_ingest)

    p_list = sub.add_parser("list", help="Lista reuniões e vídeos processados")
    p_list.add_argument("--search", "-s", default=None, help="Filtro textual")
    p_list.add_argument("--limit", type=int, default=30)
    p_list.set_defaults(func=cmd_list)

    p_show = sub.add_parser("show", help="Exibe a Ata Markdown ou JSON estruturado de um documento")
    p_show.add_argument("doc_id")
    p_show.add_argument("--json", action="store_true", help="Exibe JSON estruturado")
    p_show.set_defaults(func=cmd_show)

    p_exp = sub.add_parser("export", help="Exporta transcrição ou relatório (.srt, .txt, .md, .json)")
    p_exp.add_argument("doc_id")
    p_exp.add_argument("--format", "-f", choices=["srt", "txt", "md", "json"], default="md")
    p_exp.add_argument("--output", "-o", default=None)
    p_exp.set_defaults(func=cmd_export)

    p_dbx = sub.add_parser("push-databricks", help="Envia transcrição de um documento para Volume UC no Databricks")
    p_dbx.add_argument("doc_id")
    p_dbx.add_argument("--run-pipeline", action="store_true")
    p_dbx.set_defaults(func=cmd_push_databricks)

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Exception as exc:
        print(f"[ERRO] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
