import unittest
from datetime import datetime, timezone, timedelta
from src.domain.entities.memory import MemoryEpisode, ProvenanceType, EvidenceStatus
from src.domain.entities.decision import DecisionReport, DecisionVerdict
from src.application.services.evidence_quality_evaluator import EvidenceQualityEvaluator
from src.application.services.staleness_detector import StalenessDetector
from src.application.services.experimental_comparator import ExperimentalComparator


class TestDecisionEngine(unittest.TestCase):
    """Bateria de testes unitários para a Fase 4 (Evidence Intelligence & Decision Engine)."""

    def test_evidence_quality_evaluator_completeness(self):
        """Avalia que o score mede a completude experimental dos metadados."""
        full_ep = MemoryEpisode(
            id="ep1", query="Latência H.264", response="1.42 ms por frame",
            commit_hash="a1b2c3d4", measured_at="2026-11-12T10:00:00+00:00",
            environment_context={"hardware": "RTX 5090", "os": "linux", "metrics": {"latency_ms": 1.42}}
        )

        score, breakdown = EvidenceQualityEvaluator.evaluate(full_ep)
        self.assertEqual(score, 1.0)
        self.assertTrue(breakdown["has_commit_hash"])
        self.assertTrue(breakdown["has_environment_context"])
        self.assertTrue(breakdown["has_timestamp"])
        self.assertTrue(breakdown["has_identifiable_metrics"])

        # Evidência incompleta (sem commit e sem hardware)
        sparse_ep = MemoryEpisode(
            id="ep2", query="Latência H.264", response="Parece rápido",
            commit_hash="", measured_at=None, environment_context={}
        )
        sparse_score, sparse_breakdown = EvidenceQualityEvaluator.evaluate(sparse_ep)
        self.assertLess(sparse_score, 0.5)
        self.assertFalse(sparse_breakdown["has_commit_hash"])

    def test_staleness_detector_hardware_mismatch(self):
        """Detecta divergência quando o hardware atual difere da medição registrada."""
        detector = StalenessDetector(default_ttl_days=90)

        ep = MemoryEpisode(
            id="ep_old_hw", query="Throughput", response="120 fps",
            environment_context={"hardware": "RTX 3060 12GB"},
            created_at=datetime.now(timezone.utc).isoformat()
        )

        analysis = detector.analyze(ep, current_hardware="NVIDIA RTX 5090 32GB")
        self.assertTrue(analysis.is_stale)
        self.assertFalse(analysis.hardware_match)
        self.assertTrue(any("Divergência de Hardware" in r for r in analysis.reasons))

    def test_staleness_detector_fresh_compatible(self):
        """Evidência recente e em hardware compatível deve ser avaliada como não-stale."""
        detector = StalenessDetector(default_ttl_days=90)

        ep = MemoryEpisode(
            id="ep_current", query="Throughput", response="120 fps",
            environment_context={"hardware": "RTX 5090"},
            commit_hash="a4f12b7",
            created_at=datetime.now(timezone.utc).isoformat()
        )

        analysis = detector.analyze(ep, current_hardware="RTX 5090", current_commit="a4f12b7")
        self.assertFalse(analysis.is_stale)
        self.assertEqual(analysis.status_recommendation, EvidenceStatus.VALID)

    def test_staleness_detector_ttl_expired(self):
        """Evidência com mais de 90 dias deve acusar validade temporal excedida."""
        detector = StalenessDetector(default_ttl_days=90)
        old_date = (datetime.now(timezone.utc) - timedelta(days=120)).isoformat()

        ep = MemoryEpisode(
            id="ep_expired", query="Throughput", response="120 fps",
            environment_context={"hardware": "RTX 5090"},
            measured_at=old_date
        )

        analysis = detector.analyze(ep, current_hardware="RTX 5090")
        self.assertTrue(analysis.is_stale)
        self.assertTrue(any("Validade Temporal Excedida" in r for r in analysis.reasons))

    def test_experimental_comparator_unit_normalization(self):
        """Normaliza unidades de latência (ms vs µs) e elege menor valor como vencedor."""
        comparator = ExperimentalComparator()

        ep_ms = MemoryEpisode(
            id="ep_a", experiment_id="exp_ms", query="latência",
            response="Medição: 3.5 ms por frame",
            environment_context={"hardware": "RTX 4080"}
        )
        ep_us = MemoryEpisode(
            id="ep_b", experiment_id="exp_us", query="latência",
            response="Medição: 1200 µs por frame",  # 1200 µs = 1.2 ms (vencedor!)
            environment_context={"hardware": "RTX 5090"}
        )

        res = comparator.compare([ep_ms, ep_us])
        self.assertIsNotNone(res)
        self.assertEqual(res.winner_episode_id, "ep_b")
        self.assertEqual(res.ranking[0]["experiment_id"], "exp_us")
        self.assertEqual(res.ranking[0]["metric_value"], 1.2)
        self.assertIn("superando 'exp_ms'", res.summary)

    def test_decision_report_model(self):
        """Valida que a entidade DecisionReport preserva todos os campos e veredictos."""
        report = DecisionReport(
            query="Qual codec usar para baixa latência?",
            recommendation="Utilizar NVENC H.264 com preset P1",
            verdict=DecisionVerdict.FAVORABLE,
            theoretical_basis=[{"book": "WebRTC Guide", "chapter": "Codecs"}],
            empirical_evidence=[{"experiment": "bench_p1", "latency": "1.2ms"}],
            completeness_score=0.95,
            relevance_score=0.88,
            staleness_analysis={"is_stale": False},
            limitations=["Limitado a GPUs NVIDIA Blackwell/Ada"],
            next_validation_steps=["Testar em GPU Intel Arc"]
        )

        self.assertEqual(report.verdict, DecisionVerdict.FAVORABLE)
        self.assertEqual(report.completeness_score, 0.95)
        self.assertEqual(len(report.limitations), 1)


if __name__ == "__main__":
    unittest.main()
