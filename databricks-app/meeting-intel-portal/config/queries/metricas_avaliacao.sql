SELECT
  modelo_llm,
  categoria_metrica,
  total_transcricoes_volume,
  total_transcricoes_gabarito,
  tp,
  fp,
  fn,
  ROUND(precisao * 100.0, 1) AS precisao_pct,
  ROUND(recall * 100.0, 1) AS recall_pct,
  ROUND(f1_score * 100.0, 1) AS f1_pct,
  ROUND(taxa_json_valido * 100.0, 1) AS taxa_json_valido_pct,
  latencia_media_seg,
  latencia_p50_seg,
  latencia_p95_seg,
  custo_medio_reuniao_usd,
  custo_projecao_1000_usd,
  CAST(avaliado_em AS STRING) AS avaliado_em
FROM workspace.dev_vitortesteestudos_meeting_intelligence_poc.gold_metricas_avaliacao
ORDER BY
  CASE
    WHEN categoria_metrica LIKE 'Geral%' THEN 1
    WHEN categoria_metrica = 'Decisões' THEN 2
    WHEN categoria_metrica = 'Pendências' THEN 3
    WHEN categoria_metrica = 'Action Items' THEN 4
    ELSE 5
  END
