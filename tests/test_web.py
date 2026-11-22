from fastapi.testclient import TestClient

from audit_rag.theme import GITHUB_URL
from audit_rag.web import app


def test_home_page_renders() -> None:
    with TestClient(app) as client:
        response = client.get("/")
    assert response.status_code == 200
    text = response.text
    assert "audit-rag-assistant" in text
    assert GITHUB_URL in text
    assert 'id="q"' in text
    assert "demo, not an audit" in text.lower()
    assert "SWC Registry" in text
    assert "not-so-smart-contracts" in text


def test_health_endpoint() -> None:
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] in {"ok", "no-index"}
