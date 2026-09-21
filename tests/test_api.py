from starlette.testclient import TestClient
from src.adapters.inbound.api.fastapi_app import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "ReductorPrompt"


def test_list_books_endpoint():
    response = client.get("/api/v1/books")
    assert response.status_code == 200
    data = response.json()
    assert "books" in data
    assert isinstance(data["books"], list)


def test_query_context_only_endpoint():
    payload = {
        "query": "Como funciona LSM Tree?",
        "only_context": True,
        "max_tokens": 1000
    }
    response = client.post("/api/v1/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert "tokens_used" in data
    assert data["tokens_used"] >= 0
    assert data["reduction_percentage"] >= 0.0
