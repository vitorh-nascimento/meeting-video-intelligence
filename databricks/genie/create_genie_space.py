"""
Cria (ou atualiza) um Databricks Genie Space dedicado às tabelas Gold da POC
Meeting & Video Intelligence, seguindo rigorosamente o schema v2 do Genie API:
- IDs hex de 32 caracteres minúsculos únicos e ordenados
- data_sources.tables ordenados por identifier
- column_configs ordenados por column_name
- Campos de texto como arrays de strings
- Validação read-only de cada example_question_sql antes de criar o espaço

Uso:
    python databricks/genie/create_genie_space.py \
      --profile vitor.teste \
      --warehouse bf5166fb4194bfb5 \
      --catalog workspace \
      --schema dev_vitortesteestudos_meeting_intelligence_poc
"""

from __future__ import annotations

import argparse
import json
import subprocess
import uuid
from pathlib import Path
from typing import Any, Dict, List, Tuple

GENIE_DIR = Path(__file__).resolve().parent
GENIE_JSON_PATH = GENIE_DIR / "genie_space_meeting_intelligence.json"


def new_hex_id(seed_idx: int, prefix: str) -> str:
    return f"{prefix}{seed_idx:030x}"[:32]


def run_cli(args: List[str]) -> str:
    res = subprocess.run(["databricks", *args], capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"CLI falhou ({' '.join(args)}): {res.stderr or res.stdout}")
    return res.stdout


