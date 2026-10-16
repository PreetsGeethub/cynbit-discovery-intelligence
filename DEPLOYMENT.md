# Deployment guide

## 1. Deploy the FastAPI backend on Render

This repository includes `render.yaml` for the API service. The blueprint deploys the `fix/evidence-and-question-deduplication` branch and uses the lean `requirements-api.txt` dependency list.

1. Push/pull the latest feature branch to GitHub and confirm the new `render.yaml` is present.
2. Sign in to Render and choose **New + → Blueprint** (or create a Web Service manually).
3. Connect `PreetsGeethub/cynbit-discovery-intelligence` and select branch `fix/evidence-and-question-deduplication`.
4. If using the blueprint, review the service settings before applying it. If creating manually, use:
   - Runtime: Python 3
   - Build command: `pip install -r requirements-api.txt`
   - Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - Health check path: `/health`
5. In Render environment variables, set `OPENROUTER_API_KEY` to your private key. Never put the key in Git or this file. Confirm `OPENROUTER_MODEL` is `openrouter/free`, and keep the timeout and rate-limit variables set.
6. Deploy and wait for the service to become healthy.
7. Test `https://YOUR-API.onrender.com/health` in a browser. Expected JSON: `{"status":"ok"}`. Then open `/docs` to inspect the API. Do not run the model evaluation as a deployment check.

The default per-IP limit is 5 `/analyze` requests per 60 seconds. The limiter is in-memory and is suitable only for a single API process; it is not shared across instances. OpenRouter quota limits are separate from this application limit. Render free services may sleep when idle, so the first request after inactivity can be slow.

## 2. Deploy the Streamlit dashboard on Community Cloud

1. Create/sign in to a Streamlit Community Cloud account at https://share.streamlit.io/.
2. Choose **Create app** and select this GitHub repository.
3. Select branch `fix/evidence-and-question-deduplication` and entrypoint `ui/streamlit_app.py`.
4. In **Advanced settings**, choose Python 3.12 (or another supported version compatible with the project).
5. Deploy the app. The root `requirements.txt` contains the dashboard and API client dependencies.
6. After deployment, open app settings and add this environment variable under **Secrets** using TOML syntax:

   ```toml
   API_URL = "https://YOUR-API.onrender.com"
   API_REQUEST_TIMEOUT_SECONDS = "180"
   ```

   Replace the placeholder with the actual Render service URL. Do not put the OpenRouter API key in Streamlit secrets; only the backend needs it.
7. Save/reboot the Streamlit app and test a short, non-confidential synthetic brief. The first API call can take a while if the Render service was sleeping.

## 3. Post-deployment smoke checks

- `GET /health` returns HTTP 200.
- `GET /docs` loads.
- A short brief is rejected by the API with HTTP 422 before a model call.
- A valid synthetic brief returns a structured report.
- Repeated requests beyond the configured limit return HTTP 429 with a `Retry-After` header.
- Provider rate/quota errors return a controlled HTTP 503.
- The Streamlit app displays the report and JSON download.

Use synthetic data only in this public assessment demo. Deployment is not complete until you verify both services and the dashboard-to-API connection.
