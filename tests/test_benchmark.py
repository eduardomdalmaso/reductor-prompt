import unittest
from unittest.mock import MagicMock
from src.application.services.query_rewriter_service import QueryRewriterService
from src.application.services.prompt_compressor_service import PromptCompressorService
from scripts.benchmark_baseline import benchmark_single_query


class TestBenchmarkBaseline(unittest.TestCase):
    """Garante que o harness de medição de benchmark executa com precisão matemática."""

    def test_benchmark_single_query_structure(self):
        rewriter = QueryRewriterService(enable_expansion=True)
        compressor = PromptCompressorService()
        
        mock_embedder = MagicMock()
        mock_embedder.embed_text.return_value = [0.1] * 768
        
        mock_vector_store = MagicMock()
        mock_vector_store.search.return_value = []

        query_item = {
            "id": "test_q",
            "category": "factual",
            "query": "Qual a diferença entre B-Tree e LSM-Tree?"
        }

        result = benchmark_single_query(
            query_item=query_item,
            rewriter=rewriter,
            embedder=mock_embedder,
            vector_store=mock_vector_store,
            compressor=compressor,
            iterations=1
        )

        self.assertEqual(result["id"], "test_q")
        self.assertIn("timings_ms", result)
        self.assertIn("query_expansion", result["timings_ms"])
        self.assertIn("embeddings", result["timings_ms"])
        self.assertIn("vector_search", result["timings_ms"])
        self.assertIn("fusion_and_compression", result["timings_ms"])
        self.assertIn("total_retrieval", result["timings_ms"])
        self.assertIn("metrics", result)


if __name__ == "__main__":
    unittest.main()