def build_space_payload(catalog: str, schema: str) -> Tuple[Dict[str, Any], List[Tuple[str, str]]]:
    fq = f"{catalog}.{schema}"

    tables = [
        {
            "identifier": f"{fq}.gold_action_items",
            "description": [
                "Plano de ação consolidado com 1 linha por action item extraído das transcrições de reuniões via ai_query + responseFormat."
            ],
            "column_configs": sorted(
                [
                    {"column_name": "documento_id", "exclude": True},
                    {
                        "column_name": "arquivo_origem",
                        "description": ["Nome do arquivo de transcrição original (.vtt, .srt, .txt)."],
                    },
                    {
                        "column_name": "data_reuniao",
                        "description": ["Data em que a reunião ocorreu (DATE)."],
                        "synonyms": ["data", "dia da reunião"],
                    },
                    {
                        "column_name": "titulo_origem",
                        "description": ["Título da reunião de origem do action item."],
                        "synonyms": ["reunião", "título"],
                    },
                    {
                        "column_name": "tipo_midia",
                        "description": ["Tipo de reunião (Reunião Corporativa, Discovery/Cliente, Comitê Executivo, Post-mortem/Incidente, Workshop/Aula Técnica)."],
                        "enable_format_assistance": True,
                        "enable_entity_matching": True,
                    },
                    {
                        "column_name": "categoria_ia",
                        "description": ["Categoria temática classificada pela LLM."],
                        "synonyms": ["domínio", "área", "tema"],
                        "enable_format_assistance": True,
                        "enable_entity_matching": True,
                    },
                    {
                        "column_name": "tarefa",
                        "description": ["Descrição clara da tarefa / ação combinada na reunião."],
                        "synonyms": ["ação", "item de ação", "atividade"],
                    },
                    {
                        "column_name": "responsavel",
                        "description": ["Nome da pessoa responsável pela execução do action item."],
                        "synonyms": ["dono", "owner", "assignee"],
                        "enable_format_assistance": True,
                        "enable_entity_matching": True,
                    },
                    {
                        "column_name": "prazo",
                        "description": ["Prazo acordado para conclusão (ex.: DD/MM/AAAA ou A definir)."],
                        "synonyms": ["deadline", "data limite"],
                    },
                    {
                        "column_name": "prioridade",
                        "description": ["Prioridade do action item: Alta, Média ou Baixa."],
                        "synonyms": ["urgência", "criticidade"],
                        "enable_format_assistance": True,
                        "enable_entity_matching": True,
                    },
                    {
                        "column_name": "status",
                        "description": ["Status do action item (Pendente, Em andamento, Concluído)."],
                        "enable_format_assistance": True,
                        "enable_entity_matching": True,
                    },
                    {
                        "column_name": "data_processamento",
                        "description": ["Timestamp do processamento na camada Gold."],
                    },
                ],
                key=lambda c: c["column_name"],
            ),
        },
        {
            "identifier": f"{fq}.gold_decisoes",
            "description": [
                "Registro histórico de decisões aprovadas em reuniões corporativas com contexto, impacto e participantes envolvidos."
            ],
            "column_configs": sorted(
                [
                    {"column_name": "documento_id", "exclude": True},
                    {
                        "column_name": "arquivo_origem",
                        "description": ["Nome do arquivo de transcrição original."],
                    },
                    {
                        "column_name": "data_reuniao",
                        "description": ["Data da reunião onde a decisão foi aprovada."],
                    },
                    {
                        "column_name": "titulo_origem",
                        "description": ["Título da reunião onde a decisão foi tomada."],
                        "synonyms": ["reunião"],
                    },
                    {
                        "column_name": "tipo_midia",
                        "description": ["Tipo de reunião."],
                        "enable_format_assistance": True,
                        "enable_entity_matching": True,
                    },
                    {
                        "column_name": "categoria_ia",
                        "description": ["Categoria temática da reunião."],
                        "synonyms": ["área", "tema"],
                        "enable_format_assistance": True,
                        "enable_entity_matching": True,
                    },
                    {
                        "column_name": "decisao",
                        "description": ["Descrição objetiva da decisão aprovada."],
                        "synonyms": ["deliberação", "aprovação"],
                    },
                    {
                        "column_name": "contexto",
                        "description": ["Contexto que motivou a decisão."],
                    },
                    {
                        "column_name": "impacto",
                        "description": ["Impacto esperado da decisão no negócio ou arquitetura."],
                    },
                    {
                        "column_name": "participantes_envolvidos",
                        "description": ["Array de participantes envolvidos na decisão."],
                    },
                    {
                        "column_name": "data_processamento",
                        "description": ["Timestamp do processamento na camada Gold."],
                    },
                ],
                key=lambda c: c["column_name"],
            ),
        },
        {
            "identifier": f"{fq}.gold_metricas_avaliacao",
            "description": [
                "Resultados da avaliação quantitativa da POC comparando a saída do ai_query + responseFormat contra o gabarito manual de 6 transcrições (precisão, recall, F1, taxa de JSON válido, latência e custo)."
            ],
            "column_configs": sorted(
                [
                    {
                        "column_name": "avaliado_em",
                        "description": ["Timestamp da avaliação da POC."],
                    },
                    {
                        "column_name": "modelo_llm",
                        "description": ["Endpoint Foundation Model usado no ai_query."],
                    },
                    {
                        "column_name": "categoria_metrica",
                        "description": ["Dimensão avaliada: Geral, Decisões, Pendências, Action Items ou Parsing de Falantes (Silver)."],
                        "enable_format_assistance": True,
                        "enable_entity_matching": True,
                    },
                    {
                        "column_name": "total_transcricoes_volume",
                        "description": ["Quantidade total de transcrições processadas no Volume."],
                    },
                    {
                        "column_name": "total_transcricoes_gabarito",
                        "description": ["Quantidade de transcrições com gabarito manual avaliadas."],
                    },
                    {"column_name": "tp", "description": ["Verdadeiros positivos (True Positives)."]},
                    {"column_name": "fp", "description": ["Falsos positivos (False Positives)."]},
                    {"column_name": "fn", "description": ["Falsos negativos (False Negatives)."]},
                    {
                        "column_name": "precisao",
                        "description": ["Precisão da extração (0 a 1; multiplique por 100 para percentual)."],
                        "synonyms": ["precision"],
                    },
                    {
                        "column_name": "recall",
                        "description": ["Recall/revocação da extração (0 a 1; multiplique por 100 para percentual)."],
                    },
                    {
                        "column_name": "f1_score",
                        "description": ["F1-Score harmônico entre precisão e recall (0 a 1)."],
                    },
                    {
                        "column_name": "taxa_json_valido",
                        "description": ["Proporção de transcrições que retornaram JSON estritamente válido (0 a 1)."],
                        "synonyms": ["json válido"],
                    },
                    {
                        "column_name": "latencia_media_seg",
                        "description": ["Latência média por chamada ai_query em segundos."],
                    },
                    {
                        "column_name": "latencia_p50_seg",
                        "description": ["Latência mediana (p50) em segundos."],
                    },
                    {
                        "column_name": "latencia_p95_seg",
                        "description": ["Latência p95 em segundos."],
                    },
                    {
                        "column_name": "custo_medio_reuniao_usd",
                        "description": ["Custo estimado em USD por reunião processada."],
                    },
                    {
                        "column_name": "custo_projecao_1000_usd",
                        "description": ["Projeção de custo mensal para 1.000 reuniões em USD."],
                    },
                ],
                key=lambda c: c["column_name"],
            ),
        },
        {
            "identifier": f"{fq}.gold_pendencias",
            "description": [
                "Pendências, bloqueios e dependências em aberto identificados nas transcrições de reuniões."
            ],
            "column_configs": sorted(
                [
                    {"column_name": "documento_id", "exclude": True},
                    {
                        "column_name": "arquivo_origem",
                        "description": ["Nome do arquivo de transcrição original."],
                    },
                    {
                        "column_name": "data_reuniao",
                        "description": ["Data da reunião onde a pendência foi levantada."],
                    },
                    {
                        "column_name": "titulo_origem",
                        "description": ["Título da reunião de origem."],
                    },
                    {
                        "column_name": "tipo_midia",
                        "description": ["Tipo de reunião."],
                        "enable_format_assistance": True,
                        "enable_entity_matching": True,
                    },
                    {
                        "column_name": "categoria_ia",
                        "description": ["Categoria temática da reunião."],
                        "enable_format_assistance": True,
                        "enable_entity_matching": True,
                    },
                    {
                        "column_name": "descricao",
                        "description": ["Descrição da pendência ou bloqueio em aberto."],
                        "synonyms": ["bloqueio", "impedimento", "dependência"],
                    },
                    {
                        "column_name": "responsavel_ou_area",
                        "description": ["Área ou pessoa de quem a pendência depende."],
                        "synonyms": ["área responsável", "dependência"],
                        "enable_format_assistance": True,
                        "enable_entity_matching": True,
                    },
                    {
                        "column_name": "impacto",
                        "description": ["Impacto do bloqueio."],
                    },
                    {
                        "column_name": "status",
                        "description": ["Status atual da pendência (ex.: Pendente)."],
                        "enable_format_assistance": True,
                        "enable_entity_matching": True,
                    },
                    {
                        "column_name": "data_processamento",
                        "description": ["Timestamp do processamento na camada Gold."],
                    },
                ],
                key=lambda c: c["column_name"],
            ),
        },
        {
            "identifier": f"{fq}.gold_transcricoes_catalogo",
            "description": [
                "Catálogo mestre com 1 linha por reunião processada: resumo executivo, falantes extraídos na Silver, categoria temática, contagens de decisões/pendências/action items, tokens e status de JSON válido."
            ],
            "column_configs": sorted(
                [
                    {"column_name": "documento_id", "exclude": True},
                    {
                        "column_name": "arquivo_origem",
                        "description": ["Nome do arquivo no Unity Catalog Volume."],
                    },
                    {
                        "column_name": "formato_arquivo",
                        "description": ["Formato original do arquivo: vtt, srt ou txt."],
                        "enable_format_assistance": True,
                        "enable_entity_matching": True,
                    },
                    {
                        "column_name": "data_reuniao",
                        "description": ["Data em que a reunião aconteceu."],
                    },
                    {
                        "column_name": "titulo",
                        "description": ["Título executivo da reunião."],
                    },
                    {
                        "column_name": "tipo_midia",
                        "description": ["Tipo da reunião."],
                        "enable_format_assistance": True,
                        "enable_entity_matching": True,
                    },
                    {
                        "column_name": "categoria_ia",
                        "description": ["Categoria temática classificada pelo modelo LLM."],
                        "synonyms": ["tema", "domínio"],
                        "enable_format_assistance": True,
                        "enable_entity_matching": True,
                    },
                    {
                        "column_name": "falantes",
                        "description": ["Array de falantes extraídos deterministicamente na camada Silver."],
                        "synonyms": ["participantes", "speakers"],
                    },
                    {
                        "column_name": "qtd_falantes",
                        "description": ["Quantidade de falantes distintos na reunião."],
                    },
                    {
                        "column_name": "total_turnos",
                        "description": ["Total de turnos de fala identificados na transcrição."],
                    },
                    {
                        "column_name": "falantes_texto",
                        "description": ["Lista textual dos falantes separados por vírgula."],
                    },
                    {
                        "column_name": "total_palavras",
                        "description": ["Quantidade total de palavras da transcrição limpa."],
                    },
                    {
                        "column_name": "duracao_estimada_min",
                        "description": ["Duração da reunião em minutos."],
                    },
                    {
                        "column_name": "resumo_executivo",
                        "description": ["Resumo executivo gerado pelo ai_query."],
                    },
                    {
                        "column_name": "qtd_decisoes",
                        "description": ["Total de decisões extraídas da reunião."],
                    },
                    {
                        "column_name": "qtd_pendencias",
                        "description": ["Total de pendências/bloqueios extraídos da reunião."],
                    },
                    {
                        "column_name": "qtd_action_items",
                        "description": ["Total de action items extraídos da reunião."],
                    },
                    {
                        "column_name": "ferramentas_tecnologias",
                        "description": ["Ferramentas e tecnologias mencionadas na reunião."],
                    },
                    {
                        "column_name": "tokens_entrada_estimados",
                        "description": ["Estimativa de tokens de entrada enviados ao LLM."],
                    },
                    {
                        "column_name": "tokens_saida_estimados",
                        "description": ["Estimativa de tokens de saída retornados pelo LLM."],
                    },
                    {
                        "column_name": "modelo_llm",
                        "description": ["Endpoint usado no ai_query."],
                    },
                    {
                        "column_name": "json_valido",
                        "description": ["Indica se o retorno respeitou estritamente o JSON Schema do responseFormat."],
                    },
                    {
                        "column_name": "extracao_erro",
                        "description": ["Mensagem de erro do ai_query (NULL quando bem-sucedido)."],
                    },
                    {
                        "column_name": "data_processamento",
                        "description": ["Timestamp do processamento na camada Gold."],
                    },
                ],
                key=lambda c: c["column_name"],
            ),
        },
    ]

    sample_questions = [
        "Quais action items de prioridade Alta estão pendentes e quem são os responsáveis?",
        "Quantas reuniões, decisões, pendências e action items foram processados por categoria?",
        "Quais pendências e bloqueios estão em aberto nas reuniões de Governança, Segurança e FinOps?",
        "Quais decisões foram aprovadas nas reuniões de Engenharia de Dados e Lakehouse?",
        "Qual foi a precisão, recall, taxa de JSON válido, latência média e custo estimado da POC?",
    ]

    example_sqls: List[Tuple[str, str]] = [
        (
            "Quais action items de prioridade Alta estão pendentes e quem são os responsáveis?",
            f"SELECT data_reuniao, titulo_origem, tarefa, responsavel, prazo, prioridade, status FROM {fq}.gold_action_items WHERE prioridade = 'Alta' AND status = 'Pendente' ORDER BY data_reuniao, prazo",
        ),
        (
            "Quantas reuniões, decisões, pendências e action items foram processados por categoria?",
            f"SELECT categoria_ia, COUNT(*) AS total_reunioes, SUM(qtd_decisoes) AS total_decisoes, SUM(qtd_pendencias) AS total_pendencias, SUM(qtd_action_items) AS total_action_items FROM {fq}.gold_transcricoes_catalogo GROUP BY categoria_ia ORDER BY total_reunioes DESC",
        ),
        (
            "Quais pendências e bloqueios estão em aberto?",
            f"SELECT data_reuniao, titulo_origem, categoria_ia, descricao, responsavel_ou_area, impacto FROM {fq}.gold_pendencias WHERE status = 'Pendente' ORDER BY data_reuniao DESC",
        ),
        (
            "Quais decisões foram aprovadas nas reuniões de Engenharia de Dados & Lakehouse?",
            f"SELECT data_reuniao, titulo_origem, decisao, impacto FROM {fq}.gold_decisoes WHERE categoria_ia ILIKE '%Lakehouse%' ORDER BY data_reuniao DESC",
        ),
        (
            "Qual foi a precisão, recall, taxa de JSON válido, latência média e custo estimado da POC?",
            f"SELECT categoria_metrica, ROUND(precisao * 100, 1) AS precisao_pct, ROUND(recall * 100, 1) AS recall_pct, ROUND(f1_score * 100, 1) AS f1_pct, ROUND(taxa_json_valido * 100, 1) AS json_valido_pct, latencia_media_seg, custo_medio_reuniao_usd, custo_projecao_1000_usd FROM {fq}.gold_metricas_avaliacao ORDER BY categoria_metrica",
        ),
    ]

    payload: Dict[str, Any] = {
        "version": 2,
        "config": {
            "sample_questions": sorted(
                [{"id": new_hex_id(i + 1, "10"), "question": [q]} for i, q in enumerate(sample_questions)],
                key=lambda x: x["id"],
            )
        },
        "data_sources": {
            "tables": sorted(tables, key=lambda t: t["identifier"]),
        },
        "instructions": {
            "text_instructions": [
                {
                    "id": new_hex_id(1, "30"),
                    "content": [
                        "Você é o assistente executivo da POC Meeting & Video Intelligence no Databricks Lakehouse.",
                        "Use gold_transcricoes_catalogo para visão geral de reuniões, resumos executivos, falantes e contagens.",
                        "Use gold_decisoes para decisões aprovadas, gold_pendencias para bloqueios/pendências em aberto e gold_action_items para tarefas com responsável, prazo e prioridade.",
                        "Use gold_metricas_avaliacao quando perguntarem sobre precisão, recall, F1, taxa de JSON válido, latência ou custo da POC.",
                        "Responda sempre em Português do Brasil de forma objetiva, apresentando tabelas ordenadas por data ou prioridade.",
                    ],
                }
            ],
            "example_question_sqls": sorted(
                [
                    {"id": new_hex_id(i + 1, "20"), "question": [q], "sql": [s]}
                    for i, (q, s) in enumerate(example_sqls)
                ],
                key=lambda x: x["id"],
            ),
        },
    }

    return payload, example_sqls


