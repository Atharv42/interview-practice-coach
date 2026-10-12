"""Health and system status routes."""

from fastapi import APIRouter

from app.models.schemas import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse, summary="Service health check")
def health_check() -> HealthResponse:
    """Return application operational status."""
    return HealthResponse(
        status="healthy",
        version="0.1.0",
        service="interview-practice-coach-backend",
    )
