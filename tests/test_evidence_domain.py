import unittest
from datetime import datetime
from src.domain.entities.memory import MemoryEpisode, ProvenanceType, EvidenceStatus
from src.domain.ports.inbound import IngestEvidenceCommand


class TestEvidenceDomain(unittest.TestCase):
    """Garante que a fundação de domínio suporta proveniência com retrocompatibilidade total."""

    def test_legacy_v1_episode_deserialization(self):
        """Valida que episódios persistidos no esquema v1 continuam 100% funcionais."""
        legacy_data = {
            "id": "ep_legacy_123",
            "query": "Como configurar o WAL no PostgreSQL?",
            "response": "Configure o max_wal_size e checkpoint_completion_target...",
            "sources": [{"book_title": "Database Internals", "page": 84}],
            "topic": "PostgreSQL Internals",
            "tokens_used": 150,
            "tokens_saved": 2800,
            "reduction_percentage": 94.8,
            "created_at": "2026-01-10T10:00:00",
            "confidence_score": 1.0,
            "hit_count": 5
        }

        episode = MemoryEpisode.from_dict(legacy_data)

        self.assertEqual(episode.id, "ep_legacy_123")
        self.assertEqual(episode.provenance, ProvenanceType.THEORETICAL)
        self.assertEqual(episode.status, EvidenceStatus.VALID)
        self.assertEqual(episode.schema_version, "1.0")
        self.assertIsNone(episode.project_source)
        self.assertEqual(episode.environment_context, {})
        self.assertEqual(episode.source_hashes, [])

    def test_empirical_v2_episode_roundtrip(self):
        """Valida serialização e desserialização de evidências empíricas do HydraStream."""
        episode = MemoryEpisode(
            id="hydra_bench_001",
            query="Overhead de decodificação NVENC H.264 em streaming WebRTC",
            response="Medição real: 1.42ms por frame em batch de 16 streams concorrentes.",
            provenance=ProvenanceType.EMPIRICAL,
            status=EvidenceStatus.VALID,
            schema_version="2.0",
            project_source="HydraStream",
            commit_hash="a4f12b7",
            experiment_id="bench_nvenc_v1",
            measured_at="2026-11-12T14:00:00",
            environment_context={
                "hardware": "RTX 5090 32GB",
                "driver": "570.86",
                "concurrency": 16,
                "resolution": "1080p60"
            },
            source_hashes=["sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"]
        )

        serialized = episode.to_dict()
        self.assertEqual(serialized["provenance"], "empirical")
        self.assertEqual(serialized["status"], "valid")
        self.assertEqual(serialized["project_source"], "HydraStream")
        self.assertEqual(serialized["environment_context"]["hardware"], "RTX 5090 32GB")

        reconstructed = MemoryEpisode.from_dict(serialized)
        self.assertEqual(reconstructed.provenance, ProvenanceType.EMPIRICAL)
        self.assertEqual(reconstructed.status, EvidenceStatus.VALID)
        self.assertEqual(reconstructed.commit_hash, "a4f12b7")
        self.assertEqual(reconstructed.environment_context["concurrency"], 16)

    def test_ingest_evidence_command_contract(self):
        """Valida a estrutura do comando de ingestão."""
        cmd = IngestEvidenceCommand(
            query="Latência de transmuxing RTP",
            response="Zero-copy transmuxing atinge 0.28ms",
            project_source="HydraStream",
            experiment_id="rtp_transmux_01",
            commit_hash="c891ab0",
            environment_context={"kernel": "Linux 6.12"}
        )
        self.assertEqual(cmd.provenance, ProvenanceType.EMPIRICAL)
        self.assertEqual(cmd.status, EvidenceStatus.VALID)
        self.assertEqual(cmd.project_source, "HydraStream")


if __name__ == "__main__":
    unittest.main()
