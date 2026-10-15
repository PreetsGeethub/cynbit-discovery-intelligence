# Technical Approach Report: Cynbit Discovery Intelligence

**Project:** Cynbit Discovery Intelligence  
**Assessment:** AI/ML Engineer Intern  
**Implementation status:** API analysis flow has been exercised successfully; dashboard and evaluation should be verified before submission.

## 1. Problem and Design Goals

The prototype converts an unstructured client brief into a structured discovery artifact that a human can review. The engineering challenge is to distinguish information explicitly supported by the input from information that remains unknown, expose missing requirements, and avoid silently inventing project constraints.

Design goals:
1. Accept a bounded text brief through an API.
2. Extract a consistent set of requirement fields.
3. Retain supporting evidence from the source brief.
4. Mark fields unknown when evidence is absent or invalid.
5. Validate model output against a typed schema.
6. Generate follow-up questions for missing information.
7. Handle invalid model responses through controlled errors.
8. Keep model configuration and credentials outside source control.

## 2. Architecture

```text
User
  |
  v
Streamlit Dashboard
  | POST /analyze
  v
FastAPI Endpoint
  |
  v
LLM Analysis Layer ----> OpenRouter-compatible chat completion API
  |
  v
JSON Parsing -> Evidence Verification -> Pydantic Validation
  |
  v
Deterministic Missing-Field and Risk Checks
  |
  v
Structured Discovery Result -> Dashboard and JSON download
```

Streamlit is the presentation layer, FastAPI handles HTTP requests, and the analysis module coordinates inference and post-processing. Pydantic defines the contract between generated data and the application. The LLM proposes content; application code validates it.

## 3. Technology Choices

| Component | Technology | Reason |
|---|---|---|
| API | FastAPI | Typed request/response models and HTTP error handling |
| Validation | Pydantic | Explicit schema and validation of structured output |
| LLM client | OpenAI-compatible Python client | Supports the configured OpenRouter endpoint |
| Model routing | OpenRouter | Allows model configuration to change without rewriting the app |
| UI | Streamlit | Rapid demonstration without a separate frontend build |
| Configuration | Environment variables | Keeps credentials and deployment settings out of code |
| Tests | Pytest | Supports repeatable local tests |
| HTTP client | Requests | Lets the dashboard call the API |

The model identifier is configurable. A free model router may select different models over time, so quality and availability can vary. The exact model used should be recorded during evaluation.

## 4. Input and Output Contract

The API accepts a brief as text, with minimum and maximum length constraints. The response includes six requirement objects: `project_goal`, `target_users`, `integrations`, `timeline`, `budget`, and `security_requirements`.

Each requirement contains:
- `value`: extracted value, or null when unknown.
- `evidence`: supporting text snippets from the source brief.
- `status`: `stated` or `unknown`.

The response also includes `missing_information`, `potential_risks`, and `discovery_questions`.

## 5. Analysis Pipeline

### Step 1: Request validation
FastAPI validates the request body before analysis. Briefs outside the permitted length limits should fail validation before reaching the model.

### Step 2: Structured model request
The prompt asks the model to return JSON, use only facts supported by the brief, include exact quotations, leave absent information unknown, and avoid inventing vendors, budgets, or deadlines. Prompt instructions improve behavior but are not a correctness boundary.

### Step 3: JSON parsing
The analysis layer rejects empty output, strips optional Markdown fences, and parses JSON. Malformed JSON or an unexpected top-level structure raises an error.

### Step 4: Evidence verification
For each requirement, the application checks whether an evidence snippet is a non-empty string appearing verbatim in the original brief. A field is marked `stated` only if a non-empty value and at least one matching evidence snippet exist. Otherwise, the value becomes null, evidence is cleared, and status becomes `unknown`.

This prevents unsupported quotations from being accepted as evidence. It does not prove that a matching quote semantically supports the extracted value; a stronger implementation could track source offsets and add human-reviewed semantic-support tests.

