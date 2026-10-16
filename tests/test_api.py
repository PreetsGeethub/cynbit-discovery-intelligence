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


def _valid_extraction():
    from app.schemas import DiscoveryExtraction, Requirement

    unknown = Requirement(value=None, evidence=[], status="unknown")
    return DiscoveryExtraction(
        project_goal=unknown,
        target_users=unknown,
        integrations=unknown,
        timeline=unknown,
        budget=unknown,
        security_requirements=unknown,
    )


def test_analyze_rate_limit_returns_429_and_retry_after(monkeypatch):
    from app.rate_limit import analyze_rate_limiter

    analyze_rate_limiter.reset()
    monkeypatch.setattr(analyze_rate_limiter, "limit", 2)
    monkeypatch.setattr(analyze_rate_limiter, "window_seconds", 60)
    with patch("app.main.analyze_brief", return_value=_valid_extraction()):
        first = client.post(
            "/analyze", json={"brief": "We need an internal support portal."}
        )
        second = client.post(
            "/analyze", json={"brief": "We need an internal support portal."}
        )
        third = client.post(
            "/analyze", json={"brief": "We need an internal support portal."}
        )

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 429
    assert third.headers["retry-after"]
    assert third.json()["detail"] == "Rate limit exceeded. Please retry later."
    analyze_rate_limiter.reset()


def test_provider_rate_limit_returns_controlled_503():
    from app.provider_errors import ProviderRateLimitError

    with patch(
        "app.main.analyze_brief",
        side_effect=ProviderRateLimitError("provider quota details should not leak"),
    ):
        response = client.post(
            "/analyze", json={"brief": "We need an internal support portal."}
        )

    assert response.status_code == 503
    assert response.headers["retry-after"] == "30"
    assert "provider quota details should not leak" not in response.text
