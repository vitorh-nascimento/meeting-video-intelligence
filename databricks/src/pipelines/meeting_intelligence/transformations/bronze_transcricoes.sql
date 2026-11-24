-- =============================================================================
-- Camada Bronze — Ingestão Incremental de Transcrições com read_files()
-- Lê arquivos .srt, .vtt, .txt e .json do Unity Catalog Volume configurado em
-- `raw_volume_path` usando Auto Loader SQL (`STREAM read_files(...)`).
-- =============================================================================

CREATE OR REFRESH STREAMING TABLE bronze_transcricoes_raw
COMMENT 'Ingestão incremental de transcrições brutas (.srt, .vtt, .txt, .json) do Unity Catalog Volume usando read_files()'
CLUSTER BY AUTO
TBLPROPERTIES ('quality' = 'bronze')
AS
SELECT
  sha2(_metadata.file_path, 256) AS documento_id,
  _metadata.file_name AS arquivo_origem,
  _metadata.file_path AS caminho_arquivo,
  _metadata.file_size AS tamanho_bytes,
  _metadata.file_modification_time AS data_modificacao,
  value AS conteudo_bruto,
  current_timestamp() AS ingerido_em
FROM STREAM read_files(
  '${raw_volume_path}',
  format => 'text',
  wholeText => true,
  pathGlobFilter => '*.{srt,vtt,txt,json}'
);
