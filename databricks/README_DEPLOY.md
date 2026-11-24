# Deploy da POC no Databricks Lakehouse (DAB + Lakeflow SDP + `ai_query` + Genie Space)

Este diretório contém um **Databricks Asset Bundle (DAB)** parametrizável implementando todas as etapas da POC de sumarização de reuniões no Databricks Lakehouse:

## Arquitetura Medalhão & Avaliação
- **Dados Fictícios (`poc_data/`):** gerador reproduzível de **18 transcrições corporativas** (`.vtt` Teams, `.srt` Zoom/Whisper e `.txt` Meet) prontas para upload no Unity Catalog Volume `/Volumes/<catalog>/<schema>/raw_transcripts`.
- **Bronze (`bronze_transcricoes_raw`):** Streaming Table em Lakeflow SDP SQL com **`STREAM read_files(..., format => 'text', wholeText => true)`**.
- **Silver (`silver_transcricoes_limpas`):** Limpeza determinística de timestamps/WEBVTT/HTML + **parsing de falantes (`falantes`, `qtd_falantes`, `total_turnos`)** e **metadados** (`data_reuniao`, `formato_arquivo`, `titulo_metadado`, `tipo_midia`, `duracao_estimada_min`, `tokens_entrada_estimados`).
- **Gold (`gold_tabelas_analiticas.sql`):**
  - `gold_transcricoes_extracao`: Streaming Table que invoca **`ai_query`** com **`responseFormat` (JSON Schema estrito)** e `failOnError => false` **1 única vez por transcrição**, registrando `json_valido` e `extracao_erro`.
  - Materialized Views analíticas com Liquid Clustering:
    - `gold_transcricoes_catalogo`
    - `gold_decisoes`
    - `gold_pendencias`
    - `gold_action_items`
- **Avaliação Quantitativa (`eval/`):**
  - Gabarito manual de **6 transcrições** (`eval/gabarito_manual.json` + tabela `eval_gabarito_manual`).
  - Script `eval/evaluate_poc.py` medindo **precisão, recall, F1, taxa de JSON válido, latência (média/p50/p95) e custo estimado (DBU/USD)**, salvando em `gold_metricas_avaliacao` e gerando `eval/RELATORIO_AVALIACAO_POC.md`.
- **Genie Space (`genie/create_genie_space.py`):** cria e valida um **Genie Space** dedicado conectado às 5 tabelas Gold (`gold_transcricoes_catalogo`, `gold_decisoes`, `gold_pendencias`, `gold_action_items` e `gold_metricas_avaliacao`).

## Passo a Passo Reproduzível

```powershell
# 1. Gerar as 18 transcrições fictícias
.venv\Scripts\python.exe databricks\poc_data\generate_transcripts.py

# 2. Validar e fazer deploy do DAB (Schema, Volume e Pipeline Serverless)
cd databricks
databricks bundle validate -t dev --profile <SEU_PERFIL>
databricks bundle deploy -t dev --profile <SEU_PERFIL>

# 3. Subir as 18 transcrições no Volume do Unity Catalog
databricks fs cp -r poc_data/transcripts/ dbfs:/Volumes/<CATALOG>/<SCHEMA_DEPLOYADO>/raw_transcripts/ --overwrite --profile <SEU_PERFIL>

# 4. Executar a pipeline Lakeflow Medallion
databricks bundle run meeting_intelligence_pipeline -t dev --profile <SEU_PERFIL>

# 5. Rodar avaliação contra o gabarito de 6 transcrições (precisão, recall, JSON válido, latência e custo)
cd ..
.venv\Scripts\python.exe databricks\eval\evaluate_poc.py `
  --profile <SEU_PERFIL> `
  --warehouse <WAREHOUSE_ID> `
  --catalog <CATALOG> `
  --schema <SCHEMA_DEPLOYADO>

# 6. Criar e validar o Genie Space conectado às tabelas Gold
.venv\Scripts\python.exe databricks\genie\create_genie_space.py `
  --profile <SEU_PERFIL> `
  --warehouse <WAREHOUSE_ID> `
  --catalog <CATALOG> `
  --schema <SCHEMA_DEPLOYADO>
```
