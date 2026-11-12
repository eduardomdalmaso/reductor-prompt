import unittest
import json
from unittest.mock import MagicMock
from src.domain.entities.memory import MemoryEpisode, ProvenanceType, EvidenceStatus
from src.adapters.outbound.memory.chroma_episodic_memory import (
    _serialize_metadata,
    _deserialize_metadata,
    _build_where_filter
)


class TestChromaEpisodicMemoryAdapter(unittest.TestCase):
    """Testa a serialização, compatibilidade v1/v2 e filtros do adaptador ChromaDB."""

    def test_serialize_metadata_produces_flat_primitives(self):
        """ChromaDB requer tipos primitivos (sem dicionários aninhados não serializados)."""
        ep = MemoryEpisode(
            id="ep_test_01",
            query="Como funciona o Raft no Redis?",
            response="Raft garante consenso distribuído...",
            provenance=ProvenanceType.EMPIRICAL,
            status=EvidenceStatus.VALID,
            project_source="HydraStream",
            commit_hash="a1b2c3d",
            environment_context={"hardware": "RTX 5090", "concurrency": 8},
            source_hashes=["sha256:123456"]
        )

        meta = _serialize_metadata(ep)

        self.assertIsInstance(meta["provenance"], str)
        self.assertEqual(meta["provenance"], "empirical")
        self.assertIsInstance(meta["status"], str)
        self.assertEqual(meta["status"], "valid")
        self.assertIsInstance(meta["environment_context_json"], str)
        # O Chroma não aceita dict direto
        self.assertNotIn("environment_context", meta)

    def test_deserialize_legacy_v1_metadata(self):
        """Garante que metadados legados sem campos v2 continuam recuperáveis."""
        legacy_meta = {
            "query": "Diferença entre mutex e rwlock?",
            "topic": "Concorrência",
            "tokens_used": 120,
            "tokens_saved": 1500,
            "reduction_percentage": 92.5,
            "created_at": "2026-01-01T00:00:00",
            "hit_count": 2,
            "sources_json": json.dumps([{"book_title": "Rust Atomics and Locks"}])
        }

        reconstructed = _deserialize_metadata(
            ep_id="legacy_001",
            doc="Mutex bloqueia leitura e escrita...",
            meta=legacy_meta,
            confidence=0.95
        )

        self.assertEqual(reconstructed.id, "legacy_001")
        self.assertEqual(reconstructed.provenance, ProvenanceType.THEORETICAL)
        self.assertEqual(reconstructed.status, EvidenceStatus.VALID)
        self.assertEqual(reconstructed.schema_version, "1.0")
        self.assertEqual(len(reconstructed.sources), 1)
        self.assertEqual(reconstructed.sources[0]["book_title"], "Rust Atomics and Locks")

    def test_build_where_filter_conditions(self):
        """Valida a construção da cláusula where do ChromaDB."""
        # Ambos
        f_both = _build_where_filter(ProvenanceType.EMPIRICAL, EvidenceStatus.VALID)
        self.assertEqual(f_both, {"$and": [{"provenance": "empirical"}, {"status": "valid"}]})

        # Apenas proveniência
        f_prov = _build_where_filter(ProvenanceType.THEORETICAL, None)
        self.assertEqual(f_prov, {"provenance": "theoretical"})

        # Apenas status
        f_status = _build_where_filter(None, EvidenceStatus.STALE)
        self.assertEqual(f_status, {"status": "stale"})

        # Nenhum
        f_none = _build_where_filter(None, None)
        self.assertIsNone(f_none)


if __name__ == "__main__":
    unittest.main()
