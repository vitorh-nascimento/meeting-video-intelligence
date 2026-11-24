-- =============================================================================
-- Camada Gold — Extração Estruturada com ai_query() + responseFormat (JSON Schema)
-- + Materialized Views analíticas prontas para Genie Space e AI/BI Dashboards:
--   1. gold_transcricoes_extracao  (Streaming Table: chama ai_query 1x por doc)
--   2. gold_transcricoes_catalogo  (MV: catálogo consolidado + taxa JSON válido)
--   3. gold_decisoes               (MV: 1 linha por decisão aprovada)
--   4. gold_pendencias             (MV: 1 linha por pendência/bloqueio)
--   5. gold_action_items           (MV: 1 linha por action item com dono/prazo)
-- =============================================================================

CREATE OR REFRESH STREAMING TABLE gold_transcricoes_extracao
COMMENT 'Extração estruturada via ai_query() com responseFormat (JSON Schema estrito) — executada uma única vez por transcrição'
CLUSTER BY (data_reuniao, tipo_midia)
TBLPROPERTIES ('quality' = 'gold')
AS
WITH llm_calls AS (
  SELECT
    documento_id,
    arquivo_origem,
    formato_arquivo,
    data_reuniao,
    titulo_metadado,
    tipo_midia,
    falantes,
    qtd_falantes,
    total_turnos,
    falantes_texto,
    total_palavras,
    duracao_estimada_min,
    tokens_entrada_estimados,
    ingerido_em,
    '${ai_query_endpoint}' AS modelo_llm,
    ai_query(
      '${ai_query_endpoint}',
      concat(
        'Você é um analista sênior de atas corporativas. Analise a transcrição de reunião abaixo e extraia em Português do Brasil: ',
        '1) titulo_sugerido conciso; ',
        '2) categoria_ia (escolha exatamente uma das categorias permitidas no schema); ',
        '3) resumo_executivo objetivo (2 a 4 frases); ',
        '4) decisoes: TODAS as decisões explicitamente aprovadas/fechadas na reunião (separe cada decisão distinta como um item separado); ',
        '5) pendencias: TODAS as pendências, bloqueios ou itens em aberto aguardando terceiros; ',
        '6) action_items: TODAS as tarefas atribuídas com responsavel (nome completo do falante/pessoa), prazo exato citado (ou "A definir"), prioridade (Alta, Média ou Baixa) e status "Pendente"; ',
        '7) ferramentas_tecnologias citadas.\n\n',
        'Metadados conhecidos — Data: ', coalesce(cast(data_reuniao AS STRING), 'N/A'),
        ' | Falantes: ', coalesce(falantes_texto, 'N/A'),
        '\n\nTranscrição:\n',
        conteudo_limpo
      ),
      responseFormat => '{"type":"json_schema","json_schema":{"name":"extracao_reuniao","strict":true,"schema":{"type":"object","properties":{"titulo_sugerido":{"type":"string"},"categoria_ia":{"type":"string","enum":["Engenharia de Dados & Lakehouse","Arquitetura Cloud & Infraestrutura","Produto & Discovery de Cliente","Governança, Segurança & FinOps","Operações, SRE & Qualidade","Alinhamento & Gestão de Equipe"]},"resumo_executivo":{"type":"string"},"decisoes":{"type":"array","items":{"type":"object","properties":{"decisao":{"type":"string"},"contexto":{"type":"string"},"impacto":{"type":"string"},"participantes_envolvidos":{"type":"array","items":{"type":"string"}}},"required":["decisao","contexto","impacto","participantes_envolvidos"],"additionalProperties":false}},"pendencias":{"type":"array","items":{"type":"object","properties":{"descricao":{"type":"string"},"responsavel_ou_area":{"type":"string"},"impacto":{"type":"string"},"status":{"type":"string"}},"required":["descricao","responsavel_ou_area","impacto","status"],"additionalProperties":false}},"action_items":{"type":"array","items":{"type":"object","properties":{"tarefa":{"type":"string"},"responsavel":{"type":"string"},"prazo":{"type":"string"},"prioridade":{"type":"string","enum":["Alta","Média","Baixa"]},"status":{"type":"string"}},"required":["tarefa","responsavel","prazo","prioridade","status"],"additionalProperties":false}},"ferramentas_tecnologias":{"type":"array","items":{"type":"string"}}},"required":["titulo_sugerido","categoria_ia","resumo_executivo","decisoes","pendencias","action_items","ferramentas_tecnologias"],"additionalProperties":false}}}',
      modelParameters => named_struct('temperature', CAST(0.0 AS DOUBLE), 'max_tokens', 2500),
      failOnError => false
    ) AS ai_resp
  FROM STREAM(silver_transcricoes_limpas)
),
parsed AS (
  SELECT
    *,
    ai_resp.result AS raw_json,
    ai_resp.errorMessage AS extracao_erro,
    from_json(
      ai_resp.result,
      'STRUCT<
        titulo_sugerido: STRING,
        categoria_ia: STRING,
        resumo_executivo: STRING,
        decisoes: ARRAY<STRUCT<decisao: STRING, contexto: STRING, impacto: STRING, participantes_envolvidos: ARRAY<STRING>>>,
        pendencias: ARRAY<STRUCT<descricao: STRING, responsavel_ou_area: STRING, impacto: STRING, status: STRING>>,
        action_items: ARRAY<STRUCT<tarefa: STRING, responsavel: STRING, prazo: STRING, prioridade: STRING, status: STRING>>,
        ferramentas_tecnologias: ARRAY<STRING>
      >'
    ) AS extracao_struct
  FROM llm_calls
)
SELECT
  documento_id,
  arquivo_origem,
  formato_arquivo,
  data_reuniao,
  titulo_metadado,
  tipo_midia,
  falantes,
  qtd_falantes,
  total_turnos,
  falantes_texto,
  total_palavras,
  duracao_estimada_min,
  tokens_entrada_estimados,
  cast(ceil(length(coalesce(raw_json, '')) / 4.0) AS INT) AS tokens_saida_estimados,
  modelo_llm,
  raw_json,
  extracao_erro,
  (extracao_erro IS NULL AND extracao_struct IS NOT NULL) AS json_valido,
  extracao_struct,
  ingerido_em,
  current_timestamp() AS processado_gold_em
