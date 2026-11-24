"""
Avaliação quantitativa da POC de Sumarização de Reuniões (Databricks ai_query + responseFormat).

Mede e persiste:
1. Taxa de JSON válido (%) sobre todas as transcrições processadas na Gold.
2. Qualidade do parsing de falantes e datas na camada Silver contra o gabarito manual.
3. Precisão, Recall e F1 para Decisões, Pendências e Action Items (além de acurácia de
   Responsável, Prazo e Prioridade nos Action Items) comparando contra o gabarito manual
   de 6 transcrições (`databricks/eval/gabarito_manual.json`).
4. Latência real (média, p50, p95, min, max) executando benchmark cronometrado de `ai_query`
   com `responseFormat` sobre as 6 transcrições do gabarito no SQL Warehouse.
5. Custo estimado (tokens de entrada/saída, DBUs pay-per-token, USD por reunião e projeção
   mensal para 1.000 reuniões).

Salva:
- Tabela Delta `gold_metricas_avaliacao` no schema alvo do Databricks (consumível no Genie Space)
- Tabela Delta `eval_gabarito_manual` com o gabarito de referência no Unity Catalog
- `databricks/eval/resultados_avaliacao.json`
- `databricks/eval/RELATORIO_AVALIACAO_POC.md`

Uso:
    python databricks/eval/evaluate_poc.py \
      --profile <SEU_PERFIL> \
      --warehouse <SQL_WAREHOUSE_ID> \
      --catalog workspace \
      --schema dev_vitortesteestudos_meeting_intelligence_poc
"""

from __future__ import annotations

import argparse
import json
import math
import re
import statistics
import subprocess
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

EVAL_DIR = Path(__file__).resolve().parent
GABARITO_PATH = EVAL_DIR / "gabarito_manual.json"
RESULTS_JSON_PATH = EVAL_DIR / "resultados_avaliacao.json"
REPORT_MD_PATH = EVAL_DIR / "RELATORIO_AVALIACAO_POC.md"

# Referência de preço Databricks Foundation Model Pay-per-Token (Llama 3.3 70B Instruct)
# Fonte: Tabela pública Databricks FMAPI (AWS US-East, $0.07/DBU):
# ~14.286 DBUs / 1M tokens de entrada ($1.00/1M) e ~42.857 DBUs / 1M tokens de saída ($3.00/1M)
DBU_PRICE_USD = 0.07
INPUT_DBU_PER_1M = 14.286
OUTPUT_DBU_PER_1M = 42.857

PT_STOPWORDS: Set[str] = {
    "a", "o", "as", "os", "de", "da", "do", "das", "dos", "e", "em", "no", "na", "nos", "nas",
    "para", "por", "com", "sem", "um", "uma", "uns", "umas", "que", "se", "ao", "aos", "ate",
    "sobre", "entre", "como", "mais", "ser", "foi", "sao", "esta", "estao", "ainda", "nao",
    "ja", "seu", "sua", "seus", "suas", "nosso", "nossa", "pelo", "pela", "pelos", "pelas",
    "todos", "todas", "cada", "ou", "tambem", "time", "equipe", "area", "pendente",
}


def run_sql(profile: str, warehouse: str, sql: str) -> List[Dict[str, Any]]:
    cmd = [
        "databricks",
        "experimental",
        "aitools",
        "tools",
        "query",
        "--profile",
        profile,
        "--warehouse",
        warehouse,
        "-o",
        "json",
        sql,
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"Erro SQL (rc={res.returncode}): {res.stderr or res.stdout}")
    out = res.stdout.strip()
    if not out:
        return []
    try:
        parsed = json.loads(out)
    except json.JSONDecodeError:
        return []
    if isinstance(parsed, list):
        return parsed
    return [parsed]


def normalize_text(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text or "")
    ascii_only = "".join(ch for ch in nfkd if not unicodedata.combining(ch))
    clean = re.sub(r"[^a-z0-9\s]", " ", ascii_only.lower())
    return re.sub(r"\s+", " ", clean).strip()


def tokenize(text: str) -> Set[str]:
    return {t for t in normalize_text(text).split() if len(t) >= 3 and t not in PT_STOPWORDS}


