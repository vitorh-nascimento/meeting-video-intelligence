-- @param prioridade STRING
SELECT
  CAST(data_reuniao AS STRING) AS data_reuniao,
  titulo_origem,
  categoria_ia,
  tarefa,
  responsavel,
  prazo,
  prioridade,
  status
FROM workspace.dev_vitortesteestudos_meeting_intelligence_poc.gold_action_items
WHERE :prioridade = 'Todas' OR prioridade = :prioridade
ORDER BY
  CASE prioridade WHEN 'Alta' THEN 1 WHEN 'Média' THEN 2 ELSE 3 END,
  data_reuniao DESC