def main() -> None:
    parser = argparse.ArgumentParser(description="Cria/atualiza Genie Space da POC Meeting Intelligence")
    parser.add_argument("--profile", required=True)
    parser.add_argument("--warehouse", required=True)
    parser.add_argument("--catalog", default="workspace")
    parser.add_argument("--schema", default="dev_vitortesteestudos_meeting_intelligence_poc")
    parser.add_argument("--title", default="Meeting & Video Intelligence POC — Decisões, Pendências e Action Items")
    parser.add_argument(
        "--description",
        default="Genie Space dedicado à POC de sumarização de reuniões: consulta decisões aprovadas, pendências/bloqueios, planos de ação (action items), catálogo de transcrições e métricas de qualidade (precisão, recall, JSON válido, latência e custo).",
    )
    args = parser.parse_args()

    payload, example_sqls = build_space_payload(args.catalog, args.schema)
    GENIE_DIR.mkdir(parents=True, exist_ok=True)
    GENIE_JSON_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    # 1. Validar todos os SQLs de exemplo (read-only) antes de criar o Genie Space
    print("[1/4] Validando todos os SQLs de exemplo no SQL Warehouse ...")
    for idx, (q, sql) in enumerate(example_sqls, start=1):
        out = run_cli(
            [
                "experimental",
                "aitools",
                "tools",
                "query",
                "--profile",
                args.profile,
                "--warehouse",
                args.warehouse,
                "-o",
                "json",
                sql,
            ]
        )
        rows = json.loads(out) if out.strip() else []
        print(f"    -> SQL #{idx} OK ({len(rows)} linhas): {q[:60]}...")

    # 2. Garantir pasta parent_path do usuário
    me = json.loads(run_cli(["current-user", "me", "--profile", args.profile]))
    user_name = me["userName"]
    parent_path = f"/Workspace/Users/{user_name}/genie_spaces"
    run_cli(["workspace", "mkdirs", parent_path, "--profile", args.profile])

    # 3. Verificar se já existe um Genie Space com o mesmo título (idempotência)
    existing = json.loads(run_cli(["genie", "list-spaces", "--profile", args.profile]))
    matched_id = None
    for sp in existing.get("spaces", []):
        if sp.get("title") == args.title:
            matched_id = sp.get("space_id")
            break

    compact_json = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    if matched_id:
        print(f"[2/4] Atualizando Genie Space existente: {matched_id} ...")
        run_cli(
            [
                "genie",
                "update-space",
                matched_id,
                "--serialized-space",
                compact_json,
                "--title",
                args.title,
                "--description",
                args.description,
                "--profile",
                args.profile,
            ]
        )
        space_id = matched_id
    else:
        print("[2/4] Criando novo Genie Space ...")
        created = json.loads(
            run_cli(
                [
                    "genie",
                    "create-space",
                    args.warehouse,
                    compact_json,
                    "--title",
                    args.title,
                    "--description",
                    args.description,
                    "--parent-path",
                    parent_path,
                    "--profile",
                    args.profile,
                    "-o",
                    "json",
                ]
            )
        )
        space_id = created["space_id"]

    print(f"[3/4] Genie Space pronto! space_id = {space_id}")

    # 4. Validar conversa real no Genie Space
    print("[4/4] Validando pergunta real no Genie Space ...")
    conv_out = run_cli(
        [
            "genie",
            "start-conversation",
            space_id,
            "Quais action items de prioridade Alta estão pendentes e quem são os responsáveis?",
            "--profile",
            args.profile,
            "-o",
            "json",
        ]
    )
    conv = json.loads(conv_out)
    print(f"    -> Conversa concluída! status={conv.get('status')} conversation_id={conv.get('conversation_id')}")
    for att in conv.get("attachments", []) or []:
        if att.get("text"):
            print("    -> Resposta Genie:", str(att["text"].get("content", ""))[:400])
        if att.get("query"):
            print("    -> SQL gerado:", str(att["query"].get("query", ""))[:300])


if __name__ == "__main__":
    main()