FROM parsed;


CREATE OR REFRESH MATERIALIZED VIEW gold_transcricoes_catalogo
COMMENT 'Catálogo consolidado de reuniões com resumo executivo, falantes, categoria, contagens e status de validação JSON'
CLUSTER BY (categoria_ia, data_reuniao)
TBLPROPERTIES ('quality' = 'gold')
AS
SELECT
  documento_id,
  arquivo_origem,
  formato_arquivo,
  data_reuniao,
  coalesce(nullif(extracao_struct.titulo_sugerido, ''), titulo_metadado) AS titulo,
  tipo_midia,
  coalesce(extracao_struct.categoria_ia, 'Alinhamento & Gestão de Equipe') AS categoria_ia,
  falantes,
  qtd_falantes,
  total_turnos,
  falantes_texto,
  total_palavras,
  duracao_estimada_min,
  extracao_struct.resumo_executivo AS resumo_executivo,
  coalesce(size(extracao_struct.decisoes), 0) AS qtd_decisoes,
  coalesce(size(extracao_struct.pendencias), 0) AS qtd_pendencias,
  coalesce(size(extracao_struct.action_items), 0) AS qtd_action_items,
  extracao_struct.ferramentas_tecnologias AS ferramentas_tecnologias,
  tokens_entrada_estimados,
  tokens_saida_estimados,
  modelo_llm,
  json_valido,
  extracao_erro,
  processado_gold_em AS data_processamento
FROM gold_transcricoes_extracao;


CREATE OR REFRESH MATERIALIZED VIEW gold_decisoes
COMMENT 'Registro histórico de decisões aprovadas em reuniões com contexto, impacto e participantes envolvidos'
CLUSTER BY (categoria_ia, data_reuniao)
TBLPROPERTIES ('quality' = 'gold')
AS
SELECT
  g.documento_id,
  g.arquivo_origem,
  g.data_reuniao,
  coalesce(nullif(g.extracao_struct.titulo_sugerido, ''), g.titulo_metadado) AS titulo_origem,
  g.tipo_midia,
  coalesce(g.extracao_struct.categoria_ia, 'Alinhamento & Gestão de Equipe') AS categoria_ia,
  d.decisao AS decisao,
  coalesce(d.contexto, '') AS contexto,
  coalesce(d.impacto, '') AS impacto,
  d.participantes_envolvidos AS participantes_envolvidos,
  g.processado_gold_em AS data_processamento
FROM gold_transcricoes_extracao g
LATERAL VIEW explode(g.extracao_struct.decisoes) exploded AS d
WHERE g.json_valido = true AND d.decisao IS NOT NULL;


CREATE OR REFRESH MATERIALIZED VIEW gold_pendencias
COMMENT 'Pendências, bloqueios e dependências em aberto extraídas das transcrições por área responsável'
CLUSTER BY (status, categoria_ia)
TBLPROPERTIES ('quality' = 'gold')
AS
SELECT
  g.documento_id,
  g.arquivo_origem,
  g.data_reuniao,
  coalesce(nullif(g.extracao_struct.titulo_sugerido, ''), g.titulo_metadado) AS titulo_origem,
  g.tipo_midia,
  coalesce(g.extracao_struct.categoria_ia, 'Alinhamento & Gestão de Equipe') AS categoria_ia,
  p.descricao AS descricao,
  coalesce(nullif(p.responsavel_ou_area, ''), 'A definir') AS responsavel_ou_area,
  coalesce(nullif(p.impacto, ''), 'Médio') AS impacto,
  coalesce(nullif(p.status, ''), 'Pendente') AS status,
  g.processado_gold_em AS data_processamento
FROM gold_transcricoes_extracao g
LATERAL VIEW explode(g.extracao_struct.pendencias) exploded AS p
WHERE g.json_valido = true AND p.descricao IS NOT NULL;


CREATE OR REFRESH MATERIALIZED VIEW gold_action_items
COMMENT 'Plano de ação consolidado (1 linha por Action Item) com responsável, prazo, prioridade e status'
CLUSTER BY (prioridade, status, categoria_ia)
TBLPROPERTIES ('quality' = 'gold')
AS
SELECT
  g.documento_id,
  g.arquivo_origem,
  g.data_reuniao,
  coalesce(nullif(g.extracao_struct.titulo_sugerido, ''), g.titulo_metadado) AS titulo_origem,
  g.tipo_midia,
  coalesce(g.extracao_struct.categoria_ia, 'Alinhamento & Gestão de Equipe') AS categoria_ia,
  a.tarefa AS tarefa,
  coalesce(nullif(a.responsavel, ''), 'A definir') AS responsavel,
  coalesce(nullif(a.prazo, ''), 'A definir') AS prazo,
  coalesce(nullif(a.prioridade, ''), 'Média') AS prioridade,
  coalesce(nullif(a.status, ''), 'Pendente') AS status,
  g.processado_gold_em AS data_processamento
FROM gold_transcricoes_extracao g
LATERAL VIEW explode(g.extracao_struct.action_items) exploded AS a
WHERE g.json_valido = true AND a.tarefa IS NOT NULL;
