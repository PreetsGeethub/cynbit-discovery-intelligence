import os
from unittest.mock import patch

from fastapi.testclient import TestClient

os.environ.setdefault("OPENROUTER_API_KEY", "test-key")
os.environ.setdefault("OPENROUTER_MODEL", "test-model")

from app.main import app

client = TestClient(app)


def test_health_endpoint_is_available():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_analyze_rejects_briefs_that_are_too_short_without_calling_model():
    with patch("app.main.analyze_brief") as analyze:
        response = client.post("/analyze", json={"brief": "too short"})

    assert response.status_code == 422
    analyze.assert_not_called()


def test_analyze_returns_controlled_error_when_analysis_fails():
    with patch("app.main.analyze_brief", side_effect=RuntimeError("provider details should not leak")):
        response = client.post(
            "/analyze",
            json={"brief": "We need a support portal for our internal team."},
        )

    assert response.status_code == 502
    assert response.json() == {"detail": "Analysis failed. Check server logs."}
    assert "provider details should not leak" not in response.text


def test_analyze_rejects_missing_brief():
    response = client.post("/analyze", json={})
    assert response.status_code == 422
