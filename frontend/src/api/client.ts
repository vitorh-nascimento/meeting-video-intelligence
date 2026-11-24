import type {
  ActionItem,
  AppSettings,
  Capabilities,
  ChatCitation,
  DocumentDetailData,
  DocumentSummary,
  JobStatus,
  PendingItem,
} from "../types";

const API_BASE = import.meta.env.VITE_API_BASE || "";

async function handleResponse<T>(resp: Response): Promise<T> {
  if (!resp.ok) {
    let detail = `Erro HTTP ${resp.status}`;
    try {
      const data = await resp.json();
      if (data?.detail) detail = String(data.detail);
    } catch {
      const text = await resp.text();
      if (text) detail = text;
    }
    throw new Error(detail);
  }
  return resp.json() as Promise<T>;
}

export const api = {
  async ingestFile(params: {
    file: File;
    title?: string;
    template: string;
    language?: string;
    pushToDatabricks?: boolean;
    runDatabricksPipeline?: boolean;
  }): Promise<JobStatus> {
    const fd = new FormData();
    fd.append("file", params.file);
    if (params.title) fd.append("title", params.title);
    fd.append("template", params.template);
    if (params.language) fd.append("language", params.language);
    fd.append("push_to_databricks", String(Boolean(params.pushToDatabricks)));
    fd.append("run_databricks_pipeline", String(Boolean(params.runDatabricksPipeline)));

    const resp = await fetch(`${API_BASE}/api/ingest/file`, {
      method: "POST",
      body: fd,
    });
    return handleResponse<JobStatus>(resp);
  },

  async ingestUrl(params: {
    url: string;
    title?: string;
    template: string;
    force_ai_transcription: boolean;
    language?: string;
    push_to_databricks?: boolean;
    run_databricks_pipeline?: boolean;
  }): Promise<JobStatus> {
    const resp = await fetch(`${API_BASE}/api/ingest/url`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(params),
    });
    return handleResponse<JobStatus>(resp);
  },

  async ingestText(params: {
    text: string;
    title: string;
    format_hint: "auto" | "srt" | "vtt" | "txt" | "json";
    template: string;
    language?: string;
  }): Promise<JobStatus> {
    const resp = await fetch(`${API_BASE}/api/ingest/text`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(params),
    });
    return handleResponse<JobStatus>(resp);
  },

  async getJob(jobId: string): Promise<JobStatus> {
    const resp = await fetch(`${API_BASE}/api/jobs/${jobId}`);
    return handleResponse<JobStatus>(resp);
  },

  async listJobs(): Promise<JobStatus[]> {
    const resp = await fetch(`${API_BASE}/api/jobs`);
    return handleResponse<JobStatus[]>(resp);
  },

  async listDocuments(filters?: {
    search?: string;
    media_type?: string;
    category?: string;
    date_from?: string;
    date_to?: string;
  }): Promise<DocumentSummary[]> {
    const qs = new URLSearchParams();
    if (filters?.search) qs.set("search", filters.search);
    if (filters?.media_type && filters.media_type !== "Todos") qs.set("media_type", filters.media_type);
    if (filters?.category && filters.category !== "Todas") qs.set("category", filters.category);
    if (filters?.date_from) qs.set("date_from", filters.date_from);
    if (filters?.date_to) qs.set("date_to", filters.date_to);
    const suffix = qs.toString() ? `?${qs.toString()}` : "";
    const resp = await fetch(`${API_BASE}/api/documents${suffix}`);
    return handleResponse<DocumentSummary[]>(resp);
  },

  async getDocument(docId: string): Promise<DocumentDetailData> {
    const resp = await fetch(`${API_BASE}/api/documents/${docId}`);
    return handleResponse<DocumentDetailData>(resp);
  },

  async deleteDocument(docId: string): Promise<void> {
    const resp = await fetch(`${API_BASE}/api/documents/${docId}`, { method: "DELETE" });
    await handleResponse(resp);
  },

  async updateActionItem(docId: string, itemId: number, updates: Partial<ActionItem>): Promise<ActionItem> {
    const resp = await fetch(`${API_BASE}/api/documents/${docId}/action-items/${itemId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(updates),
    });
    return handleResponse<ActionItem>(resp);
  },

  async updatePendingItem(docId: string, itemId: number, updates: Partial<PendingItem>): Promise<PendingItem> {
    const resp = await fetch(`${API_BASE}/api/documents/${docId}/pendings/${itemId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(updates),
    });
    return handleResponse<PendingItem>(resp);
  },

  async askQuestion(
    docId: string,
    question: string
  ): Promise<{ answer: string; citations: ChatCitation[]; provider: string }> {
    const resp = await fetch(`${API_BASE}/api/documents/${docId}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    return handleResponse(resp);
  },

  getExportUrl(docId: string, fmt: "srt" | "txt" | "md" | "json"): string {
    return `${API_BASE}/api/documents/${docId}/export/${fmt}`;
  },

  async pushToDatabricks(docId: string, runPipeline: boolean): Promise<Record<string, unknown>> {
    const resp = await fetch(`${API_BASE}/api/documents/${docId}/push-databricks`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ run_pipeline: runPipeline }),
    });
    return handleResponse(resp);
  },

  async reanalyzeDocument(docId: string, template: string): Promise<DocumentDetailData> {
    const resp = await fetch(`${API_BASE}/api/documents/${docId}/reanalyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ template }),
    });
    return handleResponse<DocumentDetailData>(resp);
  },

  async getSettings(): Promise<AppSettings> {
    const resp = await fetch(`${API_BASE}/api/settings`);
    return handleResponse<AppSettings>(resp);
  },

  async updateSettings(settings: Partial<AppSettings>): Promise<AppSettings> {
    const resp = await fetch(`${API_BASE}/api/settings`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ settings }),
    });
    return handleResponse<AppSettings>(resp);
  },

  async getCapabilities(): Promise<Capabilities> {
    const resp = await fetch(`${API_BASE}/api/settings/capabilities`);
    return handleResponse<Capabilities>(resp);
  },
};
