SELECT
  COUNT(*) AS total_reunioes,
  COALESCE(SUM(qtd_decisoes), 0) AS total_decisoes,
  COALESCE(SUM(qtd_pendencias), 0) AS total_pendencias,
  COALESCE(SUM(qtd_action_items), 0) AS total_action_items,
  ROUND(AVG(CASE WHEN json_valido THEN 100.0 ELSE 0.0 END), 1) AS taxa_json_valido_pct,
  COALESCE(SUM(total_palavras), 0) AS total_palavras,
  CAST(MAX(data_processamento) AS STRING) AS ultima_atualizacao
FROM workspace.dev_vitortesteestudos_meeting_intelligence_poc.gold_transcricoes_catalogo
