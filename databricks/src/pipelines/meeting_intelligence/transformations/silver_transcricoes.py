"""
Camada Silver — Higienização de SRT/VTT/HTML + Enriquecimento Semântico com Databricks AI Functions:
- ai_classify (v2.0): classificação temática parametrizável
- ai_summarize: resumo executivo estruturado
- ai_extract (v2.0 com JSON schema rico): extração de decisões, pendências,
  action items (tarefa, responsável, prazo, prioridade), insights, métricas, riscos e tecnologias.
"""

import json

from pyspark import pipelines as dp
from pyspark.sql import functions as F

DEFAULT_CATEGORIES_JSON = json.dumps(
    [
        "Engenharia de Dados & Lakehouse",
        "Arquitetura Cloud & Infraestrutura",
        "Produto & Discovery de Cliente",
        "Alinhamento & Gestão de Equipe",
        "Treinamento & Aula Técnica",
        "Governança, Segurança & FinOps",
        "Geral / Outros",
    ],
    ensure_ascii=False,
)

CATEGORIES_JSON = spark.conf.get("categories_json", DEFAULT_CATEGORIES_JSON)

EXTRACTION_SCHEMA = json.dumps(
    {
        "titulo_sugerido": {"type": "string"},
        "topicos_principais": {"type": "array", "items": {"type": "string"}},
        "decisoes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "decisao": {"type": "string"},
                    "contexto": {"type": "string"},
                    "impacto": {"type": "string"},
                    "participantes_envolvidos": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
        "pendencias": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "descricao": {"type": "string"},
                    "responsavel_ou_area": {"type": "string"},
                    "impacto": {"type": "string"},
                    "status": {"type": "string"},
                },
            },
        },
        "action_items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "tarefa": {"type": "string"},
                    "responsavel": {"type": "string"},
                    "prazo": {"type": "string"},
                    "prioridade": {"type": "enum", "labels": ["Alta", "Média", "Baixa"]},
                    "status": {"type": "string"},
                },
            },
        },
        "insights": {"type": "array", "items": {"type": "string"}},
        "aprendizados_tecnicos": {"type": "array", "items": {"type": "string"}},
        "metricas_citadas": {"type": "array", "items": {"type": "string"}},
        "riscos": {"type": "array", "items": {"type": "string"}},
        "ferramentas_tecnologias": {"type": "array", "items": {"type": "string"}},
    },
    ensure_ascii=False,
)

EXTRACTION_INSTRUCTIONS = (
    "Extraia em Português do Brasil as decisões aprovadas, pendências/bloqueios em aberto, "
    "action items com responsável/prazo/prioridade e informações-chave da transcrição. "
    "Use status 'Pendente' por padrão para pendências e action items."
)


@dp.table(
    name="silver_transcricoes_enriquecidas",
    comment="Transcrições higienizadas e enriquecidas em passo único com Databricks AI Functions",
    table_properties={"quality": "silver", "delta.enableRowTracking": "true"},
    cluster_by=["categoria_ia", "tipo_midia"],
)
@dp.expect_or_drop("conteudo_valido", "LENGTH(conteudo_limpo) > 20")
def silver_transcricoes_enriquecidas():
    bronze_df = spark.readStream.table("bronze_transcricoes_raw")

    # Remove cabeçalho WEBVTT, timestamps SRT/VTT, índices numéricos isolados e tags HTML/voice
    sem_vtt = F.regexp_replace(F.col("conteudo_bruto"), r"(?m)^WEBVTT.*$", "")
    sem_timestamps = F.regexp_replace(
        sem_vtt,
        r"(?:\d{1,2}:)?\d{2}:\d{2}[,\.]\d{3}\s*-->\s*(?:\d{1,2}:)?\d{2}:\d{2}[,\.]\d{3}",
        " ",
    )
    sem_indices = F.regexp_replace(sem_timestamps, r"(?m)^\s*\d+\s*$", " ")
    sem_tags = F.regexp_replace(sem_indices, r"<[^>]+>", " ")

    df_clean = (
        bronze_df.withColumn("conteudo_limpo", F.trim(F.regexp_replace(sem_tags, r"\s+", " ")))
        .withColumn("total_palavras", F.size(F.split(F.col("conteudo_limpo"), r"\s+")))
        .withColumn(
            "tipo_midia",
            F.when(F.col("arquivo_origem").rlike("(?i)youtube|video|aula|curso|palestra"), "Vídeo Técnico/Aula")
            .when(F.col("arquivo_origem").rlike("(?i)meet|teams|zoom|reuniao|daily|weekly|sync"), "Reunião")
            .when(F.col("arquivo_origem").rlike("(?i)podcast|audio|gravacao"), "Áudio/Podcast")
            .when(F.col("arquivo_origem").rlike("(?i)entrevista|discovery"), "Entrevista")
            .otherwise("Outro"),
        )
    )

    df_enriched = (
        df_clean.withColumn(
            "classificacao_raw",
            F.call_function(
                "ai_classify",
                F.col("conteudo_limpo"),
                F.lit(CATEGORIES_JSON),
                F.create_map(F.lit("version"), F.lit("2.0")),
            ),
        )
        .withColumn("categoria_ia", F.expr("classificacao_raw:response[0]::STRING"))
        .withColumn("resumo_executivo", F.expr("ai_summarize(conteudo_limpo, 120)"))
        .withColumn(
            "extracao_raw",
            F.call_function(
                "ai_extract",
                F.col("conteudo_limpo"),
                F.lit(EXTRACTION_SCHEMA),
                F.create_map(
                    F.lit("version"),
                    F.lit("2.0"),
                    F.lit("instructions"),
                    F.lit(EXTRACTION_INSTRUCTIONS),
                ),
            ),
        )
        .withColumn("extracao_erro", F.expr("extracao_raw:error_message::STRING"))
        .withColumn("atualizado_em", F.current_timestamp())
    )

    return df_enriched
