"""API endpoints for practice session management, persistence, and historical analytics."""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.models.analytics import AnalyticsDashboardResponse
from app.models.session import (
    SessionCreateRequest,
    SessionDeleteResponse,
    SessionDetailResponse,
    SessionListResponse,
)
from app.storage.session_repository import (
    SessionAlreadyExistsError,
    SessionRepository,
)

router = APIRouter(prefix="/sessions", tags=["Practice Sessions"])


def get_session_repo() -> SessionRepository:
    """Dependency provider for SessionRepository."""
    return SessionRepository()


@router.post(
    "",
    response_model=SessionDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create or save a practice session with delivery metrics",
    description=(
        "Persists practice session metadata, audio transcript and metrics, "
        "visual metrics, and calculated session feature vectors. "
        "Strictly privacy-preserving: raw audio and video files are never stored."
    ),
)
def create_session(
    payload: SessionCreateRequest,
    repo: SessionRepository = Depends(get_session_repo),
) -> SessionDetailResponse:
    """Persist session metadata and delivery mechanics into local storage."""
    try:
        return repo.create_session(payload)
    except SessionAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to persist practice session: {e}",
        ) from e


@router.get(
    "",
    response_model=SessionListResponse,
    status_code=status.HTTP_200_OK,
    summary="List historical practice sessions with summaries and pagination",
    description="Returns stored practice sessions ordered by creation date.",
)
def list_sessions(
    limit: int = Query(default=50, ge=1, le=100, description="Max sessions to return"),
    offset: int = Query(default=0, ge=0, description="Number of sessions to skip"),
    order: str = Query(
        default="desc",
        pattern="^(?i:asc|desc)$",
        description="Sort order by created_at ('asc' or 'desc')",
    ),
    repo: SessionRepository = Depends(get_session_repo),
) -> SessionListResponse:
    """List session summaries with pagination and chronological sorting."""
    summaries, total = repo.list_sessions(limit=limit, offset=offset, order=order)
    return SessionListResponse(
        total=total,
        limit=limit,
        offset=offset,
        sessions=summaries,
    )


@router.get(
    "/analytics/summary",
    response_model=AnalyticsDashboardResponse,
    status_code=status.HTTP_200_OK,
    summary="Compute aggregate PCA, clustering, and trends across stored sessions",
    description=(
        "Pulls chronological session history directly from the database and runs "
        "unsupervised 2D PCA dimensionality reduction, K-Means delivery clustering, "
        "and pacing trend regressions."
    ),
)
def get_persisted_sessions_analytics(
    repo: SessionRepository = Depends(get_session_repo),
) -> AnalyticsDashboardResponse:
    """Compute longitudinal delivery trends and PCA archetype clustering from database."""
    return repo.compute_analytics_summary()


@router.get(
    "/{session_id}",
    response_model=SessionDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve detailed session metrics by ID",
    description="Returns the full metadata, transcript, audio metrics, and visual metrics.",
)
def get_session(
    session_id: str,
    repo: SessionRepository = Depends(get_session_repo),
) -> SessionDetailResponse:
    """Fetch complete session details by unique identifier."""
    session = repo.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with ID '{session_id}' not found.",
        )
    return session


@router.delete(
    "/{session_id}",
    response_model=SessionDeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Permanently delete a practice session and all its metrics",
    description=(
        "Permanently removes the session record, audio metrics, transcript, "
        "visual metrics, and feature vectors. Supports user-driven privacy and data deletion."
    ),
)
def delete_session(
    session_id: str,
    repo: SessionRepository = Depends(get_session_repo),
) -> SessionDeleteResponse:
    """Permanently delete a session and cascading records."""
    deleted = repo.delete_session(session_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with ID '{session_id}' not found.",
        )
    return SessionDeleteResponse(
        session_id=session_id,
        deleted=True,
        message=f"Session '{session_id}' and all associated metrics were permanently deleted.",
    )
