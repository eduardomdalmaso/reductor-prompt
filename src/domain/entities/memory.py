from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone


class ProvenanceType(str, Enum):
    """Categoria de proveniência do conhecimento."""
    THEORETICAL = "theoretical"      # Derivado de literatura, livros e RFCs
    EMPIRICAL = "empirical"          # Medições reais, benchmarks e execuções de projetos
    HUMAN_CURATED = "human_curated"  # Decisões arquiteturais e curadoria humana explícita


class EvidenceStatus(str, Enum):
    """Ciclo de vida e validade temporal da evidência."""
    VALID = "valid"                            # Evidência atual e confirmada
    STALE = "stale"                            # Fonte, runtime ou hardware sofreram alterações
    INVALID = "invalid"                        # Incompatibilidade ou refutação comprovada
    PENDING_VALIDATION = "pending_validation"  # Requer novo teste ou aferição


@dataclass
class MemoryEpisode:
    """Entidade que representa uma memória episódica ou evidência indexada no Cérebro."""
    id: str
    query: str
    response: str
    sources: List[Dict[str, Any]] = field(default_factory=list)
    topic: Optional[str] = None
    tokens_used: int = 0
    tokens_saved: int = 0
    reduction_percentage: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    confidence_score: float = 1.0
    hit_count: int = 0

    # Dimensões de Proveniência & Evidência (v2.0)
    provenance: ProvenanceType = ProvenanceType.THEORETICAL
    status: EvidenceStatus = EvidenceStatus.VALID
    schema_version: str = "2.0"
    project_source: Optional[str] = None
    commit_hash: Optional[str] = None
    experiment_id: Optional[str] = None
    measured_at: Optional[str] = None
    environment_context: Dict[str, Any] = field(default_factory=dict)
    source_hashes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serializa o episódio preservando todos os metadados de domínio."""
        return {
            "id": self.id,
            "query": self.query,
            "response": self.response,
            "sources": self.sources,
            "topic": self.topic,
            "tokens_used": self.tokens_used,
            "tokens_saved": self.tokens_saved,
            "reduction_percentage": self.reduction_percentage,
            "created_at": self.created_at,
            "confidence_score": self.confidence_score,
            "hit_count": self.hit_count,
            "provenance": self.provenance.value if isinstance(self.provenance, ProvenanceType) else self.provenance,
            "status": self.status.value if isinstance(self.status, EvidenceStatus) else self.status,
            "schema_version": self.schema_version,
            "project_source": self.project_source,
            "commit_hash": self.commit_hash,
            "experiment_id": self.experiment_id,
            "measured_at": self.measured_at,
            "environment_context": self.environment_context,
            "source_hashes": self.source_hashes
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryEpisode":
        """Reconstrói a entidade com retrocompatibilidade total com esquemas legados (v1.0)."""
        raw_prov = data.get("provenance", ProvenanceType.THEORETICAL.value)
        try:
            provenance = ProvenanceType(raw_prov)
        except ValueError:
            provenance = ProvenanceType.THEORETICAL

        raw_status = data.get("status", EvidenceStatus.VALID.value)
        try:
            status = EvidenceStatus(raw_status)
        except ValueError:
            status = EvidenceStatus.VALID

        return cls(
            id=data["id"],
            query=data["query"],
            response=data["response"],
            sources=data.get("sources", []),
            topic=data.get("topic"),
            tokens_used=data.get("tokens_used", 0),
            tokens_saved=data.get("tokens_saved", 0),
            reduction_percentage=data.get("reduction_percentage", 0.0),
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
            confidence_score=data.get("confidence_score", 1.0),
            hit_count=data.get("hit_count", 0),
            provenance=provenance,
            status=status,
            schema_version=data.get("schema_version", "1.0"),
            project_source=data.get("project_source"),
            commit_hash=data.get("commit_hash"),
            experiment_id=data.get("experiment_id"),
            measured_at=data.get("measured_at"),
            environment_context=data.get("environment_context", {}),
            source_hashes=data.get("source_hashes", [])
        )
