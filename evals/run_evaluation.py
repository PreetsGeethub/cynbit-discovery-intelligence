"""Run a repeatable labeled evaluation against the configured LLM.

Usage:
    python -m evals.run_evaluation
    python -m evals.run_evaluation --output reports/evaluation_results.json

This calls the configured provider and can incur API usage. Results are observations
for this model/configuration and dataset, not a general guarantee of correctness.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from app import llm

ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = ROOT / "evals" / "discovery_eval.json"
FIELDS = (
    "project_goal",
    "target_users",
    "integrations",
    "timeline",
    "budget",
    "security_requirements",
)


def normalize(text: str) -> str:
    return " ".join(text.casefold().split())


def safe_rate(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 4) if denominator else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="reports/evaluation_results.json")
    parser.add_argument("--limit", type=int, default=0, help="Evaluate only the first N cases (0 means all).")
    args = parser.parse_args()

    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    cases = dataset["cases"][: args.limit or None]
    if not cases:
        print("Evaluation dataset contains no cases.", file=sys.stderr)
        return 2

    status_total = 0
    status_correct = 0
    tp = fp = fn = 0
    evidence_total = 0
    evidence_source_matches = 0
    stated_with_evidence = 0
    stated_count = 0
    expected_stated_count = 0
    value_checks_total = 0
    value_checks_passed = 0
    results = []
    failures = 0
    durations = []

    for case in cases:
        started = time.perf_counter()
        record = {"id": case["id"], "expected_status": case["expected_status"]}
        try:
            output = llm.analyze_brief(case["brief"])
            elapsed = round(time.perf_counter() - started, 3)
            durations.append(elapsed)
            actual_status = {}
            field_results = {}
            for field in FIELDS:
                expected = case["expected_status"][field]
                requirement = getattr(output, field)
                actual = requirement.status
                actual_status[field] = actual
                status_total += 1
                status_correct += int(actual == expected)
                expected_stated = expected == "stated"
                actual_stated = actual == "stated"
                expected_stated_count += int(expected_stated)
                stated_count += int(actual_stated)
                tp += int(expected_stated and actual_stated)
                fp += int(not expected_stated and actual_stated)
                fn += int(expected_stated and not actual_stated)

                if actual_stated:
                    stated_with_evidence += int(bool(requirement.evidence))
                for quote in requirement.evidence:
                    evidence_total += 1
                    evidence_source_matches += int(
                        isinstance(quote, str) and quote.strip() in case["brief"]
                    )

                checks = case.get("value_contains", {}).get(field, [])
                checks_passed = [
                    token for token in checks
                    if token.casefold() in normalize(requirement.value or "")
                ]
                value_checks_total += len(checks)
                value_checks_passed += len(checks_passed)
                field_results[field] = {
                    "expected_status": expected,
                    "actual_status": actual,
                    "status_correct": actual == expected,
                    "value": requirement.value,
                    "evidence": requirement.evidence,
                    "evidence_source_matches": all(
                        isinstance(q, str) and q.strip() in case["brief"]
                        for q in requirement.evidence
                    ),
                    "value_checks": checks,
                    "value_checks_passed": checks_passed,
                }

            expected_missing = sorted(
                field.replace("_", " ")
                for field, status in case["expected_status"].items()
                if status == "unknown"
            )
            actual_missing = sorted(output.missing_information)
            missing_correct = expected_missing == actual_missing
            record.update({
                "ok": True,
                "elapsed_seconds": elapsed,
                "fields": field_results,
                "expected_missing_information": expected_missing,
                "actual_missing_information": actual_missing,
                "missing_information_exact_match": missing_correct,
                "discovery_questions": [
                    {"question": q.question, "priority": q.priority}
                    for q in output.discovery_questions
                ],
                "potential_risks": output.potential_risks,
                "notes": case.get("notes"),
            })
        except KeyboardInterrupt:
            elapsed = round(time.perf_counter() - started, 3)
            record.update({
                "ok": False,
                "interrupted": True,
                "elapsed_seconds": elapsed,
                "error_type": "KeyboardInterrupt",
                "error": "Interrupted by user; this case was not scored.",
            })
            failures += 1
            elapsed = round(time.perf_counter() - started, 3)
            record.update({
                "ok": False,
                "elapsed_seconds": elapsed,
                "error_type": type(exc).__name__,
                "error": str(exc),
            })
        results.append(record)
        print(f"[{'OK' if record['ok'] else 'FAIL'}] {case['id']} ({record['elapsed_seconds']}s)")
        if record.get("interrupted"):
            print("Evaluation interrupted; writing a partial report for completed cases.")
            break

    total_expected = len(cases) * len(FIELDS)
    precision = safe_rate(tp, tp + fp)
    recall = safe_rate(tp, tp + fn)
    f1 = round(2 * precision * recall / (precision + recall), 4) if precision is not None and recall is not None and precision + recall else None
    field_accuracy = safe_rate(status_correct, status_total)
    evidence_match_rate = safe_rate(evidence_source_matches, evidence_total)
    evidence_coverage = safe_rate(stated_with_evidence, stated_count)
    value_check_rate = safe_rate(value_checks_passed, value_checks_total)
    missing_exact = [r for r in results if r.get("ok")]
    missing_accuracy = safe_rate(
        sum(r["missing_information_exact_match"] for r in missing_exact),
        len(missing_exact),
    )
    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset_path": "evals/discovery_eval.json",
        "cases_requested": len(cases),
        "cases_completed": len(results),
        "cases_succeeded": sum(1 for item in results if item.get("ok")),
        "cases_failed": sum(1 for item in results if not item.get("ok")),
        "cases_not_run": max(0, len(cases) - len(results)),
        "interrupted": any(item.get("interrupted") for item in results),
        "field_status_accuracy": field_accuracy,
        "stated_field_precision": precision,
        "stated_field_recall": recall,
        "stated_field_f1": f1,
        "evidence_source_match_rate": evidence_match_rate,
        "stated_fields_with_evidence_rate": evidence_coverage,
        "labeled_value_check_rate": value_check_rate,
        "missing_information_exact_match_rate": missing_accuracy,
        "field_statuses_evaluated": status_total,
        "expected_stated_fields": expected_stated_count,
        "actual_stated_fields": stated_count,
        "evidence_quotes_evaluated": evidence_total,
        "labeled_value_checks": value_checks_total,
        "mean_case_latency_seconds": round(sum(durations) / len(durations), 3) if durations else None,
        "limitations": [
            "Status labels and value checks are manually authored for this synthetic dataset.",
            "Evidence source-match rate checks literal presence only; it does not prove semantic support.",
            "Discovery-question usefulness and risk quality require human review and are not scored automatically.",
            "A small synthetic dataset is not representative of all real client briefs.",
            "Model/provider configuration may change; record the configured model when comparing runs."
        ],
        "cases": results,
    }
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = ROOT / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("\nEvaluation summary")
    for key in (
        "cases_succeeded", "cases_failed", "field_status_accuracy",
        "stated_field_precision", "stated_field_recall", "stated_field_f1",
        "evidence_source_match_rate", "stated_fields_with_evidence_rate",
        "labeled_value_check_rate", "missing_information_exact_match_rate",
        "mean_case_latency_seconds",
    ):
        print(f"{key}: {summary[key]}")
    print(f"Full report: {output_path}")
    return 1 if failures or len(results) < len(cases) else 0


if __name__ == "__main__":
    raise SystemExit(main())
