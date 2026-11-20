"""
Camada Bronze — Ingestão Incremental via Auto Loader (cloudFiles).
Monitora continuamente o Unity Catalog Volume configurado em `raw_volume_path`
para arquivos .srt, .vtt, .txt e .json.
"""

from pyspark import pipelines as dp
from pyspark.sql import functions as F

RAW_VOLUME_PATH = spark.conf.get("raw_volume_path")


@dp.table(
    name="bronze_transcricoes_raw",
    comment="Ingestão incremental de transcrições brutas (.srt, .vtt, .txt, .json) do Unity Catalog Volume",
    table_properties={"quality": "bronze"},
    cluster_by_auto=True,
)
def bronze_transcricoes_raw():
    return (
        spark.readStream.format("cloudFiles")
        .option("cloudFiles.format", "text")
        .option("wholetext", "true")
        .option("pathGlobFilter", "*.{srt,vtt,txt,json}")
        .load(RAW_VOLUME_PATH)
        .select(
            F.sha2(F.col("_metadata.file_path"), 256).alias("documento_id"),
            F.col("_metadata.file_name").alias("arquivo_origem"),
            F.col("_metadata.file_path").alias("caminho_arquivo"),
            F.col("_metadata.file_size").alias("tamanho_bytes"),
            F.col("_metadata.file_modification_time").alias("data_modificacao"),
            F.col("value").alias("conteudo_bruto"),
            F.current_timestamp().alias("ingerido_em"),
        )
    )
