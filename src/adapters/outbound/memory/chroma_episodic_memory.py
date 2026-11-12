import os
import json
import logging
from typing import List, Dict, Any, Optional
try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
except ImportError:
    chromadb = None
    ChromaSettings = None

from src.domain.entities.memory import MemoryEpisode, ProvenanceType, EvidenceStatus
from src.domain.ports.outbound import IEpisodicMemoryPort
from src.config.settings import settings

logger = logging.getLogger(__name__)


def _serialize_metadata(episode: MemoryEpisode) -> Dict[str, Any]:
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
        "environment_context_json": json.dumps(episode.environment_context, sort_keys=True, ensure_ascii=False)
    }


def _deserialize_metadata(ep_id: str, doc: str, meta: Dict[str, Any], confidence: float = 1.0) -> MemoryEpisode:
    """Reconstrói a entidade MemoryEpisode usando from_dict para retrocompatibilidade v1/v2."""
    meta_copy = dict(meta or {})
    
    # Desserializa campos JSON aninhados com fallback seguro
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
        "source_hashes": source_hashes
    }
    return MemoryEpisode.from_dict(raw_data)


def _build_where_filter(provenance: Optional[ProvenanceType], status: Optional[EvidenceStatus]) -> Optional[Dict[str, Any]]:
    """Constrói cláusula de filtro 'where' nativa do ChromaDB."""
    conditions = []
    if provenance:
        val = provenance.value if isinstance(provenance, ProvenanceType) else str(provenance)
        conditions.append({"provenance": val})
    if status:
        val = status.value if isinstance(status, EvidenceStatus) else str(status)
        conditions.append({"status": val})

    if len(conditions) > 1:
        return {"$and": conditions}
    elif len(conditions) == 1:
        return conditions[0]
    return None


class ChromaEpisodicMemoryAdapter(IEpisodicMemoryPort):
    """Adaptador de Memória Episódica persistente no ChromaDB (agent_episodic_brain)."""

    def __init__(self, persist_directory: str = None, mode: str = None, host: str = None, port: int = None):
        self.persist_dir = persist_directory or settings.CHROMA_PERSIST_DIR
        self.mode = (mode or settings.CHROMA_MODE).lower()
        self.host = host or settings.CHROMA_HOST
        self.port = port or settings.CHROMA_PORT
        self.collection_name = "agent_episodic_brain"

        self.client = self._init_client()
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )

    def _init_client(self):
        if not chromadb:
            raise ImportError("O pacote 'chromadb' não está instalado no ambiente Python ativo.")
        if self.mode == "http":
            try:
                client = chromadb.HttpClient(host=self.host, port=self.port, settings=ChromaSettings(anonymized_telemetry=False))
                client.heartbeat()
                return client
            except Exception as e:
                logger.warning(f"ChromaDB HTTP falhou ({e}), usando persistente local: '{self.persist_dir}'")
        os.makedirs(self.persist_dir, exist_ok=True)
        return chromadb.PersistentClient(path=self.persist_dir, settings=ChromaSettings(anonymized_telemetry=False))

    def save_episode(self, episode: MemoryEpisode, embedding: List[float]) -> None:
        self.collection.upsert(
            ids=[episode.id],
            embeddings=[embedding],
            documents=[episode.response],
            metadatas=[_serialize_metadata(episode)]
        )

    def get_episode(self, episode_id: str) -> Optional[MemoryEpisode]:
        results = self.collection.get(ids=[episode_id], include=["documents", "metadatas"])
        if not results or not results["ids"]:
            return None
        return _deserialize_metadata(
            ep_id=results["ids"][0],
            doc=results["documents"][0],
            meta=results["metadatas"][0]
        )

    def search_episodes(
        self,
        query_embedding: List[float],
        min_similarity: float = 0.88,
        top_k: int = 1,
        provenance: Optional[ProvenanceType] = None,
        status: Optional[EvidenceStatus] = EvidenceStatus.VALID
    ) -> List[MemoryEpisode]:
        count = self.collection.count()
        if count == 0:
            return []

        where_clause = _build_where_filter(provenance, status)
        kwargs: Dict[str, Any] = {
            "query_embeddings": [query_embedding],
            "n_results": min(top_k, count),
            "include": ["documents", "metadatas", "distances"]
        }
        if where_clause:
            kwargs["where"] = where_clause

        try:
            results = self.collection.query(**kwargs)
        except Exception as e:
            logger.warning(f"Erro na busca filtrada: {e}. Tentando busca aberta.")
            del kwargs["where"]
            results = self.collection.query(**kwargs)

        episodes: List[MemoryEpisode] = []
        if not results or not results["ids"] or not results["ids"][0]:
            return []

        for i, ep_id in enumerate(results["ids"][0]):
            distance = results["distances"][0][i] if results.get("distances") else 0.0
            similarity = max(0.0, 1.0 - distance)
            if similarity < min_similarity:
                continue

            doc = results["documents"][0][i]
            meta = results["metadatas"][0][i]
            episodes.append(_deserialize_metadata(ep_id, doc, meta, confidence=similarity))

            # Atualiza hit count
            try:
                meta["hit_count"] = int(meta.get("hit_count", 0)) + 1
                self.collection.update(ids=[ep_id], metadatas=[meta])
            except Exception:
                pass

        return episodes

    def list_episodes(
        self,
        limit: int = 50,
        query_filter: Optional[str] = None,
        provenance: Optional[ProvenanceType] = None,
        status: Optional[EvidenceStatus] = None
    ) -> List[MemoryEpisode]:
        count = self.collection.count()
        if count == 0:
            return []

        where_clause = _build_where_filter(provenance, status)
        kwargs: Dict[str, Any] = {"limit": limit, "include": ["documents", "metadatas"]}
        if where_clause:
            kwargs["where"] = where_clause

        results = self.collection.get(**kwargs)
        if not results or not results["ids"]:
            return []

        episodes = []
        for i, ep_id in enumerate(results["ids"]):
            doc = results["documents"][i]
            meta = results["metadatas"][i]
            query = meta.get("query", "")
            if query_filter and query_filter.lower() not in query.lower() and query_filter.lower() not in doc.lower():
                continue
            episodes.append(_deserialize_metadata(ep_id, doc, meta))
        return episodes

    def delete_episode(self, episode_id: str) -> bool:
        try:
            self.collection.delete(ids=[episode_id])
            return True
        except Exception as e:
            logger.error(f"Erro ao deletar episódio {episode_id}: {e}")
            return False

    def clear_all(self) -> None:
        try:
            self.client.delete_collection(name=self.collection_name)
            self.collection = self.client.get_or_create_collection(name=self.collection_name, metadata={"hnsw:space": "cosine"})
        except Exception as e:
            logger.error(f"Erro ao limpar coleção de memória: {e}")
