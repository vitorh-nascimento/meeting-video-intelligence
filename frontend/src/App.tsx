import React, { useEffect, useState } from "react";
import { BookOpen, PlusCircle, Settings, Sparkles } from "lucide-react";
import { api } from "./api/client";
import { DocumentDetail } from "./components/DocumentDetail";
import { IngestPanel } from "./components/IngestPanel";
import { LibraryView } from "./components/LibraryView";
import { SettingsView } from "./components/SettingsView";

type ViewKey = "ingest" | "library" | "detail" | "settings";

export default function App() {
  const [view, setView] = useState<ViewKey>("ingest");
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const [categories, setCategories] = useState<string[]>([]);

  useEffect(() => {
    api
      .getSettings()
      .then((s) => setCategories(s.categories || []))
      .catch(() => {});
  }, []);

  const openDocument = (docId: string) => {
    setSelectedDocId(docId);
    setView("detail");
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-50">
      {/* Header */}
      <header className="bg-slate-900 text-white border-b border-slate-800 sticky top-0 z-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-4">
          <div
            onClick={() => setView("library")}
            className="flex items-center gap-2.5 cursor-pointer"
          >
            <div className="w-9 h-9 rounded-xl bg-indigo-600 flex items-center justify-center shadow-sm">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-sm sm:text-base font-bold tracking-tight leading-none">
                Meeting &amp; Video Intelligence
              </h1>
              <p className="text-[11px] text-slate-400 mt-0.5">
                Transcrição Multimodal • Extração LLM • Databricks Lakehouse POC
              </p>
            </div>
          </div>

          <nav className="flex items-center gap-1.5">
            <button
              type="button"
              onClick={() => setView("ingest")}
              className={`px-3.5 py-2 rounded-xl text-xs sm:text-sm font-medium flex items-center gap-1.5 transition ${
                view === "ingest"
                  ? "bg-indigo-600 text-white"
                  : "text-slate-300 hover:text-white hover:bg-slate-800"
              }`}
            >
              <PlusCircle className="w-4 h-4" />
              <span className="hidden sm:inline">Nova Ingestão</span>
            </button>
            <button
              type="button"
              onClick={() => setView("library")}
              className={`px-3.5 py-2 rounded-xl text-xs sm:text-sm font-medium flex items-center gap-1.5 transition ${
                view === "library" || view === "detail"
                  ? "bg-indigo-600 text-white"
                  : "text-slate-300 hover:text-white hover:bg-slate-800"
              }`}
            >
              <BookOpen className="w-4 h-4" />
              <span className="hidden sm:inline">Biblioteca</span>
            </button>
            <button
              type="button"
              onClick={() => setView("settings")}
              className={`px-3.5 py-2 rounded-xl text-xs sm:text-sm font-medium flex items-center gap-1.5 transition ${
                view === "settings"
                  ? "bg-indigo-600 text-white"
                  : "text-slate-300 hover:text-white hover:bg-slate-800"
              }`}
            >
              <Settings className="w-4 h-4" />
              <span className="hidden sm:inline">Configurações</span>
            </button>
          </nav>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-6">
        {view === "ingest" && <IngestPanel onCompleted={openDocument} />}
        {view === "library" && (
          <LibraryView categories={categories} onSelectDocument={openDocument} />
        )}
        {view === "detail" && selectedDocId && (
          <DocumentDetail docId={selectedDocId} onBack={() => setView("library")} />
        )}
        {view === "settings" && (
          <SettingsView onSaved={(s) => setCategories(s.categories || [])} />
        )}
      </main>
    </div>
  );
}
