"""Unit and API integration tests for AI coaching, STAR evaluation, and content quality feedback."""

import pytest
from fastapi.testclient import TestClient

from app.api.sessions import get_session_repo
from app.main import app
from app.models.audio import AudioMetrics
from app.models.session import SessionCreateRequest
from app.models.visual import VisualMetrics
from app.pipeline.coaching_engine import (
    evaluate_content_clarity,
    evaluate_star_framework,
    generate_delivery_advice,
    generate_polished_excerpt,
)
from app.storage.database import Database
from app.storage.session_repository import SessionRepository


@pytest.fixture
def temp_db(tmp_path):
    """Fixture providing an isolated temporary SQLite database."""
    db_file = tmp_path / "test_coaching.db"
    db = Database(db_path=str(db_file))
    yield db
    db.close()


@pytest.fixture
def repo(temp_db):
    """Fixture providing a SessionRepository connected to the temporary database."""
    return SessionRepository(db=temp_db)


@pytest.fixture
def client(repo):
    """FastAPI TestClient with overridden repository."""
    app.dependency_overrides[get_session_repo] = lambda: repo
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


SAMPLE_STAR_TRANSCRIPT = (
    "At my previous company, our team was facing a critical performance "
    "degradation on the auth microservice. "
    "My responsibility was to lead the diagnostic effort and ensure zero "
    "downtime for active users. "
    "I implemented an in-memory Redis caching layer and refactored the "
    "token validation queries. "
    "As a result, API response latency dropped by 45% and we achieved "
    "99.99% uptime across peak sales."
)


def make_test_audio_metrics(wpm: float = 145.0, filler_ratio: float = 0.02) -> AudioMetrics:
    return AudioMetrics(
        total_duration_seconds=60.0,
        speaking_duration_seconds=52.0,
        total_words=int(wpm),
        words_per_minute=wpm,
        articulation_rate_wpm=wpm * 1.15,
        filler_words_count=int(wpm * filler_ratio),
        filler_words_ratio=filler_ratio,
        filler_words_breakdown={"um": 2, "like": 1},
        pause_count=5,
        total_pause_duration_seconds=8.0,
        average_pause_duration_seconds=1.6,
        longest_pause_duration_seconds=2.2,
        pause_threshold_seconds=0.5,
        pauses=[],
    )


def make_test_visual_metrics(gaze: float = 0.85, stability: float = 0.88) -> VisualMetrics:
    return VisualMetrics(
        total_duration_seconds=60.0,
        frames_analyzed=1800,
        face_detected_ratio=1.0,
        centered_gaze_ratio=gaze,
        gaze_distribution={"center": gaze, "left": 0.08, "right": 0.07},
        head_stability_score=stability,
        head_movement_variance=0.002,
        hands_visible_ratio=0.5,
        hand_gestures_per_minute=6.0,
        tracking_notes=[],
        ethical_disclaimer="Geometric estimates only.",
    )


def test_star_framework_complete_answer():
    """Verify STAR engine correctly identifies all 4 components in a structured response."""
    result = evaluate_star_framework(SAMPLE_STAR_TRANSCRIPT)
    assert result.situation_detected is True
    assert result.task_detected is True
    assert result.action_detected is True
    assert result.result_detected is True
    assert result.overall_star_score == 100.0
    assert "all four star components" in result.star_summary.lower()
    assert result.situation_snippet is not None
    assert result.result_snippet is not None


def test_star_framework_partial_missing_result():
    """Verify STAR engine detects missing Result component and scores appropriately."""
    partial_transcript = (
        "In my last role, we were facing customer churn due to slow onboarding. "
        "My goal was to redesign the initial onboarding checklist. "
        "I implemented a self-service tour and refactored our registration flow."
    )
    result = evaluate_star_framework(partial_transcript)
    assert result.situation_detected is True
    assert result.task_detected is True
    assert result.action_detected is True
    assert result.result_detected is False
    assert result.overall_star_score == 75.0
    assert "result" in result.star_summary.lower()


def test_star_framework_very_short_response():
    """Verify ultra-short responses trigger constructive structural guidance."""
    result = evaluate_star_framework("I wrote code.")
    assert result.overall_star_score <= 25.0
    assert "brief" in result.star_summary.lower()


