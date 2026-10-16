from app.schemas import DiscoveryExtraction


def test_valid_discovery_extraction():
    result = DiscoveryExtraction.model_validate({
        "project_goal": {
            "value": "AI support assistant",
            "evidence": ["We need an AI support assistant"],
            "status": "stated",
        },
        "target_users": {
            "value": "Support team",
            "evidence": ["Our support team will use it"],
            "status": "stated",
        },
        "integrations": {
            "value": "CRM",
            "evidence": ["connected to our CRM"],
            "status": "stated",
        },
        "timeline": {
            "value": "Four weeks",
            "evidence": ["launch in four weeks"],
            "status": "stated",
        },
        "budget": {
            "value": None,
            "evidence": [],
            "status": "unknown",
        },
        "security_requirements": {
            "value": None,
            "evidence": [],
            "status": "unknown",
        },
        "missing_information": ["budget", "security requirements"],
        "potential_risks": ["CRM vendor has not been selected"],
        "discovery_questions": [
            {
                "question": "Which CRM will be used?",
                "priority": "high",
            }
        ],
    })

    assert result.timeline.value == "Four weeks"
    assert result.budget.status == "unknown"
    assert isinstance(result.missing_information, list)
    assert isinstance(result.potential_risks, list)


def test_tentative_requirement_status_is_supported():
    result = DiscoveryExtraction.model_validate({
        "project_goal": {
            "value": "Customer support dashboard",
            "evidence": ["We need a customer support dashboard."],
            "status": "stated",
        },
        "target_users": {
            "value": None,
            "evidence": [],
            "status": "unknown",
        },
        "integrations": {
            "value": "Potential Salesforce integration",
            "evidence": ["We might integrate Salesforce."],
            "status": "tentative",
        },
        "timeline": {
            "value": "Approximately two months",
            "evidence": ["approximately two months"],
            "status": "tentative",
        },
        "budget": {
            "value": None,
            "evidence": [],
            "status": "unknown",
        },
        "security_requirements": {
            "value": None,
            "evidence": [],
            "status": "unknown",
        },
    })

    assert result.integrations.status == "tentative"
    assert result.timeline.status == "tentative"
