from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.api.v1.assessment import router as assessment_router
from app.api.v1.auth import router as auth_router
from app.api.v1.health import router as health_router
from app.api.v1.jobs import router as jobs_router
from app.api.v1.materials import router as materials_router
from app.api.v1.projects import direct_router as projects_direct_router
from app.api.v1.projects import router as projects_router
from app.api.v1.spaces import router as spaces_router
from app.api.v1.quizzes import router as quizzes_router
from app.api.v1.structure import router as structure_router
from app.api.v1.tutor import router as tutor_router

app = FastAPI(
    title="AI Study Companion API",
    version="0.1.0",
    description="FastAPI backend shell — Phase 04. Service layer owns domain logic; routes stay thin.",
)

# CORS — origins from settings (CORS_ORIGINS, comma-separated) per blueprint §22
_settings = get_settings()
_allow_origins = [o.strip() for o in _settings.cors_origins.split(",") if o.strip()]
if not _allow_origins:
    _allow_origins = ["http://localhost:5173"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Versioned API prefix per blueprint §19: all routes under /api
app.include_router(health_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(spaces_router, prefix="/api/v1")
app.include_router(projects_router, prefix="/api/v1")
app.include_router(projects_direct_router, prefix="/api/v1")
app.include_router(materials_router, prefix="/api/v1")
app.include_router(jobs_router, prefix="/api/v1")
app.include_router(structure_router, prefix="/api/v1")
app.include_router(tutor_router, prefix="/api/v1")
app.include_router(quizzes_router, prefix="/api/v1")
app.include_router(assessment_router, prefix="/api/v1")


@app.get("/")
def root():
    return {"message": "AI Study Companion API — Phase 04 shell", "docs": "/docs", "health": "/api/v1/health"}
