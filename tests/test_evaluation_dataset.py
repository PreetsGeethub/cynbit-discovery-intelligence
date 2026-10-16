import json
from pathlib import Path

FIELDS = {
    "project_goal",
    "target_users",
    "integrations",
    "timeline",
    "budget",
    "security_requirements",
}
DATASET = Path(__file__).resolve().parents[1] / "evals" / "discovery_eval.json"


def test_evaluation_dataset_has_labeled_cases_for_every_requirement_field():
    data = json.loads(DATASET.read_text(encoding="utf-8"))
    assert len(data["cases"]) >= 10
    ids = [case["id"] for case in data["cases"]]
    assert len(ids) == len(set(ids))

    for case in data["cases"]:
        assert set(case["expected_status"]) == FIELDS
        assert set(case["expected_status"].values()) <= {"stated", "unknown"}
        assert isinstance(case["brief"], str) and case["brief"].strip()
