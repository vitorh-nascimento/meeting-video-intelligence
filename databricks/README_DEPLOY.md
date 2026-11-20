# Deploy da POC no Databricks Lakehouse (DAB + Lakeflow SDP + AI Functions)

Este diretório contém um **Databricks Asset Bundle (DAB)** 100% independente e parametrizável, sem nenhuma credencial, URL ou schema pessoal hardcoded.

## Pré-requisitos
1. [Databricks CLI](https://docs.databricks.com/dev-tools/cli/install.html) (`>= 0.230`).
2. Workspace Databricks com **Unity Catalog**, **Serverless Compute** e **Databricks AI Functions** habilitados.
3. Perfil configurado localmente:
   ```bash
   databricks auth login --host https://<seu-workspace>.cloud.databricks.com --profile meu-perfil
   ```

## Arquitetura Medalhão
- **Landing Zone (Volume UC):** `/Volumes/<catalog>/<schema>/<volume_name>`
- **Bronze (`bronze_transcricoes_raw`):** Streaming Table com Auto Loader (`cloudFiles`) lendo `.srt`, `.vtt`, `.txt`, `.json`.
- **Silver (`silver_transcricoes_enriquecidas`):** Higienização de timestamps/HTML + `ai_classify` (v2.0), `ai_summarize` e `ai_extract` (v2.0 com JSON schema estruturado).
- **Gold (Materialized Views):**
  - `gold_transcricoes_catalogo`
  - `gold_action_items`
  - `gold_decisoes`
  - `gold_pendencias`

## Passo a Passo de Deploy

```bash
cd databricks

# 1. Validar o bundle parametrizando catalog/schema do seu ambiente
databricks bundle validate --strict -t dev \
  --profile meu-perfil \
  --var="catalog=workspace" \
  --var="schema=meeting_intelligence_dev"

# 2. Fazer deploy do Schema, Volume e Pipeline Serverless
databricks bundle deploy -t dev \
  --profile meu-perfil \
  --var="catalog=workspace" \
  --var="schema=meeting_intelligence_dev"

# 3. Subir uma transcrição gerada pelo app local (ou via botão "Enviar para Databricks" na UI)
databricks fs cp ../data/exemplo.srt \
  dbfs:/Volumes/workspace/meeting_intelligence_dev/raw_transcripts/exemplo.srt \
  --profile meu-perfil

# 4. Executar a pipeline Lakeflow
databricks bundle run meeting_intelligence_pipeline -t dev \
  --profile meu-perfil \
  --var="catalog=workspace" \
  --var="schema=meeting_intelligence_dev"
```

## Consultas de Validação no SQL Editor / Genie Space

```sql
-- Catálogo geral
SELECT titulo, tipo_midia, categoria_ia, resumo_executivo, ferramentas_tecnologias
FROM <catalog>.<schema>.gold_transcricoes_catalogo
ORDER BY data_processamento DESC;

-- Plano de ação consolidado
SELECT titulo_origem, tarefa, responsavel, prazo, prioridade, status
FROM <catalog>.<schema>.gold_action_items
WHERE status = 'Pendente'
ORDER BY prioridade;

-- Decisões e pendências
SELECT titulo_origem, decisao, impacto, participantes_envolvidos
FROM <catalog>.<schema>.gold_decisoes;

SELECT titulo_origem, descricao, responsavel_ou_area, impacto, status
FROM <catalog>.<schema>.gold_pendencias;
```