def test_content_clarity_scoring():
    """Verify content clarity correctly discounts elevated filler words."""
    metrics_clean = make_test_audio_metrics(wpm=140.0, filler_ratio=0.01)
    clarity_clean = evaluate_content_clarity(SAMPLE_STAR_TRANSCRIPT, metrics_clean)
    assert clarity_clean.score >= 80
    assert clarity_clean.conciseness_rating == "Well-Balanced & Focused"

    metrics_fillers = make_test_audio_metrics(wpm=140.0, filler_ratio=0.09)
    clarity_fillers = evaluate_content_clarity(SAMPLE_STAR_TRANSCRIPT, metrics_fillers)
    assert clarity_fillers.score < clarity_clean.score
    assert clarity_fillers.filler_density_percent == 9.0


def test_delivery_advice_pacing_and_pauses():
    """Verify delivery coaching provides tailored pacing and pause recommendations."""
    # Fast pacing
    fast_audio = make_test_audio_metrics(wpm=180.0)
    advice_fast = generate_delivery_advice(fast_audio, make_test_visual_metrics())
    assert (
        "fast" in advice_fast.pacing_feedback.lower()
        or "slow down" in advice_fast.pacing_feedback.lower()
    )

    # Extended pause
    fast_audio.longest_pause_duration_seconds = 4.2
    advice_pause = generate_delivery_advice(fast_audio, make_test_visual_metrics())
    assert "extended pause" in advice_pause.pause_feedback.lower()


def test_polished_excerpt_generation():
    """Verify polished excerpt cleans fillers and structures professional tone."""
    raw = "Um, at my previous company, like we were facing a really tough outage."
    polished = generate_polished_excerpt(raw)
    assert polished is not None
    assert "um" not in polished.lower()
    assert "like" not in polished.lower()


def test_api_evaluate_coaching_direct_payload(client):
    """Test POST /api/v1/coaching/evaluate with direct transcript and metrics."""
    payload = {
        "question_prompt": "Tell me about a time you resolved a major bug.",
        "transcript": SAMPLE_STAR_TRANSCRIPT,
        "audio_metrics": make_test_audio_metrics().model_dump(),
        "visual_metrics": make_test_visual_metrics().model_dump(),
    }
    response = client.post("/api/v1/coaching/evaluate", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["star_analysis"]["overall_star_score"] == 100.0
    assert data["clarity"]["score"] >= 80
    assert len(data["top_strengths"]) >= 2
    assert len(data["areas_for_improvement"]) >= 1
    assert "ethical" in data["ethical_disclaimer"].lower()


def test_api_evaluate_coaching_by_session_id(client, repo):
    """Test POST /api/v1/coaching/evaluate pulling saved session from database."""
    repo.create_session(
        SessionCreateRequest(
            session_id="coach_sess_01",
            title="System Architecture Question",
            transcript=SAMPLE_STAR_TRANSCRIPT,
            audio_metrics=make_test_audio_metrics(),
            visual_metrics=make_test_visual_metrics(),
        )
    )

    response = client.post(
        "/api/v1/coaching/evaluate",
        json={"session_id": "coach_sess_01"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == "coach_sess_01"
    assert data["question_prompt"] == "System Architecture Question"
    assert data["star_analysis"]["overall_star_score"] == 100.0


def test_api_get_session_coaching_endpoint(client, repo):
    """Test GET /api/v1/coaching/sessions/{session_id}."""
    repo.create_session(
        SessionCreateRequest(
            session_id="coach_sess_02",
            title="Team Conflict Resolution",
            transcript=SAMPLE_STAR_TRANSCRIPT,
            audio_metrics=make_test_audio_metrics(),
        )
    )

    response = client.get("/api/v1/coaching/sessions/coach_sess_02")
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == "coach_sess_02"
    assert data["question_prompt"] == "Team Conflict Resolution"
    assert data["clarity"]["conciseness_rating"] == "Well-Balanced & Focused"


def test_api_get_session_coaching_not_found(client):
    """Test GET /api/v1/coaching/sessions/{session_id} with unknown ID returns 404."""
    response = client.get("/api/v1/coaching/sessions/unknown_session")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