def text_similarity(a: str, b: str) -> float:
    ta = tokenize(a)
    tb = tokenize(b)
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    # Overlap coefficient combinado com Dice (robusto quando o LLM gera frase um pouco mais longa)
    dice = (2.0 * inter) / (len(ta) + len(tb))
    overlap = inter / min(len(ta), len(tb))
    return 0.55 * overlap + 0.45 * dice


def match_items(
    gold_texts: List[str], pred_texts: List[str], threshold: float = 0.38
) -> Tuple[int, int, int, List[Tuple[int, int, float]]]:
    """Matching guloso 1-para-1 por maior similaridade >= threshold."""
    candidates: List[Tuple[float, int, int]] = []
    for gi, g in enumerate(gold_texts):
        for pi, p in enumerate(pred_texts):
            sim = text_similarity(g, p)
            if sim >= threshold:
                candidates.append((sim, gi, pi))
    candidates.sort(reverse=True)

    used_g: Set[int] = set()
    used_p: Set[int] = set()
    matches: List[Tuple[int, int, float]] = []
    for sim, gi, pi in candidates:
        if gi not in used_g and pi not in used_p:
            used_g.add(gi)
            used_p.add(pi)
            matches.append((gi, pi, sim))

    tp = len(matches)
    fp = max(0, len(pred_texts) - tp)
    fn = max(0, len(gold_texts) - tp)
    return tp, fp, fn, matches


def prf(tp: int, fp: int, fn: int) -> Dict[str, Any]:
    prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1": round(f1, 4),
    }


def sql_escape(val: str) -> str:
    return (val or "").replace("\\", "\\\\").replace("'", "\\'")


