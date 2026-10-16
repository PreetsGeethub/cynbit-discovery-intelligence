import json
import os
from types import SimpleNamespace

# Configure dummy credentials before importing the client module. Tests replace
# the model call, so these values are never used for a network request.
os.environ.setdefault("OPENROUTER_API_KEY", "test-key")
os.environ.setdefault("OPENROUTER_MODEL", "test-model")

from app import llm
from app.schemas import DiscoveryQuestion


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
            "status": "unknown",  # The server derives status itself.
        },
        "target_users": {
            "value": "Support team",
            "evidence": ["Support team"],
            "status": "stated",
        },
        "integrations": {
            "value": "CRM",
            "evidence": ["CRM"],
            "status": "stated",
        },
        "timeline": {
            "value": "Four weeks",
            "evidence": ["four weeks"],
            "status": "stated",
        },
        "budget": {"value": None, "evidence": [], "status": "unknown"},
        "security_requirements": {
            "value": None,
            "evidence": [],
            "status": "unknown",
        },
        "missing_information": [],
        "potential_risks": [],
        "discovery_questions": [],
    }
    payload.update(overrides)
    return payload


def test_valid_exact_evidence_is_marked_stated(monkeypatch):
    brief = (
        "We need a support assistant. Support team will use it; "
        "CRM integration; launch in four weeks."
    )
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


def test_evidence_matching_allows_whitespace_variation_and_returns_source_quote(monkeypatch):
    brief = (
        "We need a customer support portal.\n"
        "It must integrate with Salesforce and our existing customer database."
    )
    payload = model_payload()
    payload["project_goal"]["evidence"] = ["We need a customer support portal."]
    payload["integrations"] = {
        "value": "Salesforce and existing customer database",
        "evidence": [
            "It must integrate with   Salesforce and our existing customer database."
        ],
        "status": "unknown",
    }

    monkeypatch.setattr(
        llm.client.chat.completions,
        "create",
        lambda **kwargs: fake_response(payload),
    )

    result = llm.analyze_brief(brief)

    assert result.integrations.status == "stated"
    assert result.integrations.evidence == [
        "It must integrate with Salesforce and our existing customer database."
    ]


def test_specific_questions_suppress_generic_fallbacks(monkeypatch):
    brief = (
        "We need a customer support portal for 50 internal support agents. "
        "It must integrate with Salesforce and our existing customer database. "
        "It will process customer contact details and requires role-based access control."
    )
    payload = model_payload()
    payload["integrations"] = {
        "value": "Salesforce and customer database",
        "evidence": ["The CRM is configured with a new API."],
        "status": "stated",
    }
    payload["security_requirements"] = {
        "value": "Role-based access control",
        "evidence": ["All data is encrypted at rest."],
        "status": "stated",
    }
    payload["discovery_questions"] = [
        {
            "question": "What Salesforce objects and data need to be integrated?",
            "priority": "high",
        },
        {
            "question": "What roles and permissions are needed for role-based access control?",
            "priority": "high",
        },
        {
            "question": "Are there compliance requirements for customer contact details?",
            "priority": "high",
        },
    ]

    monkeypatch.setattr(
        llm.client.chat.completions,
        "create",
        lambda **kwargs: fake_response(payload),
    )

    result = llm.analyze_brief(brief)
    questions = [item.question for item in result.discovery_questions]

    assert not any(
        question == "Which systems must the solution integrate with?"
        for question in questions
    )
    assert not any(
        question == "What security, privacy, or compliance requirements apply?"
        for question in questions
    )
    assert all(isinstance(item, DiscoveryQuestion) for item in result.discovery_questions)


