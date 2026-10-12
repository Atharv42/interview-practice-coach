"""Unit and API tests for multimodal feature store, PCA, clustering, and trend analysis."""

from fastapi.testclient import TestClient

from app.main import app
from app.models.audio import AudioMetrics
from app.models.visual import VisualMetrics
from app.pipeline.analytics import (
    compute_delivery_trends,
    compute_pca_and_clustering,
    extract_session_feature_vector,
)

client = TestClient(app)


def make_dummy_audio_metrics(wpm: float = 140.0, filler_ratio: float = 0.04) -> AudioMetrics:
    return AudioMetrics(
        total_duration_seconds=60.0,
        speaking_duration_seconds=50.0,
        total_words=int(wpm),
        words_per_minute=wpm,
        articulation_rate_wpm=wpm * 1.2,
        filler_words_count=int(wpm * filler_ratio),
        filler_words_ratio=filler_ratio,
        filler_words_breakdown={"um": 2},
        pause_count=6,
        total_pause_duration_seconds=10.0,
        average_pause_duration_seconds=1.66,
        longest_pause_duration_seconds=2.5,
        pause_threshold_seconds=0.5,
        pauses=[],
    )


def make_dummy_visual_metrics(gaze: float = 0.8, stability: float = 0.9) -> VisualMetrics:
    return VisualMetrics(
        total_duration_seconds=60.0,
        frames_analyzed=1800,
        face_detected_ratio=1.0,
        centered_gaze_ratio=gaze,
        gaze_distribution={"center": gaze, "left": (1 - gaze) / 2, "right": (1 - gaze) / 2},
        head_stability_score=stability,
        head_movement_variance=0.002,
        hands_visible_ratio=0.5,
        hand_gestures_per_minute=6.0,
        tracking_notes=[],
        ethical_disclaimer="Approximate geometric estimates only.",
    )


def test_feature_vector_imputation():
    # 1. Full multimodal
    vec_full = extract_session_feature_vector(
        session_id="s1",
        audio_metrics=make_dummy_audio_metrics(145.0, 0.02),
        visual_metrics=make_dummy_visual_metrics(0.85, 0.95),
    )
    assert vec_full.has_audio is True
    assert vec_full.has_visual is True
    assert vec_full.words_per_minute == 145.0
    assert vec_full.centered_gaze_ratio == 0.85

    # 2. Audio only (visual imputed)
    vec_audio_only = extract_session_feature_vector(
        session_id="s2",
        audio_metrics=make_dummy_audio_metrics(130.0, 0.05),
        visual_metrics=None,
    )
    assert vec_audio_only.has_audio is True
    assert vec_audio_only.has_visual is False
    assert vec_audio_only.words_per_minute == 130.0
    assert vec_audio_only.centered_gaze_ratio == 0.70  # neutral default

    # 3. Visual only (audio imputed)
    vec_visual_only = extract_session_feature_vector(
        session_id="s3",
        audio_metrics=None,
        visual_metrics=make_dummy_visual_metrics(0.75, 0.88),
    )
    assert vec_visual_only.has_audio is False
    assert vec_visual_only.has_visual is True
    assert vec_visual_only.words_per_minute == 135.0  # neutral default


def test_pca_insufficient_samples_fallback():
    # Only 2 sessions -> insufficient for 2D PCA
    vectors = [
        extract_session_feature_vector(
            "s1", session_index=0, audio_metrics=make_dummy_audio_metrics(120)
        ),
        extract_session_feature_vector(
            "s2", session_index=1, audio_metrics=make_dummy_audio_metrics(130)
        ),
    ]
    pca_result, clusters = compute_pca_and_clustering(vectors)
    assert pca_result.is_fallback is True
    assert "Insufficient sessions (2/3)" in pca_result.status_message
    assert len(clusters) == 0
    assert len(pca_result.points) == 2


def test_pca_and_clustering_reproducibility():
    # 4 distinct sessions
    vectors = [
        extract_session_feature_vector(
            f"s{i}",
            session_index=i,
            audio_metrics=make_dummy_audio_metrics(100.0 + i * 25.0, 0.02 + i * 0.02),
            visual_metrics=make_dummy_visual_metrics(0.6 + i * 0.1, 0.7 + i * 0.08),
        )
        for i in range(4)
    ]

    pca_run1, clusters1 = compute_pca_and_clustering(vectors, random_state=42)
    pca_run2, clusters2 = compute_pca_and_clustering(vectors, random_state=42)

    assert pca_run1.is_fallback is False
    assert len(pca_run1.explained_variance_ratio) == 2
    assert len(pca_run1.points) == 4
    assert len(clusters1) >= 2

    # Verify exact numerical reproducibility with fixed random seed
    for p1, p2 in zip(pca_run1.points, pca_run2.points, strict=False):
        assert p1.pca_x == p2.pca_x
        assert p1.pca_y == p2.pca_y
        assert p1.cluster_id == p2.cluster_id


def test_trend_analysis_slopes():
    # Decreasing filler words and steady pace across 3 sessions
    vectors = [
        extract_session_feature_vector(
            f"s{i}",
            session_index=i,
            audio_metrics=make_dummy_audio_metrics(140.0, 0.08 - (i * 0.03)),
        )
        for i in range(3)
    ]
    trends = compute_delivery_trends(vectors)
    assert len(trends.points) == 3
    assert abs(trends.wpm_slope) < 2.0  # Steady pace
    assert trends.filler_ratio_slope < 0.0  # Downward improvement trend
    assert "downward improvement trend" in trends.filler_direction_summary.lower()


def test_aggregate_analytics_api_endpoint():
    payload = {
        "sessions": [
            {
                "session_id": "session-1",
                "session_index": 0,
                "audio_metrics": make_dummy_audio_metrics(125.0, 0.06).model_dump(),
                "visual_metrics": make_dummy_visual_metrics(0.70, 0.85).model_dump(),
            },
            {
                "session_id": "session-2",
                "session_index": 1,
                "audio_metrics": make_dummy_audio_metrics(135.0, 0.04).model_dump(),
                "visual_metrics": make_dummy_visual_metrics(0.75, 0.88).model_dump(),
            },
            {
                "session_id": "session-3",
                "session_index": 2,
                "audio_metrics": make_dummy_audio_metrics(145.0, 0.02).model_dump(),
                "visual_metrics": make_dummy_visual_metrics(0.85, 0.92).model_dump(),
            },
        ]
    }

    response = client.post("/api/v1/analytics/aggregate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["total_sessions_analyzed"] == 3
    assert data["pca"]["is_fallback"] is False
    assert len(data["pca"]["points"]) == 3
    assert len(data["clusters"]) >= 2
    assert data["trends"]["wpm_slope"] > 0
    assert "statistical groupings" in data["ethical_note"].lower()