def percentile(values: List[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    k = (len(ordered) - 1) * (p / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return ordered[int(k)]
    return ordered[f] * (c - k) + ordered[c] * (k - f)


def main() -> None:
    parser = argparse.ArgumentParser(description="Avaliação quantitativa da POC Databricks")
    parser.add_argument("--profile", required=True)
    parser.add_argument("--warehouse", required=True)
    parser.add_argument("--catalog", default="workspace")
    parser.add_argument("--schema", default="dev_vitortesteestudos_meeting_intelligence_poc")
    parser.add_argument("--endpoint", default="databricks-meta-llama-3-3-70b-instruct")
    parser.add_argument(
        "--latencies",
        default="",
        help="Opcional: lista de latências medidas (seg) separadas por vírgula para pular re-execução do benchmark",
    )
    args = parser.parse_args()

    fq_schema = f"{args.catalog}.{args.schema}"
    gabarito = json.loads(GABARITO_PATH.read_text(encoding="utf-8"))
    gt_by_file = {item["arquivo_origem"]: item for item in gabarito["transcricoes"]}

    # 1. Buscar todos os registros da tabela Gold de extração (todas as 18 transcrições)
    print(f"[1/5] Consultando {fq_schema}.gold_transcricoes_extracao ...")
    rows = run_sql(
        args.profile,
        args.warehouse,
        f"""
        SELECT
          arquivo_origem,
          formato_arquivo,
          CAST(data_reuniao AS STRING) AS data_reuniao,
          falantes_texto,
          qtd_falantes,
          total_palavras,
          tokens_entrada_estimados,
          tokens_saida_estimados,
          modelo_llm,
          json_valido,
          extracao_erro,
          raw_json
        FROM {fq_schema}.gold_transcricoes_extracao
        ORDER BY arquivo_origem
        """,
    )
    if not rows:
        raise RuntimeError(f"Nenhum registro encontrado em {fq_schema}.gold_transcricoes_extracao")

    total_docs = len(rows)
    valid_json_docs = 0
    total_input_tokens = 0
    total_output_tokens = 0
    parsed_by_file: Dict[str, Dict[str, Any]] = {}

    for r in rows:
        fname = r["arquivo_origem"]
        raw = r.get("raw_json") or ""
        in_tok = int(r.get("tokens_entrada_estimados") or 0)
        out_tok = int(r.get("tokens_saida_estimados") or 0)
        total_input_tokens += in_tok
        total_output_tokens += out_tok

        # Validação independente em Python além do booleano SQL
        py_valid = False
        parsed_obj = None
        if raw and not r.get("extracao_erro"):
            try:
                parsed_obj = json.loads(raw)
                if (
                    isinstance(parsed_obj, dict)
                    and all(k in parsed_obj for k in ("decisoes", "pendencias", "action_items"))
                    and isinstance(parsed_obj["decisoes"], list)
                    and isinstance(parsed_obj["pendencias"], list)
                    and isinstance(parsed_obj["action_items"], list)
                ):
                    py_valid = True
            except json.JSONDecodeError:
                py_valid = False

        sql_valid = str(r.get("json_valido")).lower() in ("true", "1")
        if py_valid and sql_valid:
            valid_json_docs += 1
        parsed_by_file[fname] = {
            "row": r,
            "parsed": parsed_obj,
            "valid": py_valid and sql_valid,
        }

    json_valid_rate = round(valid_json_docs / total_docs, 4)
    print(f"    -> Total processado: {total_docs} | JSON válido: {valid_json_docs}/{total_docs} ({json_valid_rate*100:.1f}%)")

    # 2. Comparar as 6 transcrições com o gabarito manual (Precision / Recall / F1 + Silver Parsing)
    print("[2/5] Calculando Precisão, Recall, F1 e acurácia de Silver/Action Items contra gabarito de 6 transcrições ...")
    totals = {
        "decisoes": {"tp": 0, "fp": 0, "fn": 0},
        "pendencias": {"tp": 0, "fp": 0, "fn": 0},
        "action_items": {"tp": 0, "fp": 0, "fn": 0},
        "falantes_silver": {"tp": 0, "fp": 0, "fn": 0},
    }
    ai_field_hits = {"responsavel": 0, "prazo": 0, "prioridade": 0, "matched_total": 0}
    date_hits = 0
    per_doc_eval: List[Dict[str, Any]] = []

    for fname, gt in gt_by_file.items():
        if fname not in parsed_by_file:
            raise RuntimeError(f"Arquivo do gabarito não encontrado na Gold: {fname}")
        entry = parsed_by_file[fname]
        row = entry["row"]
        pred = entry["parsed"] or {}

        # Silver parsing check: data_reuniao e falantes
        if str(row.get("data_reuniao", "")) == gt["data_reuniao"]:
            date_hits += 1
        pred_speakers = [s.strip() for s in (row.get("falantes_texto") or "").split(",") if s.strip()]
        gt_speakers_norm = {normalize_text(s) for s in gt["falantes_esperados"]}
        pred_speakers_norm = {normalize_text(s) for s in pred_speakers}
        s_tp = len(gt_speakers_norm & pred_speakers_norm)
        s_fp = len(pred_speakers_norm - gt_speakers_norm)
        s_fn = len(gt_speakers_norm - pred_speakers_norm)
        totals["falantes_silver"]["tp"] += s_tp
        totals["falantes_silver"]["fp"] += s_fp
        totals["falantes_silver"]["fn"] += s_fn

        # Gold extraction checks
        pred_dec = [d.get("decisao", "") for d in pred.get("decisoes", [])]
        pred_pen = [p.get("descricao", "") for p in pred.get("pendencias", [])]
        pred_ai_objs = pred.get("action_items", [])
        pred_ai = [a.get("tarefa", "") for a in pred_ai_objs]
        gt_ai_objs = gt["action_items"]
        gt_ai = [a["tarefa"] for a in gt_ai_objs]

        d_tp, d_fp, d_fn, _ = match_items(gt["decisoes"], pred_dec)
        p_tp, p_fp, p_fn, _ = match_items(gt["pendencias"], pred_pen)
        a_tp, a_fp, a_fn, a_matches = match_items(gt_ai, pred_ai)

        for cat, (tp, fp, fn) in (
            ("decisoes", (d_tp, d_fp, d_fn)),
            ("pendencias", (p_tp, p_fp, p_fn)),
            ("action_items", (a_tp, a_fp, a_fn)),
        ):
            totals[cat]["tp"] += tp
            totals[cat]["fp"] += fp
            totals[cat]["fn"] += fn

        for gi, pi, _ in a_matches:
            ai_field_hits["matched_total"] += 1
            gt_obj = gt_ai_objs[gi]
            pr_obj = pred_ai_objs[pi]
            gt_resp = normalize_text(gt_obj["responsavel"])
            pr_resp = normalize_text(pr_obj.get("responsavel", ""))
            # Aceita match exato ou primeiro nome contido no nome completo
            if gt_resp and pr_resp and (gt_resp == pr_resp or gt_resp.split()[0] in pr_resp.split()):
                ai_field_hits["responsavel"] += 1
            if normalize_text(gt_obj["prazo"]) in normalize_text(pr_obj.get("prazo", "")):
                ai_field_hits["prazo"] += 1
            if normalize_text(gt_obj["prioridade"]) == normalize_text(pr_obj.get("prioridade", "")):
                ai_field_hits["prioridade"] += 1

        per_doc_eval.append(
            {
                "arquivo_origem": fname,
                "formato": row.get("formato_arquivo"),
                "json_valido": entry["valid"],
                "decisoes": prf(d_tp, d_fp, d_fn),
                "pendencias": prf(p_tp, p_fp, p_fn),
                "action_items": prf(a_tp, a_fp, a_fn),
                "falantes_silver": prf(s_tp, s_fp, s_fn),
            }
        )

    metrics_by_cat = {cat: prf(v["tp"], v["fp"], v["fn"]) for cat, v in totals.items()}
    overall_tp = sum(totals[c]["tp"] for c in ("decisoes", "pendencias", "action_items"))
    overall_fp = sum(totals[c]["fp"] for c in ("decisoes", "pendencias", "action_items"))
    overall_fn = sum(totals[c]["fn"] for c in ("decisoes", "pendencias", "action_items"))
    overall_prf = prf(overall_tp, overall_fp, overall_fn)

    # 3. Benchmark cronometrado de latência real do ai_query + responseFormat (nas 6 transcrições do gabarito)
    print("[3/5] Medindo latência real de ai_query() + responseFormat nas 6 transcrições do gabarito ...")
    schema_json = json.dumps(
        {
            "type": "json_schema",
            "json_schema": {
                "name": "extracao_reuniao",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "titulo_sugerido": {"type": "string"},
                        "resumo_executivo": {"type": "string"},
                        "decisoes": {"type": "array", "items": {"type": "string"}},
                        "pendencias": {"type": "array", "items": {"type": "string"}},
                        "action_items": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "tarefa": {"type": "string"},
                                    "responsavel": {"type": "string"},
                                    "prazo": {"type": "string"},
                                    "prioridade": {"type": "string", "enum": ["Alta", "Média", "Baixa"]},
                                },
                                "required": ["tarefa", "responsavel", "prazo", "prioridade"],
                                "additionalProperties": False,
                            },
                        },
                    },
                    "required": ["titulo_sugerido", "resumo_executivo", "decisoes", "pendencias", "action_items"],
                    "additionalProperties": False,
                },
            },
        },
        ensure_ascii=False,
    )
    latencies_sec: List[float] = []
    if args.latencies.strip():
        latencies_sec = [round(float(x.strip()), 2) for x in args.latencies.split(",") if x.strip()]
        print(f"    -> Usando {len(latencies_sec)} leituras de latência medidas anteriormente: {latencies_sec}")
    else:
        for fname in gt_by_file.keys():
            sql_bench = f"""
            SELECT
              arquivo_origem,
              ai_query(
                '{args.endpoint}',
                concat(
                  'Extraia em PT-BR titulo_sugerido, resumo_executivo, decisoes, pendencias e action_items (tarefa, responsavel, prazo, prioridade) da transcrição:\\n',
                  conteudo_limpo
                ),
                responseFormat => '{schema_json}',
                modelParameters => named_struct('temperature', CAST(0.0 AS DOUBLE), 'max_tokens', 1800),
                failOnError => false
              ).errorMessage AS err
            FROM {fq_schema}.silver_transcricoes_limpas
            WHERE arquivo_origem = '{sql_escape(fname)}'
            """
            t0 = time.perf_counter()
            run_sql(args.profile, args.warehouse, sql_bench)
            dt = round(time.perf_counter() - t0, 2)
            latencies_sec.append(dt)
            print(f"    -> {fname}: {dt:.2f}s")

    latency_stats = {
        "amostras": len(latencies_sec),
        "media_seg": round(statistics.mean(latencies_sec), 2),
        "p50_seg": round(percentile(latencies_sec, 50), 2),
        "p95_seg": round(percentile(latencies_sec, 95), 2),
        "min_seg": round(min(latencies_sec), 2),
        "max_seg": round(max(latencies_sec), 2),
        "leituras_seg": latencies_sec,
    }

    # 4. Cálculo de custo estimado (tokens entrada/saída -> DBUs -> USD)
    print("[4/5] Calculando estimativa de tokens e custo (DBU / USD) ...")
    # Prompt system + schema adiciona ~380 tokens fixos por transcrição
    prompt_overhead_tokens = 380 * total_docs
    eff_input_tokens = total_input_tokens + prompt_overhead_tokens
    input_dbus = (eff_input_tokens / 1_000_000.0) * INPUT_DBU_PER_1M
    output_dbus = (total_output_tokens / 1_000_000.0) * OUTPUT_DBU_PER_1M
    total_dbus = input_dbus + output_dbus
    total_usd = total_dbus * DBU_PRICE_USD
    usd_per_doc = total_usd / total_docs
    cost_stats = {
        "modelo": args.endpoint,
        "total_documentos": total_docs,
        "tokens_entrada_total": eff_input_tokens,
        "tokens_saida_total": total_output_tokens,
        "tokens_entrada_medio": round(eff_input_tokens / total_docs, 1),
        "tokens_saida_medio": round(total_output_tokens / total_docs, 1),
        "dbus_totais_estimados": round(total_dbus, 5),
        "custo_total_18_docs_usd": round(total_usd, 5),
        "custo_medio_por_reuniao_usd": round(usd_per_doc, 5),
        "projecao_1000_reunioes_usd": round(usd_per_doc * 1000.0, 2),
        "premissa_preco": f"Pay-per-Token FMAPI ($0.07/DBU; {INPUT_DBU_PER_1M} DBU/1M in; {OUTPUT_DBU_PER_1M} DBU/1M out)",
    }

    # 5. Persistir resultados no Unity Catalog (eval_gabarito_manual + gold_metricas_avaliacao) e no repositório
    print(f"[5/5] Persistindo tabelas {fq_schema}.eval_gabarito_manual e {fq_schema}.gold_metricas_avaliacao ...")
    run_sql(
        args.profile,
        args.warehouse,
        f"""
        CREATE OR REPLACE TABLE {fq_schema}.eval_gabarito_manual (
          arquivo_origem STRING COMMENT 'Nome do arquivo de transcrição do gabarito manual',
          data_reuniao DATE COMMENT 'Data esperada da reunião',
          falantes_esperados STRING COMMENT 'Lista de falantes esperados',
          qtd_decisoes_gabarito INT COMMENT 'Quantidade de decisões no gabarito',
          qtd_pendencias_gabarito INT COMMENT 'Quantidade de pendências no gabarito',
          qtd_action_items_gabarito INT COMMENT 'Quantidade de action items no gabarito',
          gabarito_json STRING COMMENT 'JSON completo do gabarito manual'
        )
        COMMENT 'Gabarito manual de 6 transcrições usado para medir precisão e recall da POC'
        """,
    )
    gt_values = []
    for item in gabarito["transcricoes"]:
        gt_values.append(
            "('{f}', DATE '{d}', '{spk}', {nd}, {np}, {na}, '{js}')".format(
                f=sql_escape(item["arquivo_origem"]),
                d=item["data_reuniao"],
                spk=sql_escape(", ".join(item["falantes_esperados"])),
                nd=len(item["decisoes"]),
                np=len(item["pendencias"]),
                na=len(item["action_items"]),
                js=sql_escape(json.dumps(item, ensure_ascii=False)),
            )
        )
    run_sql(
        args.profile,
        args.warehouse,
        f"INSERT INTO {fq_schema}.eval_gabarito_manual VALUES " + ", ".join(gt_values),
    )

    run_sql(
        args.profile,
        args.warehouse,
        f"""
        CREATE OR REPLACE TABLE {fq_schema}.gold_metricas_avaliacao (
          avaliado_em TIMESTAMP COMMENT 'Data e hora da execução da avaliação',
          modelo_llm STRING COMMENT 'Endpoint Foundation Model avaliado no ai_query',
          categoria_metrica STRING COMMENT 'Dimensão avaliada (Geral, Decisões, Pendências, Action Items, Falantes Silver)',
          total_transcricoes_volume INT COMMENT 'Total de transcrições processadas na Gold',
          total_transcricoes_gabarito INT COMMENT 'Total de transcrições com gabarito manual',
          tp INT COMMENT 'Verdadeiros positivos',
          fp INT COMMENT 'Falsos positivos',
          fn INT COMMENT 'Falsos negativos',
          precisao DOUBLE COMMENT 'Precisão (TP / (TP + FP)) de 0 a 1',
          recall DOUBLE COMMENT 'Recall (TP / (TP + FN)) de 0 a 1',
          f1_score DOUBLE COMMENT 'F1-Score harmônico de 0 a 1',
          taxa_json_valido DOUBLE COMMENT 'Proporção de respostas JSON válidas segundo o responseFormat (0 a 1)',
          latencia_media_seg DOUBLE COMMENT 'Latência média por chamada ai_query em segundos',
          latencia_p50_seg DOUBLE COMMENT 'Latência mediana (p50) em segundos',
          latencia_p95_seg DOUBLE COMMENT 'Latência p95 em segundos',
          custo_medio_reuniao_usd DOUBLE COMMENT 'Custo estimado em USD por transcrição',
          custo_projecao_1000_usd DOUBLE COMMENT 'Projeção de custo mensal para 1.000 reuniões em USD'
        )
        COMMENT 'Métricas quantitativas de avaliação da POC: precisão, recall, F1, taxa de JSON válido, latência e custo'
        """,
    )

    metric_rows = [
        ("Geral (Decisões + Pendências + Action Items)", overall_prf),
        ("Decisões", metrics_by_cat["decisoes"]),
        ("Pendências", metrics_by_cat["pendencias"]),
        ("Action Items", metrics_by_cat["action_items"]),
        ("Parsing de Falantes (Silver)", metrics_by_cat["falantes_silver"]),
    ]
    eval_values = []
    for label, m in metric_rows:
        eval_values.append(
            "(current_timestamp(), '{ep}', '{lbl}', {td}, {tg}, {tp}, {fp}, {fn}, {pr}, {rc}, {f1}, {jv}, {lm}, {p50}, {p95}, {cu}, {c1k})".format(
                ep=sql_escape(args.endpoint),
                lbl=sql_escape(label),
                td=total_docs,
                tg=len(gt_by_file),
                tp=m["tp"],
                fp=m["fp"],
                fn=m["fn"],
                pr=m["precision"],
                rc=m["recall"],
                f1=m["f1"],
                jv=json_valid_rate,
                lm=latency_stats["media_seg"],
                p50=latency_stats["p50_seg"],
                p95=latency_stats["p95_seg"],
                cu=cost_stats["custo_medio_por_reuniao_usd"],
                c1k=cost_stats["projecao_1000_reunioes_usd"],
            )
        )
    run_sql(
        args.profile,
        args.warehouse,
        f"INSERT INTO {fq_schema}.gold_metricas_avaliacao VALUES " + ", ".join(eval_values),
    )

    summary = {
        "avaliado_em_utc": datetime.now(timezone.utc).isoformat(),
        "schema_databricks": fq_schema,
        "modelo_llm": args.endpoint,
        "total_transcricoes_processadas": total_docs,
        "total_transcricoes_gabarito": len(gt_by_file),
        "taxa_json_valido": json_valid_rate,
        "taxa_data_reuniao_silver": round(date_hits / len(gt_by_file), 4),
        "metricas_geral": overall_prf,
        "metricas_por_categoria": metrics_by_cat,
        "acuracia_campos_action_items": {
            "matched_action_items": ai_field_hits["matched_total"],
            "responsavel": round(
                ai_field_hits["responsavel"] / max(1, ai_field_hits["matched_total"]), 4
            ),
            "prazo": round(ai_field_hits["prazo"] / max(1, ai_field_hits["matched_total"]), 4),
            "prioridade": round(
                ai_field_hits["prioridade"] / max(1, ai_field_hits["matched_total"]), 4
            ),
        },
        "latencia": latency_stats,
        "custo": cost_stats,
        "detalhe_por_transcricao": per_doc_eval,
    }
    RESULTS_JSON_PATH.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    # Gerar relatório Markdown legível no repositório
    md_lines = [
        "# Relatório de Avaliação Quantitativa — POC de Sumarização de Reuniões",
        "",
        f"- **Data da avaliação (UTC):** `{summary['avaliado_em_utc']}`",
        f"- **Schema Unity Catalog:** `{fq_schema}`",
        f"- **Endpoint LLM (`ai_query` + `responseFormat`):** `{args.endpoint}`",
        f"- **Transcrições processadas no Volume:** **{total_docs}** (`.vtt`, `.srt`, `.txt`)",
        f"- **Gabarito manual de referência:** **{len(gt_by_file)} transcrições** (`databricks/eval/gabarito_manual.json`)",
        "",
        "## 1. Resumo Executivo das Métricas",
        "",
        "| Dimensão | TP | FP | FN | Precisão | Recall | F1-Score |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for label, m in metric_rows:
        md_lines.append(
            f"| **{label}** | {m['tp']} | {m['fp']} | {m['fn']} | {m['precision']*100:.1f}% | {m['recall']*100:.1f}% | {m['f1']*100:.1f}% |"
        )
    md_lines.extend(
        [
            "",
            "## 2. Validação JSON, Acurácia de Campos, Latência e Custo",
            "",
            "| Indicador | Resultado Medido |",
            "|---|---|",
            f"| **Taxa de JSON válido (`responseFormat`)** | **{valid_json_docs}/{total_docs} ({json_valid_rate*100:.1f}%)** |",
            f"| **Acurácia de Data da Reunião (Silver)** | **{date_hits}/{len(gt_by_file)} ({summary['taxa_data_reuniao_silver']*100:.1f}%)** |",
            f"| **Acurácia de Responsável nos Action Items** | **{summary['acuracia_campos_action_items']['responsavel']*100:.1f}%** |",
            f"| **Acurácia de Prazo nos Action Items** | **{summary['acuracia_campos_action_items']['prazo']*100:.1f}%** |",
            f"| **Acurácia de Prioridade nos Action Items** | **{summary['acuracia_campos_action_items']['prioridade']*100:.1f}%** |",
            f"| **Latência Média por Transcrição (`ai_query`)** | **{latency_stats['media_seg']:.2f}s** (p50: `{latency_stats['p50_seg']:.2f}s` • p95: `{latency_stats['p95_seg']:.2f}s`) |",
            f"| **Tokens Médios por Transcrição (In / Out)** | **{cost_stats['tokens_entrada_medio']:.0f} in / {cost_stats['tokens_saida_medio']:.0f} out** |",
            f"| **Custo Total (18 Transcrições)** | **\\${cost_stats['custo_total_18_docs_usd']:.5f} USD** (`{cost_stats['dbus_totais_estimados']:.5f} DBUs`) |",
            f"| **Custo Médio por Reunião** | **\\${cost_stats['custo_medio_por_reuniao_usd']:.5f} USD** |",
            f"| **Projeção Mensal (1.000 Reuniões)** | **\\${cost_stats['projecao_1000_reunioes_usd']:.2f} USD/mês** |",
            "",
            f"> *Premissa de custo:* {cost_stats['premissa_preco']}.",
            "",
            "## 3. Resultado por Transcrição do Gabarito",
            "",
            "| Arquivo | Formato | JSON Válido | Decisões (P/R) | Pendências (P/R) | Action Items (P/R) | Falantes Silver (P/R) |",
            "|---|---|---|---:|---:|---:|---:|",
        ]
    )
    for d in per_doc_eval:
        md_lines.append(
            f"| `{d['arquivo_origem']}` | `{d['formato']}` | {'✅' if d['json_valido'] else '❌'} | "
            f"{d['decisoes']['precision']*100:.0f}% / {d['decisoes']['recall']*100:.0f}% | "
            f"{d['pendencias']['precision']*100:.0f}% / {d['pendencias']['recall']*100:.0f}% | "
            f"{d['action_items']['precision']*100:.0f}% / {d['action_items']['recall']*100:.0f}% | "
            f"{d['falantes_silver']['precision']*100:.0f}% / {d['falantes_silver']['recall']*100:.0f}% |"
        )
    REPORT_MD_PATH.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print("\n=== AVALIAÇÃO CONCLUÍDA ===")
    print(json.dumps({
        "json_valido": f"{valid_json_docs}/{total_docs} ({json_valid_rate*100:.1f}%)",
        "geral": overall_prf,
        "por_categoria": metrics_by_cat,
        "latencia": latency_stats,
        "custo": cost_stats,
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
