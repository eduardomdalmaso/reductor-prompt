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


from src.adapters.outbound.memory.memory_serializer import (
    build_where_filter as _build_where_filter,
    deserialize_metadata as _deserialize_metadata,
    serialize_metadata as _serialize_metadata,
)


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
