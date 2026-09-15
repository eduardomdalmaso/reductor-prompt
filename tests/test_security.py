import pytest
from fastapi.testclient import TestClient
from src.adapters.inbound.api.fastapi_app import app
from src.config.settings import settings
from scripts.fetch_books import is_safe_public_url


client = TestClient(app)


def test_ssrf_blocking_local_ips():
    """Valida que URLs apontando para loopback, RFC 1918 e metadata são bloqueadas."""
    dangerous_urls = [
        "http://127.0.0.1:11434/api/tags",
        "http://localhost:8000/health",
        "http://0.0.0.0:8001",
        "http://169.254.169.254/latest/meta-data/",
        "http://10.0.0.1/admin",
        "http://192.168.1.1/router",
        "file:///etc/passwd",
        "ftp://example.com/file.pdf"
    ]
    for url in dangerous_urls:
        is_safe, reason = is_safe_public_url(url)
        assert not is_safe, f"URL perigosa não foi bloqueada: {url}"
        assert "bloqueado" in reason.lower() or "não permitido" in reason.lower() or "proibido" in reason.lower()


def test_fetch_endpoint_rejects_ssrf():
    """Testa se o endpoint /api/v1/fetch rejeita requisições SSRF com HTTP 400."""
    response = client.post("/api/v1/fetch", json={
        "urls": "http://127.0.0.1:11434/api/generate",
        "ingest_after": False
    })
    assert response.status_code == 400
    assert "SSRF" in response.json()["detail"]


def test_auth_security_key_enforcement(monkeypatch):
    """Testa se o middleware de autenticação protege endpoints quando API_SECURITY_KEY está configurada."""
    monkeypatch.setattr(settings, "API_SECURITY_KEY", "super-secret-key-123")

    # 1. Sem token -> 401 Unauthorized
    response_unauth = client.post("/api/v1/ingest")
    assert response_unauth.status_code == 401

    # 2. Token incorreto -> 401 Unauthorized
    response_wrong = client.post("/api/v1/ingest", headers={"X-API-Key": "wrong-key"})
    assert response_wrong.status_code == 401

    # 3. Token correto via X-API-Key -> 200 OK
    response_ok = client.get("/api/v1/queries/export", headers={"X-API-Key": "super-secret-key-123"})
    assert response_ok.status_code == 200

    # 4. Token correto via Authorization Bearer -> 200 OK
    response_bearer = client.get("/api/v1/queries/export", headers={"Authorization": "Bearer super-secret-key-123"})
    assert response_bearer.status_code == 200


def test_cors_configuration():
    """Valida que o CORS está configurado com origens específicas e métodos seguros."""
    response = client.options("/api/v1/books", headers={
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "GET"
    })
    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers
