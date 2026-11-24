-- @param categoria STRING
SELECT
  arquivo_origem,
  formato_arquivo,
  CAST(data_reuniao AS STRING) AS data_reuniao,
  titulo,
  tipo_midia,
  categoria_ia,
  qtd_falantes,
  falantes_texto,
  total_palavras,
  duracao_estimada_min,
  resumo_executivo,
  qtd_decisoes,
  qtd_pendencias,
  qtd_action_items,
  json_valido,
  modelo_llm
FROM workspace.dev_vitortesteestudos_meeting_intelligence_poc.gold_transcricoes_catalogo
WHERE :categoria = 'Todas' OR categoria_ia = :categoria
ORDER BY data_reuniao DESC, arquivo_origem ASC
