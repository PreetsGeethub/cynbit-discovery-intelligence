
from fastapi import FastAPI

app = FastAPI(
    title="Cynbit Discovery Intelligence",
    description="Evidence-backed client discovery and requirement analysis.",
    version="0.1.0",
)


@app.get("/")
def root():
    return {
        "name": "Cynbit Discovery Intelligence",
        "status": "running",
        "version": "0.1.0",
    }


@app.get("/health")
def health():
    return {"status": "ok"}
