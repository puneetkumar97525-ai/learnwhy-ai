import json
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import admin, auth, educator, learning
from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.seed import seed_database
from app.services.tutor import tutor_adapter

EVAL_REPORT_PATH = Path(__file__).resolve().parent.parent.parent / "evaluation" / "latest_evaluation_report.json"


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_database(db)
    yield


app = FastAPI(
    title="LearnWhy AI API",
    description=(
        "PSM147 / QE4 — An Explainable, Misconception-Aware Personalized Learning Platform "
        "Using Knowledge Tracing and Adaptive Remediation."
    ),
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(learning.router)
app.include_router(educator.router)
app.include_router(admin.router)


@app.get("/api/health", tags=["system"])
def health_check():
    """
    Public health check endpoint. Never exposes secrets or personal learner data.
    """
    return {
        "status": "ok",
        "product": settings.APP_NAME,
        "problem_id": "PSM147 / QE4",
        "version": settings.APP_VERSION,
        "rule_engine_version": settings.RULE_ENGINE_VERSION,
        "mastery_model_version": settings.MASTERY_MODEL_VERSION,
        "mastery_alpha": settings.MASTERY_ALPHA,
        "llm_tutor_adapter": "enabled" if tutor_adapter.is_enabled else "deterministic_curated_fallback",
    }


@app.get("/api/evaluation/report", tags=["research"])
def get_evaluation_report():
    """Returns the latest reproducible evaluation report comparing Baseline A and Proposed B."""
    if EVAL_REPORT_PATH.exists():
        with open(EVAL_REPORT_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "status": "not_generated",
        "message": "Run `python3 evaluation/evaluate_methods.py` to generate the report.",
    }

