import os
import json
import logging
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings as ChromaSettings

from src.domain.entities.memory import MemoryEpisode
from src.domain.ports.outbound import IEpisodicMemoryPort
from src.config.settings import settings

logger = logging.getLogger(__name__)


class ChromaEpisodicMemoryAdapter(IEpisodicMemoryPort):
    """Adaptador de Memória Episódica persistente no ChromaDB (agent_episodic_brain)."""

    def __init__(
        self,
        persist_directory: Optional[str] = None,
        mode: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None
    ):
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
        """Inicializa HttpClient (Podman) ou PersistentClient (Local)."""
        if self.mode == "http":
            try:
                client = chromadb.HttpClient(
                    host=self.host,
                    port=self.port,
                    settings=ChromaSettings(anonymized_telemetry=False)
                )
                client.heartbeat()
                return client
            except Exception as e:
                logger.warning(
                    f"Falha ao conectar ChromaDB para memória em http://{self.host}:{self.port}: {e}. "
                    f"Usando persistência local em '{self.persist_dir}'."
                )
        
        os.makedirs(self.persist_dir, exist_ok=True)
        return chromadb.PersistentClient(
            path=self.persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False)
        )

    def save_episode(self, episode: MemoryEpisode, embedding: List[float]) -> None:
        """Salva ou atualiza uma memória episódica."""
        metadata = {
            "query": episode.query,
            "topic": episode.topic or "",
            "tokens_used": episode.tokens_used,
            "tokens_saved": episode.tokens_saved,
            "reduction_percentage": episode.reduction_percentage,
            "created_at": episode.created_at,
            "hit_count": episode.hit_count,
            "sources_json": json.dumps(episode.sources, ensure_ascii=False)
        }

        self.collection.upsert(
            ids=[episode.id],
            embeddings=[embedding],
            documents=[episode.response],
            metadatas=[metadata]
        )
        logger.info(f"💾 Memória gravada no cérebro com ID: {episode.id}")

    def search_episodes(
        self, 
        query_embedding: List[float], 
        min_similarity: float = 0.88, 
        top_k: int = 1
    ) -> List[MemoryEpisode]:
        """Busca no cérebro por limiar de similaridade de cosseno."""
        count = self.collection.count()
        if count == 0:
            return []

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, count),
            include=["documents", "metadatas", "distances"]
        )

        episodes: List[MemoryEpisode] = []
        if not results or not results["ids"] or not results["ids"][0]:
            return []

        for i, ep_id in enumerate(results["ids"][0]):
            distance = results["distances"][0][i] if results.get("distances") else 0.0
            # Métrica cosseno no ChromaDB: distance = 1 - similarity => similarity = 1 - distance
            similarity = max(0.0, 1.0 - distance)

            if similarity < min_similarity:
                continue

            doc = results["documents"][0][i]
            meta = results["metadatas"][0][i]

            sources = []
            if "sources_json" in meta and meta["sources_json"]:
                try:
                    sources = json.loads(meta["sources_json"])
                except Exception:
                    pass

            episodes.append(
                MemoryEpisode(
                    id=ep_id,
                    query=meta.get("query", ""),
                    response=doc,
                    sources=sources,
                    topic=meta.get("topic"),
                    tokens_used=int(meta.get("tokens_used", 0)),
                    tokens_saved=int(meta.get("tokens_saved", 0)),
                    reduction_percentage=float(meta.get("reduction_percentage", 0.0)),
                    created_at=meta.get("created_at", ""),
                    confidence_score=similarity,
                    hit_count=int(meta.get("hit_count", 0)) + 1
                )
            )

            # Atualiza hit count no ChromaDB em background
            try:
                meta["hit_count"] = int(meta.get("hit_count", 0)) + 1
                self.collection.update(
                    ids=[ep_id],
                    metadatas=[meta]
                )
            except Exception:
                pass

        return episodes

    def list_episodes(self, limit: int = 50, query_filter: Optional[str] = None) -> List[MemoryEpisode]:
        """Lista episódios da memória."""
        count = self.collection.count()
        if count == 0:
            return []

        results = self.collection.get(
            limit=limit,
            include=["documents", "metadatas"]
        )

        episodes: List[MemoryEpisode] = []
        if not results or not results["ids"]:
            return []

        for i, ep_id in enumerate(results["ids"]):
            doc = results["documents"][i]
            meta = results["metadatas"][i]
            query = meta.get("query", "")

            if query_filter and query_filter.lower() not in query.lower() and query_filter.lower() not in doc.lower():
                continue

            sources = []
            if "sources_json" in meta and meta["sources_json"]:
                try:
                    sources = json.loads(meta["sources_json"])
                except Exception:
                    pass

            episodes.append(
                MemoryEpisode(
                    id=ep_id,
                    query=query,
                    response=doc,
                    sources=sources,
                    topic=meta.get("topic"),
                    tokens_used=int(meta.get("tokens_used", 0)),
                    tokens_saved=int(meta.get("tokens_saved", 0)),
                    reduction_percentage=float(meta.get("reduction_percentage", 0.0)),
                    created_at=meta.get("created_at", ""),
                    confidence_score=1.0,
                    hit_count=int(meta.get("hit_count", 0))
                )
            )

        return episodes

    def delete_episode(self, episode_id: str) -> bool:
        """Deleta uma memória do cérebro."""
        try:
            self.collection.delete(ids=[episode_id])
            return True
        except Exception as e:
            logger.error(f"Erro ao deletar episódio {episode_id}: {e}")
            return False

    def clear_all(self) -> None:
        """Limpa toda a memória episódica."""
        try:
            self.client.delete_collection(name=self.collection_name)
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
        except Exception as e:
            logger.error(f"Erro ao limpar coleção de memória: {e}")
