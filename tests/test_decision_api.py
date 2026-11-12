import unittest
import asyncio
from unittest.mock import MagicMock
import httpx

from src.adapters.inbound.api.fastapi_app import app, get_decision_use_case
from src.domain.entities.decision import DecisionReport, DecisionVerdict


class TestDecisionAPI(unittest.TestCase):
    """Testa o endpoint POST /api/v1/decisions."""

    def setUp(self):
        self.mock_use_case = MagicMock()
        app.dependency_overrides[get_decision_use_case] = lambda: self.mock_use_case

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_post_decisions_returns_structured_report(self):
        """Endpoint retorna o DecisionResponseDTO completo e determinístico."""
        fake_report = DecisionReport(
            decision_id="dec_test_001",
            query="Qual codec usar para baixa latência?",
            recommendation="Adotar NVENC H.264",
            verdict=DecisionVerdict.FAVORABLE,
            policy_version="1.0",
            completeness_score=0.92,
            relevance_score=0.89,
            used_commit_hashes=["a4f12b7"],
            used_source_books=["WebRTC Guide"],
            limitations=["Limitado à RTX 5090"],
            next_validation_steps=["Validar em AV1"]
        )
        self.mock_use_case.execute.return_value = fake_report

        async def _run():
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                payload = {
                    "query": "Qual codec usar para baixa latência?",
                    "target_hardware": "RTX 5090",
                    "target_commit": "a4f12b7"
                }
                resp = await client.post("/api/v1/decisions", json=payload)
                self.assertEqual(resp.status_code, 200)
                data = resp.json()
                self.assertEqual(data["decision_id"], "dec_test_001")
                self.assertEqual(data["verdict"], "FAVORABLE")
                self.assertEqual(data["policy_version"], "1.0")
                self.assertIn("a4f12b7", data["used_commit_hashes"])
                self.assertIn("WebRTC Guide", data["used_source_books"])

        asyncio.run(_run())

    def test_post_decisions_validation_error_422(self):
        """Payload com query curta (< 5 chars) retorna 422."""
        async def _run():
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                payload = {"query": "abc"}
                resp = await client.post("/api/v1/decisions", json=payload)
                self.assertEqual(resp.status_code, 422)

        asyncio.run(_run())


if __name__ == "__main__":
    unittest.main()
