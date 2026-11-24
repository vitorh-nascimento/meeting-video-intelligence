export type ExtractionTemplate =
  | "Reunião Corporativa"
  | "Aula/Vídeo Técnico"
  | "Discovery/Cliente"
  | "Sessão Legislativa / Política";

export interface JobStatus {
  id: string;
  status: "running" | "completed" | "failed" | string;
  stage: string;
  progress: number;
  message: string;
  source_type: string;
  source_ref: string;
  title: string;
  document_id?: string | null;
  error?: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentSummary {
  id: string;
  title: string;
  source_type: string;
  source_ref: string;
  media_type: string;
  template: string;
  category: string;
  language: string;
  duration_seconds: number;
  duration_formatted: string;
  word_count: number;
  transcriber_provider: string;
  llm_provider: string;
  summary_short: string;
  databricks_synced_at?: string | null;
  created_at: string;
  updated_at: string;
  decisions_count: number;
  pendings_count: number;
  action_items_count: number;
  action_items_done: number;
}

export interface TranscriptSegment {
  index: number;
  inicio: string;
  fim: string;
  start_seconds: number;
  end_seconds: number;
  speaker?: string | null;
  texto: string;
}

export interface DecisionItem {
  id: number;
  decisao: string;
  contexto: string;
  impacto: string;
  participantes_envolvidos: string[];
}

export interface PendingItem {
  id: number;
  descricao: string;
  responsavel_ou_area: string;
  impacto: string;
  status: string;
}

export interface ActionItem {
  id: number;
  tarefa: string;
  responsavel: string;
  prazo: string;
  prioridade: string;
  status: string;
}

export interface KeyKnowledge {
  insights: string[];
  aprendizados_tecnicos: string[];
  metricas_citadas: string[];
  riscos: string[];
  ferramentas_tecnologias: string[];
}

export interface ChatCitation {
  timestamp: string;
  trecho: string;
}

export interface ChatMessage {
  id?: number;
  role: "user" | "assistant";
  content: string;
  citations: ChatCitation[];
  created_at?: string;
}

export interface DocumentDetailData extends DocumentSummary {
  transcript_format: string;
  raw_srt: string;
  clean_text: string;
  segments: TranscriptSegment[];
  summary_bullets: string[];
  knowledge: KeyKnowledge;
  ata_markdown: string;
  analysis: Record<string, unknown>;
  databricks_volume_path?: string | null;
  decisions: DecisionItem[];
  pendings: PendingItem[];
  action_items: ActionItem[];
  chat_history: ChatMessage[];
}

export interface Capabilities {
  ffmpeg_available: boolean;
  yt_dlp_available: boolean;
  youtube_transcript_api_available: boolean;
  faster_whisper_available: boolean;
  databricks_cli_available: boolean;
}

export interface AppSettings {
  transcriber_provider: string;
  gemini_transcription_model: string;
  audio_chunk_minutes: number;
  whisper_model_size: string;
  whisper_device: string;
  whisper_compute_type: string;
  llm_provider: string;
  gemini_api_key: string;
  gemini_api_key_configured?: boolean;
  gemini_llm_model: string;
  openai_api_key: string;
  openai_api_key_configured?: boolean;
  openai_model: string;
  openai_base_url: string;
  azure_openai_endpoint: string;
  azure_openai_api_key: string;
  azure_openai_api_key_configured?: boolean;
  azure_openai_deployment: string;
  azure_openai_api_version: string;
  ollama_base_url: string;
  ollama_model: string;
  databricks_host: string;
  databricks_token: string;
  databricks_token_configured?: boolean;
  databricks_profile: string;
  databricks_catalog: string;
  databricks_schema: string;
  databricks_volume_name: string;
  databricks_pipeline_id: string;
  databricks_llm_endpoint: string;
  glossary_terms: string[];
  categories: string[];
}
