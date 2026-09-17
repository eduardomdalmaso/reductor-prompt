import pytest
from typing import List, Dict, Any, Optional

from src.domain.entities.memory import MemoryEpisode
from src.domain.ports.outbound import IEpisodicMemoryPort, IEmbeddingPort, IVectorStorePort, ILLMPort
from src.domain.entities.book import ScoredChunk, BookChunk
from src.application.use_cases.manage_brain_use_case import ManageBrainUseCase
from src.application.use_cases.query_books_use_case import QueryBooksUseCase


class MockEpisodicMemoryPort(IEpisodicMemoryPort):
    """Mock em memória para testes unitários rápidos."""
    def __init__(self):
        self.storage: Dict[str, MemoryEpisode] = {}
        self.embeddings: Dict[str, List[float]] = {}

    def save_episode(self, episode: MemoryEpisode, embedding: List[float]) -> None:
        self.storage[episode.id] = episode
        self.embeddings[episode.id] = embedding

    def search_episodes(
        self, 
        query_embedding: List[float], 
        min_similarity: float = 0.88, 
        top_k: int = 1
    ) -> List[MemoryEpisode]:
        if not self.storage:
            return []
        # Retorna o primeiro se houver
        ep = list(self.storage.values())[0]
        ep.confidence_score = 0.95
        return [ep]

    def list_episodes(self, limit: int = 50, query_filter: Optional[str] = None) -> List[MemoryEpisode]:
        episodes = list(self.storage.values())
        if query_filter:
            episodes = [e for e in episodes if query_filter.lower() in e.query.lower()]
        return episodes[:limit]

    def delete_episode(self, episode_id: str) -> bool:
        if episode_id in self.storage:
            del self.storage[episode_id]
            return True
        return False

    def clear_all(self) -> None:
        self.storage.clear()
        self.embeddings.clear()


class MockEmbeddingPort(IEmbeddingPort):
    def embed_text(self, text: str) -> List[float]:
        return [0.1, 0.2, 0.3, 0.4]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [[0.1, 0.2, 0.3, 0.4] for _ in texts]


class MockVectorStorePort(IVectorStorePort):
    def upsert_chunks(self, book, chunks, embeddings) -> None:
        pass

    def search(self, query_embedding: List[float], top_k: int = 4, book_title_filter: Optional[str] = None) -> List[ScoredChunk]:
        chunk = BookChunk(
            id="c1",
            book_id="b1",
            chunk_index=0,
            text_content="Clean Architecture separa regras de negócio da interface e do banco de dados.",
            estimated_tokens=50,
            chapter_or_section="Capítulo 1",
            page_number=10
        )
        return [ScoredChunk(chunk=chunk, score=0.92, book_title="Clean Architecture")]

    def delete_book(self, book_id: str) -> None:
        pass

    def list_indexed_books(self) -> List[Dict[str, Any]]:
        return [{"book_id": "b1", "title": "Clean Architecture", "chunks_count": 1}]


class MockLLMPort(ILLMPort):
    def generate_response(self, system_instruction: str, prompt: str, temperature: float = 0.1) -> str:
        return "Clean Architecture consiste em desacoplar o domínio das camadas de infraestrutura."


def test_manage_brain_use_case_teach_and_list():
    memory_port = MockEpisodicMemoryPort()
    embedding_port = MockEmbeddingPort()
    use_case = ManageBrainUseCase(memory_port=memory_port, embedding_port=embedding_port)

    episode = use_case.teach_brain(
        query="Como funciona Circuit Breaker em Go?",
        insight="Circuit Breaker monitora falhas consecutivas e abre o circuito com fallback.",
        topic="Resiliência"
    )

    assert episode.id is not None
    assert episode.topic == "Resiliência"
    assert "Circuit Breaker" in episode.response

    knowledge = use_case.list_knowledge()
    assert len(knowledge) == 1
    assert knowledge[0]["query"] == "Como funciona Circuit Breaker em Go?"


def test_query_books_use_case_brain_hit():
    memory_port = MockEpisodicMemoryPort()
    embedding_port = MockEmbeddingPort()
    vector_store = MockVectorStorePort()
    llm_port = MockLLMPort()

    # Preenche uma memória no cérebro
    memory_port.save_episode(
        MemoryEpisode(
            id="ep1",
            query="O que é Clean Architecture?",
            response="Resposta prévia do cérebro sobre Clean Architecture.",
            confidence_score=0.96
        ),
        [0.1, 0.2, 0.3, 0.4]
    )

    use_case = QueryBooksUseCase(
        embedding_port=embedding_port,
        vector_store=vector_store,
        llm_port=llm_port,
        memory_port=memory_port
    )

    result = use_case.execute(
        query="O que é Clean Architecture?",
        use_brain=True
    )

    assert result["from_brain"] is True
    assert "Memória Recuperada do Cérebro Coletivo" in result["response"]
    assert result["brain_episode_id"] == "ep1"
