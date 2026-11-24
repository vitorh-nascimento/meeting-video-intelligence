import React, { useEffect, useState } from "react";
import {
  AlertTriangle,
  ArrowLeft,
  Check,
  CheckCircle2,
  CheckSquare,
  CloudUpload,
  Copy,
  Download,
  FileText,
  Lightbulb,
  Loader2,
  RefreshCw,
  Search,
  Square,
} from "lucide-react";
import { api } from "../api/client";
import type { DocumentDetailData, ExtractionTemplate } from "../types";
import { TranscriptChat } from "./TranscriptChat";

const REANALYZE_TEMPLATES: ExtractionTemplate[] = [
  "Reunião Corporativa",
  "Aula/Vídeo Técnico",
  "Discovery/Cliente",
  "Sessão Legislativa / Política",
];

interface DocumentDetailProps {
  docId: string;
  onBack: () => void;
}

type DetailTab =
  | "summary"
  | "decisions"
  | "pendings"
  | "actions"
  | "knowledge"
  | "transcript";

export const DocumentDetail: React.FC<DocumentDetailProps> = ({ docId, onBack }) => {
  const [doc, setDoc] = useState<DocumentDetailData | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<DetailTab>("summary");
  const [copiedAta, setCopiedAta] = useState(false);
  const [transcriptQuery, setTranscriptQuery] = useState("");
  const [highlightTs, setHighlightTs] = useState<string | null>(null);
  const [pushingDbx, setPushingDbx] = useState(false);
  const [dbxNotice, setDbxNotice] = useState<string | null>(null);
  const [reanalyzeTemplate, setReanalyzeTemplate] = useState<ExtractionTemplate>("Sessão Legislativa / Política");
  const [reanalyzing, setReanalyzing] = useState(false);

  const loadDoc = async () => {
    setLoading(true);
    try {
      const data = await api.getDocument(docId);
      setDoc(data);
      if (REANALYZE_TEMPLATES.includes(data.template as ExtractionTemplate)) {
        setReanalyzeTemplate(data.template as ExtractionTemplate);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDoc();
  }, [docId]);

  const handleCopyAta = async () => {
    if (!doc) return;
    await navigator.clipboard.writeText(doc.ata_markdown);
    setCopiedAta(true);
    setTimeout(() => setCopiedAta(false), 2000);
  };

  const toggleActionItem = async (itemId: number, currentStatus: string) => {
    if (!doc) return;
    const nextStatus = currentStatus === "Concluído" ? "Pendente" : "Concluído";
    const updated = await api.updateActionItem(doc.id, itemId, { status: nextStatus });
    setDoc({
      ...doc,
      action_items: doc.action_items.map((a) => (a.id === itemId ? updated : a)),
    });
  };

  const togglePendingItem = async (itemId: number, currentStatus: string) => {
    if (!doc) return;
    const nextStatus = currentStatus === "Concluído" ? "Pendente" : "Concluído";
    const updated = await api.updatePendingItem(doc.id, itemId, { status: nextStatus });
    setDoc({
      ...doc,
      pendings: doc.pendings.map((p) => (p.id === itemId ? updated : p)),
    });
  };

  const handlePushDatabricks = async (runPipeline: boolean) => {
    if (!doc) return;
    setPushingDbx(true);
    setDbxNotice(null);
    try {
      await api.pushToDatabricks(doc.id, runPipeline);
      setDbxNotice(
        runPipeline
          ? "Transcrição enviada ao Volume UC e pipeline Lakeflow acionada!"
          : "Transcrição enviada com sucesso ao Volume UC no Databricks!"
      );
      await loadDoc();
    } catch (err) {
      setDbxNotice(`Erro Databricks: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setPushingDbx(false);
    }
  };

  const handleReanalyze = async () => {
    if (!doc) return;
    setReanalyzing(true);
    setDbxNotice(`Reanalisando transcrição com o template "${reanalyzeTemplate}" (sem refazer o Whisper)...`);
    try {
      const updated = await api.reanalyzeDocument(doc.id, reanalyzeTemplate);
      setDoc(updated);
      setDbxNotice(`Análise atualizada com sucesso usando o template "${reanalyzeTemplate}"!`);
    } catch (err) {
      setDbxNotice(`Erro ao reanalisar: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setReanalyzing(false);
    }
  };

  const handleJumpToTimestamp = (ts: string) => {
    setHighlightTs(ts);
    setActiveTab("transcript");
  };

  if (loading || !doc) {
    return (
      <div className="py-16 text-center text-slate-500 flex items-center justify-center gap-2">
        <Loader2 className="w-5 h-5 animate-spin text-indigo-600" /> Carregando análise...
      </div>
    );
  }

  const filteredSegments = doc.segments.filter((seg) => {
    if (!transcriptQuery.trim()) return true;
    const q = transcriptQuery.toLowerCase();
    return (
      seg.texto.toLowerCase().includes(q) ||
      (seg.speaker || "").toLowerCase().includes(q) ||
      seg.inicio.toLowerCase().includes(q)
    );
  });

  const isLegislative = doc.template === "Sessão Legislativa / Política";
  const tabs: { id: DetailTab; label: string; badge?: number }[] = [
    { id: "summary", label: isLegislative ? "Boletim & Ata" : "Resumo & Ata" },
    { id: "decisions", label: isLegislative ? "Votações & Decisões" : "Decisões", badge: doc.decisions.length },
    { id: "pendings", label: isLegislative ? "Indicações & Pendências" : "Pendências", badge: doc.pendings.length },
    { id: "actions", label: isLegislative ? "Encaminhamentos" : "Action Items", badge: doc.action_items.length },
    { id: "knowledge", label: "Informações & Entidades" },
    { id: "transcript", label: "Transcrição", badge: doc.segments.length },
  ];

  return (
    <div className="space-y-5">
      {/* Cabeçalho do documento */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5">
        <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
          <div className="space-y-2">
            <button
              type="button"
              onClick={onBack}
              className="inline-flex items-center gap-1.5 text-xs font-medium text-indigo-600 hover:text-indigo-800"
            >
              <ArrowLeft className="w-3.5 h-3.5" /> Voltar para Biblioteca
            </button>
            <h2 className="text-xl font-bold text-slate-900">{doc.title}</h2>
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <span className="px-2.5 py-1 rounded-full bg-indigo-50 text-indigo-700 font-medium">
                {doc.media_type}
              </span>
              <span className="px-2.5 py-1 rounded-full bg-slate-100 text-slate-700 font-medium">
                {doc.category}
              </span>
              <span className="px-2.5 py-1 rounded-full bg-slate-100 text-slate-600">
                Duração: {doc.duration_formatted}
              </span>
              <span className="px-2.5 py-1 rounded-full bg-slate-100 text-slate-600">
                {doc.word_count.toLocaleString("pt-BR")} palavras
              </span>
              <span className="px-2.5 py-1 rounded-full bg-slate-100 text-slate-600">
                Transcritor: {doc.transcriber_provider} • LLM: {doc.llm_provider}
              </span>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {(["md", "srt", "txt", "json"] as const).map((fmt) => (
              <a
                key={fmt}
                href={api.getExportUrl(doc.id, fmt)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-slate-300 hover:bg-slate-50 text-xs font-medium text-slate-700 transition"
              >
                <Download className="w-3.5 h-3.5" /> .{fmt}
              </a>
            ))}
            <div className="flex items-center gap-1.5">
              <select
                value={reanalyzeTemplate}
                onChange={(e) => setReanalyzeTemplate(e.target.value as ExtractionTemplate)}
                disabled={reanalyzing}
                className="rounded-xl border border-slate-300 bg-white px-2.5 py-1.5 text-xs text-slate-700"
                title="Escolher template para reanalisar a transcrição já salva"
              >
                {REANALYZE_TEMPLATES.map((tpl) => (
                  <option key={tpl} value={tpl}>
                    {tpl}
                  </option>
                ))}
              </select>
              <button
                type="button"
                disabled={reanalyzing}
                onClick={handleReanalyze}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-xs font-medium transition cursor-pointer"
              >
                {reanalyzing ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <RefreshCw className="w-3.5 h-3.5" />
                )}
                {reanalyzing ? "Reanalisando..." : "Reanalisar"}
              </button>
            </div>
            <button
              type="button"
              disabled={pushingDbx}
              onClick={() => handlePushDatabricks(false)}
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-slate-900 hover:bg-slate-800 disabled:opacity-50 text-white text-xs font-medium transition"
            >
              {pushingDbx ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <CloudUpload className="w-3.5 h-3.5" />
              )}
              Enviar para Databricks
            </button>
          </div>
        </div>

        {dbxNotice && (
          <div className="mt-3 rounded-xl px-3.5 py-2 text-xs bg-slate-100 text-slate-700 border border-slate-200">
            {dbxNotice}
          </div>
        )}
      </div>

      {/* Layout principal: Conteúdo em Abas + Chat Q&A */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-5 items-start">
        <div className="xl:col-span-8 bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
          {/* Navegação por abas */}
          <div className="flex overflow-x-auto border-b border-slate-200 px-3 pt-2 gap-1 bg-slate-50/70">
            {tabs.map((t) => (
              <button
                key={t.id}
                type="button"
                onClick={() => setActiveTab(t.id)}
                className={`px-3.5 py-2.5 text-xs sm:text-sm font-medium whitespace-nowrap border-b-2 transition flex items-center gap-1.5 ${
                  activeTab === t.id
                    ? "border-indigo-600 text-indigo-700 bg-white rounded-t-xl"
                    : "border-transparent text-slate-600 hover:text-slate-900"
                }`}
              >
                {t.label}
                {typeof t.badge === "number" && (
                  <span className="px-1.5 py-0.5 text-[11px] rounded-full bg-slate-200/80 text-slate-700">
                    {t.badge}
                  </span>
                )}
              </button>
            ))}
          </div>

          <div className="p-6">
            {/* ABA 1: Resumo & Ata */}
            {activeTab === "summary" && (
              <div className="space-y-6">
                <div>
                  <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-500 mb-2">
                    Resumo Executivo
                  </h3>
                  <p className="text-slate-800 leading-relaxed text-sm sm:text-base">
                    {doc.summary_short}
                  </p>
                </div>

                {doc.summary_bullets.length > 0 && (
                  <div>
                    <h4 className="text-sm font-semibold text-slate-800 mb-2">
                      Principais Tópicos Discutidos
                    </h4>
                    <ul className="space-y-1.5 list-disc pl-5 text-sm text-slate-700">
                      {doc.summary_bullets.map((b, i) => (
                        <li key={i}>{b}</li>
                      ))}
                    </ul>
                  </div>
                )}

                <div className="pt-4 border-t border-slate-200">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="text-sm font-semibold text-slate-800 flex items-center gap-1.5">
                      <FileText className="w-4 h-4 text-indigo-600" />
                      Ata / Relatório Pronto (Markdown)
                    </h4>
                    <button
                      type="button"
                      onClick={handleCopyAta}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-50 hover:bg-indigo-100 text-indigo-700 text-xs font-medium transition"
                    >
                      {copiedAta ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                      {copiedAta ? "Copiado!" : "Copiar para Teams / E-mail / Confluence"}
                    </button>
                  </div>
                  <pre className="bg-slate-900 text-slate-100 rounded-xl p-4 text-xs overflow-x-auto whitespace-pre-wrap leading-relaxed font-mono">
                    {doc.ata_markdown}
                  </pre>
                </div>
              </div>
            )}

            {/* ABA 2: Decisões */}
            {activeTab === "decisions" && (
              <div className="space-y-3">
                {doc.decisions.length === 0 ? (
                  <p className="text-sm text-slate-500">Nenhuma decisão formal identificada nesta transcrição.</p>
                ) : (
                  doc.decisions.map((d) => (
                    <div key={d.id} className="rounded-xl border border-slate-200 p-4 space-y-2">
                      <div className="flex items-start gap-2">
                        <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
                        <p className="font-semibold text-slate-900 text-sm">{d.decisao}</p>
                      </div>
                      {d.contexto && (
                        <p className="text-xs text-slate-600 pl-7">
                          <strong>Contexto:</strong> {d.contexto}
                        </p>
                      )}
                      {d.impacto && (
                        <p className="text-xs text-slate-600 pl-7">
                          <strong>Impacto:</strong> {d.impacto}
                        </p>
                      )}
                      {d.participantes_envolvidos.length > 0 && (
                        <div className="pl-7 flex flex-wrap gap-1.5 pt-1">
                          {d.participantes_envolvidos.map((p, idx) => (
                            <span
                              key={idx}
                              className="text-[11px] px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700"
                            >
                              {p}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            )}

            {/* ABA 3: Pendências */}
            {activeTab === "pendings" && (
              <div className="space-y-3">
                {doc.pendings.length === 0 ? (
                  <p className="text-sm text-slate-500">Nenhuma pendência ou bloqueio identificado.</p>
                ) : (
                  doc.pendings.map((p) => {
                    const done = p.status === "Concluído";
                    return (
                      <div
                        key={p.id}
                        className={`rounded-xl border p-4 flex items-start justify-between gap-3 transition ${
                          done ? "bg-slate-50 border-slate-200 opacity-75" : "border-amber-200 bg-amber-50/30"
                        }`}
                      >
                        <button
                          type="button"
                          onClick={() => togglePendingItem(p.id, p.status)}
                          className="flex items-start gap-3 text-left flex-1"
                        >
                          {done ? (
                            <CheckSquare className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
                          ) : (
                            <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
                          )}
                          <div>
                            <p className={`text-sm font-medium ${done ? "line-through text-slate-500" : "text-slate-900"}`}>
                              {p.descricao}
                            </p>
                            <p className="text-xs text-slate-600 mt-1">
                              Responsável/Área: <strong>{p.responsavel_ou_area}</strong> • Impacto:{" "}
                              <strong>{p.impacto}</strong>
                            </p>
                          </div>
                        </button>
                        <span
                          className={`text-xs px-2.5 py-1 rounded-full font-medium shrink-0 ${
                            done ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-800"
                          }`}
                        >
                          {p.status}
                        </span>
                      </div>
                    );
                  })
                )}
              </div>
            )}

            {/* ABA 4: Action Items (Checklist Interativo) */}
            {activeTab === "actions" && (
              <div className="space-y-3">
                {doc.action_items.length === 0 ? (
                  <p className="text-sm text-slate-500">Nenhum Action Item identificado nesta transcrição.</p>
                ) : (
                  doc.action_items.map((a) => {
                    const done = a.status === "Concluído";
                    return (
                      <div
                        key={a.id}
                        className={`rounded-xl border p-4 flex items-start justify-between gap-3 transition ${
                          done ? "bg-slate-50 border-slate-200 opacity-75" : "bg-white border-slate-200 hover:border-indigo-300"
                        }`}
                      >
                        <button
                          type="button"
                          onClick={() => toggleActionItem(a.id, a.status)}
                          className="flex items-start gap-3 text-left flex-1"
                        >
                          {done ? (
                            <CheckSquare className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
                          ) : (
                            <Square className="w-5 h-5 text-slate-400 shrink-0 mt-0.5" />
                          )}
                          <div>
                            <p className={`text-sm font-medium ${done ? "line-through text-slate-500" : "text-slate-900"}`}>
                              {a.tarefa}
                            </p>
                            <div className="flex flex-wrap items-center gap-3 text-xs text-slate-600 mt-1.5">
                              <span>
                                Responsável: <strong>{a.responsavel}</strong>
                              </span>
                              <span>
                                Prazo: <strong>{a.prazo}</strong>
                              </span>
                            </div>
                          </div>
                        </button>
                        <div className="flex items-center gap-2 shrink-0">
                          <span
                            className={`text-xs px-2.5 py-1 rounded-full font-medium ${
                              a.prioridade === "Alta"
                                ? "bg-red-100 text-red-700"
                                : a.prioridade === "Baixa"
                                ? "bg-slate-100 text-slate-600"
                                : "bg-indigo-100 text-indigo-700"
                            }`}
                          >
                            {a.prioridade}
                          </span>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            )}

            {/* ABA 5: Informações & Entidades */}
            {activeTab === "knowledge" && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {[
                  { title: "Insights Principais", items: doc.knowledge.insights || [] },
                  { title: "Aprendizados Técnicos", items: doc.knowledge.aprendizados_tecnicos || [] },
                  { title: "Métricas & Números Citados", items: doc.knowledge.metricas_citadas || [] },
                  { title: "Riscos Levantados", items: doc.knowledge.riscos || [] },
                ].map((section) => (
                  <div key={section.title} className="rounded-xl border border-slate-200 p-4">
                    <h4 className="text-sm font-semibold text-slate-900 mb-2 flex items-center gap-1.5">
                      <Lightbulb className="w-4 h-4 text-indigo-600" />
                      {section.title}
                    </h4>
                    {section.items.length === 0 ? (
                      <p className="text-xs text-slate-400">Nenhum item registrado.</p>
                    ) : (
                      <ul className="list-disc pl-4 space-y-1 text-xs text-slate-700">
                        {section.items.map((x, idx) => (
                          <li key={idx}>{x}</li>
                        ))}
                      </ul>
                    )}
                  </div>
                ))}

                <div className="md:col-span-2 rounded-xl border border-slate-200 p-4">
                  <h4 className="text-sm font-semibold text-slate-900 mb-2.5">
                    Ferramentas &amp; Tecnologias Mencionadas
                  </h4>
                  {(doc.knowledge.ferramentas_tecnologias || []).length === 0 ? (
                    <p className="text-xs text-slate-400">Nenhuma tecnologia identificada.</p>
                  ) : (
                    <div className="flex flex-wrap gap-2">
                      {doc.knowledge.ferramentas_tecnologias.map((tech, idx) => (
                        <span
                          key={idx}
                          className="text-xs font-medium px-3 py-1 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200/70"
                        >
                          {tech}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* ABA 6: Transcrição Completa com Timestamps */}
            {activeTab === "transcript" && (
              <div className="space-y-4">
                <div className="relative">
                  <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-2.5" />
                  <input
                    type="text"
                    value={transcriptQuery}
                    onChange={(e) => setTranscriptQuery(e.target.value)}
                    placeholder="Filtrar na transcrição por termo, locutor ou timestamp..."
                    className="w-full pl-10 pr-3 py-2 rounded-xl border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>

                <div className="max-h-[480px] overflow-y-auto divide-y divide-slate-100 border border-slate-200 rounded-xl">
                  {filteredSegments.map((seg) => {
                    const tsShort = seg.inicio.split(",")[0];
                    const isHighlighted = highlightTs && seg.inicio.startsWith(highlightTs);
                    return (
                      <div
                        key={seg.index}
                        className={`p-3 text-sm flex items-start gap-3 ${
                          isHighlighted ? "bg-indigo-50" : "hover:bg-slate-50"
                        }`}
                      >
                        <span className="font-mono text-xs text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded shrink-0 mt-0.5">
                          {tsShort}
                        </span>
                        <p className="text-slate-800 leading-relaxed">
                          {seg.speaker && (
                            <strong className="text-slate-900 mr-1.5">{seg.speaker}:</strong>
                          )}
                          {seg.texto}
                        </p>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Coluna lateral: Chat Q&A */}
        <div className="xl:col-span-4">
          <TranscriptChat
            docId={doc.id}
            initialHistory={doc.chat_history || []}
            onJumpToTimestamp={handleJumpToTimestamp}
          />
        </div>
      </div>
    </div>
  );
};
