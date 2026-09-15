from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check():
    """Health-check endpoint — Phase 04 shell, no DB/AI side effects."""
    return {"status": "ok"}
