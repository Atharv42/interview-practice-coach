"""Unit and API integration tests for practice session persistence and lifecycle management."""

import pytest
from fastapi.testclient import TestClient

from app.api.analytics import get_session_repo as get_analytics_session_repo
from app.api.sessions import get_session_repo
from app.main import app
from app.models.audio import (
    AudioAnalysisResponse,
    AudioMetrics,
    AudioSegment,
    PauseDetail,
    WordTimestamp,
)
from app.models.session import SessionCreateRequest
from app.models.visual import (
    VisualAnalysisResponse,
    VisualMetrics,
)
from app.storage.database import Database, resolve_db_path
from app.storage.session_repository import (
    SessionAlreadyExistsError,
    SessionRepository,
)


def sample_audio_metrics(wpm: float = 142.0, filler_ratio: float = 0.03) -> AudioMetrics:
    """Helper creating realistic acoustic delivery metrics."""
    return AudioMetrics(
        total_duration_seconds=45.0,
        speaking_duration_seconds=38.0,
        total_words=105,
        words_per_minute=wpm,
        articulation_rate_wpm=165.0,
        filler_words_count=3,
        filler_words_ratio=filler_ratio,
        filler_words_breakdown={"um": 2, "like": 1},
        pause_count=4,
        total_pause_duration_seconds=7.0,
        average_pause_duration_seconds=1.75,
        longest_pause_duration_seconds=2.4,
        pause_threshold_seconds=0.5,
        pauses=[
            PauseDetail(
                start=10.0,
                end=11.75,
                duration=1.75,
                preceding_word="first",
                following_word="point",
            )
        ],
    )


def sample_visual_metrics(gaze: float = 0.82, stability: float = 0.91) -> VisualMetrics:
    """Helper creating realistic visual delivery metrics."""
    return VisualMetrics(
        total_duration_seconds=45.0,
        frames_analyzed=1350,
        face_detected_ratio=0.98,
        centered_gaze_ratio=gaze,
        gaze_distribution={"center": gaze, "left": (1 - gaze) / 2, "right": (1 - gaze) / 2},
        head_stability_score=stability,
        head_movement_variance=0.0018,
        hands_visible_ratio=0.45,
        hand_gestures_per_minute=5.5,
        tracking_notes=["Good framing", "Stable head position"],
        ethical_disclaimer="Approximate geometric visual delivery estimates only.",
    )


@pytest.fixture
def temp_db(tmp_path):
    """Fixture providing an isolated temporary SQLite database."""
    db_file = tmp_path / "test_sessions.db"
    db = Database(db_path=str(db_file))
    yield db
    db.close()


@pytest.fixture
def repo(temp_db):
    """Fixture providing a SessionRepository connected to the temporary database."""
    return SessionRepository(db=temp_db)


@pytest.fixture
def client_with_temp_db(repo):
    """Fixture providing a FastAPI TestClient with the session repository overridden."""
    app.dependency_overrides[get_session_repo] = lambda: repo
    app.dependency_overrides[get_analytics_session_repo] = lambda: repo
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ============================================================================
# Unit Tests: Storage Schema & Repository
# ============================================================================


def test_schema_tables_and_indexes_exist(temp_db):
    """Verify all required tables and indexes are created in SQLite."""
    with temp_db.connection() as conn:
        tables = [
            row["name"]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        ]
        assert "sessions" in tables
        assert "audio_metrics" in tables
        assert "visual_metrics" in tables
        assert "session_feature_vectors" in tables

        indices = [
            row["name"]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='index'").fetchall()
        ]
        assert "idx_sessions_created_at" in indices


