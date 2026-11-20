import React, { useState } from "react";
import { Loader2, MessageSquare, Send, Clock } from "lucide-react";
import { api } from "../api/client";
import type { ChatMessage } from "../types";

interface TranscriptChatProps {
  docId: string;
  initialHistory: ChatMessage[];
  onJumpToTimestamp?: (timestamp: string) => void;
}

export const TranscriptChat: React.FC<TranscriptChatProps> = ({
  docId,
  initialHistory,
  onJumpToTimestamp,
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>(initialHistory);
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleAsk = async (e: React.FormEvent) => {
    e.preventDefault();
    const q = question.trim();
    if (!q || loading) return;

    setError(null);
    setQuestion("");
    setMessages((prev) => [...prev, { role: "user", content: q, citations: [] }]);
    setLoading(true);
    try {
      const resp = await api.askQuestion(docId, q);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: resp.answer,
          citations: resp.citations || [],
        },
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao consultar IA.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm flex flex-col h-[560px]">
      <div className="px-4 py-3.5 border-b border-slate-100 flex items-center gap-2">
        <MessageSquare className="w-4 h-4 text-indigo-600" />
        <div>
          <h3 className="text-sm font-semibold text-slate-900">Chat Q&amp;A sobre a Transcrição</h3>
          <p className="text-xs text-slate-500">Pergunte detalhes e receba citações com timestamp</p>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.length === 0 ? (
          <div className="text-center py-10 px-4">
            <p className="text-sm font-medium text-slate-600">Faça uma pergunta sobre este conteúdo</p>
            <div className="mt-3 flex flex-wrap justify-center gap-2">
              {[
                "Quais foram os principais riscos levantados?",
                "Quem ficou responsável pelas entregas?",
                "Quais ferramentas ou números foram citados?",
              ].map((suggestion) => (
                <button
                  key={suggestion}
                  type="button"
                  onClick={() => setQuestion(suggestion)}
                  className="text-xs px-3 py-1.5 rounded-full bg-slate-100 hover:bg-indigo-50 hover:text-indigo-700 text-slate-600 transition"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((msg, i) => (
            <div
              key={i}
              className={`flex flex-col ${msg.role === "user" ? "items-end" : "items-start"}`}
            >
              <div
                className={`max-w-[90%] rounded-2xl px-3.5 py-2.5 text-sm whitespace-pre-wrap ${
                  msg.role === "user"
                    ? "bg-indigo-600 text-white"
                    : "bg-slate-100 text-slate-800"
                }`}
              >
                {msg.content}
              </div>
              {msg.citations && msg.citations.length > 0 && (
                <div className="mt-2 space-y-1.5 max-w-[90%]">
                  {msg.citations.map((cit, idx) => (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => onJumpToTimestamp?.(cit.timestamp)}
                      className="w-full text-left text-xs bg-indigo-50/70 hover:bg-indigo-100 border border-indigo-200/70 rounded-xl px-3 py-2 transition flex items-start gap-2"
                    >
                      <span className="inline-flex items-center gap-1 font-mono font-semibold text-indigo-700 shrink-0">
                        <Clock className="w-3 h-3" /> {cit.timestamp}
                      </span>
                      <span className="text-slate-700 line-clamp-2">{cit.trecho}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          ))
        )}
        {loading && (
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <Loader2 className="w-4 h-4 animate-spin text-indigo-600" />
            Consultando transcrição...
          </div>
        )}
        {error && <div className="text-xs text-red-600 bg-red-50 rounded-lg p-2.5">{error}</div>}
      </div>

      <form onSubmit={handleAsk} className="p-3 border-t border-slate-100 flex gap-2">
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ex.: O que foi decidido sobre prazo e custos?"
          className="flex-1 rounded-xl border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
        <button
          type="submit"
          disabled={loading || !question.trim()}
          className="px-3.5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white transition"
        >
          <Send className="w-4 h-4" />
        </button>
      </form>
    </div>
  );
};
