import json
import os
from types import SimpleNamespace

# Configure dummy credentials before importing the client module. Tests replace
# the model call, so these values are never used for a network request.
os.environ.setdefault("OPENROUTER_API_KEY", "test-key")
os.environ.setdefault("OPENROUTER_MODEL", "test-model")

import pytest

from app import llm


def fake_response(payload, content_override=None):
    content = content_override if content_override is not None else json.dumps(payload)
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=content),
                finish_reason="stop",
            )
        ]
    )


def model_payload(**overrides):
    payload = {
        "project_goal": {
            "value": "Support assistant",
            "evidence": ["We need a support assistant."],
            "status": "unknown",  # The server must derive status itself.
        },
        "target_users": {"value": "Support team", "evidence": ["Support team"], "status": "stated"},
        "integrations": {"value": "CRM", "evidence": ["CRM"], "status": "stated"},
        "timeline": {"value": "Four weeks", "evidence": ["four weeks"], "status": "stated"},
        "budget": {"value": None, "evidence": [], "status": "unknown"},
        "security_requirements": {"value": None, "evidence": [], "status": "unknown"},
        "missing_information": [],
        "potential_risks": [],
        "discovery_questions": [],
    }
    payload.update(overrides)
    return payload


def test_valid_exact_evidence_is_marked_stated(monkeypatch):
    brief = "We need a support assistant. Support team will use it; CRM integration; launch in four weeks."
    payload = model_payload()
    payload["target_users"]["evidence"] = ["Support team"]
    payload["integrations"]["evidence"] = ["CRM"]
    payload["timeline"]["evidence"] = ["four weeks"]

    monkeypatch.setattr(
        llm.client.chat.completions,
        "create",
        lambda **kwargs: fake_response(payload),
    )

    result = llm.analyze_brief(brief)

    assert result.project_goal.status == "stated"
    assert result.project_goal.evidence == ["We need a support assistant."]
    assert result.project_goal.value == "Support assistant"


def test_unsupported_evidence_is_rejected_and_requirement_becomes_unknown(monkeypatch):
    brief = "We need a support assistant."
    payload = model_payload()
    payload["project_goal"] = {
        "value": "Support assistant",
        "evidence": ["The company approved a $50,000 budget."],
        "status": "stated",
    }

    monkeypatch.setattr(
        llm.client.chat.completions,
        "create",
        lambda **kwargs: fake_response(payload),
    )

    result = llm.analyze_brief(brief)

    assert result.project_goal.status == "unknown"
    assert result.project_goal.value is None
    assert result.project_goal.evidence == []
    assert "project goal" in result.missing_information


def test_unknown_fields_get_deterministic_questions_and_risks(monkeypatch):
    brief = "We are exploring an internal tool."
    payload = {
        field: {"value": "invented", "evidence": ["not in brief"], "status": "stated"}
        for field in llm.REQUIREMENT_FIELDS
    }
    payload.update({
        "missing_information": [],
        "potential_risks": [],
        "discovery_questions": [],
    })

    monkeypatch.setattr(
        llm.client.chat.completions,
        "create",
        lambda **kwargs: fake_response(payload),
    )

    result = llm.analyze_brief(brief)

    questions = [
    item["question"] if isinstance(item, dict) else item.question
    for item in result.discovery_questions
]
    assert len(set(questions)) == len(llm.REQUIREMENT_FIELDS)
    assert any("business outcome" in question for question in questions)
    assert any("budget range" in question for question in questions)
    assert any("Integration scope is unclear" in risk for risk in result.potential_risks)
    assert any("timeline is unspecified" in risk for risk in result.potential_risks)


def test_markdown_json_fence_is_accepted(monkeypatch):
    brief = "We need a support assistant."
    payload = model_payload()
    fenced = "```json\n" + json.dumps(payload) + "\n```"

    monkeypatch.setattr(
        llm.client.chat.completions,
        "create",
        lambda **kwargs: fake_response(payload, content_override=fenced),
    )

    result = llm.analyze_brief(brief)

    assert result.project_goal.status == "stated"
