"""Pydantic schemas and protocol models for real-time streaming WebSocket sessions."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from app.models.audio import AudioMetrics
from app.models.visual import VisualMetrics


class ClientMessageType(StrEnum):
    """Message types received from the client over WebSocket."""

    START = "stream_start"
    AUDIO_CHUNK = "audio_chunk"
    VISUAL_FRAME = "visual_frame"
    STOP = "stream_stop"
    PING = "ping"


class ServerMessageType(StrEnum):
    """Message types emitted by the server to the client over WebSocket."""

    READY = "stream_ready"
    METRICS_UPDATE = "metrics_update"
    ALERT = "alert"
    FINAL_REPORT = "final_report"
    ERROR = "error"
    PONG = "pong"


class StreamStartConfig(BaseModel):
    """Configuration payload sent by client when initializing a live stream."""

    session_id: str | None = Field(None, description="Optional custom session identifier")
    title: str | None = Field(None, description="Optional interview question or topic")
    language: str = Field(default="en", description="Speech language code")
    pause_threshold_seconds: float = Field(
        default=0.5, ge=0.1, le=5.0, description="Pause detection duration threshold"
    )
    target_min_wpm: float = Field(default=120.0, ge=60.0, description="Target lower pacing bound")
    target_max_wpm: float = Field(default=165.0, le=250.0, description="Target upper pacing bound")
    save_to_database: bool = Field(
        default=True, description="Whether to persist the session to database upon completion"
    )


class LiveMetricsUpdate(BaseModel):
    """Incremental delivery mechanics metrics emitted periodically during speech."""

    elapsed_seconds: float = Field(..., ge=0.0, description="Total elapsed practice duration")
    current_wpm_estimate: float | None = Field(
        None, description="Current running speaking pace estimate"
    )
    recent_filler_count: int = Field(0, description="Count of filler words identified so far")
    current_pause_seconds: float = Field(
        0.0, ge=0.0, description="Duration of current ongoing pause interval if active"
    )
    centered_gaze_ratio: float | None = Field(
        None, ge=0.0, le=1.0, description="Running centered gaze ratio"
    )
    head_stability_score: float | None = Field(
        None, ge=0.0, le=1.0, description="Running head posture stability score"
    )
    face_detected: bool = Field(True, description="Whether face is currently visible in frame")


class DeliveryAlert(BaseModel):
    """Real-time feedback alert notifying the candidate of delivery extremes."""

    timestamp_seconds: float = Field(..., ge=0.0, description="Timestamp of alert trigger")
    alert_type: str = Field(
        ...,
        description="Classification: rapid_pacing, extended_pause, off_center_gaze, face_missing",
    )
    message: str = Field(..., description="Actionable objective delivery reminder")
    severity: str = Field(default="info", description="Severity level: info, warning, caution")


class StreamFinalReport(BaseModel):
    """Consolidated delivery analytics emitted when stream completes."""

    session_id: str = Field(..., description="Session identifier")
    total_duration_seconds: float = Field(..., ge=0.0, description="Total stream duration")
    audio_metrics: AudioMetrics | None = Field(None, description="Acoustic delivery metrics")
    visual_metrics: VisualMetrics | None = Field(None, description="Visual delivery metrics")
    transcript: str | None = Field(None, description="Spoken transcript")
    alerts_triggered_count: int = Field(0, description="Total real-time alerts fired")
    saved_to_db: bool = Field(False, description="Whether session was persisted to database")
    context: dict[str, Any] | None = Field(default=None, description="Additional metadata")
