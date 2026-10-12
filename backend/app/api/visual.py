"""API endpoints for visual delivery metrics and client-side tracking capabilities."""

from typing import Any

from fastapi import APIRouter, status

from app.models.visual import (
    VisualAnalysisRequest,
    VisualAnalysisResponse,
    VisualMetrics,
)
from app.pipeline.visual_features import (
    ETHICAL_DISCLAIMER_TEXT,
    compute_visual_metrics,
)

router = APIRouter(prefix="/visual", tags=["Visual Pipeline"])


def generate_objective_observations(metrics: VisualMetrics) -> list[str]:
    """Generate objective, non-judgmental observations based on geometric measurements."""
    observations: list[str] = []

    # Gaze observation
    if metrics.face_detected_ratio > 0.5:
        pct_center = int(metrics.centered_gaze_ratio * 100)
        observations.append(
            f"Estimated gaze: directed toward camera center in ~{pct_center}% of frames."
        )
    else:
        observations.append("Face visibility was limited during this session.")

    # Head stability observation
    if metrics.head_stability_score >= 0.85:
        observations.append("Head position remained relatively steady across the session.")
    elif metrics.head_stability_score >= 0.6:
        observations.append("Moderate head movement observed across the session.")
    else:
        observations.append(
            "Frequent head repositioning recorded. Consider checking camera positioning."
        )

    # Hand gesture observation
    if metrics.hands_visible_ratio > 0.3:
        gpm = metrics.hand_gestures_per_minute
        observations.append(
            f"Hand movement frequency: approximately {gpm:.1f} gesture episodes per minute."
        )
    else:
        observations.append(
            "Hands were mostly outside camera view, which is normal for standard desktop framing."
        )

    return observations


@router.post(
    "/analyze",
    response_model=VisualAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Compute objective visual delivery metrics from landmark timeseries",
    description=(
        "Analyzes client-side extracted facial and pose landmark coordinates. "
        "Calculates approximate gaze orientation, head stability, and hand gesture frequency. "
        "Strictly privacy-preserving: raw video is never sent or stored."
    ),
)
def analyze_visual_stream(payload: VisualAnalysisRequest) -> VisualAnalysisResponse:
    """Analyze geometric landmark frames and produce visual delivery metrics."""
    metrics = compute_visual_metrics(
        frames=payload.frames,
        known_duration_seconds=payload.recording_duration_seconds,
    )
    observations = generate_objective_observations(metrics)

    return VisualAnalysisResponse(
        status="success",
        metrics=metrics,
        recommendations=observations,
    )


@router.get(
    "/capabilities",
    summary="Get visual tracking capabilities and privacy specifications",
)
def get_visual_capabilities() -> dict[str, Any]:
    """Return supported visual measurement capabilities and ethical boundaries."""
    return {
        "privacy_model": "client_side_processing",
        "raw_video_retention": "none",
        "supported_features": [
            "approximate_gaze_direction",
            "head_centroid_stability",
            "hand_gesture_frequency",
        ],
        "mediapipe_version": "1.1.0",
        "ethical_design": {
            "disclaimer": ETHICAL_DISCLAIMER_TEXT,
            "prohibited_features": [
                "emotion_recognition",
                "confidence_scoring",
                "honesty_detection",
                "personality_assessment",
                "likeability_rating",
            ],
        },
    }
