import React, { useState } from "react";
import {
  ArrowRight,
  BookOpen,
  Building2,
  CheckCircle2,
  CloudUpload,
  Database,
  FileAudio,
  FileText,
  GraduationCap,
  Layers,
  Link2,
  Lock,
  MessageSquareText,
  PlayCircle,
  Settings,
  ShieldCheck,
  Sparkles,
  Users,
  Workflow,
} from "lucide-react";

interface HomeGuideViewProps {
  onNavigate: (view: "ingest" | "library" | "settings") => void;
}

export const HomeGuideView: React.FC<HomeGuideViewProps> = ({ onNavigate }) => {
  const [activeTab, setActiveTab] = useState<"quickstart" | "enterprise" | "lakehouse">(
    "quickstart"
  );

  return (
    <div className="space-y-8 pb-8">
      {/* Hero Banner */}
      <section className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900 text-white p-6 sm:p-10 shadow-xl border border-slate-800">
        <div className="relative z-10 max-w-4xl space-y-5">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/20 border border-indigo-400/30 text-indigo-200 text-xs font-medium">
            <Sparkles className="w-3.5 h-3.5" />
            Portal Meeting &amp; Video Intelligence • Guia de Uso &amp; Operação Empresarial
          </div>

          <h2 className="text-2xl sm:text-4xl font-bold tracking-tight leading-tight">
            Transforme gravações e transcrições em{" "}
            <span className="text-indigo-300">
              decisões, pendências e planos de ação governados
            </span>
          </h2>

          <p className="text-sm sm:text-base text-slate-300 leading-relaxed max-w-3xl">
            Este portal reúne ingestão unificada (Teams, Zoom, Google Meet, YouTube ou gravações
            locais &gt;1h sem legenda), extração estruturada validada por LLM, chat com citações
            clicáveis por timestamp e sincronização direta com o{" "}
            <strong className="text-white">Databricks Lakehouse + Genie Space</strong> — com opção
            de operação <strong className="text-emerald-300">100% offline</strong> para reuniões
            corporativas sigilosas.
          </p>

          <div className="flex flex-wrap gap-3 pt-2">
            <button
              type="button"
              onClick={() => onNavigate("ingest")}
              className="px-5 py-2.5 rounded-xl bg-indigo-500 hover:bg-indigo-400 text-white text-sm font-semibold inline-flex items-center gap-2 shadow-sm transition cursor-pointer"
            >
              <PlayCircle className="w-4 h-4" />
              Começar Nova Ingestão
              <ArrowRight className="w-4 h-4" />
            </button>
            <button
              type="button"
              onClick={() => onNavigate("library")}
              className="px-5 py-2.5 rounded-xl bg-white/10 hover:bg-white/15 text-white text-sm font-medium inline-flex items-center gap-2 border border-white/15 transition cursor-pointer"
            >
              <BookOpen className="w-4 h-4" />
              Abrir Biblioteca de Atas
            </button>
            <button
              type="button"
              onClick={() => onNavigate("settings")}
              className="px-5 py-2.5 rounded-xl bg-white/5 hover:bg-white/10 text-slate-200 text-sm font-medium inline-flex items-center gap-2 border border-white/10 transition cursor-pointer"
            >
              <Settings className="w-4 h-4" />
              Configurar Provedores &amp; Databricks
            </button>
          </div>
        </div>
      </section>

      {/* 3 Pillars Overview */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs space-y-2.5">
          <div className="w-10 h-10 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center">
            <FileAudio className="w-5 h-5" />
          </div>
          <h3 className="font-semibold text-slate-900">1. Ingestão Multimodal</h3>
          <p className="text-sm text-slate-600 leading-relaxed">
            Aceita transcrições prontas (<code className="text-xs bg-slate-100 px-1 py-0.5 rounded">.vtt</code>,{" "}
            <code className="text-xs bg-slate-100 px-1 py-0.5 rounded">.srt</code>,{" "}
            <code className="text-xs bg-slate-100 px-1 py-0.5 rounded">.txt</code>,{" "}
            <code className="text-xs bg-slate-100 px-1 py-0.5 rounded">.json</code>), links de vídeo
            (YouTube / yt-dlp) e gravações locais (<code className="text-xs bg-slate-100 px-1 py-0.5 rounded">.mp4</code>,{" "}
            <code className="text-xs bg-slate-100 px-1 py-0.5 rounded">.m4a</code>) com compressão
            e chunking automático para reuniões longas.
          </p>
        </div>

        <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs space-y-2.5">
          <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <h3 className="font-semibold text-slate-900">2. Sigilo &amp; Governança Corporativa</h3>
          <p className="text-sm text-slate-600 leading-relaxed">
            Alterne entre nuvem governada (<strong>Databricks Unity Gateway / Azure OpenAI</strong>)
            ou modo <strong>100% local offline</strong> (<code>faster-whisper</code> +{" "}
            <code>Ollama</code>) para dados confidenciais, LGPD e reuniões de diretoria. Zero
            segredos hardcoded.
          </p>
        </div>

        <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs space-y-2.5">
          <div className="w-10 h-10 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center">
            <Database className="w-5 h-5" />
          </div>
          <h3 className="font-semibold text-slate-900">3. Escala no Databricks Lakehouse</h3>
          <p className="text-sm text-slate-600 leading-relaxed">
            Envie transcrições para um <strong>Unity Catalog Volume</strong> com um clique e
            alimente automaticamente a pipeline Medalhão (<code>read_files</code> → Parsing Silver →{" "}
            <code>ai_query</code> + <code>responseFormat</code> Gold) conectada ao{" "}
            <strong>Genie Space</strong>.
          </p>
        </div>
      </section>

      {/* Interactive Guide Tabs */}
      <section className="bg-white rounded-3xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="border-b border-slate-200 px-5 pt-5 flex flex-wrap gap-2 bg-slate-50/70">
          <button
            type="button"
            onClick={() => setActiveTab("quickstart")}
            className={`px-4 py-2.5 rounded-t-xl text-sm font-semibold inline-flex items-center gap-2 border-b-2 transition cursor-pointer ${
              activeTab === "quickstart"
                ? "border-indigo-600 text-indigo-700 bg-white"
                : "border-transparent text-slate-600 hover:text-slate-900"
            }`}
          >
            <GraduationCap className="w-4 h-4" />
            Tutorial Passo a Passo (Como Usar)
          </button>

          <button
            type="button"
            onClick={() => setActiveTab("enterprise")}
            className={`px-4 py-2.5 rounded-t-xl text-sm font-semibold inline-flex items-center gap-2 border-b-2 transition cursor-pointer ${
              activeTab === "enterprise"
                ? "border-indigo-600 text-indigo-700 bg-white"
                : "border-transparent text-slate-600 hover:text-slate-900"
            }`}
          >
            <Building2 className="w-4 h-4" />
            Como Usar em Ambiente Empresarial
          </button>

          <button
            type="button"
            onClick={() => setActiveTab("lakehouse")}
            className={`px-4 py-2.5 rounded-t-xl text-sm font-semibold inline-flex items-center gap-2 border-b-2 transition cursor-pointer ${
              activeTab === "lakehouse"
                ? "border-indigo-600 text-indigo-700 bg-white"
                : "border-transparent text-slate-600 hover:text-slate-900"
            }`}
          >
            <Workflow className="w-4 h-4" />
            Integração Databricks &amp; Genie Space
          </button>
        </div>

        <div className="p-6 sm:p-8">
          {/* TAB 1: QUICKSTART */}
          {activeTab === "quickstart" && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-bold text-slate-900">
                  Fluxo de uso no dia a dia (4 passos)
                </h3>
                <p className="text-sm text-slate-600 mt-1">
                  Siga esta sequência para processar sua primeira reunião ou aula técnica em menos de
                  2 minutos.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="rounded-2xl border border-slate-200 p-5 space-y-2">
                  <div className="flex items-center gap-2.5">
                    <span className="w-7 h-7 rounded-full bg-indigo-600 text-white text-xs font-bold flex items-center justify-center">
                      1
                    </span>
                    <h4 className="font-semibold text-slate-900">Configure o motor (opcional)</h4>
                  </div>
                  <p className="text-sm text-slate-600 leading-relaxed">
                    Em <strong>Configurações</strong>, escolha seu provedor de LLM (
                    <code>Gemini</code>, <code>OpenAI</code>, <code>Azure OpenAI</code>,{" "}
                    <code>Databricks</code>, <code>Ollama</code> local ou <code>Heuristic</code>{" "}
                    offline para testes sem chave). Adicione também termos do seu{" "}
                    <strong>Glossário Técnico</strong> (siglas, sistemas, projetos) para melhorar a
                    acurácia da transcrição e extração.
                  </p>
                </div>

                <div className="rounded-2xl border border-slate-200 p-5 space-y-2">
                  <div className="flex items-center gap-2.5">
                    <span className="w-7 h-7 rounded-full bg-indigo-600 text-white text-xs font-bold flex items-center justify-center">
                      2
                    </span>
                    <h4 className="font-semibold text-slate-900">Escolha o modo em Nova Ingestão</h4>
                  </div>
                  <ul className="text-sm text-slate-600 space-y-1.5 list-disc pl-5">
                    <li>
                      <strong className="text-slate-800">Upload de Arquivo:</strong> arraste{" "}
                      <code>.vtt</code> (Teams), <code>.srt</code> (Zoom), <code>.txt</code> ou
                      gravação <code>.mp4/.m4a/.mp3</code>.
                    </li>
                    <li>
                      <strong className="text-slate-800">URL de Vídeo:</strong> cole um link do
                      YouTube; o sistema tenta legendas grátis primeiro e faz fallback por IA se não
                      houver legenda.
                    </li>
                    <li>
                      <strong className="text-slate-800">Colar Transcrição:</strong> cole diretamente
                      o texto ou ata do Google Meet / Teams.
                    </li>
                  </ul>
                </div>

                <div className="rounded-2xl border border-slate-200 p-5 space-y-2">
                  <div className="flex items-center gap-2.5">
                    <span className="w-7 h-7 rounded-full bg-indigo-600 text-white text-xs font-bold flex items-center justify-center">
                      3
                    </span>
                    <h4 className="font-semibold text-slate-900">
                      Revise Decisões, Pendências e Action Items
                    </h4>
                  </div>
                  <p className="text-sm text-slate-600 leading-relaxed">
                    Ao concluir, a tela de detalhe exibe Resumo Executivo, Decisões Aprovadas,
                    Pendências/Bloqueios e um <strong>Checklist interativo de Action Items</strong>{" "}
                    com responsável, prazo e prioridade. Copie a <strong>Ata Markdown</strong>{" "}
                    pronta para colar no Teams, Slack, Confluence ou e-mail.
                  </p>
                </div>

                <div className="rounded-2xl border border-slate-200 p-5 space-y-2">
                  <div className="flex items-center gap-2.5">
                    <span className="w-7 h-7 rounded-full bg-indigo-600 text-white text-xs font-bold flex items-center justify-center">
                      4
                    </span>
                    <h4 className="font-semibold text-slate-900">
                      Pergunte no Chat &amp; Exporte ou Sincronize
                    </h4>
                  </div>
                  <p className="text-sm text-slate-600 leading-relaxed">
                    Use a aba <strong>Chat Q&amp;A</strong> para tirar dúvidas específicas com
                    citações clicáveis <code>[HH:MM:SS]</code> que destacam o trecho exato da fala.
                    Exporte em <code>.md</code>, <code>.srt</code>, <code>.txt</code> ou{" "}
                    <code>.json</code> — ou clique em <strong>Enviar para Databricks</strong> para
                    consolidar no Lakehouse.
                  </p>
                </div>
              </div>

              <div className="rounded-2xl bg-indigo-50/70 border border-indigo-100 p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div className="flex items-start gap-3">
                  <MessageSquareText className="w-5 h-5 text-indigo-600 mt-0.5 shrink-0" />
                  <div className="text-sm text-indigo-950">
                    <strong>Dica de Template:</strong> selecione <em>Reunião Corporativa</em> para
                    comitês/dailies, <em>Discovery/Cliente</em> para levantamento de requisitos ou{" "}
                    <em>Aula/Vídeo Técnico</em> para extrair aprendizados, ferramentas e métricas.
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => onNavigate("ingest")}
                  className="shrink-0 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold transition cursor-pointer"
                >
                  Ir para Nova Ingestão
                </button>
              </div>
            </div>
          )}

          {/* TAB 2: ENTERPRISE USAGE */}
          {activeTab === "enterprise" && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-bold text-slate-900">
                  Guia Prático: Como Usar em Ambiente Empresarial com Segurança
                </h3>
                <p className="text-sm text-slate-600 mt-1">
                  Boas práticas para equipes de engenharia, produto, PMO e diretoria operarem o
                  portal respeitando políticas de LGPD, sigilo corporativo e governança de dados.
                </p>
              </div>

              {/* Confidentiality Matrix */}
              <div className="overflow-x-auto rounded-2xl border border-slate-200">
                <table className="w-full text-left text-sm">
                  <thead className="bg-slate-50 border-b border-slate-200 text-slate-700">
                    <tr>
                      <th className="px-4 py-3 font-semibold">Classificação da Reunião</th>
                      <th className="px-4 py-3 font-semibold">Configuração Recomendada</th>
                      <th className="px-4 py-3 font-semibold">Onde os dados trafegam</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200 text-slate-600">
                    <tr>
                      <td className="px-4 py-3 font-medium text-slate-900">
                        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-rose-50 text-rose-700 text-xs font-semibold">
                          <Lock className="w-3 h-3" /> Altamente Confidencial / M&amp;A / RH / LGPD
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <code>TRANSCRIBER_PROVIDER=local_whisper</code> +{" "}
                        <code>LLM_PROVIDER=ollama</code> (ou <code>heuristic</code>)
                      </td>
                      <td className="px-4 py-3">
                        <strong>100% na máquina/rede local</strong>. Zero envio para APIs externas;
                        áudio temporário é apagado ao fim do job.
                      </td>
                    </tr>
                    <tr>
                      <td className="px-4 py-3 font-medium text-slate-900">
                        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-amber-50 text-amber-800 text-xs font-semibold">
                          <ShieldCheck className="w-3 h-3" /> Interno Corporativo (Governado)
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <code>LLM_PROVIDER=databricks</code> (Unity Gateway / Model Serving) ou{" "}
                        <code>azure_openai</code> na assinatura da empresa
                      </td>
                      <td className="px-4 py-3">
                        Dentro do tenant corporativo com auditoria, controle de acesso Unity Catalog
                        (RBAC) e contrato de não-treinamento (zero data retention).
                      </td>
                    </tr>
                    <tr>
                      <td className="px-4 py-3 font-medium text-slate-900">
                        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 text-xs font-semibold">
                          <Link2 className="w-3 h-3" /> Público / Treinamentos / YouTube
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <code>TRANSCRIBER_PROVIDER=gemini</code> +{" "}
                        <code>LLM_PROVIDER=gemini</code> ou <code>openai</code>
                      </td>
                      <td className="px-4 py-3">
                        Nuvem pública com alta velocidade e custo reduzido para vídeos técnicos,
                        webinars e conferências públicas.
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>

              {/* Enterprise Operational Scenarios */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="rounded-2xl border border-slate-200 p-5 space-y-2.5">
                  <div className="flex items-center gap-2 text-slate-900 font-semibold">
                    <Users className="w-4 h-4 text-indigo-600" />
                    Microsoft Teams, SharePoint, Zoom e Google Meet
                  </div>
                  <ul className="text-sm text-slate-600 space-y-1.5 list-disc pl-5">
                    <li>
                      <strong>Teams / Stream:</strong> baixe o arquivo <code>.vtt</code> da aba
                      <em> Transcrição</em> (mantém as tags <code>&lt;v Nome&gt;</code> de cada
                      participante) e arraste em <strong>Nova Ingestão</strong>.
                    </li>
                    <li>
                      <strong>Gravações sem legenda (&gt; 1h):</strong> baixe o <code>.mp4</code> do
                      SharePoint/Drive; o backend extrai o áudio com <code>ffmpeg</code> (mono 16kHz
                      48kbps), divide em blocos de 20 min e recompõe os timestamps sem truncar.
                    </li>
                    <li>
                      <strong>Privacidade em disco:</strong> arquivos temporários enviados para{" "}
                      <code>data/uploads/</code> são excluídos automaticamente assim que o job
                      finaliza.
                    </li>
                  </ul>
                </div>

                <div className="rounded-2xl border border-slate-200 p-5 space-y-2.5">
                  <div className="flex items-center gap-2 text-slate-900 font-semibold">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                    Governança, Credenciais e Human-in-the-Loop
                  </div>
                  <ul className="text-sm text-slate-600 space-y-1.5 list-disc pl-5">
                    <li>
                      <strong>Gestão de Segredos:</strong> em servidores compartilhados, forneça
                      chaves apenas via variáveis de ambiente / Key Vault / Databricks Secrets (nunca
                      commite <code>.env</code>). Na UI, chaves sempre aparecem mascaradas.
                    </li>
                    <li>
                      <strong>Glossário Corporativo:</strong> cadastre nomes de squads, produtos,
                      ERPs e siglas em <strong>Configurações</strong> para evitar erros de grafia em
                      atas executivas.
                    </li>
                    <li>
                      <strong>Revisão Humana:</strong> trate a ata gerada como rascunho acelerado —
                      valide donos e prazos antes de distribuir ou sincronizar no Lakehouse
                      corporativo.
                    </li>
                    <li>
                      <strong>Automação via CLI:</strong> times podem integrar o comando{" "}
                      <code>python -m app.cli ingest ... --output-md</code> e{" "}
                      <code>push-databricks</code> em scripts internos ou rotinas agendadas.
                    </li>
                  </ul>
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: DATABRICKS LAKEHOUSE & GENIE */}
          {activeTab === "lakehouse" && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-bold text-slate-900">
                  Arquitetura Corporativa no Databricks Lakehouse + Genie Space
                </h3>
                <p className="text-sm text-slate-600 mt-1">
                  Para consolidar dezenas ou milhares de reuniões da empresa inteira com governança
                  Unity Catalog, auditoria e consultas em linguagem natural para gestores.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                <div className="rounded-2xl border border-slate-200 bg-slate-50/70 p-4 space-y-1.5">
                  <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wide text-slate-500">
                    <CloudUpload className="w-4 h-4 text-indigo-600" />
                    Landing (UC Volume)
                  </div>
                  <p className="text-sm font-semibold text-slate-900">raw_transcripts</p>
                  <p className="text-xs text-slate-600 leading-relaxed">
                    Recebe arquivos <code>.vtt</code>, <code>.srt</code>, <code>.txt</code> e{" "}
                    <code>.json</code> enviados pelo botão do portal, CLI ou integração SharePoint.
                  </p>
                </div>

                <div className="rounded-2xl border border-amber-200 bg-amber-50/40 p-4 space-y-1.5">
                  <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wide text-amber-700">
                    <Layers className="w-4 h-4" />
                    Bronze (read_files)
                  </div>
                  <p className="text-sm font-semibold text-slate-900">bronze_transcricoes_raw</p>
                  <p className="text-xs text-slate-600 leading-relaxed">
                    Streaming Table incremental via <code>STREAM read_files(..., wholeText =&gt; true)</code>{" "}
                    com hash SHA-256 e metadados de arquivo.
                  </p>
                </div>

                <div className="rounded-2xl border border-sky-200 bg-sky-50/40 p-4 space-y-1.5">
                  <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wide text-sky-700">
                    <FileText className="w-4 h-4" />
                    Silver (Limpeza + Parsing)
                  </div>
                  <p className="text-sm font-semibold text-slate-900">
                    silver_transcricoes_limpas
                  </p>
                  <p className="text-xs text-slate-600 leading-relaxed">
                    Higienização determinística de timestamps/HTML + extração de{" "}
                    <strong>falantes (speakers)</strong>, turnos, data da reunião e contagem de
                    palavras/tokens.
                  </p>
                </div>

                <div className="rounded-2xl border border-emerald-200 bg-emerald-50/40 p-4 space-y-1.5">
                  <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wide text-emerald-700">
                    <Sparkles className="w-4 h-4" />
                    Gold (ai_query + Genie)
                  </div>
                  <p className="text-sm font-semibold text-slate-900">
                    4 tabelas Gold + Genie Space
                  </p>
                  <p className="text-xs text-slate-600 leading-relaxed">
                    Extração com <code>ai_query</code> + <code>responseFormat</code> (JSON Schema
                    estrito) gerando <code>catalogo</code>, <code>decisoes</code>,{" "}
                    <code>pendencias</code> e <code>action_items</code> prontas para perguntas no
                    Genie Space.
                  </p>
                </div>
              </div>

              <div className="rounded-2xl border border-slate-200 p-5 space-y-3">
                <h4 className="font-semibold text-slate-900 text-sm">
                  Exemplos de perguntas que gestores fazem no Genie Space após a sincronização:
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5 text-xs text-slate-700">
                  <div className="rounded-xl bg-slate-50 border border-slate-200 px-3.5 py-2.5">
                    &ldquo;Quais action items de prioridade Alta estão pendentes e quem são os
                    responsáveis?&rdquo;
                  </div>
                  <div className="rounded-xl bg-slate-50 border border-slate-200 px-3.5 py-2.5">
                    &ldquo;Liste todas as decisões aprovadas nas reuniões de Governança, Segurança e
                    FinOps.&rdquo;
                  </div>
                  <div className="rounded-xl bg-slate-50 border border-slate-200 px-3.5 py-2.5">
                    &ldquo;Quais bloqueios/pendências ainda aguardam times externos (Jurídico,
                    Infra, IAM)?&rdquo;
                  </div>
                  <div className="rounded-xl bg-slate-50 border border-slate-200 px-3.5 py-2.5">
                    &ldquo;Qual foi a taxa de JSON válido, precisão, recall e custo médio da POC de
                    extração?&rdquo;
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </section>
    </div>
  );
};
