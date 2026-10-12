"""Pydantic schemas for visual delivery metrics, landmark tracking, and privacy-first analysis."""


from pydantic import BaseModel, Field


class LandmarkPoint(BaseModel):
    """Normalized 2D/3D geometric landmark coordinates (0.0 to 1.0)."""

    x: float = Field(..., description="Normalized horizontal coordinate")
    y: float = Field(..., description="Normalized vertical coordinate")
    z: float | None = Field(None, description="Optional normalized depth coordinate")


class VisualFrameSample(BaseModel):
    """Timestamped geometric sample extracted client-side (no raw video stored)."""

    timestamp: float = Field(..., ge=0.0, description="Timestamp of frame in seconds")
    # Face landmark proxies: nose tip, left eye corners, right eye corners, irises
    nose_tip: LandmarkPoint | None = Field(None, description="Nose bridge or tip coordinate")
    left_eye_inner: LandmarkPoint | None = Field(None, description="Left eye inner corner")
    left_eye_outer: LandmarkPoint | None = Field(None, description="Left eye outer corner")
    left_iris: LandmarkPoint | None = Field(None, description="Left pupil/iris center")
    right_eye_inner: LandmarkPoint | None = Field(None, description="Right eye inner corner")
    right_eye_outer: LandmarkPoint | None = Field(None, description="Right eye outer corner")
    right_iris: LandmarkPoint | None = Field(None, description="Right pupil/iris center")
    # Pose landmark proxies: wrists
    left_wrist: LandmarkPoint | None = Field(None, description="Left wrist coordinate")
    right_wrist: LandmarkPoint | None = Field(None, description="Right wrist coordinate")


class VisualMetrics(BaseModel):
    """Objective geometric delivery indicators (no emotion or personality inferences)."""

    total_duration_seconds: float = Field(..., ge=0.0, description="Duration analyzed in seconds")
    frames_analyzed: int = Field(..., ge=0, description="Total video/landmark frames sampled")
    face_detected_ratio: float = Field(
        ..., ge=0.0, le=1.0, description="Ratio of frames with a detected face"
    )
    centered_gaze_ratio: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Estimated ratio of frames where gaze was oriented toward the camera cone",
    )
    gaze_distribution: dict[str, float] = Field(
        default_factory=dict,
        description="Gaze directions distribution ('center', 'left', 'right', 'up', 'down')",
    )
    head_stability_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Stability index: 1.0 = steady, 0.0 = high displacement variance",
    )
    head_movement_variance: float = Field(
        ..., ge=0.0, description="Variance of head centroid position across sampled frames"
    )
    hands_visible_ratio: float = Field(
        ..., ge=0.0, le=1.0, description="Ratio of frames where at least one hand is visible"
    )
    hand_gestures_per_minute: float = Field(
        ..., ge=0.0, description="Frequency of detected significant hand movements per minute"
    )
    tracking_notes: list[str] = Field(
        default_factory=list, description="Diagnostic notes regarding tracking conditions"
    )
    ethical_disclaimer: str = Field(
        ...,
        description="Disclaimer: geometric proxies only, not emotion/personality detection",
    )


class VisualAnalysisRequest(BaseModel):
    """Payload containing client-side extracted landmark frames."""

    session_id: str | None = Field(None, description="Optional associated session ID")
    recording_duration_seconds: float | None = Field(
        None, ge=0.0, description="Known recording duration in seconds"
    )
    frames: list[VisualFrameSample] = Field(
        default_factory=list, description="Timestamped geometric landmark samples"
    )


class VisualAnalysisResponse(BaseModel):
    """Structured response containing calculated visual delivery metrics."""

    status: str = Field(default="success")
    metrics: VisualMetrics = Field(..., description="Computed geometric visual metrics")
    recommendations: list[str] = Field(
        default_factory=list, description="Objective tips based purely on delivery mechanics"
    )