def test_create_and_get_session_multimodal(repo):
    """Verify saving and retrieving a full multimodal practice session."""
    words = [
        WordTimestamp(word="hello", start=0.0, end=0.4, probability=0.99),
        WordTimestamp(word="world", start=0.5, end=0.9, probability=0.98),
    ]
    segments = [AudioSegment(id=0, start=0.0, end=0.9, text="hello world", words=words)]
    audio_m = sample_audio_metrics(140.0, 0.02)
    visual_m = sample_visual_metrics(0.85, 0.90)

    request = SessionCreateRequest(
        session_id="session_multimodal_01",
        title="Software Engineer Mock Interview",
        notes="Practiced answering technical architecture questions.",
        language="en",
        duration_seconds=45.0,
        transcript="hello world",
        audio_metrics=audio_m,
        audio_segments=segments,
        audio_words=words,
        visual_metrics=visual_m,
    )

    created = repo.create_session(request)
    assert created.session_id == "session_multimodal_01"
    assert created.has_audio is True
    assert created.has_visual is True
    assert created.transcript == "hello world"
    assert created.audio_metrics is not None
    assert created.audio_metrics.words_per_minute == 140.0
    assert len(created.audio_segments) == 1
    assert len(created.audio_words) == 2
    assert created.visual_metrics is not None
    assert created.visual_metrics.centered_gaze_ratio == 0.85
    assert created.feature_vector is not None
    assert created.feature_vector.words_per_minute == 140.0
    assert created.feature_vector.centered_gaze_ratio == 0.85

    # Retrieve from DB and verify exact persistence
    retrieved = repo.get_session("session_multimodal_01")
    assert retrieved is not None
    assert retrieved.session_id == "session_multimodal_01"
    assert retrieved.title == "Software Engineer Mock Interview"
    assert retrieved.notes == "Practiced answering technical architecture questions."
    assert retrieved.transcript == "hello world"
    assert retrieved.audio_metrics.filler_words_count == 3
    assert len(retrieved.audio_metrics.pauses) == 1
    assert retrieved.audio_metrics.pauses[0].preceding_word == "first"
    assert retrieved.visual_metrics.head_stability_score == 0.90
    assert retrieved.feature_vector.head_stability_score == 0.90


def test_create_session_auto_id_and_duration_inference(repo):
    """Verify session ID generation and duration inference from metrics."""
    audio_m = sample_audio_metrics()
    req = SessionCreateRequest(
        audio_metrics=audio_m,
        transcript="Sample transcript",
    )
    created = repo.create_session(req)
    assert created.session_id.startswith("sess_")
    assert created.duration_seconds == 45.0  # inferred from audio_metrics
    assert created.has_audio is True
    assert created.has_visual is False


def test_create_session_duplicate_id_raises_error(repo):
    """Verify attempting to create a duplicate session ID raises SessionAlreadyExistsError."""
    req = SessionCreateRequest(session_id="dup_sess_01", title="First")
    repo.create_session(req)

    with pytest.raises(SessionAlreadyExistsError):
        repo.create_session(req)


def test_get_nonexistent_session_returns_none(repo):
    """Verify non-existent session ID lookup returns None."""
    assert repo.get_session("does_not_exist") is None


def test_list_sessions_pagination_and_sorting(repo):
    """Verify pagination and chronological ordering."""
    # Empty DB
    summaries, total = repo.list_sessions()
    assert total == 0
    assert summaries == []

    # Insert 3 sessions with distinct timestamps
    for i in range(3):
        repo.create_session(
            SessionCreateRequest(
                session_id=f"sess_{i}",
                title=f"Session {i}",
                created_at=f"2026-10-10T10:0{i}:00Z",
                transcript=f"Transcript number {i} " * 10,
                audio_metrics=sample_audio_metrics(120.0 + i * 10),
            )
        )

    # Test DESC ordering (default, newest first)
    desc_list, total_desc = repo.list_sessions(limit=2, offset=0, order="desc")
    assert total_desc == 3
    assert len(desc_list) == 2
    assert desc_list[0].session_id == "sess_2"
    assert desc_list[1].session_id == "sess_1"
    assert desc_list[0].transcript_snippet is not None
    assert desc_list[0].transcript_snippet.endswith("...")

    # Test offset pagination
    page_2, _ = repo.list_sessions(limit=2, offset=2, order="desc")
    assert len(page_2) == 1
    assert page_2[0].session_id == "sess_0"

    # Test ASC ordering (oldest first)
    asc_list, _ = repo.list_sessions(limit=3, order="asc")
    assert asc_list[0].session_id == "sess_0"
    assert asc_list[2].session_id == "sess_2"


