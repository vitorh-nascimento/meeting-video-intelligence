-- =============================================================================
-- Camada Silver — Limpeza, Parsing de Falantes (Speakers) e Metadados
-- Responsabilidades determinísticas (sem chamada de LLM):
-- 1. Extrair metadados (formato, data da reunião, título de cabeçalho, duração,
--    tipo de mídia).
-- 2. Extrair falantes (suporta Microsoft Teams <v Nome>, SRT/TXT "Nome: fala"
--    e prefixo com timestamp "[HH:MM:SS] Nome: fala") e contar turnos.
-- 3. Higienizar conteúdo preservando atribuição "Falante: fala" para maximizar
--    precisão de responsáveis e decisões na camada Gold.
-- =============================================================================

CREATE OR REFRESH STREAMING TABLE silver_transcricoes_limpas (
  CONSTRAINT conteudo_valido EXPECT (length(conteudo_limpo) > 20) ON VIOLATION DROP ROW,
  CONSTRAINT falantes_identificados EXPECT (qtd_falantes > 0)
)
COMMENT 'Transcrições higienizadas com parsing determinístico de falantes (speakers), turnos e metadados estruturados'
CLUSTER BY (data_reuniao, tipo_midia)
TBLPROPERTIES (
  'quality' = 'silver',
  'delta.enableRowTracking' = 'true'
)
AS
WITH base AS (
  SELECT
    documento_id,
    arquivo_origem,
    caminho_arquivo,
    tamanho_bytes,
    data_modificacao,
    ingerido_em,
    conteudo_bruto,
    lower(regexp_extract(arquivo_origem, '\\.([^.]+)$', 1)) AS formato_arquivo,
    -- Metadados extraídos do cabeçalho (VTT NOTE / TXT) ou nome do arquivo
    coalesce(
      try_to_date(regexp_extract(conteudo_bruto, 'Data:\\s*(\\d{4}-\\d{2}-\\d{2})', 1), 'yyyy-MM-dd'),
      try_to_date(regexp_extract(arquivo_origem, '^(\\d{4}-\\d{2}-\\d{2})', 1), 'yyyy-MM-dd'),
      to_date(data_modificacao)
    ) AS data_reuniao,
    nullif(
      trim(
        coalesce(
          nullif(regexp_extract(conteudo_bruto, 'Reunião:\\s*([^|\\r\\n]+)', 1), ''),
          initcap(replace(regexp_replace(regexp_replace(arquivo_origem, '^\\d{4}-\\d{2}-\\d{2}_', ''), '\\.[^.]+$', ''), '_', ' '))
        )
      ),
      ''
    ) AS titulo_metadado,
    try_cast(nullif(regexp_extract(conteudo_bruto, 'Duração:\\s*(\\d+)\\s*min', 1), '') AS DOUBLE) AS duracao_declarada_min,
    CASE
      WHEN arquivo_origem RLIKE '(?i)discovery|cliente' THEN 'Discovery/Cliente'
      WHEN arquivo_origem RLIKE '(?i)postmortem|incidente' THEN 'Post-mortem/Incidente'
      WHEN arquivo_origem RLIKE '(?i)workshop|aula|treinamento|video|youtube' THEN 'Workshop/Aula Técnica'
      WHEN arquivo_origem RLIKE '(?i)comite|executivo|orcamento' THEN 'Comitê Executivo'
      ELSE 'Reunião Corporativa'
    END AS tipo_midia,
    -- Falantes extraídos de tags VTT (<v Nome>) e de linhas "Nome: fala" (SRT/TXT)
    regexp_extract_all(conteudo_bruto, '<v\\s+([^>]+)>', 1) AS falantes_vtt_raw,
    regexp_extract_all(
      conteudo_bruto,
      '(?m)^(?:\\[[0-9:]+\\]\\s*)?([A-ZÀ-Ý][a-zà-ÿ]+(?:\\s+[A-ZÀ-Ý][a-zà-ÿ]+){1,3})\\s*:',
      1
    ) AS falantes_prefix_raw
  FROM STREAM(bronze_transcricoes_raw)
),
parsed AS (
  SELECT
    *,
    filter(
      transform(
        CASE WHEN size(falantes_vtt_raw) > 0 THEN falantes_vtt_raw ELSE falantes_prefix_raw END,
        s -> trim(s)
      ),
      s -> s IS NOT NULL
        AND length(s) >= 3
        AND lower(s) NOT IN ('reunião', 'reuniao', 'data', 'duração', 'duracao', 'participantes', 'local', 'pauta', 'note')
    ) AS turnos_falantes,
    -- Normalização do texto preservando "Falante: fala" antes de remover tags/timestamps
    -- Nota: usar [^\r\n]* em vez de .* pois Spark SQL regexp_replace trata '.' com DOTALL.
    trim(
      regexp_replace(
        regexp_replace(
          regexp_replace(
            regexp_replace(
              regexp_replace(
                regexp_replace(
                  regexp_replace(conteudo_bruto, '(?m)^WEBVTT[^\\r\\n]*', ''),
                  '(?m)^NOTE[^\\r\\n]*',
                  ''
                ),
                '(?m)^cue-\\d+[ \\t]*\\r?$',
                ''
              ),
              '(?:\\d{1,2}:)?\\d{2}:\\d{2}[,\\.]\\d{3}\\s*-->\\s*(?:\\d{1,2}:)?\\d{2}:\\d{2}[,\\.]\\d{3}',
              ''
            ),
            '(?m)^[ \\t]*\\d+[ \\t]*\\r?$',
            ''
          ),
          '<v\\s+([^>]+)>',
          '$1: '
        ),
        '<[^>]+>',
        ''
      )
    ) AS texto_sem_tags
  FROM base
),
cleaned AS (
  SELECT
    documento_id,
    arquivo_origem,
    caminho_arquivo,
    formato_arquivo,
    tamanho_bytes,
    data_modificacao,
    data_reuniao,
    titulo_metadado,
    tipo_midia,
    duracao_declarada_min,
    array_distinct(turnos_falantes) AS falantes,
    size(array_distinct(turnos_falantes)) AS qtd_falantes,
    size(turnos_falantes) AS total_turnos,
    array_join(array_distinct(turnos_falantes), ', ') AS falantes_texto,
    trim(regexp_replace(regexp_replace(texto_sem_tags, '[ \\t]+', ' '), '(\\r?\\n\\s*){2,}', '\n')) AS conteudo_limpo,
    ingerido_em
  FROM parsed
)
SELECT
  documento_id,
  arquivo_origem,
  caminho_arquivo,
  formato_arquivo,
  tamanho_bytes,
  data_modificacao,
  data_reuniao,
  titulo_metadado,
  tipo_midia,
  falantes,
  qtd_falantes,
  total_turnos,
  falantes_texto,
  conteudo_limpo,
  size(split(regexp_replace(conteudo_limpo, '\\s+', ' '), ' ')) AS total_palavras,
  length(conteudo_limpo) AS total_caracteres,
  coalesce(duracao_declarada_min, round(size(split(regexp_replace(conteudo_limpo, '\\s+', ' '), ' ')) / 145.0, 1)) AS duracao_estimada_min,
  cast(ceil(length(conteudo_limpo) / 4.0) AS INT) AS tokens_entrada_estimados,
  ingerido_em,
  current_timestamp() AS processado_silver_em
FROM cleaned;
