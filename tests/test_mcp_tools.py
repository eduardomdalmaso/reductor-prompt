import unittest
from unittest.mock import MagicMock, patch

from mcp.server.mcpserver import MCPServer
from src.adapters.inbound.mcp.decision_tools import register_decision_tools
from src.domain.entities.decision import DecisionReport, DecisionVerdict


class TestMCPTools(unittest.TestCase):
    def test_register_and_run_make_decision_tool(self):
        mcp = MCPServer("TestMCP")
        register_decision_tools(mcp)

        mock_report = DecisionReport(
            decision_id="dec_test_123",
            query="Qual codec usar para WebRTC?",
            verdict=DecisionVerdict.FAVORABLE,
            recommendation="Adotar H.264 / Opus com base em baixa latência.",
            justification="Benchmarks empíricos comprovam latência < 2ms.",
            empirical_evidence=[
                {"experiment_id": "exp_01", "semantic_score": 0.91, "completeness_score": 1.0, "is_stale": False}
            ],
            theoretical_basis=[{"book_title": "Pion WebRTC", "score": 0.89}],
            policy_version="1.0.0",
            created_at="2026-11-12T12:00:00Z",
            used_source_books=["Pion WebRTC"]
        )

        with patch("src.adapters.inbound.mcp.decision_tools.MakeDecisionUseCase") as mock_uc_cls:
            mock_uc = MagicMock()
            mock_uc.execute.return_value = mock_report
            mock_uc_cls.return_value = mock_uc

            from src.domain.ports.inbound import MakeDecisionCommand
            cmd = MakeDecisionCommand(query="Qual codec usar para WebRTC?")
            report = mock_uc.execute(cmd)

            self.assertEqual(report.verdict, DecisionVerdict.FAVORABLE)
            self.assertEqual(report.decision_id, "dec_test_123")
            self.assertIn("Pion WebRTC", report.used_source_books)


if __name__ == "__main__":
    unittest.main()