def test_delete_session_cascades_and_removes_all_records(repo, temp_db):
    """Verify permanent deletion cascades to audio, visual, and feature tables."""
    req = SessionCreateRequest(
        session_id="delete_me",
        audio_metrics=sample_audio_metrics(),
        visual_metrics=sample_visual_metrics(),
        transcript="Test transcript",
    )
    repo.create_session(req)

    # Verify rows exist across tables
    with temp_db.connection() as conn:
        assert (
            conn.execute(
                "SELECT COUNT(*) as c FROM sessions WHERE session_id = 'delete_me'"
            ).fetchone()["c"]
            == 1
        )
        assert (
            conn.execute(
                "SELECT COUNT(*) as c FROM audio_metrics WHERE session_id = 'delete_me'"
            ).fetchone()["c"]
            == 1
        )
        assert (
            conn.execute(
                "SELECT COUNT(*) as c FROM visual_metrics WHERE session_id = 'delete_me'"
            ).fetchone()["c"]
            == 1
        )
        assert (
            conn.execute(
                "SELECT COUNT(*) as c FROM session_feature_vectors WHERE session_id = 'delete_me'"
            ).fetchone()["c"]
            == 1
        )

    # Delete session
    deleted = repo.delete_session("delete_me")
    assert deleted is True

    # Verify all records permanently removed
    with temp_db.connection() as conn:
        assert (
            conn.execute(
                "SELECT COUNT(*) as c FROM sessions WHERE session_id = 'delete_me'"
            ).fetchone()["c"]
            == 0
        )
        assert (
            conn.execute(
                "SELECT COUNT(*) as c FROM audio_metrics WHERE session_id = 'delete_me'"
            ).fetchone()["c"]
            == 0
        )
        assert (
            conn.execute(
                "SELECT COUNT(*) as c FROM visual_metrics WHERE session_id = 'delete_me'"
            ).fetchone()["c"]
            == 0
        )
        assert (
            conn.execute(
                "SELECT COUNT(*) as c FROM session_feature_vectors WHERE session_id = 'delete_me'"
            ).fetchone()["c"]
            == 0
        )

    # Deleting again returns False
    assert repo.delete_session("delete_me") is False


def test_compute_analytics_summary_from_persisted_history(repo):
    """Verify running PCA and trend analytics directly over stored sessions."""
    # 1. Zero sessions
    empty_summary = repo.compute_analytics_summary()
    assert empty_summary.total_sessions_analyzed == 0
    assert empty_summary.pca.is_fallback is True

    # 2. Add 4 sessions
    for i in range(4):
        repo.create_session(
            SessionCreateRequest(
                session_id=f"hist_sess_{i}",
                created_at=f"2026-10-11T12:0{i}:00Z",
                audio_metrics=sample_audio_metrics(
                    wpm=110.0 + i * 15.0,
                    filler_ratio=0.08 - i * 0.02,
                ),
                visual_metrics=sample_visual_metrics(
                    gaze=0.65 + i * 0.08,
                    stability=0.75 + i * 0.05,
                ),
            )
        )

    summary = repo.compute_analytics_summary()
    assert summary.total_sessions_analyzed == 4
    assert summary.pca.is_fallback is False
    assert len(summary.pca.points) == 4
    assert len(summary.clusters) >= 2
    assert len(summary.trends.points) == 4
    assert summary.trends.wpm_slope > 0.0  # pace accelerated across sessions
    assert summary.trends.filler_ratio_slope < 0.0  # filler words decreased


# ============================================================================
# API Integration Tests (FastAPI TestClient)
# ============================================================================


