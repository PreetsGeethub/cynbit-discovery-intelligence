
import logging

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.llm import analyze_brief
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


@app.post("/analyze", response_model=DiscoveryExtraction)
def analyze(request: AnalyzeRequest):
    try:
        return analyze_brief(request.brief)
    except Exception as exc:
        logger.error("Analysis failed (%s)", type(exc).__name__)
        raise HTTPException(
            status_code=502,
            detail="Analysis failed. Check server logs.",
        ) from exc
