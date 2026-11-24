SELECT
  categoria_ia,
  COUNT(*) AS reunioes,
  COALESCE(SUM(qtd_decisoes), 0) AS decisoes,
  COALESCE(SUM(qtd_pendencias), 0) AS pendencias,
  COALESCE(SUM(qtd_action_items), 0) AS action_items
FROM workspace.dev_vitortesteestudos_meeting_intelligence_poc.gold_transcricoes_catalogo
GROUP BY categoria_ia
ORDER BY reunioes DESC, categoria_ia ASC
