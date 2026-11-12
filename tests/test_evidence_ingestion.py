import unittest
import threading
from unittest.mock import MagicMock
from src.domain.entities.memory import MemoryEpisode, ProvenanceType, EvidenceStatus
from src.domain.ports.inbound import IngestEvidenceCommand
from src.domain.exceptions.exceptions import EvidenceConflictException, EmbeddingException
from src.application.use_cases.ingest_evidence_use_case import IngestEvidenceUseCase, canonical_hash, build_evidence_id


class TestEvidenceIngestion(unittest.TestCase):
    """Bateria de testes de aceitação da Ingestão de Evidências Empíricas (Fase 2)."""

    def setUp(self):
        self.mock_memory = MagicMock()
        self.mock_embedder = MagicMock()
        self.mock_embedder.embed_text.return_value = [0.1, 0.2, 0.3]
        self.use_case = IngestEvidenceUseCase(
            memory_port=self.mock_memory,
            embedding_port=self.mock_embedder
        )

    def test_ingest_new_empirical_evidence(self):
        """Nova evidência gera embedding e é persistida com proveniência explícita."""
        self.mock_memory.get_episode.return_value = None

        cmd = IngestEvidenceCommand(
            query="Latência de inferência YOLO11 no Triton",
            response="Medição real: 2.15ms em FP16 batch=1",
            project_source="HydraStream",
            experiment_id="triton_bench_yolo11",
            commit_hash="f189a02",
            environment_context={"gpu": "RTX 5090", "concurrency": 1}
        )

        episode, is_created = self.use_case.execute(cmd)

        self.assertIsNotNone(episode.id)
        self.assertTrue(is_created)
        self.assertEqual(episode.provenance, ProvenanceType.EMPIRICAL)
        self.assertEqual(episode.status, EvidenceStatus.VALID)
        self.assertEqual(episode.project_source, "HydraStream")
        self.assertIsNotNone(episode.content_hash)
        self.mock_embedder.embed_text.assert_called_once_with(cmd.query)
        self.mock_memory.save_episode.assert_called_once()

    def test_idempotent_duplicate_evidence_bypasses_embedding(self):
        """Evidência idêntica pré-existente é retornada sem gastar inferência de embedding."""
        cmd = IngestEvidenceCommand(
            query="Overhead do Go2rtc WebRTC",
            response="0.32ms por pacote RTP",
            project_source="HydraStream",
            experiment_id="go2rtc_rtp_01",
            commit_hash="b447812",
            environment_context={"os": "linux"}
        )

        ev_id = build_evidence_id(cmd.project_source, cmd.experiment_id)
        c_hash = canonical_hash({
            "query": cmd.query.strip(),
            "response": cmd.response.strip(),
            "commit_hash": cmd.commit_hash.strip(),
            "environment_context": cmd.environment_context,
            "project_source": cmd.project_source.strip(),
            "experiment_id": cmd.experiment_id.strip()
        })

        existing_episode = MemoryEpisode(
            id=ev_id,
            query=cmd.query,
            response=cmd.response,
            provenance=ProvenanceType.EMPIRICAL,
            status=EvidenceStatus.VALID,
            content_hash=c_hash,
            project_source=cmd.project_source,
            commit_hash=cmd.commit_hash
        )
        self.mock_memory.get_episode.return_value = existing_episode

        result, is_created = self.use_case.execute(cmd)

        self.assertEqual(result.id, ev_id)
        self.assertFalse(is_created)
        # Embedding NÃO deve ser chamado em repetição idempotente
        self.mock_embedder.embed_text.assert_not_called()
        self.mock_memory.save_episode.assert_not_called()

    def test_conflict_detection_on_different_content(self):
        """Mesmo ID de experimento com conteúdo alterado lança EvidenceConflictException."""
        cmd = IngestEvidenceCommand(
            query="Overhead do Go2rtc WebRTC",
            response="NOVO VALOR: 0.99ms por pacote",
            project_source="HydraStream",
            experiment_id="go2rtc_rtp_01",
            commit_hash="b447812"
        )

        existing_episode = MemoryEpisode(
            id=build_evidence_id(cmd.project_source, cmd.experiment_id),
            query=cmd.query,
            response="VALOR ANTIGO: 0.32ms",
            provenance=ProvenanceType.EMPIRICAL,
            content_hash="hash_diferente_123"
        )
        self.mock_memory.get_episode.return_value = existing_episode

        with self.assertRaises(EvidenceConflictException):
            self.use_case.execute(cmd)

    def test_embedding_failure_does_not_persist(self):
        """Se o embedding falhar, a evidência não é persistida de forma corrompida."""
        self.mock_memory.get_episode.return_value = None
        self.mock_embedder.embed_text.side_effect = EmbeddingException("Ollama", "Timeout")

        cmd = IngestEvidenceCommand(
            query="Teste falha",
            response="Teste",
            project_source="HydraStream",
            experiment_id="fail_exp",
            commit_hash="abc"
        )

        with self.assertRaises(EmbeddingException):
            self.use_case.execute(cmd)

        self.mock_memory.save_episode.assert_not_called()

    def test_concurrent_ingestion_thread_safety(self):
        """Ingestões concorrentes do mesmo experimento são coordenadas sem colisão."""
        self.mock_memory.get_episode.return_value = None
        cmd = IngestEvidenceCommand(
            query="Concorrência NVENC",
            response="1.5ms",
            project_source="HydraStream",
            experiment_id="concurrent_nvenc",
            commit_hash="c001"
        )

        results = []
        errors = []

        def _worker():
            try:
                res, _ = self.use_case.execute(cmd)
                results.append(res)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=_worker) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0)
        self.assertEqual(len(results), 4)


if __name__ == "__main__":
    unittest.main()
