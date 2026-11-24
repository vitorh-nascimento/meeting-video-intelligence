"""
Gerador reproduzível de 18 transcrições corporativas fictícias (PT-BR) para a POC
Meeting & Video Intelligence no Databricks Lakehouse.

Gera arquivos em três formatos reais encontrados em ambientes empresariais:
- .vtt (Microsoft Teams com tags <v Nome Sobrenome>)
- .srt (Zoom / Whisper / gravações legendadas)
- .txt (Google Meet / atas com cabeçalho de metadados)

Uso:
    python databricks/poc_data/generate_transcripts.py
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

OUTPUT_DIR = Path(__file__).resolve().parent / "transcripts"


def _fmt_vtt_ts(seconds: int) -> str:
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}.000"


def _fmt_srt_ts(seconds: int) -> str:
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d},000"


def _fmt_txt_ts(seconds: int) -> str:
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def render_vtt(title: str, date_str: str, duration_min: int, turns: List[Tuple[str, str]]) -> str:
    lines = [
        "WEBVTT",
        f"NOTE Reunião: {title} | Data: {date_str} | Duração: {duration_min} min",
        "",
    ]
    t = 5
    for idx, (speaker, text) in enumerate(turns, start=1):
        dur = max(12, min(48, len(text.split()) // 2 + 10))
        lines.append(f"cue-{idx:03d}")
        lines.append(f"{_fmt_vtt_ts(t)} --> {_fmt_vtt_ts(t + dur)}")
        lines.append(f"<v {speaker}>{text}</v>")
        lines.append("")
        t += dur + 3
    return "\n".join(lines).strip() + "\n"


def render_srt(title: str, date_str: str, duration_min: int, turns: List[Tuple[str, str]]) -> str:
    lines = []
    t = 4
    # Primeiro bloco de contexto da gravação (comum em transcrições de abertura)
    intro_speaker, _ = turns[0]
    lines.append("1")
    lines.append(f"{_fmt_srt_ts(0)} --> {_fmt_srt_ts(3)}")
    lines.append(f"{intro_speaker}: Iniciando gravação da reunião {title}, data {date_str}, duração prevista de {duration_min} minutos.")
    lines.append("")
    for idx, (speaker, text) in enumerate(turns, start=2):
        dur = max(12, min(48, len(text.split()) // 2 + 10))
        lines.append(str(idx))
        lines.append(f"{_fmt_srt_ts(t)} --> {_fmt_srt_ts(t + dur)}")
        lines.append(f"{speaker}: {text}")
        lines.append("")
        t += dur + 3
    return "\n".join(lines).strip() + "\n"


def render_txt(title: str, date_str: str, duration_min: int, turns: List[Tuple[str, str]]) -> str:
    participants = sorted({spk for spk, _ in turns})
    lines = [
        f"Reunião: {title}",
        f"Data: {date_str}",
        f"Duração: {duration_min} min",
        f"Participantes: {', '.join(participants)}",
        "---",
        "",
    ]
    t = 10
    for speaker, text in turns:
        dur = max(15, min(50, len(text.split()) // 2 + 12))
        lines.append(f"[{_fmt_txt_ts(t)}] {speaker}: {text}")
        t += dur + 5
    return "\n".join(lines).strip() + "\n"


MEETINGS: List[Dict] = [
    # ------------------------------------------------------------------
    # 1 a 6: TRANSCRIÇÕES COM GABARITO MANUAL (2 .vtt, 2 .srt, 2 .txt)
    # ------------------------------------------------------------------
    {
        "filename": "2026-11-02_reuniao_migracao_lakehouse_medallion.vtt",
        "format": "vtt",
        "title": "Comitê de Arquitetura — Migração para Databricks Lakehouse Medallion",
        "date": "2026-11-02",
        "duration_min": 42,
        "turns": [
            ("Marina Souza", "Bom dia pessoal, hoje vamos fechar o desenho da migração do data warehouse legado para o Databricks Lakehouse em arquitetura Medalhão."),
            ("Rafael Lima", "Fizemos os testes com Lakeflow Spark Declarative Pipelines em modo serverless e o tempo de carga caiu de 3 horas para 22 minutos."),
            ("Marina Souza", "Excelente. Então fica oficialmente aprovado que todas as novas pipelines de vendas e estoque serão implementadas em Lakeflow Serverless usando Liquid Clustering nas tabelas Gold."),
            ("Camila Rocha", "Concordo. Também precisamos definir o padrão de ingestão dos arquivos CSV do ERP. O Auto Loader com read_files resolveu os problemas de schema drift."),
            ("Marina Souza", "Perfeito, segunda decisão registrada: a camada Bronze vai padronizar ingestão incremental via read_files a partir de Volumes do Unity Catalog."),
            ("Diego Martins", "Só um alerta importante: ainda estamos bloqueados aguardando o time de Infraestrutura liberar o Private Link entre a VPC do ERP SAP e o workspace Databricks."),
            ("Camila Rocha", "Outro ponto em aberto é a validação jurídica sobre o período de retenção de 7 anos para dados fiscais no Delta Lake, ainda não recebemos parecer do Jurídico."),
            ("Marina Souza", "Vamos transformar isso em ações claras. Rafael, você fica responsável por criar o template do Databricks Asset Bundle com as camadas Bronze, Silver e Gold até 10/11/2026, prioridade Alta."),
            ("Rafael Lima", "Combinado, entrego o bundle validado até dia 10."),
            ("Marina Souza", "Diego, por favor escale o chamado do Private Link com a equipe de Redes e traga uma previsão de entrega até 06/11/2026, prioridade Alta."),
            ("Diego Martins", "Pode deixar, abro a escalação hoje mesmo."),
            ("Marina Souza", "Camila, documente a estratégia de Liquid Clustering e governança de retenção na wiki de Arquitetura até 14/11/2026, prioridade Média."),
            ("Camila Rocha", "Anotado! Até dia 14 publico a documentação."),
        ],
    },
    {
        "filename": "2026-11-03_reuniao_comite_finops_nuvem_q4.srt",
        "format": "srt",
        "title": "Comitê Mensal FinOps — Otimização de Custos Cloud Q4",
        "date": "2026-11-03",
        "duration_min": 35,
        "turns": [
            ("Lucas Ferreira", "Pessoal, nossa fatura mensal de computação em nuvem subiu 28% em outubro por causa de clusters interativos ociosos e SQL Warehouses grandes ligados de madrugada."),
            ("Beatriz Mendes", "Analisei as system tables de billing do Databricks e 41% do gasto veio de 4 clusters clássicos sem auto-termination configurado."),
            ("Lucas Ferreira", "Então decisão fechada: vamos habilitar auto-termination obrigatório de 15 minutos em todos os clusters interativos e migrar os jobs de ETL noturnos para Serverless Compute."),
            ("Thiago Alves", "Também recomendo definir orçamento mensal com alerta automático quando o consumo atingir 80% da meta do trimestre."),
            ("Lucas Ferreira", "Aprovado! Segunda decisão: implementar alertas de orçamento no Unity Catalog e FinOps dashboard com gatilho em 80% do budget mensal."),
            ("Beatriz Mendes", "Temos uma pendência em aberto: o time de Ciência de Dados ainda não justificou a necessidade de manter duas instâncias GPU ligadas 24x7 em homologação."),
            ("Thiago Alves", "E continua pendente a definição de tags obrigatórias de centro de custo junto à Controladoria para rateio por diretoria."),
            ("Lucas Ferreira", "Vamos às tarefas. Beatriz, aplique a política de cluster com auto-termination de 15 minutos em dev e homologação até 07/11/2026, prioridade Alta."),
            ("Beatriz Mendes", "Feito, aplico até sexta."),
            ("Lucas Ferreira", "Thiago, construa o painel FinOps usando system.billing.usage com alerta em 80% do orçamento até 12/11/2026, prioridade Alta."),
            ("Thiago Alves", "Perfeito, começo amanhã."),
            ("Lucas Ferreira", "Eu mesmo vou cobrar a lista de centros de custo da Controladoria até 09/11/2026, prioridade Média."),
        ],
    },
    {
        "filename": "2026-11-04_reuniao_governanca_unity_catalog_lgpd.txt",
        "format": "txt",
        "title": "Alinhamento Governança de Dados — Unity Catalog e LGPD",
        "date": "2026-11-04",
        "duration_min": 48,
        "turns": [
            ("Fernanda Costa", "O objetivo de hoje é fechar as regras de mascaramento de PII e controle de acesso no Unity Catalog antes da auditoria externa de LGPD."),
            ("Gustavo Pereira", "Mapeamos 14 tabelas com CPF, e-mail e telefone de clientes na camada Silver e Gold."),
            ("Fernanda Costa", "Fica decidido que todas as colunas de PII receberão Column Masks nativas no Unity Catalog vinculadas ao grupo corporativo pii_authorized_analysts."),
            ("Juliana Nunes", "Para os analistas regionais, precisamos também restringir as linhas por filial."),
            ("Fernanda Costa", "Aprovado. Segunda decisão: ativar Row-Level Security por código de filial nas tabelas de clientes e pedidos da camada Gold."),
            ("Gustavo Pereira", "Temos um bloqueio no momento: o provedor de identidade Entra ID ainda não sincronizou via SCIM os grupos regionais de vendas com a conta Databricks."),
            ("Juliana Nunes", "Também ficou pendente a aprovação do DPO sobre o texto do termo de responsabilidade para exportação de dados em CSV."),
            ("Fernanda Costa", "Ações definidas: Gustavo, implemente as funções SQL de Column Mask para CPF, e-mail e telefone nas 14 tabelas até 13/11/2026, prioridade Alta."),
            ("Gustavo Pereira", "Combinado, crio as funções e aplico nas tabelas até dia 13."),
            ("Fernanda Costa", "Juliana, configure o filtro de Row-Level Security nas tabelas Gold de clientes e pedidos até 16/11/2026, prioridade Alta."),
            ("Juliana Nunes", "Anotado, deixo pronto com testes de permissão."),
            ("Fernanda Costa", "Vou agendar revisão com o DPO e cobrar o time de IAM sobre o SCIM do Entra ID até 08/11/2026, prioridade Alta."),
        ],
    },
    {
        "filename": "2026-11-05_discovery_cliente_portal_selfservice_bi.vtt",
        "format": "vtt",
        "title": "Discovery com Diretoria Comercial — Portal Self-Service BI e Genie",
        "date": "2026-11-05",
        "duration_min": 40,
        "turns": [
            ("Carla Oliveira", "Obrigado por participar, pessoal. Queremos entender como os gerentes regionais consomem os números de vendas hoje."),
            ("Eduardo Santos", "Hoje levamos dois dias pedindo relatório ad-hoc para o time de BI só para saber quais produtos caíram de margem na semana."),
            ("Carla Oliveira", "Se entregarmos um Genie Space conectado às tabelas Gold de vendas e margem, vocês conseguiriam fazer essas perguntas em linguagem natural."),
            ("Eduardo Santos", "Isso resolveria 80% das nossas reuniões de segunda-feira! Mas precisamos que o conceito de receita líquida seja único para todas as diretorias."),
            ("Patrícia Gomes", "Perfeito. Então fechamos duas decisões de produto: primeiro, criar um piloto de Genie Space focado nos 12 gerentes comerciais regionais; segundo, publicar uma Metric View oficial para receita líquida e margem bruta."),
            ("Eduardo Santos", "Uma pendência do nosso lado: ainda não consolidamos a nova tabela de metas por região de 2027, que depende da aprovação da Vice-Presidência."),
            ("Patrícia Gomes", "E do lado técnico está pendente validar se os gerentes comerciais já possuem licença de acesso ao Databricks SQL para usar o Genie."),
            ("Carla Oliveira", "Vamos fechar os próximos passos. Patrícia, publique a Metric View de receita líquida e margem bruta e configure o Genie Space piloto até 18/11/2026, prioridade Alta."),
            ("Patrícia Gomes", "Beleza, entrego com perguntas de exemplo validadas."),
            ("Carla Oliveira", "Eduardo, compartilhe o dicionário de KPIs comerciais e a lista dos 12 gerentes participantes do piloto até 10/11/2026, prioridade Alta."),
            ("Eduardo Santos", "Envio ainda nesta semana, até dia 10."),
            ("Carla Oliveira", "Eu vou confirmar os acessos Databricks SQL dos 12 gerentes com o time de TI até 12/11/2026, prioridade Média."),
        ],
    },
    {
        "filename": "2026-11-06_postmortem_incidente_pipeline_streaming.srt",
        "format": "srt",
        "title": "Post-Mortem Incidente SEV-2 — Atraso na Pipeline de Streaming de Pedidos",
        "date": "2026-11-06",
        "duration_min": 38,
        "turns": [
            ("André Carvalho", "Vamos revisar o incidente de ontem às 09h15 quando a pipeline de pedidos acumulou 47 minutos de lag."),
            ("Renata Barros", "A causa raiz foi uma mudança não anunciada no payload JSON do microserviço de checkout que adicionou um campo aninhado incompatível, derrubando a tarefa sem schema evolution."),
            ("André Carvalho", "Como não tínhamos tabela de quarentena para _rescued_data, a pipeline inteira travou até fazermos hotfix manual."),
            ("Bruno Teixeira", "Precisamos blindar isso. Proponho adotar schemaEvolutionMode rescue na Bronze e criar uma tabela de quarentena monitorada com alerta no Slack."),
            ("André Carvalho", "Decisão aprovada: todas as tabelas Bronze de eventos passarão a usar schemaEvolutionMode rescue com envio de registros corrompidos para quarentena."),
            ("Renata Barros", "Segunda decisão: adicionar contrato de dados automatizado no CI do microserviço de checkout para bloquear mudanças quebradoras antes de produção."),
            ("Bruno Teixeira", "Fica uma pendência: ainda não temos definição de SLA oficial de atraso máximo com o time de Logística para calibrar o alerta de lag."),
            ("Renata Barros", "Outra pendência é que o time de Checkout ainda não informou a data para remover o campo legado que causou conflito de tipagem."),
            ("André Carvalho", "Action items: Bruno, habilite schemaEvolutionMode rescue e a tabela de quarentena com alerta de lag no Slack até 11/11/2026, prioridade Alta."),
            ("Bruno Teixeira", "Combinado, subo em produção após validar em staging."),
            ("André Carvalho", "Renata, implemente a validação de JSON Schema no pipeline CI do checkout junto ao time de pagamentos até 19/11/2026, prioridade Alta."),
            ("Renata Barros", "Perfeito, abro o PR com o time de checkout."),
            ("André Carvalho", "Vou alinhar o SLA máximo de latência com a gerência de Logística até 13/11/2026, prioridade Média."),
        ],
    },
    {
        "filename": "2026-11-09_planejamento_sprint_genie_ai_assistants.txt",
        "format": "txt",
        "title": "Planejamento Sprint 24 — POC de Sumarização de Reuniões com AI Functions",
        "date": "2026-11-09",
        "duration_min": 45,
        "turns": [
            ("Vitor Almeida", "Pessoal, nesta Sprint 24 vamos fechar a POC de sumarização de reuniões no Databricks para demonstrar à diretoria de Engenharia."),
            ("Larissa Monteiro", "Precisamos garantir que o pipeline use read_files na Bronze, faça limpeza e parsing de falantes na Silver e use ai_query com responseFormat na Gold."),
            ("Vitor Almeida", "Exato. Fica decidido que a extração estruturada na Gold usará ai_query com responseFormat JSON Schema estrito no endpoint databricks-meta-llama-3-3-70b-instruct."),
            ("Henrique Duarte", "E para provar qualidade com dados, precisamos de um gabarito manual com 6 transcrições e medir precisão, recall, taxa de JSON válido, latência e custo."),
            ("Vitor Almeida", "Segunda decisão confirmada: toda demonstração de LLM em produção passará por avaliação quantitativa com gabarito antes de ir para usuários finais."),
            ("Larissa Monteiro", "Temos uma pendência importante: ainda falta a equipe de Compliance validar se gravações de reuniões com clientes externos podem ser processadas em endpoints pay-per-token."),
            ("Henrique Duarte", "Também está pendente a liberação do grupo de usuários piloto no Unity Catalog para testar o Genie Space da POC."),
            ("Vitor Almeida", "Então vamos distribuir as tarefas. Larissa, implemente as camadas Bronze com read_files, Silver com parsing de falantes e Gold com ai_query e responseFormat até 15/11/2026, prioridade Alta."),
            ("Larissa Monteiro", "Perfeito, já subo tudo via Databricks Asset Bundle."),
            ("Vitor Almeida", "Henrique, monte o gabarito manual de 6 transcrições e rode o script de métricas de precisão, recall, latência e custo até 17/11/2026, prioridade Alta."),
            ("Henrique Duarte", "Pode deixar, gero o relatório completo e salvo em tabela Gold."),
            ("Vitor Almeida", "Eu vou configurar o Genie Space conectado às tabelas Gold e solicitar o parecer de Compliance até 18/11/2026, prioridade Média."),
        ],
    },
    # ------------------------------------------------------------------
    # 7 a 18: TRANSCRIÇÕES ADICIONAIS PARA TOTALIZAR 18 ARQUIVOS NO VOLUME
    # ------------------------------------------------------------------
    {
        "filename": "2026-11-10_alinhamento_arquitetura_api_pagamentos.vtt",
        "format": "vtt",
        "title": "Alinhamento Técnico — Refatoração da API de Pagamentos Pix",
        "date": "2026-11-10",
        "duration_min": 36,
        "turns": [
            ("Marcelo Ribeiro", "Nosso pico da Black Friday deve triplicar as transações Pix e o gateway atual atingiu 82% de CPU no teste de carga."),
            ("Sofia Andrade", "Testamos filas assíncronas com idempotência por chave transacional e a latência p99 caiu para 180ms."),
            ("Marcelo Ribeiro", "Decisão tomada: vamos adotar processamento assíncrono com chave de idempotência obrigatória para todos os webhooks Pix."),
            ("Pedro Henrique", "Fica pendente receber do banco parceiro o certificado mTLS definitivo do ambiente de produção."),
            ("Marcelo Ribeiro", "Sofia, finalize os testes de carga para 3.000 TPS até 17/11/2026, prioridade Alta."),
            ("Marcelo Ribeiro", "Pedro, valide o fallback de retry exponencial e cobre o certificado mTLS do banco até 14/11/2026, prioridade Alta."),
        ],
    },
    {
        "filename": "2026-11-11_comite_seguranca_iam_zero_trust.srt",
        "format": "srt",
        "title": "Comitê de Segurança — Adoção de Zero Trust e Rotação de Segredos",
        "date": "2026-11-11",
        "duration_min": 44,
        "turns": [
            ("Daniela Pires", "Na auditoria interna encontramos 9 Personal Access Tokens sem data de expiração em pipelines legadas."),
            ("Rodrigo Nogueira", "Podemos migrar todas as integrações automatizadas para Service Principals com OAuth M2M."),
            ("Daniela Pires", "Aprovado! Decisão do comitê: desativar PATs sem expiração e exigir OAuth M2M via Service Principal em todos os jobs de produção."),
            ("Rodrigo Nogueira", "Ainda está pendente mapear quais scripts locais da equipe de Finanças usam tokens estáticos."),
            ("Daniela Pires", "Rodrigo, faça o inventário de tokens ativos e migre os jobs críticos para Service Principal até 20/11/2026, prioridade Alta."),
            ("Daniela Pires", "Vou publicar a política atualizada de rotação de credenciais no portal interno até 18/11/2026, prioridade Média."),
        ],
    },
    {
        "filename": "2026-11-12_reuniao_produto_roadmap_mobile_2027.txt",
        "format": "txt",
        "title": "Revisão de Roadmap Produto Mobile — Q1 2027",
        "date": "2026-11-12",
        "duration_min": 50,
        "turns": [
            ("Aline Vasconcelos", "Trouxemos os resultados da pesquisa com 1.200 clientes: 64% pedem modo offline no app de campo."),
            ("Gabriel Moura", "Se priorizarmos o modo offline no Q1, precisaremos adiar o redesenho da tela de perfil para o Q2."),
            ("Aline Vasconcelos", "Fica decidido: modo offline com sincronização incremental será o épico número 1 do Q1 2027 e o redesenho de perfil vai para o Q2."),
            ("Gabriel Moura", "Temos uma pendência de arquitetura sobre resolução de conflitos quando dois técnicos editam a mesma ordem de serviço offline."),
            ("Aline Vasconcelos", "Gabriel, escreva a RFC de sincronização offline e resolução de conflitos até 21/11/2026, prioridade Alta."),
            ("Aline Vasconcelos", "Vou atualizar o roadmap executivo e comunicar os stakeholders comerciais até 19/11/2026, prioridade Média."),
        ],
    },
    {
        "filename": "2026-11-13_daily_engenharia_dados_erp_sap.vtt",
        "format": "vtt",
        "title": "Sync Engenharia de Dados — Ingestão CDC do ERP SAP",
        "date": "2026-11-13",
        "duration_min": 25,
        "turns": [
            ("Fábio Cunha", "A extração incremental das tabelas VBAK e VBAP rodou sem falhas nas últimas 72 horas."),
            ("Natália Borges", "Porém a tabela de centro de custos ainda vem em snapshot completo de 18 milhões de linhas toda noite."),
            ("Fábio Cunha", "Vamos decidir: manter snapshot diário com Auto CDC FROM SNAPSHOT apenas para tabelas mestras pequenas e habilitar CDC real na tabela de centro de custos."),
            ("Natália Borges", "Fica pendente a equipe Basis do SAP liberar permissão de leitura no log de mudanças para o usuário técnico."),
            ("Fábio Cunha", "Natália, abra o ticket de permissão no SAP Basis e documente a volumetria até 16/11/2026, prioridade Alta."),
            ("Fábio Cunha", "Eu vou configurar os testes de reconciliação de contagem entre SAP e Silver até 19/11/2026, prioridade Média."),
        ],
    },
    {
        "filename": "2026-11-14_review_sla_suporte_nivel2_clientes.srt",
        "format": "srt",
        "title": "Revisão Operacional — SLA do Suporte Nível 2",
        "date": "2026-11-14",
        "duration_min": 32,
        "turns": [
            ("Tatiana Melo", "Nosso tempo médio de primeira resposta no N2 subiu de 1h20 para 2h45 depois da entrada de três clientes enterprise."),
            ("Igor Santana", "Mais de 35% dos chamados chegam sem logs anexados, o que gera duas idas e vindas com o cliente."),
            ("Tatiana Melo", "Decisão operacional: tornar obrigatório o anexo de correlation ID e logs no formulário de abertura de incidentes N2."),
            ("Igor Santana", "Ainda falta o time de Produto liberar o botão de diagnóstico automático no painel do cliente."),
            ("Tatiana Melo", "Igor, atualize o formulário no Zendesk e o playbook de triagem até 19/11/2026, prioridade Alta."),
            ("Tatiana Melo", "Vou negociar com Produto a entrada do botão de diagnóstico na próxima sprint até 22/11/2026, prioridade Média."),
        ],
    },
    {
        "filename": "2026-11-16_workshop_observabilidade_mlflow_tracing.txt",
        "format": "txt",
        "title": "Workshop Técnico — Observabilidade de Agentes IA com MLflow Tracing",
        "date": "2026-11-16",
        "duration_min": 55,
        "turns": [
            ("Helena Prado", "Hoje vamos padronizar como rastreamos latência, chamadas de ferramentas e qualidade dos agentes GenAI com MLflow Tracing."),
            ("Mateus Vieira", "Com o autolog do MLflow conseguimos inspecionar cada span de retrieval e geração e avaliar alucinações automaticamente."),
            ("Helena Prado", "Decisão de engenharia: todos os agentes em produção devem enviar traces para o experimento central no Databricks MLflow e rodar scorers de qualidade semanalmente."),
            ("Mateus Vieira", "Pendência: precisamos definir o limite de retenção de prompts com dados sensíveis nos traces junto à Segurança da Informação."),
            ("Helena Prado", "Mateus, publique o pacote interno de instrumentação MLflow Tracing com mascaramento de PII até 25/11/2026, prioridade Alta."),
            ("Helena Prado", "Vou validar a política de retenção de traces com Segurança até 23/11/2026, prioridade Média."),
        ],
    },
    {
        "filename": "2026-11-17_comite_executivo_orcamento_ti_2027.vtt",
        "format": "vtt",
        "title": "Comitê Executivo — Orçamento de Dados e IA para 2027",
        "date": "2026-11-17",
        "duration_min": 60,
        "turns": [
            ("Ricardo Tavares", "Apresentamos a proposta de orçamento de Dados e IA de 2027 com foco em consolidação de plataformas e automação com IA."),
            ("Cláudia Rezende", "Desligando os dois servidores legados de BI, economizamos 420 mil reais por ano, o que financia integralmente o consumo de AI Functions e Genie."),
            ("Ricardo Tavares", "Aprovado pelo comitê: o orçamento de 2027 contempla a desativação do BI legado até junho e reserva de 15% da verba para iniciativas de GenAI com ROI comprovado."),
            ("Cláudia Rezende", "Fica pendente a assinatura do aditivo contratual com o fornecedor de BI legado para encerrar licenças sem multa."),
            ("Ricardo Tavares", "Cláudia, envie o cronograma de desligamento do BI legado para Compras e Jurídico até 24/11/2026, prioridade Alta."),
            ("Ricardo Tavares", "Vou consolidar os KPIs de ROI das POCs de IA para a apresentação ao Conselho até 27/11/2026, prioridade Alta."),
        ],
    },
    {
        "filename": "2026-11-18_alinhamento_rh_onboarding_engenharia.srt",
        "format": "srt",
        "title": "Alinhamento RH e Engenharia — Trilha de Onboarding Técnico",
        "date": "2026-11-18",
        "duration_min": 30,
        "turns": [
            ("Priscila Duarte", "Nos últimos três meses, novos engenheiros levaram em média 11 dias úteis para receber todos os acessos de Git, nuvem e Databricks."),
            ("Eduardo Neri", "Criamos um checklist automatizado por perfil de cargo que reduz esse tempo para 2 dias."),
            ("Priscila Duarte", "Decisão fechada: adotar o provisionamento por papel (RBAC) no primeiro dia e gravar tutoriais curtos de onboarding técnico no portal interno."),
            ("Eduardo Neri", "Pendência: o time de TI Corporativa ainda não integrou o formulário de admissão com a fila automática do ServiceNow."),
            ("Priscila Duarte", "Eduardo, publique o guia passo a passo de ambiente local e Databricks no portal até 26/11/2026, prioridade Média."),
            ("Priscila Duarte", "Vou alinhar a integração do formulário de admissão com TI Corporativa até 25/11/2026, prioridade Alta."),
        ],
    },
    {
        "filename": "2026-11-19_reuniao_migracao_postgres_lakebase.txt",
        "format": "txt",
        "title": "Arquitetura de Aplicações — Migração de Estado Operacional para Lakebase",
        "date": "2026-11-19",
        "duration_min": 40,
        "turns": [
            ("Vinícius Castro", "Nosso app de aprovação de descontos precisa de leitura transacional abaixo de 20ms combinada com dados analíticos do Unity Catalog."),
            ("Bianca Cardoso", "Nos testes com Databricks Lakebase Postgres e Synced Tables conseguimos p95 de 11ms sem manter ETL manual."),
            ("Vinícius Castro", "Decisão técnica: adotar Lakebase Postgres com Synced Tables como banco operacional do portal de aprovações."),
            ("Bianca Cardoso", "Pendência aberta: confirmar com FinOps o teto de autoscaling em CU para o ambiente de produção."),
            ("Vinícius Castro", "Bianca, provisione o projeto Lakebase em staging e configure a tabela sincronizada de clientes até 27/11/2026, prioridade Alta."),
            ("Vinícius Castro", "Vou revisar a estimativa de custo de Lakebase com FinOps até 25/11/2026, prioridade Média."),
        ],
    },
    {
        "filename": "2026-11-20_revisao_contrato_fornecedor_cloud.vtt",
        "format": "vtt",
        "title": "Negociação Comercial — Renovação de Commit Cloud 2027",
        "date": "2026-11-20",
        "duration_min": 35,
        "turns": [
            ("Sérgio Matos", "Com o crescimento previsto das workloads de IA, conseguimos negociar 18% de desconto no commit anual de 2027."),
            ("Renata Campos", "Precisamos garantir cláusula de flexibilidade para realocar saldo entre compute clássico, serverless e AI Functions."),
            ("Sérgio Matos", "Fica aprovado fechar o commit anual com 18% de desconto desde que a cláusula de fungibilidade entre workloads esteja incluída."),
            ("Renata Campos", "Pendência: aguardando minuta revisada do fornecedor com a cláusula de fungibilidade."),
            ("Sérgio Matos", "Renata, revise a minuta final junto ao Jurídico até 28/11/2026, prioridade Alta."),
            ("Sérgio Matos", "Vou apresentar o comparativo de economia ao CFO até 30/11/2026, prioridade Média."),
        ],
    },
    {
        "filename": "2026-11-21_sync_qualidade_dados_dqx_alertas.srt",
        "format": "srt",
        "title": "Sync Qualidade de Dados — Regras de Expectations na Camada Silver",
        "date": "2026-11-21",
        "duration_min": 28,
        "turns": [
            ("Paula Teixeira", "Identificamos 0,8% de registros de notas fiscais chegando sem código de município válido na Silver."),
            ("Caio Batista", "Podemos adicionar expectations de qualidade na pipeline Lakeflow separando registros inválidos em uma tabela de auditoria sem travar o fluxo principal."),
            ("Paula Teixeira", "Decisão: implementar expectations ON VIOLATION DROP ROW para chaves nulas e tabela de auditoria para erros de domínio fiscal."),
            ("Caio Batista", "Pendência: aguardando tabela oficial de códigos IBGE atualizada do time Fiscal."),
            ("Paula Teixeira", "Caio, adicione as expectations de qualidade na pipeline fiscal e o painel de taxa de rejeição até 29/11/2026, prioridade Alta."),
            ("Paula Teixeira", "Vou solicitar a tabela IBGE atualizada para a equipe Fiscal até 25/11/2026, prioridade Baixa."),
        ],
    },
    {
        "filename": "2026-11-22_reuniao_lancamento_app_corporativo_ia.txt",
        "format": "txt",
        "title": "Go/No-Go — Lançamento Interno do Portal Meeting & Video Intelligence",
        "date": "2026-11-22",
        "duration_min": 34,
        "turns": [
            ("Vitor Almeida", "Pessoal, estamos prontos para o lançamento interno do portal Meeting & Video Intelligence para os times de Engenharia e Produto."),
            ("Marina Souza", "Um ponto essencial pedido pelos gestores é ter uma tela inicial clara de tutorial no portal explicando como usar no dia a dia e como usar em ambiente empresarial com segurança."),
            ("Vitor Almeida", "Totalmente de acordo! Decisão de lançamento: incluir a tela inicial de Tutorial & Guia Empresarial como página padrão do portal, detalhando modo offline para reuniões sigilosas e sincronização com Databricks."),
            ("Lucas Ferreira", "Fica pendente apenas definir a agenda da sessão de treinamento ao vivo de 30 minutos com os tech leads."),
            ("Vitor Almeida", "Vou publicar a tela inicial de tutorial no portal e validar o build de produção até 24/11/2026, prioridade Alta."),
            ("Vitor Almeida", "Marina, agende o treinamento ao vivo com os tech leads e compartilhe o link do Genie Space até 26/11/2026, prioridade Média."),
        ],
    },
]


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for old in OUTPUT_DIR.glob("*"):
        if old.is_file():
            old.unlink()

    for m in MEETINGS:
        fmt = m["format"]
        if fmt == "vtt":
            content = render_vtt(m["title"], m["date"], m["duration_min"], m["turns"])
        elif fmt == "srt":
            content = render_srt(m["title"], m["date"], m["duration_min"], m["turns"])
        else:
            content = render_txt(m["title"], m["date"], m["duration_min"], m["turns"])

        out_path = OUTPUT_DIR / m["filename"]
        out_path.write_text(content, encoding="utf-8")

    print(f"Geradas {len(MEETINGS)} transcrições fictícias em: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
