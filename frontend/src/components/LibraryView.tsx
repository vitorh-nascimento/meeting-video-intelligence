import React, { useEffect, useState } from "react";
import {
  Calendar,
  CheckSquare,
  Clock,
  Cloud,
  FileText,
  Filter,
  Search,
  Trash2,
  Video,
} from "lucide-react";
import { api } from "../api/client";
import type { DocumentSummary } from "../types";

interface LibraryViewProps {
  categories: string[];
  onSelectDocument: (docId: string) => void;
}

const MEDIA_TYPES = ["Todos", "Reunião", "Vídeo Técnico/Aula", "Áudio/Podcast", "Entrevista", "Outro"];

export const LibraryView: React.FC<LibraryViewProps> = ({ categories, onSelectDocument }) => {
  const [docs, setDocs] = useState<DocumentSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [mediaType, setMediaType] = useState("Todos");
  const [category, setCategory] = useState("Todas");
  const [dateFrom, setDateFrom] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const list = await api.listDocuments({
        search: search || undefined,
        media_type: mediaType,
        category,
        date_from: dateFrom || undefined,
      });
      setDocs(list);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const t = setTimeout(load, 200);
    return () => clearTimeout(t);
  }, [search, mediaType, category, dateFrom]);

  const handleDelete = async (e: React.MouseEvent, docId: string, title: string) => {
    e.stopPropagation();
    if (!window.confirm(`Excluir permanentemente "${title}"?`)) return;
    await api.deleteDocument(docId);
    load();
  };

  return (
    <div className="space-y-5">
      {/* Barra de filtros */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-4">
        <div className="grid grid-cols-1 md:grid-cols-12 gap-3">
          <div className="md:col-span-5 relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Buscar por título, resumo, transcrição ou categoria..."
              className="w-full pl-10 pr-3 py-2 rounded-xl border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          <div className="md:col-span-2">
            <select
              value={mediaType}
              onChange={(e) => setMediaType(e.target.value)}
              className="w-full px-3 py-2 rounded-xl border border-slate-300 text-sm bg-white"
            >
              {MEDIA_TYPES.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </div>
          <div className="md:col-span-3">
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="w-full px-3 py-2 rounded-xl border border-slate-300 text-sm bg-white"
            >
              <option value="Todas">Todas as categorias</option>
              {categories.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>
          <div className="md:col-span-2">
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="w-full px-3 py-2 rounded-xl border border-slate-300 text-sm bg-white"
              title="A partir da data"
            />
          </div>
        </div>
      </div>

      {/* Lista de documentos */}
      {loading ? (
        <div className="text-center py-16 text-slate-500 text-sm">Carregando biblioteca...</div>
      ) : docs.length === 0 ? (
        <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center">
          <Filter className="w-10 h-10 text-slate-300 mx-auto mb-3" />
          <p className="font-medium text-slate-700">Nenhum registro encontrado</p>
          <p className="text-sm text-slate-500 mt-1">
            Use a aba "Nova Ingestão" para processar sua primeira reunião, vídeo ou transcrição.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {docs.map((doc) => (
            <div
              key={doc.id}
              onClick={() => onSelectDocument(doc.id)}
              className="bg-white rounded-2xl border border-slate-200 hover:border-indigo-400 hover:shadow-md transition p-5 cursor-pointer flex flex-col justify-between gap-4"
            >
              <div>
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="inline-flex items-center gap-1 text-xs font-medium px-2.5 py-0.5 rounded-full bg-indigo-50 text-indigo-700">
                      {doc.media_type === "Vídeo Técnico/Aula" ? (
                        <Video className="w-3 h-3" />
                      ) : (
                        <FileText className="w-3 h-3" />
                      )}
                      {doc.media_type}
                    </span>
                    <span className="text-xs font-medium px-2.5 py-0.5 rounded-full bg-slate-100 text-slate-700">
                      {doc.category}
                    </span>
                    {doc.databricks_synced_at && (
                      <span
                        className="inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700"
                        title={`Sincronizado em ${doc.databricks_synced_at}`}
                      >
                        <Cloud className="w-3 h-3" /> Databricks
                      </span>
                    )}
                  </div>
                  <button
                    type="button"
                    onClick={(e) => handleDelete(e, doc.id, doc.title)}
                    className="p-1.5 text-slate-400 hover:text-red-600 rounded-lg hover:bg-red-50 transition"
                    title="Excluir documento"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>

                <h3 className="text-base font-semibold text-slate-900 mt-3 line-clamp-1">{doc.title}</h3>
                <p className="text-sm text-slate-600 mt-1.5 line-clamp-2">{doc.summary_short}</p>
              </div>

              <div className="pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
                <div className="flex items-center gap-3">
                  <span className="inline-flex items-center gap-1">
                    <Clock className="w-3.5 h-3.5" /> {doc.duration_formatted}
                  </span>
                  <span className="inline-flex items-center gap-1">
                    <Calendar className="w-3.5 h-3.5" /> {doc.created_at.slice(0, 10)}
                  </span>
                </div>
                <div className="flex items-center gap-2.5 font-medium">
                  <span className="text-slate-700">{doc.decisions_count} dec.</span>
                  <span className="text-amber-700">{doc.pendings_count} pend.</span>
                  <span className="inline-flex items-center gap-1 text-indigo-700">
                    <CheckSquare className="w-3.5 h-3.5" />
                    {doc.action_items_done}/{doc.action_items_count}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
