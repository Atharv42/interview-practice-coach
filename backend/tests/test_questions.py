"""Unit and integration tests for question bank and mock tracks APIs."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_list_all_questions():
    """Verify listing all questions without filters."""
    res = client.get("/api/v1/questions")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 15
    assert len(data["questions"]) == data["total"]
    assert len(data["categories"]) >= 4
    first_q = data["questions"][0]
    assert "id" in first_q
    assert "title" in first_q
    assert "context_hint" in first_q
    assert "target_duration_seconds" in first_q


def test_filter_questions_by_category():
    """Verify category filtering."""
    for category in ["behavioral", "system_design", "technical", "leadership"]:
        res = client.get(f"/api/v1/questions?category={category}")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] > 0
        for q in data["questions"]:
            assert q["category"] == category


def test_filter_questions_by_difficulty():
    """Verify difficulty filtering."""
    res = client.get("/api/v1/questions?difficulty=senior")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] > 0
    for q in data["questions"]:
        assert q["difficulty"] == "senior"


def test_search_questions():
    """Verify keyword query search."""
    res = client.get("/api/v1/questions?search=cache")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1
    for q in data["questions"]:
        combined = (q["title"] + q["context_hint"] + q["category_label"]).lower()
        assert "cache" in combined


def test_get_single_question_success():
    """Verify fetching an existing question by ID."""
    res = client.get("/api/v1/questions/beh-conflict-resolution")
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == "beh-conflict-resolution"
    assert data["category"] == "behavioral"
    assert "conflict" in data["title"].lower()


def test_get_single_question_not_found():
    """Verify 404 on nonexistent question slug."""
    res = client.get("/api/v1/questions/nonexistent-question-id-xyz")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_list_categories():
    """Verify category summary endpoint."""
    res = client.get("/api/v1/questions/categories")
    assert res.status_code == 200
    cats = res.json()
    assert len(cats) >= 4
    cat_keys = [c["category"] for c in cats]
    assert "behavioral" in cat_keys
    assert "system_design" in cat_keys
    for c in cats:
        assert c["count"] > 0


def test_list_mock_tracks():
    """Verify retrieving curated mock tracks."""
    res = client.get("/api/v1/questions/tracks/available")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 3
    track_ids = [t["track_id"] for t in data["tracks"]]
    assert "behavioral-core" in track_ids
    assert "senior-engineering" in track_ids


def test_get_single_mock_track():
    """Verify retrieving a detailed track by ID."""
    res = client.get("/api/v1/questions/tracks/behavioral-core")
    assert res.status_code == 200
    track = res.json()
    assert track["track_id"] == "behavioral-core"
    assert track["question_count"] == 3
    assert len(track["questions"]) == 3
    assert track["questions"][0]["id"] == "beh-intro-background"


def test_get_single_mock_track_not_found():
    """Verify 404 on nonexistent mock track."""
    res = client.get("/api/v1/questions/tracks/unknown-track-1234")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_create_custom_mock_track_success():
    """Verify creating a dynamic custom track from question IDs."""
    payload = {
        "track_name": "My Custom Sprint",
        "question_ids": ["beh-intro-background", "sys-api-rate-limiter"],
    }
    res = client.post("/api/v1/questions/tracks/custom", json=payload)
    assert res.status_code == 200
    track = res.json()
    assert track["track_name"] == "My Custom Sprint"
    assert track["question_count"] == 2
    assert len(track["questions"]) == 2


def test_create_custom_mock_track_invalid_ids():
    """Verify 400 when all provided IDs fail to resolve."""
    payload = {
        "track_name": "Invalid Track",
        "question_ids": ["fake-id-1", "fake-id-2"],
    }
    res = client.post("/api/v1/questions/tracks/custom", json=payload)
    assert res.status_code == 400
    assert "could be resolved" in res.json()["detail"].lower()
