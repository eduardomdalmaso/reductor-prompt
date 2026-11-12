import unittest
from unittest.mock import MagicMock
from src.domain.entities.decision import DecisionVerdict, DecisionReport
from src.domain.entities.memory import MemoryEpisode, ProvenanceType, EvidenceStatus
from src.domain.entities.book import BookChunk, ScoredChunk
from src.domain.ports.inbound import MakeDecisionCommand
from src.application.services.staleness_detector import StalenessAnalysis
from src.application.services.experimental_comparator import ComparisonResult
from src.application.services.decision_policy_service import DecisionPolicyService
from src.application.use_cases.make_decision_use_case import MakeDecisionUseCase


class TestDecisionOrchestration(unittest.TestCase):
    """Bateria de testes para a Fase 5 (Orquestração de Decisões & Política Determinística)."""

    def test_policy_insufficient_when_no_empirical_evidence(self):
        """Ausência de evidência empírica resulta em INSUFFICIENT, nunca em REFUTED."""
        res = DecisionPolicyService.evaluate(
            has_theoretical_basis=True,
            empirical_episodes=[],
            completeness_scores=[],
            staleness_analyses=[]
        )
        self.assertEqual(res.verdict, DecisionVerdict.INSUFFICIENT)
        self.assertIn("Ausência de evidências empíricas", res.reason)

    def test_policy_insufficient_when_all_evidence_is_stale(self):
        """Se todas as evidências forem STALE, o veredicto é INSUFFICIENT."""
        stale_ep = MemoryEpisode(id="e1", query="q", response="r", status=EvidenceStatus.STALE)
        stale_analysis = StalenessAnalysis(is_stale=True, reasons=["Hardware divergente"])

        res = DecisionPolicyService.evaluate(
            has_theoretical_basis=True,
            empirical_episodes=[stale_ep],
            completeness_scores=[0.8],
            staleness_analyses=[stale_analysis]
        )
        self.assertEqual(res.verdict, DecisionVerdict.INSUFFICIENT)
        self.assertIn("desatualizadas", res.reason)

    def test_policy_refuted_on_robust_negative_evidence(self):
        """Evidência empírica robusta com resultado inviável resulta em REFUTED."""
        ep = MemoryEpisode(
            id="e1", query="q",
            response="A replicação síncrona apresentou degradação severa e se tornou inviável.",
            status=EvidenceStatus.VALID
        )
        analysis = StalenessAnalysis(is_stale=False)

        res = DecisionPolicyService.evaluate(
            has_theoretical_basis=True,
            empirical_episodes=[ep],
            completeness_scores=[0.85],  # Robusta (>= 0.70)
            staleness_analyses=[analysis]
        )
        self.assertEqual(res.verdict, DecisionVerdict.REFUTED)
        self.assertIn("refutação", res.reason.lower())

    def test_policy_controversial_on_high_dispersion(self):
        """Dispersão superior a 50% entre experimentos compatíveis resulta em CONTROVERSIAL."""
        ep1 = MemoryEpisode(id="e1", experiment_id="exp_fast", query="q", response="1.0ms", status=EvidenceStatus.VALID)
        ep2 = MemoryEpisode(id="e2", experiment_id="exp_slow", query="q", response="2.5ms", status=EvidenceStatus.VALID)

        comp = ComparisonResult(
            metric_compared="latency",
            ranking=[
                {"rank": 1, "experiment_id": "exp_fast", "metric_value": 1.0, "unit": "ms"},
                {"rank": 2, "experiment_id": "exp_slow", "metric_value": 2.5, "unit": "ms"}
            ],
            summary="exp_fast superou exp_slow em 150%"
        )

        res = DecisionPolicyService.evaluate(
            has_theoretical_basis=True,
            empirical_episodes=[ep1, ep2],
            completeness_scores=[0.8, 0.8],
            staleness_analyses=[StalenessAnalysis(is_stale=False), StalenessAnalysis(is_stale=False)],
            comparison=comp
        )
        self.assertEqual(res.verdict, DecisionVerdict.CONTROVERSIAL)
        self.assertIn("alta dispersão", res.reason)

    def test_policy_favorable_on_convergent_evidence(self):
        """Evidência válida com boa completude e sem conflito resulta em FAVORABLE."""
        ep = MemoryEpisode(
            id="e1", query="q",
            response="Mecanismo atinge latência estável de 1.4ms sem perdas.",
            status=EvidenceStatus.VALID,
            commit_hash="a4f12b7",
            environment_context={"hardware": "RTX 5090"}
        )

        res = DecisionPolicyService.evaluate(
            has_theoretical_basis=True,
            empirical_episodes=[ep],
            completeness_scores=[0.90],
            staleness_analyses=[StalenessAnalysis(is_stale=False)]
        )
        self.assertEqual(res.verdict, DecisionVerdict.FAVORABLE)

    def test_make_decision_use_case_orchestration(self):
        """Garante que MakeDecisionUseCase orquestra todas as etapas e preserva auditoria."""
        mock_embed = MagicMock()
        mock_embed.embed_text.return_value = [0.1] * 768

        theoretical_chunk = BookChunk(
            id="c1", book_id="b1", book_title="Designing Data-Intensive",
            chunk_index=1, content="Teoria sobre durabilidade e latência.",
            token_count=15, page_number=80, chapter="Cap 5"
        )
        mock_vstore = MagicMock()
        mock_vstore.search.return_value = [ScoredChunk(chunk=theoretical_chunk, score=0.91)]

        empirical_ep = MemoryEpisode(
            id="ep_hydra_01",
            experiment_id="bench_quorum_lan",
            query="latência quorum LAN",
            response="Medição: 1.42 ms estável sob 10GbE",
            provenance=ProvenanceType.EMPIRICAL,
            status=EvidenceStatus.VALID,
            commit_hash="c891f2c",
            environment_context={"hardware": "RTX 5090", "os": "linux"}
        )
        mock_mem = MagicMock()
        mock_mem.search_episodes.return_value = [empirical_ep]

        mock_llm = MagicMock()
        mock_llm.generate_response.return_value = "A recomendação de engenharia é adotar o quorum na LAN 10GbE."

        use_case = MakeDecisionUseCase(
            embedding_port=mock_embed,
            vector_store=mock_vstore,
            memory_port=mock_mem,
            llm_port=mock_llm
        )

        cmd = MakeDecisionCommand(
            query="Qual a viabilidade de replicação com quorum em LAN?",
            target_hardware="RTX 5090",
            target_commit="c891f2c"
        )

        report = use_case.execute(cmd)

        self.assertIsInstance(report, DecisionReport)
        self.assertEqual(report.verdict, DecisionVerdict.FAVORABLE)
        self.assertEqual(report.policy_version, "1.0")
        self.assertIn("ep_hydra_01", report.used_episode_ids)
        self.assertIn("c891f2c", report.used_commit_hashes)
        self.assertIn("Designing Data-Intensive", report.used_source_books)
        self.assertGreater(report.completeness_score, 0.70)
        self.assertFalse(report.staleness_analysis["has_stale_evidence"])


if __name__ == "__main__":
    unittest.main()
