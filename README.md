# Cynbit Discovery Intelligence

An AI-assisted project discovery proof of concept that turns a client brief into structured requirements, source evidence, missing information, potential risks, and follow-up questions.

> Assessment prototype only. Outputs require human review. Do not submit confidential client information to the public demo.

## What it does

- Accepts a text brief through a FastAPI endpoint.
- Uses an OpenRouter-compatible chat completion model to propose structured requirements.
- Requests JSON-mode output where supported, parses a valid object if a model prepends explanatory text, and checks evidence against the source brief.
- Validates the response with Pydantic.
- Distinguishes confirmed (`stated`), provisional (`tentative`), and missing (`unknown`) requirements.
- Adds deterministic follow-up questions and basic risk flags.
- Displays the result in a Streamlit dashboard and allows JSON download.

Evidence matching is a useful guardrail, not proof that a quote semantically supports an interpretation. Tentative language such as “might,” “approximately,” and “not final” is treated as provisional rather than confirmed. The prototype is not production-ready and does not claim measured business impact.

## Architecture

```text
Streamlit UI -> FastAPI /analyze -> OpenRouter LLM
                                  -> JSON parsing
                                  -> evidence checks
                                  -> Pydantic validation
                                  -> deterministic fallbacks
                                  -> structured discovery report
```

## Requirements

- Python 3.11 or newer recommended
- An OpenRouter API key
- Internet access for model inference

## Setup (PowerShell)

1. Create and activate a virtual environment:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. Install dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

3. Create your local environment file:

   ```powershell
   Copy-Item .env.example .env
   ```

4. Edit `.env` and set your own key and model:

   ```dotenv
   OPENROUTER_API_KEY=your_key_here
   OPENROUTER_MODEL=openrouter/free
   LLM_TIMEOUT_SECONDS=60
   ```

   The free model router may select different models over time; output quality and availability can vary. 

   Optional API rate-limit settings (defaults: 5 analysis requests per client IP per 60 seconds): 

   ```dotenv 
   ANALYZE_RATE_LIMIT_REQUESTS=5 
   ANALYZE_RATE_LIMIT_WINDOW_SECONDS=60 
   ```

## Run the API

From the project root:

```powershell
uvicorn app.main:app --reload
```

- Health check: http://127.0.0.1:8000/health
- Interactive API docs: http://127.0.0.1:8000/docs

## Run the dashboard

Open a second terminal, activate the same virtual environment, then run:

```powershell
streamlit run ui/streamlit_app.py
```

The dashboard defaults to `http://127.0.0.1:8000` for the API and waits up to 180 seconds for a response, which can be useful with slower hosted models. To change the API address, set `API_URL` before starting Streamlit.

## API example

`POST /analyze`

```json
{
  "brief": "We need an AI support assistant connected to our CRM. It should launch in four weeks. Our support team will use it. We have not selected a CRM vendor or established a budget."
}
```

The response includes `project_goal`, `target_users`, `integrations`, `timeline`, `budget`, `security_requirements`, `missing_information`, `potential_risks`, and `discovery_questions`.

## Tests and evaluation

Run the offline test suite:

```powershell
python -m pytest -q
```

Run the labeled evaluation suite (this calls the configured model and may incur API usage):

```powershell
python -m evals.run_evaluation
```

For a quick smoke run, evaluate only the first three cases:

```powershell
python -m evals.run_evaluation --limit 3
```

The evaluation dataset is in `evals/discovery_eval.json`. A timestamped, case-level report is written to `reports/evaluation_results.json`. It includes field-status accuracy, stated-field precision/recall/F1, literal evidence source-match rate, labeled value checks, missing-information exact-match rate, and latency. These are dataset-specific measurements, not a general guarantee of correctness. Review the report's limitations before quoting any score. Do not commit API keys or real client briefs.

## Reports

- [AI Opportunity Report](reports/ai_opportunity_report.md)
- [Technical Approach Report](reports/technical_approach.md)

## Limitations and safety

- This is an assessment proof of concept, not a production deployment.
- Model output can be wrong even when it matches the schema.
- Exact quote matching does not establish semantic support.
- Contradiction detection and risk coverage are limited.
- Use synthetic briefs in a public demo; review provider data-handling terms before sending real client information.
- Keep `.env` out of version control and never commit API keys.
