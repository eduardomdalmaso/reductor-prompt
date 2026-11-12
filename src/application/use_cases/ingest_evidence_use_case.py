import json
import hashlib
import logging
import threading
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from src.domain.entities.memory import MemoryEpisode, ProvenanceType, EvidenceStatus
from src.domain.ports.inbound import IIngestEvidenceUseCase, IngestEvidenceCommand
from src.domain.ports.outbound import IEpisodicMemoryPort, IEmbeddingPort
from src.domain.exceptions.exceptions import EvidenceConflictException

logger = logging.getLogger(__name__)


def canonical_hash(payload: Dict[str, Any]) -> str:
    """Gera hash SHA-256 canônico determinístico com chaves ordenadas."""
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_evidence_id(project_source: str, experiment_id: str) -> str:
    """Gera identificador estável único para o par (project_source, experiment_id)."""
    identity = f"{project_source.strip().lower()}:{experiment_id.strip()}"
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24]


class IngestEvidenceUseCase(IIngestEvidenceUseCase):
    """Caso de uso de ingestão idempotente de evidências empíricas e benchmarks."""

    def __init__(
        self,
        memory_port: IEpisodicMemoryPort,
        embedding_port: IEmbeddingPort
    ):
        self.memory_port = memory_port
        self.embedding_port = embedding_port
        self._lock = threading.Lock()
        self._experiment_locks: Dict[str, threading.Lock] = {}

    def _get_experiment_lock(self, evidence_id: str) -> threading.Lock:
        with self._lock:
            if evidence_id not in self._experiment_locks:
                self._experiment_locks[evidence_id] = threading.Lock()
            return self._experiment_locks[evidence_id]

    def execute(self, command: IngestEvidenceCommand) -> MemoryEpisode:
        evidence_id = build_evidence_id(command.project_source, command.experiment_id)

        content_payload = {
            "query": command.query.strip(),
            "response": command.response.strip(),
            "commit_hash": command.commit_hash.strip(),
            "environment_context": command.environment_context,
            "project_source": command.project_source.strip(),
            "experiment_id": command.experiment_id.strip(),
        }
        content_hash = canonical_hash(content_payload)

        # Exclusão mútua local por evidence_id para evitar corrida em ingestões concorrentes
        with self._get_experiment_lock(evidence_id):
            existing = self.memory_port.get_episode(evidence_id)
            if existing:
                if existing.content_hash == content_hash:
                    logger.info(f"Evidência empírica idêntica já existente (idempotência): {evidence_id}")
                    return existing
                logger.warning(f"Conflito detectado no experimento '{command.experiment_id}' ({evidence_id})")
                raise EvidenceConflictException(
                    command.experiment_id,
                    f"Experimento já registrado com conteúdo diferente (hash existente: {existing.content_hash[:10]}... vs novo: {content_hash[:10]}...)"
                )

            # Vetorização semântica executada SOMENTE para evidências inéditas
            embedding = self.embedding_port.embed_text(command.query)

            episode = MemoryEpisode(
                id=evidence_id,
                query=command.query.strip(),
                response=command.response.strip(),
                sources=[],
                topic=command.topic or f"Benchmark: {command.project_source}",
                tokens_used=len(command.response.split()) * 2,
                tokens_saved=0,
                reduction_percentage=0.0,
                created_at=datetime.now(timezone.utc).isoformat(),
                confidence_score=command.confidence_score,
                hit_count=0,
                provenance=command.provenance,
                status=command.status,
                schema_version="2.0",
                project_source=command.project_source.strip(),
                commit_hash=command.commit_hash.strip(),
                experiment_id=command.experiment_id.strip(),
                content_hash=content_hash,
                measured_at=command.measured_at or datetime.now(timezone.utc).isoformat(),
                environment_context=command.environment_context,
                source_hashes=command.source_hashes
            )

            self.memory_port.save_episode(episode, embedding)
            logger.info(f"✔ Evidência empírica gravada com sucesso: {evidence_id} [{command.project_source}]")
            return episode
