"""Pydantic schemas for AI coaching, STAR framework evaluation, and content quality feedback."""

from pydantic import BaseModel, Field

from app.models.audio import AudioMetrics
from app.models.visual import VisualMetrics


class STARFrameworkAnalysis(BaseModel):
    """Evaluation of response structure according to the STAR methodology."""

    situation_detected: bool = Field(..., description="Whether Situation/context was established")
    situation_snippet: str | None = Field(None, description="Identified situation excerpt")
    task_detected: bool = Field(..., description="Whether Task/responsibility was stated")
    task_snippet: str | None = Field(None, description="Identified task excerpt")
    action_detected: bool = Field(..., description="Whether specific Action steps were detailed")
    action_snippet: str | None = Field(None, description="Identified action excerpt")
    result_detected: bool = Field(..., description="Whether quantifiable Result/outcome was stated")
    result_snippet: str | None = Field(None, description="Identified result excerpt")
    overall_star_score: float = Field(
        ..., ge=0.0, le=100.0, description="Overall STAR alignment score (0 - 100)"
    )
    star_summary: str = Field(..., description="Qualitative evaluation of structural completeness")


class ContentClarityScore(BaseModel):
    """Clarity and conciseness evaluation of spoken answer content."""

    score: int = Field(..., ge=0, le=100, description="Overall clarity score (0 - 100)")
    word_count: int = Field(..., ge=0, description="Total word count analyzed")
    conciseness_rating: str = Field(
        ..., description="Rating: Highly Concise, Well-Balanced, or Wordy / Wandering"
    )
    filler_density_percent: float = Field(
        ..., ge=0.0, le=100.0, description="Percentage of spoken words that were fillers"
    )
    observations: list[str] = Field(
        default_factory=list, description="Observations regarding clarity and verbal precision"
    )


class DeliveryCoachingAdvice(BaseModel):
    """Objective delivery advice synthesizing acoustic and geometric mechanics."""

    pacing_feedback: str = Field(..., description="Speaking pace recommendation")
    pause_feedback: str = Field(..., description="Pause duration and placement advice")
    filler_feedback: str = Field(..., description="Filler word reduction guidance")
    visual_feedback: str = Field(
        ..., description="Camera eye contact and posture steadiness advice"
    )
    overall_delivery_summary: str = Field(
        ..., description="Executive summary of delivery performance"
    )


class CoachingEvaluationRequest(BaseModel):
    """Request payload to generate personalized coaching feedback."""

    session_id: str | None = Field(
        None, description="Optional existing session ID to pull transcript and metrics from"
    )
    question_prompt: str | None = Field(
        None, description="Interview question or prompt asked to candidate"
    )
    transcript: str | None = Field(None, description="Spoken answer transcript")
    audio_metrics: AudioMetrics | None = Field(None, description="Optional audio delivery metrics")
    visual_metrics: VisualMetrics | None = Field(
        None, description="Optional visual delivery metrics"
    )


class CoachingEvaluationResponse(BaseModel):
    """Complete structured coaching report combining content analysis and delivery mechanics."""

    session_id: str | None = Field(None, description="Associated session identifier")
    question_prompt: str | None = Field(None, description="Interview prompt analyzed")
    clarity: ContentClarityScore = Field(..., description="Clarity and conciseness analysis")
    star_analysis: STARFrameworkAnalysis = Field(
        ..., description="STAR method structure evaluation"
    )
    delivery_advice: DeliveryCoachingAdvice = Field(
        ..., description="Objective acoustic and geometric delivery advice"
    )
    top_strengths: list[str] = Field(
        default_factory=list, description="Top positive attributes identified in performance"
    )
    areas_for_improvement: list[str] = Field(
        default_factory=list, description="Concrete, actionable recommendations for improvement"
    )
    sample_polished_excerpt: str | None = Field(
        None, description="Polished rephrased sentence demonstrating high executive impact"
    )
    ethical_disclaimer: str = Field(
        default=(
            "AI coaching advice evaluates structural completeness (STAR method) "
            "and objective delivery mechanics. Designed for constructive self-practice "
            "and does not determine real hiring decisions."
        ),
        description="Ethical disclaimer",
    )