def test_unknown_fields_get_deterministic_questions_and_risks(monkeypatch):
    brief = "We are exploring an internal tool."
    payload = {
        field: {
            "value": "invented",
            "evidence": ["not in brief"],
            "status": "stated",
        }
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

    questions = [item.question for item in result.discovery_questions]
    assert len(set(questions)) == len(llm.REQUIREMENT_FIELDS)
    assert any("business outcome" in question for question in questions)
    assert any("budget range" in question for question in questions)
    assert any(
        "Integration scope is unclear" in risk
        for risk in result.potential_risks
    )
    assert any(
        "timeline is unspecified" in risk
        for risk in result.potential_risks
    )


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


def test_json_object_after_explanatory_text_is_parsed(monkeypatch):
    brief = "We need a support assistant."
    payload = model_payload()
    content = "Let me analyze the brief first.\n\n" + json.dumps(payload)

    monkeypatch.setattr(
        llm.client.chat.completions,
        "create",
        lambda **kwargs: fake_response(payload, content_override=content),
    )

    result = llm.analyze_brief(brief)

    assert result.project_goal.status == "stated"


def test_tentative_vendor_and_estimated_timeline_are_not_confirmed(monkeypatch):
    brief = (
        "We need a customer support dashboard for our business. "
        "We might integrate Salesforce in the future, but the CRM decision is not final. "
        "We expect to launch in approximately two months. "
        "Our budget has not been decided yet."
    )
    payload = model_payload()
    payload["project_goal"] = {
        "value": "Customer support dashboard",
        "evidence": ["We need a customer support dashboard for our business."],
        "status": "stated",
    }
    payload["integrations"] = {
        "value": "Salesforce integration",
        "evidence": ["Salesforce"],
        "status": "stated",
    }
    payload["timeline"] = {
        "value": "Approximately two months",
        "evidence": ["approximately two months"],
        "status": "stated",
    }
    payload["budget"] = {
        "value": "Undecided",
        "evidence": ["Our budget has not been decided yet."],
        "status": "stated",
    }

    monkeypatch.setattr(
        llm.client.chat.completions,
        "create",
        lambda **kwargs: fake_response(payload),
    )

    result = llm.analyze_brief(brief)

    assert result.project_goal.status == "stated"
    assert result.integrations.status == "tentative"
    assert result.integrations.value == "Salesforce integration"
    assert result.timeline.status == "tentative"
    assert result.budget.status == "unknown"
    assert result.budget.value is None
    assert "budget" in result.missing_information
    assert any("integration" in item.question.casefold() or "salesforce" in item.question.casefold()
               for item in result.discovery_questions)
    assert any("timeline" in item.question.casefold() or "deadline" in item.question.casefold()
               for item in result.discovery_questions)


def test_empty_model_response_is_rejected(monkeypatch):
    monkeypatch.setattr(
        llm.client.chat.completions,
        "create",
        lambda **kwargs: fake_response(model_payload(), content_override=""),
    )

    try:
        llm.analyze_brief("We need a support assistant for our team.")
    except ValueError as exc:
        assert "empty content" in str(exc).lower()
    else:
        raise AssertionError("Expected empty model output to raise ValueError")


def test_invalid_json_response_retries_once_then_succeeds(monkeypatch):
    brief = "We need a support assistant for our team."
    payload = model_payload()
    responses = iter(
        [
            fake_response(payload, content_override="User Safety: safe"),
            fake_response(payload),
        ]
    )

    monkeypatch.setattr(
        llm.client.chat.completions,
        "create",
        lambda **kwargs: next(responses),
    )

    result = llm.analyze_brief(brief)

    assert result.project_goal.status == "stated"


def test_malformed_json_response_is_rejected(monkeypatch):
    monkeypatch.setattr(
        llm.client.chat.completions,
        "create",
        lambda **kwargs: fake_response(model_payload(), content_override="{not json"),
    )

    try:
        llm.analyze_brief("We need a support assistant for our team.")
    except ValueError as exc:
        assert "invalid json" in str(exc).lower()
    else:
        raise AssertionError("Expected malformed JSON to raise ValueError")


def test_non_object_model_response_is_rejected(monkeypatch):
    monkeypatch.setattr(
        llm.client.chat.completions,
        "create",
        lambda **kwargs: fake_response(
            model_payload(), content_override='["not", "an object"]'
        ),
    )

    try:
        llm.analyze_brief("We need a support assistant for our team.")
    except ValueError as exc:
        assert "json object" in str(exc).lower()
    else:
        raise AssertionError("Expected a non-object response to raise ValueError")
