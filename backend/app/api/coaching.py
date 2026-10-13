"""API endpoints for AI coaching, STAR structure evaluation, and content quality feedback."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.sessions import get_session_repo
from app.models.coaching import (
    CoachingEvaluationRequest,
    CoachingEvaluationResponse,
)
from app.pipeline.coaching_engine import evaluate_coaching
from app.storage.session_repository import SessionRepository

router = APIRouter(prefix="/coaching", tags=["AI Coaching Engine"])


@router.post(
    "/evaluate",
    response_model=CoachingEvaluationResponse,
    status_code=status.HTTP_200_OK,
    summary="Evaluate STAR structure and generate personalized delivery coaching",
    description=(
        "Performs comprehensive analysis on interview response text and metrics: "
        "detects STAR components, calculates verbal clarity scores, evaluates cadence, "
        "and generates concrete improvement tips."
    ),
)
def evaluate_interview_response(
    payload: CoachingEvaluationRequest,
    repo: SessionRepository = Depends(get_session_repo),
) -> CoachingEvaluationResponse:
    """Generate structured STAR and delivery coaching feedback."""
    transcript = payload.transcript
    audio_metrics = payload.audio_metrics
    visual_metrics = payload.visual_metrics
    question_prompt = payload.question_prompt

    # If session_id is supplied, pull session data from storage as baseline
    if payload.session_id:
        session = repo.get_session(payload.session_id)
        if not session and not transcript:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Practice session '{payload.session_id}' not found.",
            )
        if session:
            if not transcript:
                transcript = session.transcript
            if audio_metrics is None:
                audio_metrics = session.audio_metrics
            if visual_metrics is None:
                visual_metrics = session.visual_metrics
            if not question_prompt:
                question_prompt = session.title

    return evaluate_coaching(
        transcript=transcript,
        question_prompt=question_prompt,
        session_id=payload.session_id,
        audio_metrics=audio_metrics,
        visual_metrics=visual_metrics,
    )


@router.get(
    "/sessions/{session_id}",
    response_model=CoachingEvaluationResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate AI coaching advice directly for a saved practice session",
    description=(
        "Loads the stored session transcript and delivery metrics to produce "
        "instant coaching advice."
    ),
)
def get_session_coaching(
    session_id: str,
    repo: SessionRepository = Depends(get_session_repo),
) -> CoachingEvaluationResponse:
    """Retrieve structured STAR and delivery evaluation for an existing session."""
    session = repo.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Practice session '{session_id}' not found.",
        )

    return evaluate_coaching(
        transcript=session.transcript,
        question_prompt=session.title,
        session_id=session.session_id,
        audio_metrics=session.audio_metrics,
        visual_metrics=session.visual_metrics,
    )
