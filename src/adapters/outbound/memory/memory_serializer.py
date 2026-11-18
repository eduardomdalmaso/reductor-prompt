import json
from typing import Any, Dict, Optional

from src.domain.entities.memory import EvidenceStatus, MemoryEpisode, ProvenanceType


def serialize_metadata(episode: MemoryEpisode) -> Dict[str, Any]:
    """Serializa metadados para tipos primitivos suportados pelo ChromaDB."""
    prov_val = episode.provenance.value if isinstance(episode.provenance, ProvenanceType) else str(episode.provenance)
    status_val = episode.status.value if isinstance(episode.status, EvidenceStatus) else str(episode.status)
    return {
        "query": episode.query,
        "topic": episode.topic or "",
        "tokens_used": int(episode.tokens_used),
        "tokens_saved": int(episode.tokens_saved),
        "reduction_percentage": float(episode.reduction_percentage),
        "created_at": episode.created_at,
        "hit_count": int(episode.hit_count),
        "provenance": prov_val,
        "status": status_val,
        "schema_version": episode.schema_version,
        "project_source": episode.project_source or "",
        "commit_hash": episode.commit_hash or "",
        "experiment_id": episode.experiment_id or "",
        "content_hash": episode.content_hash or "",
        "measured_at": episode.measured_at or "",
        "sources_json": json.dumps(episode.sources, ensure_ascii=False),
        "source_hashes_json": json.dumps(episode.source_hashes, ensure_ascii=False),
        "environment_context_json": json.dumps(episode.environment_context, sort_keys=True, ensure_ascii=False),
    }


def deserialize_metadata(ep_id: str, doc: str, meta: Dict[str, Any], confidence: float = 1.0) -> MemoryEpisode:
    """Reconstrói a entidade MemoryEpisode usando from_dict para retrocompatibilidade v1/v2."""
    meta_copy = dict(meta or {})
    sources = json.loads(meta_copy.get("sources_json", "[]")) if isinstance(meta_copy.get("sources_json"), str) else []
    source_hashes = json.loads(meta_copy.get("source_hashes_json", "[]")) if isinstance(meta_copy.get("source_hashes_json"), str) else []
    env_ctx = json.loads(meta_copy.get("environment_context_json", "{}")) if isinstance(meta_copy.get("environment_context_json"), str) else {}

    raw_data = {
        "id": ep_id,
        "query": meta_copy.get("query", ""),
        "response": doc,
        "sources": sources,
        "topic": meta_copy.get("topic"),
        "tokens_used": meta_copy.get("tokens_used", 0),
        "tokens_saved": meta_copy.get("tokens_saved", 0),
        "reduction_percentage": meta_copy.get("reduction_percentage", 0.0),
        "created_at": meta_copy.get("created_at", ""),
        "confidence_score": confidence,
        "hit_count": meta_copy.get("hit_count", 0),
        "provenance": meta_copy.get("provenance", ProvenanceType.THEORETICAL.value),
        "status": meta_copy.get("status", EvidenceStatus.VALID.value),
        "schema_version": meta_copy.get("schema_version", "1.0"),
        "project_source": meta_copy.get("project_source") or None,
        "commit_hash": meta_copy.get("commit_hash") or None,
        "experiment_id": meta_copy.get("experiment_id") or None,
        "content_hash": meta_copy.get("content_hash") or None,
        "measured_at": meta_copy.get("measured_at") or None,
        "environment_context": env_ctx,
        "source_hashes": source_hashes,
    }
    return MemoryEpisode.from_dict(raw_data)


def build_where_filter(provenance: Optional[ProvenanceType], status: Optional[EvidenceStatus]) -> Optional[Dict[str, Any]]:
    """Constrói cláusula de filtro 'where' nativa do ChromaDB."""
    conditions = []
    if provenance:
        conditions.append({"provenance": provenance.value if isinstance(provenance, ProvenanceType) else str(provenance)})
    if status:
        conditions.append({"status": status.value if isinstance(status, EvidenceStatus) else str(status)})
    if len(conditions) > 1:
        return {"$and": conditions}
    return conditions[0] if len(conditions) == 1 else None
