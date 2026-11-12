from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class IngestEvidenceRequestDTO(BaseModel):
    """Payload de entrada para recebimento remoto de evidências e benchmarks."""
    query: str = Field(..., min_length=3, max_length=1000, description="Dúvida, hipótese ou cenário avaliado")
    response: str = Field(..., min_length=5, description="Resultado, medição ou síntese do benchmark")
    project_source: str = Field(..., min_length=2, max_length=100, description="Projeto emissor (ex: 'HydraStream')")
    experiment_id: str = Field(..., min_length=2, max_length=120, description="Identificador único do experimento")
    commit_hash: str = Field(..., min_length=4, max_length=64, description="Hash do commit testado")
    provenance: Optional[str] = Field(default="empirical", description="Categoria ('empirical', 'theoretical', 'human_curated')")
    status: Optional[str] = Field(default="valid", description="Status da evidência ('valid', 'stale', 'invalid')")
    measured_at: Optional[str] = Field(default=None, description="Timestamp ISO da medição")
    environment_context: Dict[str, Any] = Field(default_factory=dict, description="Hardware, SO, parâmetros de execução")
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Confiança na medição")
    topic: Optional[str] = Field(default=None, description="Tópico ou subsistema")
    source_hashes: List[str] = Field(default_factory=list, description="Hashes SHA-256 das fontes associadas")


class IngestEvidenceResponseDTO(BaseModel):
    """Resposta padronizada após ingestão de evidência."""
    id: str
    experiment_id: str
    project_source: str
    content_hash: str
    status: str
    is_created: bool
    message: str
