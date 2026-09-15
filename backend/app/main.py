from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.auth import router as auth_router
from app.api.v1.health import router as health_router
from app.api.v1.spaces import router as spaces_router

app = FastAPI(
    title="AI Study Companion API",
    version="0.1.0",
    description="FastAPI backend shell — Phase 04. Service layer owns domain logic; routes stay thin.",
)

# CORS — locked to frontend origin per blueprint §22; permissive for local dev in shell phase
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Versioned API prefix per blueprint §19: all routes under /api
app.include_router(health_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(spaces_router, prefix="/api/v1")


@app.get("/")
def root():
    return {"message": "AI Study Companion API — Phase 04 shell", "docs": "/docs", "health": "/api/v1/health"}
