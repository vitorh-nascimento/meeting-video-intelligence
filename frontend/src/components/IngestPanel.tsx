import React, { useEffect, useRef, useState } from "react";
import {
  CheckCircle2,
  CloudUpload,
  FileAudio,
  FileText,
  Link2,
  Loader2,
  Sparkles,
  Upload,
  AlertCircle,
} from "lucide-react";
import { api } from "../api/client";
import type { ExtractionTemplate, JobStatus } from "../types";

interface IngestPanelProps {
  onCompleted: (documentId: string) => void;
}

const TEMPLATES: ExtractionTemplate[] = [
  "Reunião Corporativa",
  "Aula/Vídeo Técnico",
  "Discovery/Cliente",
];

const STAGES = [
  "Recebido",
  "Extraindo Áudio",
  "Transcrevendo",
  "Analisando com LLM",
  "Concluído",
];

export const IngestPanel: React.FC<IngestPanelProps> = ({ onCompleted }) => {
  const [mode, setMode] = useState<"file" | "url" | "text">("file");
  const [template, setTemplate] = useState<ExtractionTemplate>("Reunião Corporativa");
  const [title, setTitle] = useState("");
  const [language, setLanguage] = useState("pt-BR");

  // File state
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // URL state
  const [url, setUrl] = useState("");
  const [forceAi, setForceAi] = useState(false);

  // Text state
  const [rawText, setRawText] = useState("");
  const [formatHint, setFormatHint] = useState<"auto" | "srt" | "vtt" | "txt" | "json">("auto");

  // Databricks optional push
  const [pushDatabricks, setPushDatabricks] = useState(false);
  const [runPipeline, setRunPipeline] = useState(false);

  // Job tracking
  const [activeJob, setActiveJob] = useState<JobStatus | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!activeJob || activeJob.status !== "running") return;
    const timer = setInterval(async () => {
      try {
        const updated = await api.getJob(activeJob.id);
        setActiveJob(updated);
        if (updated.status === "completed" && updated.document_id) {
          clearInterval(timer);
          onCompleted(updated.document_id);
        } else if (updated.status === "failed") {
          clearInterval(timer);
          setError(updated.error || updated.message);
        }
      } catch (err) {
        clearInterval(timer);
        setError(err instanceof Error ? err.message : "Erro ao consultar progresso.");
      }
    }, 1000);
    return () => clearInterval(timer);
  }, [activeJob, onCompleted]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      let job: JobStatus;
      if (mode === "file") {
        if (!selectedFile) throw new Error("Selecione ou arraste um arquivo de vídeo, áudio ou legenda.");
        job = await api.ingestFile({
          file: selectedFile,
          title: title.trim() || undefined,
          template,
          language: language || undefined,
          pushToDatabricks: pushDatabricks,
          runDatabricksPipeline: runPipeline,
        });
      } else if (mode === "url") {
        if (!url.trim()) throw new Error("Informe a URL do vídeo (YouTube ou link compatível com yt-dlp).");
        job = await api.ingestUrl({
          url: url.trim(),
          title: title.trim() || undefined,
          template,
          force_ai_transcription: forceAi,
          language: language || undefined,
          push_to_databricks: pushDatabricks,
          run_databricks_pipeline: runPipeline,
        });
      } else {
        if (rawText.trim().length < 15) {
          throw new Error("Cole uma transcrição com pelo menos 15 caracteres.");
        }
        job = await api.ingestText({
          text: rawText,
          title: title.trim() || "Transcrição Colada",
          format_hint: formatHint,
          template,
          language: language || "pt-BR",
        });
      }
      setActiveJob(job);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao iniciar processamento.");
    } finally {
      setSubmitting(false);
    }
  };

  const currentStageIdx = activeJob ? STAGES.indexOf(activeJob.stage) : -1;

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-5 border-b border-slate-100">
          <div>
            <h2 className="text-xl font-semibold text-slate-900 flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-indigo-600" />
              Nova Ingestão Inteligente
            </h2>
            <p className="text-sm text-slate-500 mt-1">
              Suba vídeos/áudios corporativos sem legenda, links do YouTube ou transcrições do Teams/Meet/Zoom.
            </p>
          </div>
          <div className="inline-flex bg-slate-100 p-1 rounded-xl">
            <button
              type="button"
              onClick={() => setMode("file")}
              className={`px-3 py-1.5 text-sm font-medium rounded-lg flex items-center gap-1.5 transition ${
                mode === "file" ? "bg-white text-indigo-700 shadow-sm" : "text-slate-600 hover:text-slate-900"
              }`}
            >
              <Upload className="w-4 h-4" /> Arquivo
            </button>
            <button
              type="button"
              onClick={() => setMode("url")}
              className={`px-3 py-1.5 text-sm font-medium rounded-lg flex items-center gap-1.5 transition ${
                mode === "url" ? "bg-white text-indigo-700 shadow-sm" : "text-slate-600 hover:text-slate-900"
              }`}
            >
              <Link2 className="w-4 h-4" /> URL Vídeo
            </button>
            <button
              type="button"
              onClick={() => setMode("text")}
              className={`px-3 py-1.5 text-sm font-medium rounded-lg flex items-center gap-1.5 transition ${
                mode === "text" ? "bg-white text-indigo-700 shadow-sm" : "text-slate-600 hover:text-slate-900"
              }`}
            >
              <FileText className="w-4 h-4" /> Texto
            </button>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="mt-6 space-y-5">
          {/* Metadados e Template */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="md:col-span-1">
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1.5">
                Perfil / Template de Extração
              </label>
              <select
                value={template}
                onChange={(e) => setTemplate(e.target.value as ExtractionTemplate)}
                className="w-full rounded-xl border border-slate-300 px-3 py-2.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                {TEMPLATES.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1.5">
                Título (opcional)
              </label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Ex.: Comitê Arquitetura Dados Q4"
                className="w-full rounded-xl border border-slate-300 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1.5">
                Idioma Principal
              </label>
              <select
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                className="w-full rounded-xl border border-slate-300 px-3 py-2.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="pt-BR">Português (Brasil)</option>
                <option value="en">Inglês</option>
                <option value="es">Espanhol</option>
                <option value="">Detectar automaticamente</option>
              </select>
            </div>
          </div>

          {/* Área de entrada por modo */}
          {mode === "file" && (
            <div
              onDragOver={(e) => {
                e.preventDefault();
                setIsDragging(true);
              }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={(e) => {
                e.preventDefault();
                setIsDragging(false);
                if (e.dataTransfer.files?.[0]) {
                  setSelectedFile(e.dataTransfer.files[0]);
                }
              }}
              onClick={() => fileInputRef.current?.click()}
              className={`border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition ${
                isDragging
                  ? "border-indigo-500 bg-indigo-50"
                  : "border-slate-300 hover:border-indigo-400 hover:bg-slate-50"
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                className="hidden"
                accept=".vtt,.srt,.txt,.json,.mp4,.mkv,.mov,.webm,.avi,.mp3,.wav,.m4a,.ogg,.aac"
                onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
              />
              <div className="mx-auto w-12 h-12 rounded-2xl bg-indigo-50 text-indigo-600 flex items-center justify-center mb-3">
                {selectedFile ? <FileAudio className="w-6 h-6" /> : <CloudUpload className="w-6 h-6" />}
              </div>
              {selectedFile ? (
                <div>
                  <p className="font-semibold text-slate-900">{selectedFile.name}</p>
                  <p className="text-xs text-slate-500 mt-1">
                    {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB — Clique para trocar o arquivo
                  </p>
                </div>
              ) : (
                <div>
                  <p className="font-medium text-slate-800">
                    Arraste e solte aqui ou clique para selecionar
                  </p>
                  <p className="text-xs text-slate-500 mt-1.5">
                    Legendas: <strong>.vtt, .srt, .txt, .json</strong> (Teams, Meet, Zoom) •
                    Vídeos/Áudios sem legenda: <strong>.mp4, .mkv, .mov, .webm, .avi, .mp3, .wav, .m4a, .ogg, .aac</strong>
                  </p>
                </div>
              )}
            </div>
          )}

          {mode === "url" && (
            <div className="space-y-3">
              <label className="block text-sm font-medium text-slate-700">
                URL do Vídeo (YouTube ou links compatíveis com yt-dlp)
              </label>
              <input
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://www.youtube.com/watch?v=..."
                className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
              <label className="inline-flex items-center gap-2 text-sm text-slate-700 cursor-pointer">
                <input
                  type="checkbox"
                  checked={forceAi}
                  onChange={(e) => setForceAi(e.target.checked)}
                  className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                />
                Forçar transcrição por IA (baixa áudio via yt-dlp mesmo se houver legenda automática)
              </label>
            </div>
          )}

          {mode === "text" && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium text-slate-700">
                  Cole a transcrição bruta (SRT, VTT, JSON ou texto de reunião)
                </label>
                <select
                  value={formatHint}
                  onChange={(e) => setFormatHint(e.target.value as typeof formatHint)}
                  className="rounded-lg border border-slate-300 px-2.5 py-1 text-xs bg-white"
                >
                  <option value="auto">Formato: Detectar automaticamente</option>
                  <option value="vtt">WebVTT (.vtt)</option>
                  <option value="srt">SubRip (.srt)</option>
                  <option value="txt">Texto puro (.txt)</option>
                  <option value="json">JSON (.json)</option>
                </select>
              </div>
              <textarea
                rows={8}
                value={rawText}
                onChange={(e) => setRawText(e.target.value)}
                placeholder="Ex.: Ana: Decidimos migrar o pipeline para Serverless até sexta-feira. Carlos vai configurar o alerta de custos..."
                className="w-full rounded-xl border border-slate-300 p-3.5 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
          )}

          {/* Opção Databricks */}
          {mode !== "text" && (
            <div className="bg-slate-50 rounded-xl p-4 border border-slate-200 flex flex-wrap items-center gap-5">
              <label className="inline-flex items-center gap-2 text-sm text-slate-700 cursor-pointer">
                <input
                  type="checkbox"
                  checked={pushDatabricks}
                  onChange={(e) => {
                    setPushDatabricks(e.target.checked);
                    if (!e.target.checked) setRunPipeline(false);
                  }}
                  className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                />
                Enviar transcrição gerada para o Volume no Databricks automaticamente
              </label>
              {pushDatabricks && (
                <label className="inline-flex items-center gap-2 text-sm text-slate-700 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={runPipeline}
                    onChange={(e) => setRunPipeline(e.target.checked)}
                    className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                  />
                  Acionar Pipeline Lakeflow após upload
                </label>
              )}
            </div>
          )}

          {error && (
            <div className="rounded-xl bg-red-50 border border-red-200 p-3.5 text-sm text-red-700 flex items-start gap-2.5">
              <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          <div className="flex justify-end">
            <button
              type="submit"
              disabled={submitting || activeJob?.status === "running"}
              className="px-6 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-medium text-sm shadow-sm flex items-center gap-2 transition"
            >
              {submitting || activeJob?.status === "running" ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Processando...
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  Transcrever e Analisar com IA
                </>
              )}
            </button>
          </div>
        </form>
      </div>

      {/* Progresso em tempo real */}
      {activeJob && (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-indigo-600">
                Pipeline em Execução
              </p>
              <h3 className="text-base font-semibold text-slate-900 mt-0.5">{activeJob.title}</h3>
            </div>
            <span className="text-sm font-semibold text-slate-700">{activeJob.progress}%</span>
          </div>

          <div className="w-full h-2.5 bg-slate-100 rounded-full overflow-hidden">
            <div
              className={`h-full transition-all duration-500 rounded-full ${
                activeJob.status === "failed"
                  ? "bg-red-500"
                  : activeJob.status === "completed"
                  ? "bg-emerald-500"
                  : "bg-indigo-600"
              }`}
              style={{ width: `${activeJob.progress}%` }}
            />
          </div>

          <div className="grid grid-cols-5 gap-2 pt-1">
            {STAGES.map((stage, idx) => {
              const isDone = activeJob.status === "completed" || idx < currentStageIdx;
              const isCurrent = activeJob.status === "running" && idx === currentStageIdx;
              return (
                <div
                  key={stage}
                  className={`rounded-xl px-2.5 py-2 text-xs font-medium border flex items-center gap-1.5 ${
                    isDone
                      ? "bg-emerald-50 border-emerald-200 text-emerald-800"
                      : isCurrent
                      ? "bg-indigo-50 border-indigo-300 text-indigo-800"
                      : "bg-slate-50 border-slate-200 text-slate-400"
                  }`}
                >
                  {isDone ? (
                    <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
                  ) : isCurrent ? (
                    <Loader2 className="w-3.5 h-3.5 shrink-0 animate-spin" />
                  ) : (
                    <span className="w-3.5 h-3.5 rounded-full border border-current inline-block shrink-0" />
                  )}
                  <span className="truncate">{stage}</span>
                </div>
              );
            })}
          </div>

          <p className="text-sm text-slate-600">{activeJob.message}</p>
        </div>
      )}
    </div>
  );
};
