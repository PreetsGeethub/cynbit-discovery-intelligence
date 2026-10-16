import logging

from fastapi import Depends, FastAPI, HTTPException
from openai import APITimeoutError
from pydantic import BaseModel, Field

from app.llm import analyze_brief
from app.provider_errors import ProviderRateLimitError
from app.rate_limit import analyze_rate_limiter
from app.schemas import DiscoveryExtraction

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Cynbit Discovery Intelligence",
    description="Evidence-backed client discovery and requirement analysis.",
    version="0.3.0",
)


class AnalyzeRequest(BaseModel):
    brief: str = Field(min_length=20, max_length=15000)


@app.get("/")
def root():
    return {
        "name": "Cynbit Discovery Intelligence",
        "status": "running",
        "version": "0.3.0",
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post(
    "/analyze",
    response_model=DiscoveryExtraction,
    dependencies=[Depends(analyze_rate_limiter.check)],
)
def analyze(request: AnalyzeRequest):
    try:
        return analyze_brief(request.brief)
    except APITimeoutError as exc:
        logger.warning("Analysis provider timed out")
        raise HTTPException(
            status_code=504,
            detail="The analysis provider took too long to respond. Please retry.",
        ) from exc
    except ProviderRateLimitError as exc:
        logger.warning("Analysis provider rate limit/quota reached")
        raise HTTPException(
            status_code=503,
            detail=(
                "The analysis provider is temporarily rate-limiting requests "
                "or has reached its quota. Please retry later."
            ),
            headers={"Retry-After": "30"},
        ) from exc
    except Exception as exc:
        logger.error("Analysis failed (%s)", type(exc).__name__)
        raise HTTPException(
            status_code=502,
            detail="Analysis failed. Check server logs.",
        ) from exc
