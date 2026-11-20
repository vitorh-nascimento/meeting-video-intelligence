"""
Contratos Pydantic v2 para validação estrita da saída da LLM, API REST e CLI.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class MediaType(str, Enum):
    REUNIAO = "Reunião"
    VIDEO_TECNICO = "Vídeo Técnico/Aula"
    AUDIO_PODCAST = "Áudio/Podcast"
    ENTREVISTA = "Entrevista"
    OUTRO = "Outro"


class ExtractionTemplate(str, Enum):
    REUNIAO_CORPORATIVA = "Reunião Corporativa"
    AULA_VIDEO_TECNICO = "Aula/Vídeo Técnico"
    DISCOVERY_CLIENTE = "Discovery/Cliente"


class PriorityLevel(str, Enum):
    ALTA = "Alta"
    MEDIA = "Média"
    BAIXA = "Baixa"


class ItemStatus(str, Enum):
    PENDENTE = "Pendente"
    EM_ANDAMENTO = "Em Andamento"
    CONCLUIDO = "Concluído"
    BLOQUEADO = "Bloqueado"


class JobStage(str, Enum):
    RECEBIDO = "Recebido"
    EXTRAINDO_AUDIO = "Extraindo Áudio"
    TRANSCREVENDO = "Transcrevendo"
    ANALISANDO_LLM = "Analisando com LLM"
    CONCLUIDO = "Concluído"
    ERRO = "Erro"


class TranscriptSegment(BaseModel):
    index: int = 1
    inicio: str = "00:00:00,000"
    fim: str = "00:00:00,000"
    start_seconds: float = 0.0
    end_seconds: float = 0.0
    speaker: Optional[str] = None
    texto: str = ""


class DecisionItem(BaseModel):
    id: Optional[int] = None
    decisao: str = Field(..., min_length=1)
    contexto: str = ""
    impacto: str = ""
    participantes_envolvidos: List[str] = Field(default_factory=list)

    @field_validator("participantes_envolvidos", mode="before")
    @classmethod
    def coerce_participants(cls, v: Any) -> List[str]:
        if v is None:
            return []
        if isinstance(v, str):
            return [x.strip() for x in v.split(",") if x.strip()]
        return [str(x).strip() for x in v if str(x).strip()]


class PendingItem(BaseModel):
    id: Optional[int] = None
    descricao: str = Field(..., min_length=1)
    responsavel_ou_area: str = "A definir"
    impacto: str = "Médio"
    status: str = "Pendente"


class ActionItem(BaseModel):
    id: Optional[int] = None
    tarefa: str = Field(..., min_length=1)
    responsavel: str = "A definir"
    prazo: str = "A definir"
    prioridade: str = "Média"
    status: str = "Pendente"

    @field_validator("prioridade", mode="before")
    @classmethod
    def normalize_priority(cls, v: Any) -> str:
        s = str(v or "Média").strip().lower()
        if s in {"alta", "high", "urgente", "crítica", "critica"}:
            return "Alta"
        if s in {"baixa", "low"}:
            return "Baixa"
        return "Média"

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, v: Any) -> str:
        s = str(v or "Pendente").strip().lower()
        if s in {"concluído", "concluido", "done", "fechado", "resolvido"}:
            return "Concluído"
        if s in {"em andamento", "in progress", "andamento"}:
            return "Em Andamento"
        if s in {"bloqueado", "blocked"}:
            return "Bloqueado"
        return "Pendente"


class KeyKnowledge(BaseModel):
    insights: List[str] = Field(default_factory=list)
    aprendizados_tecnicos: List[str] = Field(default_factory=list)
    metricas_citadas: List[str] = Field(default_factory=list)
    riscos: List[str] = Field(default_factory=list)
    ferramentas_tecnologias: List[str] = Field(default_factory=list)


class ExecutiveSummary(BaseModel):
    resumo_curto: str = ""
    topicos_principais: List[str] = Field(default_factory=list)


class DocumentMetadata(BaseModel):
    titulo: str = "Sem título"
    tipo_midia: str = MediaType.REUNIAO.value
    idioma: str = "pt-BR"
    duracao_estimada_segundos: int = 0
    duracao_formatada: str = "00:00:00"
    contagem_palavras: int = 0
    categoria_tematica: str = "Geral / Outros"


class StructuredAnalysis(BaseModel):
    """Schema validado de saída da camada de sumarização e extração LLM."""

    metadados: DocumentMetadata
    resumo_executivo: ExecutiveSummary
    decisoes: List[DecisionItem] = Field(default_factory=list)
    pendencias: List[PendingItem] = Field(default_factory=list)
    action_items: List[ActionItem] = Field(default_factory=list)
    informacoes_chave: KeyKnowledge = Field(default_factory=KeyKnowledge)
    ata_markdown: str = ""


# --- Request / Response models da API ---


class IngestUrlRequest(BaseModel):
    url: str = Field(..., min_length=5)
    title: Optional[str] = None
    template: str = ExtractionTemplate.REUNIAO_CORPORATIVA.value
    force_ai_transcription: bool = False
    language: Optional[str] = None
    push_to_databricks: bool = False
    run_databricks_pipeline: bool = False


class IngestTextRequest(BaseModel):
    text: str = Field(..., min_length=10)
    title: str = "Transcrição Colada"
    format_hint: Literal["auto", "srt", "vtt", "txt", "json"] = "auto"
    template: str = ExtractionTemplate.REUNIAO_CORPORATIVA.value
    language: Optional[str] = "pt-BR"


class JobResponse(BaseModel):
    id: str
    status: str
    stage: str
    progress: int
    message: str
    source_type: str
    source_ref: str
    title: str
    document_id: Optional[str] = None
    error: Optional[str] = None
    created_at: str
    updated_at: str


class ActionItemUpdateRequest(BaseModel):
    status: Optional[str] = None
    responsavel: Optional[str] = None
    prazo: Optional[str] = None
    prioridade: Optional[str] = None
    tarefa: Optional[str] = None


class PendingUpdateRequest(BaseModel):
    status: Optional[str] = None
    responsavel_ou_area: Optional[str] = None
    impacto: Optional[str] = None
    descricao: Optional[str] = None


class ChatQuestionRequest(BaseModel):
    question: str = Field(..., min_length=2)


class ChatCitation(BaseModel):
    timestamp: str
    trecho: str


class ChatAnswerResponse(BaseModel):
    answer: str
    citations: List[ChatCitation] = Field(default_factory=list)
    provider: str = "heuristic"


class DatabricksPushRequest(BaseModel):
    run_pipeline: bool = False


class SettingsUpdateRequest(BaseModel):
    settings: Dict[str, Any]