### Step 5: Schema validation
The normalized response is passed through Pydantic. The schema constrains statuses and question priorities to known values.

### Step 6: Derive missing information
The application recomputes missing information from the final requirement statuses. It does not rely on the model's own missing-field list.

### Step 7: Deterministic follow-up questions
For missing fields, application logic supplies standard questions about business outcome, users, integrations, launch date, budget, and security/privacy requirements. Existing questions are checked to reduce duplicates.

### Step 8: Basic risk flags
If relevant fields are unknown, deterministic checks can flag unclear integration scope, an unspecified timeline, an unspecified budget, or missing security/privacy requirements. These are preliminary indicators, not a complete risk assessment.

### Step 9: Return the result
The API returns a structured response. Analysis failures are logged server-side and exposed through a controlled HTTP error rather than returning a raw traceback.

## 6. Prompt Engineering and Reliability

The prototype uses a constrained extraction task rather than asking the model to independently design a complete solution. Prompt priorities are faithfulness, evidence-backed extraction, explicit unknowns, consistent JSON, and useful questions.

For a production implementation, consider provider-supported JSON-schema output, bounded retry logic for transient failures, request timeouts, versioned prompts and model identifiers, and logging validation failures without logging confidential briefs. Schema validity is not the same as factual correctness.

## 7. Evaluation Plan

Use 15–20 synthetic client briefs covering:

- Fully specified requirements.
- Missing fields.
- Ambiguous wording such as "launch soon".
- Contradictory statements, such as two launch dates.
- Evidence quotations absent from the source.
- Empty or malformed model responses.
- Minimal briefs with little usable scope.

Measure:
- **Field extraction accuracy:** whether values represent the source brief.
- **Evidence precision:** whether accepted quotations match the source and support the field.
- **Unknown-field handling:** whether absent requirements remain unknown.
- **Missing-information recall:** whether genuinely missing categories are identified.
- **Question usefulness:** reviewer judgment of relevance and actionability.
- **Failure handling:** whether invalid model output causes controlled behavior.

Record dataset size, labeling rules, model identifier, observed results, and representative failures. No evaluation score is claimed until measured.

## 8. Security and Privacy

This is an assessment demonstration, not a production-approved system.

- Keep API keys in `.env` and exclude that file from Git.
- Commit only a sanitized `.env.example`.
- Use synthetic briefs in the public demo.
- Avoid logging full briefs or credentials.
- Review provider data handling and retention terms before sending real client information.
- Add authentication and rate limits before exposing the service publicly.
- Require human approval before a discovery summary becomes a client commitment.

A successful endpoint response does not establish production readiness. Authentication, access control, observability, deployment hardening, and data policies need separate work.

## 9. Limitations and Next Steps

The current workflow focuses on text briefs and structured requirement analysis. Document uploads, CRM integration, autonomous actions, and multi-user production deployment are not established as implemented.

Known limitations include exact-match evidence checks, possible semantic misinterpretation, variable model output, limited risk detection, and unmeasured question usefulness.

Recommended next steps:
1. Verify the dashboard and API together.
2. Add offline tests for schema validation, evidence checks, missing-field derivation, and deterministic fallbacks.
3. Create a labeled synthetic evaluation set.
4. Record observed results and failure cases.
5. Improve contradiction detection and evidence traceability.
6. Add authentication, monitoring, and approved data handling before a production pilot.

## 10. Conclusion

Cynbit Discovery Intelligence combines LLM-based extraction with typed validation and deterministic post-processing. Its central design choice is to treat model output as a proposal that must pass application checks rather than as ground truth.

The prototype demonstrates practical AI engineering through API design, structured outputs, validation, error handling, a user-facing interface, and an evaluation plan. It should be judged by evidence correctness, unknown handling, and usefulness to human reviewers—not by the presence of an LLM alone.
