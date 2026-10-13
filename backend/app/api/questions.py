"""API endpoints for the interview question bank and multi-question mock interview tracks."""

from fastapi import APIRouter, HTTPException, Query, status

from app.models.questions import (
    CategorySummary,
    CustomTrackRequest,
    InterviewQuestion,
    MockTrackDefinition,
    MockTrackListResponse,
    QuestionListResponse,
)
from app.pipeline.question_bank import (
    create_custom_track,
    get_all_mock_tracks,
    get_all_questions,
    get_category_summaries,
    get_mock_track_by_id,
    get_question_by_id,
)

router = APIRouter(prefix="/questions", tags=["Question Bank & Mock Tracks"])


@router.get(
    "",
    response_model=QuestionListResponse,
    status_code=status.HTTP_200_OK,
    summary="List curated interview questions",
    description=(
        "Returns interview questions filtered optionally by category, difficulty, or search term."
    ),
)
def list_questions(
    category: str | None = Query(
        None, description="Category filter: behavioral, system_design, technical, leadership"
    ),
    difficulty: str | None = Query(
        None, description="Experience level: junior, mid, senior, staff"
    ),
    search: str | None = Query(None, description="Keyword search in question title or hint"),
) -> QuestionListResponse:
    """Retrieve filtered list of questions and category counts."""
    questions = get_all_questions(category=category, difficulty=difficulty, search=search)
    categories = get_category_summaries()
    return QuestionListResponse(
        questions=questions,
        total=len(questions),
        categories=categories,
    )


@router.get(
    "/categories",
    response_model=list[CategorySummary],
    status_code=status.HTTP_200_OK,
    summary="List question categories",
    description="Returns all available question categories along with total count.",
)
def list_categories() -> list[CategorySummary]:
    """Return category summary breakdown."""
    return get_category_summaries()


@router.get(
    "/tracks/available",
    response_model=MockTrackListResponse,
    status_code=status.HTTP_200_OK,
    summary="List pre-configured mock interview tracks",
    description=(
        "Returns curated multi-question interview simulation tracks for different role levels."
    ),
)
def list_mock_tracks() -> MockTrackListResponse:
    """Retrieve all curated multi-question mock tracks."""
    tracks = get_all_mock_tracks()
    return MockTrackListResponse(tracks=tracks, total=len(tracks))


@router.get(
    "/tracks/{track_id}",
    response_model=MockTrackDefinition,
    status_code=status.HTTP_200_OK,
    summary="Get mock interview track details",
    description="Returns the questions and target metrics for a specific mock track.",
)
def get_mock_track(track_id: str) -> MockTrackDefinition:
    """Retrieve a single mock track by ID."""
    track = get_mock_track_by_id(track_id)
    if not track:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mock interview track '{track_id}' not found.",
        )
    return track


@router.post(
    "/tracks/custom",
    response_model=MockTrackDefinition,
    status_code=status.HTTP_200_OK,
    summary="Create a custom multi-question mock track",
    description="Generates an on-the-fly multi-question track from a list of question slugs.",
)
def create_custom_mock_track(payload: CustomTrackRequest) -> MockTrackDefinition:
    """Generate a custom mock interview track."""
    track = create_custom_track(payload.track_name, payload.question_ids)
    if not track:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="None of the specified question IDs could be resolved in the question bank.",
        )
    return track


@router.get(
    "/{question_id}",
    response_model=InterviewQuestion,
    status_code=status.HTTP_200_OK,
    summary="Get single interview question",
    description="Retrieve prompt and coaching guidelines for an individual question slug.",
)
def get_question(question_id: str) -> InterviewQuestion:
    """Fetch an individual question by slug."""
    question = get_question_by_id(question_id)
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Question with ID '{question_id}' not found.",
        )
    return question
