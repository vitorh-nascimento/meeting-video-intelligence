SELECT
  CAST(data_reuniao AS STRING) AS data_reuniao,
  titulo_origem,
  categoria_ia,
  descricao,
  responsavel_ou_area,
  impacto,
  status
FROM workspace.dev_vitortesteestudos_meeting_intelligence_poc.gold_pendencias
ORDER BY data_reuniao DESC, titulo_origem ASC
