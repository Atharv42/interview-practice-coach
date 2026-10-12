"""Pydantic models for multimodal feature aggregation, PCA projection, clustering, and trends."""


from pydantic import BaseModel, Field

from app.models.audio import AudioMetrics
from app.models.visual import VisualMetrics


class SessionFeatureVector(BaseModel):
    """Consolidated numeric feature representation of an individual practice session."""

    session_id: str = Field(..., description="Unique session identifier")
    session_index: int = Field(0, description="Chronological index of session (0, 1, ...)")
    timestamp_iso: str | None = Field(None, description="ISO timestamp of session")
    has_audio: bool = Field(True, description="Whether audio metrics were present")
    has_visual: bool = Field(True, description="Whether visual metrics were present")

    # Audio-derived delivery mechanics
    words_per_minute: float = Field(..., ge=0.0, description="Overall speaking pace")
    articulation_rate_wpm: float = Field(..., ge=0.0, description="Speaking pace excluding pauses")
    filler_words_ratio: float = Field(..., ge=0.0, le=1.0, description="Filler word ratio")
    average_pause_duration_seconds: float = Field(
        ..., ge=0.0, description="Average duration per pause"
    )
    pause_frequency_per_minute: float = Field(
        ..., ge=0.0, description="Number of pauses per minute of speech"
    )

    # Visual-derived delivery mechanics
    centered_gaze_ratio: float = Field(
        ..., ge=0.0, le=1.0, description="Ratio of time gaze was centered"
    )
    head_stability_score: float = Field(
        ..., ge=0.0, le=1.0, description="Normalized head stability index (0.0 - 1.0)"
    )
    hand_gestures_per_minute: float = Field(
        ..., ge=0.0, description="Hand movement gesture frequency per minute"
    )


class PCAProjectionPoint(BaseModel):
    """2D projection coordinate for an individual session in PCA latent space."""

    session_id: str
    session_index: int
    pca_x: float = Field(..., description="First principal component (PC1)")
    pca_y: float = Field(..., description="Second principal component (PC2)")
    cluster_id: int = Field(..., description="Cluster identifier")
    cluster_label: str = Field(
        ...,
        description="Descriptive statistical grouping label (e.g. 'Cluster 0: Steady & Moderate')",
    )


class PCAResult(BaseModel):
    """Exploratory 2D PCA representation of delivery patterns."""

    is_fallback: bool = Field(
        ..., description="True if insufficient samples were available to fit PCA"
    )
    status_message: str = Field(..., description="Explanation of calculation state")
    explained_variance_ratio: list[float] = Field(
        default_factory=list, description="Variance explained by [PC1, PC2]"
    )
    feature_loadings: dict[str, dict[str, float]] = Field(
        default_factory=dict, description="Feature loadings onto PC1 and PC2"
    )
    points: list[PCAProjectionPoint] = Field(
        default_factory=list, description="Projected session coordinates"
    )


class ClusterSummary(BaseModel):
    """Statistical summary of an exploratory delivery archetype cluster."""

    cluster_id: int
    cluster_label: str
    session_count: int
    centroid_features: dict[str, float] = Field(
        default_factory=dict, description="Average feature values for this cluster"
    )
    description: str = Field(
        ..., description="Descriptive statistical profile (not psychological diagnosis)"
    )


class TrendPoint(BaseModel):
    """Individual data point for metric trend charts over successive sessions."""

    session_index: int
    session_id: str
    timestamp_iso: str | None = None
    words_per_minute: float
    filler_words_ratio: float
    average_pause_duration_seconds: float
    centered_gaze_ratio: float
    head_stability_score: float
    hand_gestures_per_minute: float


class TrendAnalysis(BaseModel):
    """Historical delivery mechanics progression over successive sessions."""

    points: list[TrendPoint] = Field(default_factory=list)
    wpm_slope: float = Field(
        0.0, description="Rate of change in speaking pace per session (WPM / session)"
    )
    filler_ratio_slope: float = Field(0.0, description="Rate of change in filler ratio per session")
    pace_direction_summary: str = Field(..., description="Qualitative pace trend observation")
    filler_direction_summary: str = Field(..., description="Qualitative filler trend observation")


class SessionAnalyticsInput(BaseModel):
    """Input payload for session aggregation."""

    session_id: str
    session_index: int = 0
    timestamp_iso: str | None = None
    audio_metrics: AudioMetrics | None = None
    visual_metrics: VisualMetrics | None = None


class BatchAnalyticsRequest(BaseModel):
    """Request payload containing multiple session metrics to analyze."""

    sessions: list[SessionAnalyticsInput] = Field(
        ..., description="List of sessions to aggregate and analyze"
    )


class AnalyticsDashboardResponse(BaseModel):
    """Consolidated response for analytics dashboard."""

    total_sessions_analyzed: int
    pca: PCAResult
    clusters: list[ClusterSummary]
    trends: TrendAnalysis
    ethical_note: str = Field(
        default=(
            "Statistical groupings and projections reflect geometric and acoustic mechanics only. "
            "They do not assess personality, likeability, confidence, or candidate suitability."
        )
    )
