# Technical Approach Report: Cynbit Discovery Intelligence

**Project:** Cynbit Discovery Intelligence  
**Assessment:** AI/ML Engineer Intern  
**Implementation status:** FastAPI backend and Streamlit dashboard are deployed and have been exercised together. The backend retries once with stricter instructions when the model returns malformed/non-JSON content. Offline tests and the labeled model evaluation should be run before making any claims about measured accuracy.

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
8. Limit repeated API requests and handle upstream provider throttling safely.
9. Keep model configuration and credentials outside source control.

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
- `status`: `stated` for confirmed information, `tentative` for provisional or uncertain information, or `unknown` when no supported value is available.

The response also includes `missing_information`, `potential_risks`, and `discovery_questions`.

## 5. Analysis Pipeline

### Step 1: Request validation
FastAPI validates the request body before analysis. Briefs outside the permitted length limits should fail validation before reaching the model.

### Step 2: Structured model request
The prompt asks the model to return JSON, use only facts supported by the brief, include source quotations, preserve uncertainty, leave absent information unknown, and avoid inventing vendors, budgets, or deadlines. JSON mode is requested when supported; compatibility errors fall back to the prompt-only contract. Prompt instructions improve behavior but are not a correctness boundary.

### Step 3: JSON parsing
The analysis layer rejects empty output, strips optional Markdown fences, and parses JSON. If explanatory text appears before an otherwise valid JSON object, it extracts the object and continues through the same schema and evidence checks. Malformed JSON or an unexpected top-level structure raises a controlled error.

### Step 4: Evidence verification
For each requirement, the application checks whether an evidence snippet is a non-empty string appearing verbatim in the original brief. A field is marked `stated` only if a non-empty value and matching evidence exist without clear uncertainty cues. Qualifiers such as “might,” “approximately,” or “not final” cause supported values to be marked `tentative`. An explicitly undecided budget remains `unknown`. If usable evidence is absent, the value becomes null, evidence is cleared, and status becomes `unknown`.

This prevents unsupported quotations from being accepted as evidence. It does not prove that a matching quote semantically supports the extracted value; a stronger implementation could track source offsets and add human-reviewed semantic-support tests.

### Step 5: Schema validation
The normalized response is passed through Pydantic. The schema constrains statuses and question priorities to known values.

### Step 6: Derive missing information
The application recomputes missing information from the final requirement statuses. It does not rely on the model's own missing-field list.

### Step 7: Deterministic follow-up questions
For unknown fields, application logic supplies standard questions about business outcome, users, integrations, launch date, budget, and security/privacy requirements. Tentative fields receive clarification questions about whether the option or estimate is confirmed. Existing questions are checked to reduce duplicates.

### Step 8: Basic risk flags
If relevant fields are unknown or tentative, deterministic checks can flag unclear or unconfirmed integration scope, an unspecified or estimated timeline, an unspecified budget, or missing security/privacy requirements. These are preliminary indicators, not a complete risk assessment.

### Step 9: Return the result
The API returns a structured response. Analysis failures are logged server-side and exposed through a controlled HTTP error rather than returning a raw traceback. The analysis endpoint also applies a configurable, process-local per-IP sliding-window limit (default 5 requests per 60 seconds), returning HTTP 429 and a `Retry-After` header. Upstream OpenRouter rate-limit/quota errors (including HTTP 402/429) are mapped to a generic HTTP 503 with a retry hint; provider-specific details are not exposed. Provider timeouts return HTTP 504, and the dashboard distinguishes timeout, connection, and API errors. The dashboard's default request timeout is longer than the configured model timeout to account for slower model responses.

## 6. Prompt Engineering and Reliability

The prototype uses a constrained extraction task rather than asking the model to independently design a complete solution. Prompt priorities are faithfulness, evidence-backed extraction, explicit unknowns, consistent JSON, and useful questions.

The current implementation requests JSON mode where supported and retries once with stricter instructions if the response cannot be parsed as a JSON object. This bounded retry helps recover from occasional non-JSON responses from free-model routing, but it does not guarantee success. For a production implementation, consider provider-supported JSON-schema output, selective retries for transient provider failures, versioned prompts and model identifiers, and logging validation failures without logging confidential briefs. Schema validity is not the same as factual correctness.

## 7. Evaluation

A repeatable evaluation harness is available in `evals/`.

### Run the evaluation

After configuring `.env` with `OPENROUTER_API_KEY` and `OPENROUTER_MODEL`, run:

```bash
python -m evals.run_evaluation
```

The runner calls the configured model for each labeled synthetic brief and writes a timestamped report to `reports/evaluation_results.json`. It can incur provider API usage. To run only the first few cases while iterating:

```bash
python -m evals.run_evaluation --limit 3
```

The checked-in dataset currently contains 12 cases covering complete, vague, partial, security-focused, ambiguous, contradictory, and minimal briefs. Expected statuses and selected value checks are manually labeled in `evals/discovery_eval.json`.

### Reported metrics

- **Field-status accuracy:** fraction of evaluated fields whose `stated`/`unknown` status matches the labeled expectation.
- **Stated-field precision, recall, and F1:** treats `stated` as the positive class.
- **Evidence source-match rate:** fraction of returned evidence snippets that appear literally in the original brief.
- **Stated-fields-with-evidence rate:** fraction of fields returned as stated that include at least one evidence snippet.
- **Labeled value-check rate:** fraction of manually specified expected value tokens found in extracted values.
- **Missing-information exact-match rate:** fraction of successful cases whose missing-field list exactly matches the list implied by the labeled statuses.
- **Mean case latency:** average wall-clock time for successful calls.

The runner records case-level outputs, exceptions, questions, risks, and timings to support failure analysis. A failed model call is counted as a failed case and is not silently dropped from the case success/failure totals.

### Interpretation and limitations

No score should be claimed until the runner has actually been executed. Metrics are specific to this synthetic dataset, the selected model/router, and the time of the run. Evidence source-match is a lexical check and does not prove that a quotation semantically supports the extracted value. Value-token checks are lightweight proxies rather than full semantic scoring. Discovery-question usefulness, risk quality, and contradiction handling still require human review. The labeled dataset should be reviewed and expanded as failures are found.

## 7.1. Automated reliability tests

Run the offline suite with:

```bash
python -m pytest -q
```

Tests cover requirement normalization, evidence rejection/matching, question fallback deduplication, API input validation, health checks, and controlled API errors. These tests do not call the external model unless the evaluation runner is invoked.

## 8. Security and Privacy

This is an assessment demonstration, not a production-approved system.

- Keep API keys in `.env` and exclude that file from Git.
- Commit only a sanitized `.env.example`.
- Use synthetic briefs in the public demo.
- Avoid logging full briefs or credentials.
- Review provider data handling and retention terms before sending real client information.
- Add authentication and shared-store rate limits before exposing the service publicly; the current in-memory limiter is intended for a single process only.
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
