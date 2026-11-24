SELECT
  CAST(data_reuniao AS STRING) AS data_reuniao,
  titulo_origem,
  categoria_ia,
  decisao,
  contexto,
  impacto
FROM workspace.dev_vitortesteestudos_meeting_intelligence_poc.gold_decisoes
ORDER BY data_reuniao DESC, titulo_origem ASC
