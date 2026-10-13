"""Pydantic schemas for the interview question bank and mock interview tracks."""

from pydantic import BaseModel, Field


class InterviewQuestion(BaseModel):
    """An individual curated or custom interview question."""

    id: str = Field(..., description="Unique question identifier slug")
    category: str = Field(
        ...,
        description="Category: behavioral, system_design, technical, leadership",
    )
    category_label: str = Field(..., description="Human-readable category title")
    title: str = Field(..., description="The prompt or question asked to candidate")
    context_hint: str = Field(
        ..., description="Coaching tip on how to effectively structure the answer"
    )
    target_duration_seconds: int = Field(
        120, ge=30, le=600, description="Recommended answer duration in seconds"
    )
    difficulty: str = Field("mid", description="Experience level: junior, mid, senior, staff")


class CategorySummary(BaseModel):
    """Category breakdown with question count."""

    category: str = Field(..., description="Category key")
    label: str = Field(..., description="Category display title")
    count: int = Field(..., ge=0, description="Total questions in this category")


class QuestionListResponse(BaseModel):
    """Paginated or filtered list of interview questions."""

    questions: list[InterviewQuestion] = Field(default_factory=list)
    total: int = Field(..., ge=0)
    categories: list[CategorySummary] = Field(default_factory=list)


class MockTrackDefinition(BaseModel):
    """A structured multi-question mock interview track."""

    track_id: str = Field(..., description="Unique track identifier")
    track_name: str = Field(..., description="Display title of the track")
    description: str = Field(..., description="Overview of the track focus and role archetype")
    difficulty: str = Field("senior", description="Target role seniority")
    estimated_duration_minutes: int = Field(..., ge=1)
    question_count: int = Field(..., ge=1)
    questions: list[InterviewQuestion] = Field(default_factory=list)


class MockTrackListResponse(BaseModel):
    """List of all available curated mock interview tracks."""

    tracks: list[MockTrackDefinition] = Field(default_factory=list)
    total: int = Field(..., ge=0)


class CustomTrackRequest(BaseModel):
    """Request payload to create a custom dynamic mock interview track."""

    track_name: str = Field(default="Custom Practice Track", max_length=100)
    question_ids: list[str] = Field(
        ..., min_length=1, max_length=10, description="List of question IDs to include"
    )