def test_api_create_session_success(client_with_temp_db):
    """Test POST /api/v1/sessions creating a new session."""
    payload = {
        "session_id": "api_test_01",
        "title": "System Design Practice",
        "notes": "Focused on distributed caching.",
        "language": "en",
        "duration_seconds": 60.0,
        "transcript": "Let us discuss caching layers.",
        "audio_metrics": sample_audio_metrics().model_dump(),
        "visual_metrics": sample_visual_metrics().model_dump(),
    }

    response = client_with_temp_db.post("/api/v1/sessions", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["session_id"] == "api_test_01"
    assert data["title"] == "System Design Practice"
    assert data["has_audio"] is True
    assert data["has_visual"] is True
    assert data["audio_metrics"]["words_per_minute"] == 142.0
    assert data["feature_vector"] is not None


def test_api_create_session_from_analysis_objects(client_with_temp_db):
    """Test POST /api/v1/sessions unpacking audio_analysis and visual_analysis payloads."""
    audio_analysis = AudioAnalysisResponse(
        filename="test.wav",
        transcript="This is unpacked from analysis pipeline.",
        language="en",
        language_probability=0.99,
        metrics=sample_audio_metrics(135.0),
        segments=[],
        words=[],
    )
    visual_analysis = VisualAnalysisResponse(
        status="success",
        metrics=sample_visual_metrics(0.80),
        recommendations=["Good pace"],
    )

    payload = {
        "session_id": "api_unpack_01",
        "title": "Pipeline Forwarding",
        "audio_analysis": audio_analysis.model_dump(),
        "visual_analysis": visual_analysis.model_dump(),
    }

    response = client_with_temp_db.post("/api/v1/sessions", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["session_id"] == "api_unpack_01"
    assert data["transcript"] == "This is unpacked from analysis pipeline."
    assert data["audio_metrics"]["words_per_minute"] == 135.0
    assert data["visual_metrics"]["centered_gaze_ratio"] == 0.80


def test_api_create_session_duplicate_returns_409(client_with_temp_db):
    """Test POST /api/v1/sessions duplicate returns 409 Conflict."""
    payload = {"session_id": "conflict_sess", "title": "First"}
    res1 = client_with_temp_db.post("/api/v1/sessions", json=payload)
    assert res1.status_code == 201

    res2 = client_with_temp_db.post("/api/v1/sessions", json=payload)
    assert res2.status_code == 409
    assert "already exists" in res2.json()["detail"].lower()


def test_api_get_session_by_id(client_with_temp_db):
    """Test GET /api/v1/sessions/{session_id}."""
    # 404 for missing
    res_404 = client_with_temp_db.get("/api/v1/sessions/not_found")
    assert res_404.status_code == 404

    # Create and fetch
    client_with_temp_db.post(
        "/api/v1/sessions",
        json={"session_id": "fetch_me", "title": "Fetchable"},
    )
    res_200 = client_with_temp_db.get("/api/v1/sessions/fetch_me")
    assert res_200.status_code == 200
    assert res_200.json()["session_id"] == "fetch_me"
    assert res_200.json()["title"] == "Fetchable"


def test_api_list_sessions_endpoint(client_with_temp_db):
    """Test GET /api/v1/sessions listing with pagination."""
    for i in range(5):
        client_with_temp_db.post(
            "/api/v1/sessions",
            json={"session_id": f"list_sess_{i}", "title": f"Title {i}"},
        )

    res = client_with_temp_db.get("/api/v1/sessions?limit=3&offset=0&order=asc")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 5
    assert data["limit"] == 3
    assert len(data["sessions"]) == 3
    assert data["sessions"][0]["session_id"] == "list_sess_0"


def test_api_delete_session_endpoint(client_with_temp_db):
    """Test DELETE /api/v1/sessions/{session_id}."""
    client_with_temp_db.post(
        "/api/v1/sessions",
        json={"session_id": "to_delete", "title": "Delete Me"},
    )

    del_res = client_with_temp_db.delete("/api/v1/sessions/to_delete")
    assert del_res.status_code == 200
    assert del_res.json()["deleted"] is True

    # Second delete returns 404
    del_again = client_with_temp_db.delete("/api/v1/sessions/to_delete")
    assert del_again.status_code == 404

    # Fetch returns 404
    get_res = client_with_temp_db.get("/api/v1/sessions/to_delete")
    assert get_res.status_code == 404


def test_api_sessions_analytics_summary_endpoint(client_with_temp_db):
    """Test GET /api/v1/sessions/analytics/summary endpoint."""
    # Insert 3 sessions
    for i in range(3):
        client_with_temp_db.post(
            "/api/v1/sessions",
            json={
                "session_id": f"summary_sess_{i}",
                "audio_metrics": sample_audio_metrics(120.0 + i * 15.0).model_dump(),
                "visual_metrics": sample_visual_metrics().model_dump(),
            },
        )

    res = client_with_temp_db.get("/api/v1/sessions/analytics/summary")
    assert res.status_code == 200
    data = res.json()
    assert data["total_sessions_analyzed"] == 3
    assert data["pca"]["is_fallback"] is False
    assert len(data["pca"]["points"]) == 3
    assert "statistical groupings" in data["ethical_note"].lower()


def test_create_session_preserves_audio_analysis_language_and_probability(repo, temp_db):
    """Verify detected language and confidence probability are preserved from audio_analysis."""
    audio_analysis = AudioAnalysisResponse(
        filename="spanish_interview.wav",
        transcript="Hola, gracias por la oportunidad.",
        language="es",
        language_probability=0.88,
        metrics=sample_audio_metrics(130.0),
        segments=[],
        words=[],
    )
    req = SessionCreateRequest(
        session_id="lang_test_01",
        audio_analysis=audio_analysis,
    )
    created = repo.create_session(req)
    assert created.language == "es"

    retrieved = repo.get_session("lang_test_01")
    assert retrieved.language == "es"

    with temp_db.connection() as conn:
        query = (
            "SELECT language, language_probability FROM audio_metrics "
            "WHERE session_id = 'lang_test_01'"
        )
        row = conn.execute(query).fetchone()
        assert row["language"] == "es"
        assert abs(row["language_probability"] - 0.88) < 1e-4


def test_create_and_get_session_transcript_only_no_phantom_metrics(repo):
    """Verify sessions with transcript only return None for audio_metrics, not 0 WPM."""
    req = SessionCreateRequest(
        session_id="transcript_only_sess",
        title="Transcript Only",
        transcript="This is just a transcript without extracted metrics.",
    )
    created = repo.create_session(req)
    assert created.audio_metrics is None
    assert created.transcript == "This is just a transcript without extracted metrics."
    assert created.has_audio is True

    # Retrieval must NOT fabricate dummy AudioMetrics
    retrieved = repo.get_session("transcript_only_sess")
    assert retrieved is not None
    assert retrieved.audio_metrics is None
    assert retrieved.transcript == "This is just a transcript without extracted metrics."
    assert retrieved.has_audio is True

    # List view must display None for words_per_minute rather than 0.0
    summaries, total = repo.list_sessions()
    assert total == 1
    assert summaries[0].words_per_minute is None
    assert summaries[0].filler_words_count is None
    assert summaries[0].filler_words_ratio is None
    assert summaries[0].transcript_snippet == "This is just a transcript without extracted metrics."


def test_create_session_segments_only_infers_duration_and_preserves_data(repo):
    """Verify duration inference and segment persistence when metrics are omitted."""
    words = [WordTimestamp(word="segment", start=1.0, end=1.5, probability=0.9)]
    segments = [AudioSegment(id=0, start=0.0, end=18.5, text="segment", words=words)]

    req = SessionCreateRequest(
        session_id="segments_only_sess",
        audio_segments=segments,
        audio_words=words,
    )
    created = repo.create_session(req)
    assert created.duration_seconds == 18.5
    assert created.has_audio is True
    assert created.audio_metrics is None
    assert len(created.audio_segments) == 1

    retrieved = repo.get_session("segments_only_sess")
    assert retrieved.duration_seconds == 18.5
    assert len(retrieved.audio_segments) == 1
    assert retrieved.audio_segments[0].end == 18.5
    assert len(retrieved.audio_words) == 1


def test_feature_vectors_chronological_indexing_regardless_of_order(repo):
    """Verify session_index represents true chronological index even when ordered desc."""
    for i in range(3):
        repo.create_session(
            SessionCreateRequest(
                session_id=f"order_sess_{i}",
                created_at=f"2026-10-12T08:0{i}:00Z",
                audio_metrics=sample_audio_metrics(wpm=100.0 + i * 20.0),
            )
        )

    # Ascending
    asc_vectors = repo.get_all_feature_vectors(order="asc")
    assert [v.session_index for v in asc_vectors] == [0, 1, 2]
    assert [v.words_per_minute for v in asc_vectors] == [100.0, 120.0, 140.0]

    # Descending: session_index must still reflect true chronological rank
    desc_vectors = repo.get_all_feature_vectors(order="desc")
    assert [v.session_index for v in desc_vectors] == [2, 1, 0]
    assert [v.words_per_minute for v in desc_vectors] == [140.0, 120.0, 100.0]

    # Trends computed directly from repository must show positive acceleration slope
    summary = repo.compute_analytics_summary()
    assert summary.trends.wpm_slope > 0.0


def test_api_list_sessions_case_insensitive_order(client_with_temp_db):
    """Verify GET /api/v1/sessions accepts uppercase DESC and ASC without 422."""
    for i in range(2):
        client_with_temp_db.post(
            "/api/v1/sessions",
            json={"session_id": f"case_sess_{i}", "title": f"Case {i}"},
        )

    res_desc = client_with_temp_db.get("/api/v1/sessions?order=DESC")
    assert res_desc.status_code == 200

    res_asc = client_with_temp_db.get("/api/v1/sessions?order=ASC")
    assert res_asc.status_code == 200


def test_api_analytics_persisted_summary_endpoint(client_with_temp_db):
    """Verify GET /api/v1/analytics/summary loads persisted sessions correctly."""
    for i in range(3):
        client_with_temp_db.post(
            "/api/v1/sessions",
            json={
                "session_id": f"persisted_analytics_{i}",
                "audio_metrics": sample_audio_metrics(115.0 + i * 10.0).model_dump(),
                "visual_metrics": sample_visual_metrics().model_dump(),
            },
        )

    res = client_with_temp_db.get("/api/v1/analytics/summary")
    assert res.status_code == 200
    data = res.json()
    assert data["total_sessions_analyzed"] == 3
    assert data["pca"]["is_fallback"] is False


def test_resolve_db_path_relative_and_memory(monkeypatch):
    """Verify resolve_db_path correctly resolves relative URLs and in-memory paths."""
    monkeypatch.setenv("PRACTICE_COACH_DB_PATH", "sqlite:///./practice_coach.db")
    resolved = resolve_db_path()
    assert resolved.endswith("practice_coach.db")
    assert not resolved.startswith("sqlite:///")

    monkeypatch.setenv("PRACTICE_COACH_DB_PATH", ":memory:")
    assert resolve_db_path() == ":memory:"
