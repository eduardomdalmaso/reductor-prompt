import unittest
import asyncio
from unittest.mock import patch, MagicMock
import httpx

from src.adapters.inbound.api.fastapi_app import app
from src.domain.entities.memory import MemoryEpisode, ProvenanceType, EvidenceStatus
from src.domain.exceptions.exceptions import EvidenceConflictException


class TestEvidenceAPI(unittest.TestCase):
    """Testa o endpoint POST /api/v1/evidence garantindo os status HTTP 201, 200, 409 e 422."""

    def test_ingest_evidence_created_201(self):
        """Nova evidência deve retornar HTTP 201 Created."""
        async def _run():
            fake_episode = MemoryEpisode(
                id="ev_12345",
                query="Latência NVENC",
                response="1.42ms",
                provenance=ProvenanceType.EMPIRICAL,
                status=EvidenceStatus.VALID,
                project_source="HydraStream",
                experiment_id="exp_01",
                content_hash="hash_abc"
            )

            with patch("src.adapters.inbound.api.fastapi_app.IngestEvidenceUseCase") as mock_uc_cls:
                mock_uc = MagicMock()
                mock_uc.execute.return_value = (fake_episode, True)
                mock_uc_cls.return_value = mock_uc

                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                    payload = {
                        "query": "Latência NVENC",
                        "response": "1.42ms por frame",
                        "project_source": "HydraStream",
                        "experiment_id": "exp_01",
                        "commit_hash": "a4f12b7",
                        "environment_context": {"gpu": "RTX 5090"}
                    }
                    resp = await client.post("/api/v1/evidence", json=payload)
                    self.assertEqual(resp.status_code, 201)
                    data = resp.json()
                    self.assertTrue(data["is_created"])
                    self.assertEqual(data["id"], "ev_12345")
                    self.assertEqual(data["project_source"], "HydraStream")

        asyncio.run(_run())

    def test_ingest_evidence_idempotent_duplicate_200(self):
        """Reenvio de evidência idêntica deve retornar HTTP 200 OK (idempotência)."""
        async def _run():
            fake_episode = MemoryEpisode(
                id="ev_12345",
                query="Latência NVENC",
                response="1.42ms",
                provenance=ProvenanceType.EMPIRICAL,
                status=EvidenceStatus.VALID,
                project_source="HydraStream",
                experiment_id="exp_01",
                content_hash="hash_abc"
            )

            with patch("src.adapters.inbound.api.fastapi_app.IngestEvidenceUseCase") as mock_uc_cls:
                mock_uc = MagicMock()
                mock_uc.execute.return_value = (fake_episode, False)
                mock_uc_cls.return_value = mock_uc

                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                    payload = {
                        "query": "Latência NVENC",
                        "response": "1.42ms por frame",
                        "project_source": "HydraStream",
                        "experiment_id": "exp_01",
                        "commit_hash": "a4f12b7"
                    }
                    resp = await client.post("/api/v1/evidence", json=payload)
                    self.assertEqual(resp.status_code, 200)
                    data = resp.json()
                    self.assertFalse(data["is_created"])
                    self.assertIn("existente retornada", data["message"])

        asyncio.run(_run())

    def test_ingest_evidence_conflict_409(self):
        """Conflito de conteúdo no mesmo experimento deve retornar HTTP 409 Conflict."""
        async def _run():
            with patch("src.adapters.inbound.api.fastapi_app.IngestEvidenceUseCase") as mock_uc_cls:
                mock_uc = MagicMock()
                mock_uc.execute.side_effect = EvidenceConflictException("exp_01", "Conteúdo modificado")
                mock_uc_cls.return_value = mock_uc

                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                    payload = {
                        "query": "Latência NVENC",
                        "response": "NOVO VALOR DIVERGENTE",
                        "project_source": "HydraStream",
                        "experiment_id": "exp_01",
                        "commit_hash": "a4f12b7"
                    }
                    resp = await client.post("/api/v1/evidence", json=payload)
                    self.assertEqual(resp.status_code, 409)
                    self.assertIn("Conflito de evidência", resp.json()["detail"])

        asyncio.run(_run())

    def test_ingest_evidence_validation_error_422(self):
        """Payload com campos faltantes obrigatórios deve retornar HTTP 422 Unprocessable Entity."""
        async def _run():
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                payload = {
                    "query": "x",  # Muito curto (min_length=3)
                    # project_source e commit_hash faltando
                }
                resp = await client.post("/api/v1/evidence", json=payload)
                self.assertEqual(resp.status_code, 422)

        asyncio.run(_run())


if __name__ == "__main__":
    unittest.main()
