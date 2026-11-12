import unittest
from unittest.mock import MagicMock
from src.domain.entities.book import BookChunk, ScoredChunk
from src.domain.entities.memory import MemoryEpisode, ProvenanceType, EvidenceStatus
from src.application.use_cases.query_books_use_case import QueryBooksUseCase


class TestBilateralRetrieval(unittest.TestCase):
    """Garante que a recuperação bilateral correlaciona teoria e empirismo sem misturá-los."""

    def setUp(self):
        self.mock_embedder = MagicMock()
        self.mock_embedder.embed_text.return_value = [0.1] * 768

        self.mock_vector_store = MagicMock()
        self.mock_memory = MagicMock()
        self.mock_llm = MagicMock()
        self.mock_llm.generate_response.return_value = "Síntese bilateral: a teoria recomenda X mas o HydraStream mediu Y."

        self.use_case = QueryBooksUseCase(
            embedding_port=self.mock_embedder,
            vector_store=self.mock_vector_store,
            llm_port=self.mock_llm,
            memory_port=self.mock_memory
        )

    def test_bilateral_retrieval_combines_theory_and_empirical(self):
        """Consulta retorna contexto teórico dos livros e evidências reais do HydraStream com distinção."""
        # 1. Chunks Teóricos
        theoretical_chunk = BookChunk(
            id="c1", book_id="b1", book_title="Designing Data-Intensive",
            chunk_index=1, content="A replicação síncrona garante durabilidade ao custo de latência de escrita.",
            token_count=20, page_number=152, chapter="Replication"
        )
        self.mock_vector_store.search.return_value = [ScoredChunk(chunk=theoretical_chunk, score=0.92)]

        # 2. Evidência Empírica
        empirical_ep = MemoryEpisode(
            id="hydra_bench_01",
            query="Qual a latência de replicação no cluster?",
            response="Medição real: 2.1ms com quorum de 3 nós na LAN",
            provenance=ProvenanceType.EMPIRICAL,
            status=EvidenceStatus.VALID,
            project_source="HydraStream",
            commit_hash="a891f2c",
            experiment_id="bench_lan_quorum",
            environment_context={"hardware": "RTX 5090", "lan": "10GbE"}
        )
        self.mock_memory.search_episodes.return_value = [empirical_ep]

        result = self.use_case.execute(
            query="latência de replicação",
            only_context=True,
            enable_rewriting=False
        )

        resp_text = result["response"]
        self.assertIn("Designing Data-Intensive", resp_text)
        self.assertIn("EVIDÊNCIAS EMPÍRICAS", resp_text)
        self.assertIn("HydraStream", resp_text)
        self.assertIn("#a891f2c", resp_text)
        self.assertIn("2.1ms", resp_text)

        # Verifica fontes bilaterais
        sources = result["sources"]
        provenances = [s.get("provenance") for s in sources]
        self.assertIn("empirical", provenances)

    def test_stale_evidence_excluded_by_filter(self):
        """Garante que a busca de evidências do use case especifica status=VALID."""
        self.mock_vector_store.search.return_value = []
        self.mock_memory.search_episodes.return_value = []

        self.use_case.execute(query="teste de filtro", only_context=True, enable_rewriting=False)

        # Confere se a porta foi chamada com status=VALID e provenance=EMPIRICAL
        _, kwargs = self.mock_memory.search_episodes.call_args
        self.assertEqual(kwargs.get("provenance"), ProvenanceType.EMPIRICAL)
        self.assertEqual(kwargs.get("status"), EvidenceStatus.VALID)


if __name__ == "__main__":
    unittest.main()
