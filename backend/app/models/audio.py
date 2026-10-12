"""Pydantic schemas for audio transcription, timestamps, and delivery metrics."""


from pydantic import BaseModel, Field


class WordTimestamp(BaseModel):
    """Word-level alignment timestamp."""

    word: str = Field(..., description="Spoken word token")
    start: float = Field(..., ge=0.0, description="Start time in seconds")
    end: float = Field(..., ge=0.0, description="End time in seconds")
    probability: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence probability")


class AudioSegment(BaseModel):
    """Speech segment returned by transcription."""

    id: int = Field(..., description="Segment identifier")
    start: float = Field(..., ge=0.0, description="Segment start time in seconds")
    end: float = Field(..., ge=0.0, description="Segment end time in seconds")
    text: str = Field(..., description="Segment transcription text")
    words: list[WordTimestamp] = Field(default_factory=list, description="Word timestamps")


class PauseDetail(BaseModel):
    """Details of an individual detected pause."""

    start: float = Field(..., ge=0.0, description="Pause start timestamp in seconds")
    end: float = Field(..., ge=0.0, description="Pause end timestamp in seconds")
    duration: float = Field(..., ge=0.0, description="Pause duration in seconds")
    preceding_word: str | None = Field(None, description="Word preceding the pause")
    following_word: str | None = Field(None, description="Word following the pause")


class AudioMetrics(BaseModel):
    """Calculated acoustic delivery metrics."""

    total_duration_seconds: float = Field(
        ..., ge=0.0, description="Total audio recording duration in seconds"
    )
    speaking_duration_seconds: float = Field(
        ..., ge=0.0, description="Active speech duration (total duration minus pauses)"
    )
    total_words: int = Field(..., ge=0, description="Total number of words spoken")
    words_per_minute: float = Field(
        ..., ge=0.0, description="Speaking pace in words per minute (WPM)"
    )
    articulation_rate_wpm: float = Field(
        ..., ge=0.0, description="Speaking pace excluding pauses (words / speaking duration)"
    )
    filler_words_count: int = Field(..., ge=0, description="Total count of filler words detected")
    filler_words_ratio: float = Field(
        ..., ge=0.0, le=1.0, description="Ratio of filler words to total words spoken"
    )
    filler_words_breakdown: dict[str, int] = Field(
        default_factory=dict, description="Frequency counts for each detected filler word"
    )
    pause_count: int = Field(..., ge=0, description="Number of detected pauses")
    total_pause_duration_seconds: float = Field(
        ..., ge=0.0, description="Sum of all pause durations in seconds"
    )
    average_pause_duration_seconds: float = Field(
        ..., ge=0.0, description="Average duration per pause in seconds"
    )
    longest_pause_duration_seconds: float = Field(
        ..., ge=0.0, description="Longest single pause duration in seconds"
    )
    pause_threshold_seconds: float = Field(
        ..., ge=0.1, description="Threshold in seconds used to define a pause"
    )
    pauses: list[PauseDetail] = Field(
        default_factory=list, description="Detailed list of detected pause intervals"
    )


class AudioAnalysisResponse(BaseModel):
    """Complete response returned by the audio processing pipeline."""

    filename: str = Field(..., description="Original uploaded filename")
    transcript: str = Field(..., description="Full consolidated transcript")
    language: str = Field(default="en", description="Detected language code")
    language_probability: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Language detection confidence"
    )
    metrics: AudioMetrics = Field(..., description="Calculated delivery metrics")
    segments: list[AudioSegment] = Field(
        default_factory=list, description="Transcribed audio segments"
    )
    words: list[WordTimestamp] = Field(
        default_factory=list, description="Consolidated word timestamps"
    )
