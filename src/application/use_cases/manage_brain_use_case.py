import hashlib
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from src.domain.entities.memory import MemoryEpisode
from src.domain.ports.outbound import IEpisodicMemoryPort, IEmbeddingPort

logger = logging.getLogger(__name__)


class ManageBrainUseCase:
    """Caso de uso para gerenciar e ensinar a memória episódica do cérebro coletivo."""

    def __init__(
        self,
        memory_port: IEpisodicMemoryPort,
        embedding_port: IEmbeddingPort
    ):
        self.memory_port = memory_port
        self.embedding_port = embedding_port

    def teach_brain(
        self,
        query: str,
        insight: str,
        topic: Optional[str] = None,
        sources: Optional[List[Dict[str, Any]]] = None
    ) -> MemoryEpisode:
        """Ensina um novo conhecimento/resolução ao cérebro."""
        clean_query = query.strip()
        episode_id = hashlib.sha256(clean_query.lower().encode('utf-8')).hexdigest()[:16]

        # Gera embedding da query para busca semântica futura
        vector = self.embedding_port.embed_text(clean_query)

        episode = MemoryEpisode(
            id=episode_id,
            query=clean_query,
            response=insight.strip(),
            sources=sources or [],
            topic=topic,
            tokens_used=len(insight.split()) * 2,
            tokens_saved=3500,
            reduction_percentage=98.0,
            created_at=datetime.utcnow().isoformat(),
            confidence_score=1.0,
            hit_count=0
        )

        self.memory_port.save_episode(episode, vector)
        return episode

    def consult_brain(
        self,
        query: str,
        min_similarity: float = 0.88
    ) -> Optional[MemoryEpisode]:
        """Consulta o cérebro diretamente por similaridade semântica."""
        vector = self.embedding_port.embed_text(query)
        episodes = self.memory_port.search_episodes(
            query_embedding=vector,
            min_similarity=min_similarity,
            top_k=1
        )
        return episodes[0] if episodes else None

    def list_knowledge(
        self,
        limit: int = 50,
        query_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Lista episódios e aprendizados registrados no cérebro."""
        episodes = self.memory_port.list_episodes(limit=limit, query_filter=query_filter)
        return [ep.to_dict() for ep in episodes]

    def delete_knowledge(self, episode_id: str) -> bool:
        """Remove uma memória do cérebro."""
        return self.memory_port.delete_episode(episode_id)

    def clear_brain(self) -> None:
        """Limpa toda a memória do cérebro."""
        self.memory_port.clear_all()
