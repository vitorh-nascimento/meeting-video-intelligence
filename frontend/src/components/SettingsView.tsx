import React, { useEffect, useState } from "react";
import { CheckCircle2, Cpu, Database, KeyRound, Save, Shield, XCircle } from "lucide-react";
import { api } from "../api/client";
import type { AppSettings, Capabilities } from "../types";

interface SettingsViewProps {
  onSaved?: (settings: AppSettings) => void;
}

export const SettingsView: React.FC<SettingsViewProps> = ({ onSaved }) => {
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [caps, setCaps] = useState<Capabilities | null>(null);
  const [glossaryText, setGlossaryText] = useState("");
  const [categoriesText, setCategoriesText] = useState("");
  const [saving, setSaving] = useState(false);
  const [savedMsg, setSavedMsg] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.getSettings(), api.getCapabilities()]).then(([s, c]) => {
      setSettings(s);
      setCaps(c);
      setGlossaryText((s.glossary_terms || []).join(", "));
      setCategoriesText((s.categories || []).join("\n"));
    });
  }, []);

  if (!settings) {
    return <div className="py-12 text-center text-sm text-slate-500">Carregando configurações...</div>;
  }

  const updateField = <K extends keyof AppSettings>(key: K, value: AppSettings[K]) => {
    setSettings((prev) => (prev ? { ...prev, [key]: value } : prev));
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setSavedMsg(null);
    try {
      const payload: Partial<AppSettings> = {
        ...settings,
        glossary_terms: glossaryText
          .split(",")
          .map((t) => t.trim())
          .filter(Boolean),
        categories: categoriesText
          .split("\n")
          .map((c) => c.trim())
          .filter(Boolean),
      };
      const updated = await api.updateSettings(payload);
      setSettings(updated);
      setSavedMsg("Configurações salvas localmente no SQLite com sucesso!");
      onSaved?.(updated);
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={handleSave} className="max-w-4xl mx-auto space-y-6">
      {/* Status de ferramentas locais */}
      {caps && (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5">
          <h3 className="text-sm font-semibold text-slate-900 mb-3 flex items-center gap-2">
            <Cpu className="w-4 h-4 text-indigo-600" />
            Capacidades Detectadas no Ambiente Local
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-2.5 text-xs">
            {[
              { label: "FFmpeg (Áudio/Chunks)", ok: caps.ffmpeg_available },
              { label: "yt-dlp (URLs)", ok: caps.yt_dlp_available },
              { label: "YouTube Legendas", ok: caps.youtube_transcript_api_available },
              { label: "Whisper Offline", ok: caps.faster_whisper_available },
              { label: "Databricks CLI", ok: caps.databricks_cli_available },
            ].map((item) => (
              <div
                key={item.label}
                className={`rounded-xl px-3 py-2 border flex items-center gap-2 ${
                  item.ok
                    ? "bg-emerald-50 border-emerald-200 text-emerald-800"
                    : "bg-slate-50 border-slate-200 text-slate-500"
                }`}
              >
                {item.ok ? (
                  <CheckCircle2 className="w-4 h-4 shrink-0" />
                ) : (
                  <XCircle className="w-4 h-4 shrink-0" />
                )}
                <span className="truncate font-medium">{item.label}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Provedores de Transcrição & LLM */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-5">
        <h3 className="text-base font-semibold text-slate-900 flex items-center gap-2">
          <KeyRound className="w-4 h-4 text-indigo-600" />
          Motores de Transcrição &amp; Sumarização (LLM)
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1">
              Provedor de Transcrição
            </label>
            <select
              value={settings.transcriber_provider}
              onChange={(e) => updateField("transcriber_provider", e.target.value)}
              className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm bg-white"
            >
              <option value="gemini">Google Gemini Multimodal (Cloud)</option>
              <option value="local_whisper">faster-whisper (100% Offline)</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1">
              Provedor de LLM (Extração &amp; Q&amp;A)
            </label>
            <select
              value={settings.llm_provider}
              onChange={(e) => updateField("llm_provider", e.target.value)}
              className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm bg-white"
            >
              <option value="gemini">Google Gemini API</option>
              <option value="openai">OpenAI</option>
              <option value="azure_openai">Azure OpenAI</option>
              <option value="databricks">Databricks Model Serving</option>
              <option value="ollama">Ollama (Local)</option>
              <option value="heuristic">Heurístico Offline (Sem API Key)</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1">
              Chunk de Áudio (minutos p/ vídeos &gt; 1h)
            </label>
            <input
              type="number"
              min={5}
              max={45}
              value={settings.audio_chunk_minutes}
              onChange={(e) => updateField("audio_chunk_minutes", Number(e.target.value))}
              className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm"
            />
          </div>
        </div>

        {/* Credenciais de API */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2 border-t border-slate-100">
          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1">
              Google Gemini API Key
            </label>
            <input
              type="password"
              value={settings.gemini_api_key}
              onChange={(e) => updateField("gemini_api_key", e.target.value)}
              placeholder="AIza..."
              className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm font-mono"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1">
              Modelo Gemini (LLM / Transcrição)
            </label>
            <input
              type="text"
              value={settings.gemini_llm_model}
              onChange={(e) => {
                updateField("gemini_llm_model", e.target.value);
                updateField("gemini_transcription_model", e.target.value);
              }}
              className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm font-mono"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1">
              OpenAI API Key (opcional)
            </label>
            <input
              type="password"
              value={settings.openai_api_key}
              onChange={(e) => updateField("openai_api_key", e.target.value)}
              placeholder="sk-..."
              className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm font-mono"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1">
              Modelo OpenAI / Ollama
            </label>
            <div className="grid grid-cols-2 gap-2">
              <input
                type="text"
                value={settings.openai_model}
                onChange={(e) => updateField("openai_model", e.target.value)}
                placeholder="gpt-4o-mini"
                className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm font-mono"
              />
              <input
                type="text"
                value={settings.ollama_model}
                onChange={(e) => updateField("ollama_model", e.target.value)}
                placeholder="llama3.1:8b"
                className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm font-mono"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1">
              Whisper Offline — Tamanho do Modelo
            </label>
            <select
              value={settings.whisper_model_size}
              onChange={(e) => updateField("whisper_model_size", e.target.value)}
              className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm bg-white"
            >
              <option value="tiny">tiny (ultra rápido)</option>
              <option value="base">base</option>
              <option value="small">small (recomendado CPU)</option>
              <option value="medium">medium</option>
              <option value="large-v3">large-v3 (máxima precisão / GPU)</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1">
              Ollama Base URL
            </label>
            <input
              type="text"
              value={settings.ollama_base_url}
              onChange={(e) => updateField("ollama_base_url", e.target.value)}
              className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm font-mono"
            />
          </div>
        </div>
      </div>

      {/* Glossário & Categorias */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-4">
        <h3 className="text-base font-semibold text-slate-900 flex items-center gap-2">
          <Shield className="w-4 h-4 text-indigo-600" />
          Glossário Técnico &amp; Categorias Temáticas
        </h3>
        <div>
          <label className="block text-xs font-semibold text-slate-600 mb-1">
            Glossário do Workspace (termos separados por vírgula — preservados na transcrição)
          </label>
          <textarea
            rows={3}
            value={glossaryText}
            onChange={(e) => setGlossaryText(e.target.value)}
            className="w-full rounded-xl border border-slate-300 p-3 text-sm"
          />
        </div>
        <div>
          <label className="block text-xs font-semibold text-slate-600 mb-1">
            Categorias Temáticas (uma por linha)
          </label>
          <textarea
            rows={5}
            value={categoriesText}
            onChange={(e) => setCategoriesText(e.target.value)}
            className="w-full rounded-xl border border-slate-300 p-3 text-sm"
          />
        </div>
      </div>

      {/* Integração Opcional Databricks */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-4">
        <h3 className="text-base font-semibold text-slate-900 flex items-center gap-2">
          <Database className="w-4 h-4 text-indigo-600" />
          Integração Opcional — Databricks Lakehouse (Unity Catalog &amp; Lakeflow)
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1">Databricks Host</label>
            <input
              type="url"
              value={settings.databricks_host}
              onChange={(e) => updateField("databricks_host", e.target.value)}
              placeholder="https://<workspace>.cloud.databricks.com"
              className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm font-mono"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1">Databricks Token (PAT)</label>
            <input
              type="password"
              value={settings.databricks_token}
              onChange={(e) => updateField("databricks_token", e.target.value)}
              placeholder="dapi..."
              className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm font-mono"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1">Catalog (Unity Catalog)</label>
            <input
              type="text"
              value={settings.databricks_catalog}
              onChange={(e) => updateField("databricks_catalog", e.target.value)}
              placeholder="main"
              className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm font-mono"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1">Schema</label>
            <input
              type="text"
              value={settings.databricks_schema}
              onChange={(e) => updateField("databricks_schema", e.target.value)}
              placeholder="meeting_intelligence"
              className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm font-mono"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1">Volume Name</label>
            <input
              type="text"
              value={settings.databricks_volume_name}
              onChange={(e) => updateField("databricks_volume_name", e.target.value)}
              placeholder="raw_transcripts"
              className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm font-mono"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1">
              CLI Profile (alternativa a Host/Token)
            </label>
            <input
              type="text"
              value={settings.databricks_profile}
              onChange={(e) => updateField("databricks_profile", e.target.value)}
              placeholder="DEFAULT"
              className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm font-mono"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1">Pipeline ID (Lakeflow)</label>
            <input
              type="text"
              value={settings.databricks_pipeline_id}
              onChange={(e) => updateField("databricks_pipeline_id", e.target.value)}
              placeholder="UUID da pipeline (opcional)"
              className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm font-mono"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1">
              Endpoint Model Serving / Unity Gateway
            </label>
            <input
              type="text"
              value={settings.databricks_llm_endpoint}
              onChange={(e) => updateField("databricks_llm_endpoint", e.target.value)}
              className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm font-mono"
            />
          </div>
        </div>
      </div>

      {savedMsg && (
        <div className="rounded-xl bg-emerald-50 border border-emerald-200 px-4 py-3 text-sm text-emerald-800">
          {savedMsg}
        </div>
      )}

      <div className="flex justify-end">
        <button
          type="submit"
          disabled={saving}
          className="px-6 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-sm font-medium shadow-sm flex items-center gap-2 transition"
        >
          <Save className="w-4 h-4" />
          {saving ? "Salvando..." : "Salvar Configurações"}
        </button>
      </div>
    </form>
  );
};
