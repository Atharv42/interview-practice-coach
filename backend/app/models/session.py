"""Pydantic schemas for practice session storage, retrieval, and summaries."""

from pydantic import BaseModel, Field

from app.models.analytics import SessionFeatureVector
from app.models.audio import (
    AudioAnalysisResponse,
    AudioMetrics,
    AudioSegment,
    WordTimestamp,
)
from app.models.visual import (
    VisualAnalysisResponse,
    VisualMetrics,
)


class SessionCreateRequest(BaseModel):
    """Payload to create or persist a practice session and its extracted metrics."""

    session_id: str | None = Field(
        None,
        description="Optional unique identifier. If omitted, a UUID will be generated.",
    )
    title: str | None = Field(
        None,
        description="Optional title or prompt topic for the practice session",
    )
    notes: str | None = Field(
        None,
        description="Optional reflections or notes recorded by the user",
    )
    language: str | None = Field(
        default=None,
        description=(
            "Language code of spoken content (e.g. 'en'). "
            "Inferred from audio_analysis if omitted, defaults to 'en'."
        ),
    )
    duration_seconds: float | None = Field(
        None,
        ge=0.0,
        description="Session duration in seconds. Inferred from metrics if omitted.",
    )
    created_at: str | None = Field(
        None,
        description="ISO 8601 creation timestamp. Defaults to UTC now if omitted.",
    )

    # Audio metrics and transcript
    transcript: str | None = Field(
        None,
        description="Consolidated transcript text",
    )
    audio_metrics: AudioMetrics | None = Field(
        None,
        description="Extracted acoustic delivery metrics",
    )
    audio_segments: list[AudioSegment] = Field(
        default_factory=list,
        description="Segment-level speech transcription intervals",
    )
    audio_words: list[WordTimestamp] = Field(
        default_factory=list,
        description="Word-level alignment timestamps",
    )

    # Visual delivery metrics
    visual_metrics: VisualMetrics | None = Field(
        None,
        description="Extracted visual geometric delivery metrics",
    )

    # Direct pipeline responses (for convenient payload forwarding)
    audio_analysis: AudioAnalysisResponse | None = Field(
        None,
        description="Optional complete audio analysis response to unpack",
    )
    visual_analysis: VisualAnalysisResponse | None = Field(
        None,
        description="Optional complete visual analysis response to unpack",
    )


class SessionSummary(BaseModel):
    """Compact summary of a practice session for list views."""

    session_id: str = Field(..., description="Unique session identifier")
    title: str | None = Field(None, description="Session title")
    notes: str | None = Field(None, description="Session notes")
    created_at: str = Field(..., description="ISO 8601 creation timestamp")
    duration_seconds: float = Field(..., ge=0.0, description="Session duration in seconds")
    language: str = Field(..., description="Language code")
    has_audio: bool = Field(..., description="Whether acoustic data was recorded")
    has_visual: bool = Field(..., description="Whether visual metrics were recorded")
    words_per_minute: float | None = Field(None, description="Speaking pace in WPM")
    filler_words_count: int | None = Field(None, description="Count of detected filler words")
    filler_words_ratio: float | None = Field(None, description="Filler words ratio")
    centered_gaze_ratio: float | None = Field(None, description="Centered gaze ratio")
    head_stability_score: float | None = Field(None, description="Head stability score")
    hand_gestures_per_minute: float | None = Field(None, description="Hand gesture frequency")
    transcript_snippet: str | None = Field(
        None, description="Truncated beginning of transcript for quick preview"
    )


class SessionListResponse(BaseModel):
    """Paginated list of practice sessions."""

    total: int = Field(..., ge=0, description="Total number of stored sessions")
    limit: int = Field(..., ge=1, description="Requested limit count")
    offset: int = Field(..., ge=0, description="Requested offset index")
    sessions: list[SessionSummary] = Field(
        default_factory=list, description="Chronological or ordered list of session summaries"
    )


class SessionDetailResponse(BaseModel):
    """Comprehensive detailed representation of a saved practice session."""

    session_id: str = Field(..., description="Unique session identifier")
    title: str | None = Field(None, description="Session title")
    notes: str | None = Field(None, description="Session notes")
    created_at: str = Field(..., description="ISO 8601 creation timestamp")
    duration_seconds: float = Field(..., ge=0.0, description="Session duration in seconds")
    language: str = Field(..., description="Language code")
    has_audio: bool = Field(..., description="Whether acoustic data is present")
    has_visual: bool = Field(..., description="Whether visual metrics are present")

    # Audio details
    transcript: str | None = Field(None, description="Full spoken transcript")
    audio_metrics: AudioMetrics | None = Field(None, description="Full audio delivery metrics")
    audio_segments: list[AudioSegment] = Field(
        default_factory=list, description="Transcribed audio segments"
    )
    audio_words: list[WordTimestamp] = Field(
        default_factory=list, description="Aligned word timestamps"
    )

    # Visual details
    visual_metrics: VisualMetrics | None = Field(None, description="Full visual delivery metrics")

    # Feature vector representation
    feature_vector: SessionFeatureVector | None = Field(
        None, description="Unified normalized session feature vector"
    )


class SessionDeleteResponse(BaseModel):
    """Confirmation payload returned when a session is permanently removed."""

    session_id: str = Field(..., description="Identifier of the deleted session")
    deleted: bool = Field(True, description="Whether deletion was successful")
    message: str = Field(..., description="Confirmation details")
