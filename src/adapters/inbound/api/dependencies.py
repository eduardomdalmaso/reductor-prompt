import os
import secrets
from typing import Any, Dict, Optional
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from src.adapters.outbound.embeddings.embedding_adapters import ResilientEmbeddingAdapter
from src.adapters.outbound.llm.generation_queue import GenerationQueue
from src.adapters.outbound.llm.llm_adapters import LLMFactory
from src.adapters.outbound.memory.chroma_episodic_memory import ChromaEpisodicMemoryAdapter
from src.adapters.outbound.vector_store.chroma_vector_store import ChromaVectorStoreAdapter
from src.application.services.system_telemetry_service import telemetry_service
from src.application.use_cases.ingest_evidence_use_case import IngestEvidenceUseCase
from src.application.use_cases.make_decision_use_case import MakeDecisionUseCase
from src.config.settings import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_auth = HTTPBearer(auto_error=False)

generation_queue = GenerationQueue(
    max_concurrent=int(os.getenv("LLM_MAX_CONCURRENT", "1")),
    max_pending=int(os.getenv("LLM_MAX_PENDING_QUEUE", "12")),
    acquire_timeout_s=float(os.getenv("LLM_QUEUE_TIMEOUT_S", "45.0")),
)


async def verify_auth(
    api_key: Optional[str] = Security(api_key_header),
    bearer: Optional[HTTPAuthorizationCredentials] = Security(bearer_auth),
):
    """Verifica autenticação se API_SECURITY_KEY estiver configurada no .env."""
    required_key = settings.API_SECURITY_KEY
    if not required_key:
        return True

    token = api_key or (bearer.credentials if bearer else None)
    if not token or not secrets.compare_digest(token, required_key):
        telemetry_service.log("WARNING", "SecurityGuard", "Tentativa de acesso não autorizada a endpoint protegido.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Acesso não autorizado. Forneça um X-API-Key ou Bearer Token válido.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return True


def get_evidence_use_case() -> IngestEvidenceUseCase:
    return IngestEvidenceUseCase(
        memory_port=ChromaEpisodicMemoryAdapter(),
        embedding_port=ResilientEmbeddingAdapter(),
    )


def get_decision_use_case() -> MakeDecisionUseCase:
    return MakeDecisionUseCase(
        embedding_port=ResilientEmbeddingAdapter(),
        vector_store=ChromaVectorStoreAdapter(),
        memory_port=ChromaEpisodicMemoryAdapter(),
        llm_port=LLMFactory.create(),
    )


class LLMConfigDTO(BaseModel):
    provider: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = None
    enabled: Optional[bool] = None


class LLMToggleDTO(BaseModel):
    enabled: bool


class UnloadVRAMDTO(BaseModel):
    model_name: Optional[str] = None


class MCPCallDTO(BaseModel):
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)


class FetchBooksRequestDTO(BaseModel):
    urls: str
    ingest_after: bool = True


class TeachBrainDTO(BaseModel):
    query: str = Field(..., description="Pergunta ou problema chave")
    insight: str = Field(..., description="Resposta lapidada ou código canônico")
    topic: Optional[str] = Field(default=None, description="Tópico ou categoria do conhecimento")
