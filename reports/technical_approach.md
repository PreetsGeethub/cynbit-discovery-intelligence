@'
# Technical Approach Report: Cynbit Discovery Intelligence

**Project:** Cynbit Discovery Intelligence  
**Assessment:** AI/ML Engineer Intern  
**Implementation status:** Working API analysis flow; dashboard and evaluation should be verified before submission.

## 1. Problem and Design Goals

The prototype converts an unstructured client brief into a structured discovery artifact that a human can review.

The core engineering problem is not merely generating a plausible summary. The system must distinguish information explicitly supported by the input from information that remains unknown, expose missing requirements, and avoid silently inventing project constraints.

### Design goals

1. Accept a bounded text brief through an API.
2. Extract a consistent set of requirement fields.
3. retain supporting evidence from the source brief.
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
  |
  | POST /analyze
  v
FastAPI Endpoint
  |
  v
LLM Analysis Layer
  |
  +--> OpenRouter-compatible chat completion API
  |
  v
JSON Parsing
  |
  v
Evidence Verification
  |
  v
Pydantic Schema Validation
  |
  v
Deterministic Missing-Field and Risk Checks
  |
  v
Structured Discovery Result
  |
  +--> Requirement summary
  +--> Evidence snippets
  +--> Missing information
  +--> Potential risks
  +--> Discovery questions
  +--> JSON download