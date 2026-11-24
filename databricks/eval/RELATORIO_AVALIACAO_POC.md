# Relatório de Avaliação Quantitativa — POC de Sumarização de Reuniões

- **Data da avaliação (UTC):** `2026-11-23T13:37:59.342788+00:00`
- **Schema Unity Catalog:** `workspace.dev_vitortesteestudos_meeting_intelligence_poc`
- **Endpoint LLM (`ai_query` + `responseFormat`):** `databricks-meta-llama-3-3-70b-instruct`
- **Transcrições processadas no Volume:** **18** (`.vtt`, `.srt`, `.txt`)
- **Gabarito manual de referência:** **6 transcrições** (`databricks/eval/gabarito_manual.json`)

## 1. Resumo Executivo das Métricas

| Dimensão | TP | FP | FN | Precisão | Recall | F1-Score |
|---|---:|---:|---:|---:|---:|---:|
| **Geral (Decisões + Pendências + Action Items)** | 41 | 3 | 1 | 93.2% | 97.6% | 95.3% |
| **Decisões** | 11 | 3 | 1 | 78.6% | 91.7% | 84.6% |
| **Pendências** | 12 | 0 | 0 | 100.0% | 100.0% | 100.0% |
| **Action Items** | 18 | 0 | 0 | 100.0% | 100.0% | 100.0% |
| **Parsing de Falantes (Silver)** | 19 | 0 | 0 | 100.0% | 100.0% | 100.0% |

## 2. Validação JSON, Acurácia de Campos, Latência e Custo

| Indicador | Resultado Medido |
|---|---|
| **Taxa de JSON válido (`responseFormat`)** | **18/18 (100.0%)** |
| **Acurácia de Data da Reunião (Silver)** | **6/6 (100.0%)** |
| **Acurácia de Responsável nos Action Items** | **100.0%** |
| **Acurácia de Prazo nos Action Items** | **100.0%** |
| **Acurácia de Prioridade nos Action Items** | **100.0%** |
| **Latência Média por Transcrição (`ai_query`)** | **43.56s** (p50: `32.85s` • p95: `95.68s`) |
| **Tokens Médios por Transcrição (In / Out)** | **687 in / 489 out** |
| **Custo Total (18 Transcrições)** | **\$0.03880 USD** (`0.55426 DBUs`) |
| **Custo Médio por Reunião** | **\$0.00216 USD** |
| **Projeção Mensal (1.000 Reuniões)** | **\$2.16 USD/mês** |

> *Premissa de custo:* Pay-per-Token FMAPI ($0.07/DBU; 14.286 DBU/1M in; 42.857 DBU/1M out).

## 3. Resultado por Transcrição do Gabarito

| Arquivo | Formato | JSON Válido | Decisões (P/R) | Pendências (P/R) | Action Items (P/R) | Falantes Silver (P/R) |
|---|---|---|---:|---:|---:|---:|
| `2026-11-02_reuniao_migracao_lakehouse_medallion.vtt` | `vtt` | ✅ | 100% / 100% | 100% / 100% | 100% / 100% | 100% / 100% |
| `2026-11-03_reuniao_comite_finops_nuvem_q4.srt` | `srt` | ✅ | 67% / 100% | 100% / 100% | 100% / 100% | 100% / 100% |
| `2026-11-04_reuniao_governanca_unity_catalog_lgpd.txt` | `txt` | ✅ | 100% / 100% | 100% / 100% | 100% / 100% | 100% / 100% |
| `2026-11-05_discovery_cliente_portal_selfservice_bi.vtt` | `vtt` | ✅ | 100% / 100% | 100% / 100% | 100% / 100% | 100% / 100% |
| `2026-11-06_postmortem_incidente_pipeline_streaming.srt` | `srt` | ✅ | 100% / 100% | 100% / 100% | 100% / 100% | 100% / 100% |
| `2026-11-09_planejamento_sprint_genie_ai_assistants.txt` | `txt` | ✅ | 33% / 50% | 100% / 100% | 100% / 100% | 100% / 100% |
