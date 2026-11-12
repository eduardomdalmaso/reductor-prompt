from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class MakeDecisionRequestDTO(BaseModel):
    """Payload de entrada para requisição de decisão de engenharia."""
    query: str = Field(..., min_length=5, description="Pergunta ou decisão técnica a avaliar")
    target_hardware: Optional[str] = Field(default=None, description="Hardware alvo (ex: 'RTX 5090')")
    target_commit: Optional[str] = Field(default=None, description="Versão de código alvo")
    book_filter: Optional[str] = Field(default=None, description="Filtro de livro para fundamentação teórica")
    max_tokens: int = Field(default=2500, description="Limite de tokens do contexto")
    llm_synthesis: bool = Field(default=True, description="Se deve gerar recomendação explicativa com LLM")


class DecisionResponseDTO(BaseModel):
    """Resposta com decisão de engenharia formal e rastreável."""
    decision_id: str
    query: str
    verdict: str
    recommendation: str
    policy_version: str
    completeness_score: float
    relevance_score: float
    evidence_count: int
    used_commit_hashes: List[str]
    used_source_books: List[str]
    limitations: List[str]
    next_validation_steps: List[str]
    comparative_summary: Optional[str] = None
    created_at: str
