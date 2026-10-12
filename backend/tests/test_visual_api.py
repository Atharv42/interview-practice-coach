"""API tests for visual analysis and capabilities endpoints."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_visual_capabilities_endpoint():
    response = client.get("/api/v1/visual/capabilities")
    assert response.status_code == 200
    data = response.json()
    assert data["privacy_model"] == "client_side_processing"
    assert data["raw_video_retention"] == "none"
    assert "approximate_gaze_direction" in data["supported_features"]
    assert "head_centroid_stability" in data["supported_features"]
    assert "hand_gesture_frequency" in data["supported_features"]
    assert "emotion_recognition" in data["ethical_design"]["prohibited_features"]


def test_visual_analysis_endpoint_with_frames():
    payload = {
        "session_id": "test-session-123",
        "recording_duration_seconds": 3.0,
        "frames": [
            {
                "timestamp": 0.0,
                "nose_tip": {"x": 0.5, "y": 0.5},
                "left_eye_inner": {"x": 0.45, "y": 0.48},
                "left_eye_outer": {"x": 0.55, "y": 0.48},
                "left_iris": {"x": 0.50, "y": 0.48},
            },
            {
                "timestamp": 1.0,
                "nose_tip": {"x": 0.5, "y": 0.5},
                "left_eye_inner": {"x": 0.45, "y": 0.48},
                "left_eye_outer": {"x": 0.55, "y": 0.48},
                "left_iris": {"x": 0.50, "y": 0.48},
            },
            {
                "timestamp": 2.0,
                "nose_tip": {"x": 0.5, "y": 0.5},
                "left_eye_inner": {"x": 0.45, "y": 0.48},
                "left_eye_outer": {"x": 0.55, "y": 0.48},
                "left_iris": {"x": 0.50, "y": 0.48},
            },
        ],
    }

    response = client.post("/api/v1/visual/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    metrics = data["metrics"]
    assert metrics["frames_analyzed"] == 3
    assert metrics["face_detected_ratio"] == 1.0
    assert metrics["centered_gaze_ratio"] == 1.0
    assert metrics["head_stability_score"] >= 0.95
    assert len(data["recommendations"]) > 0


def test_visual_analysis_endpoint_empty_payload():
    payload = {"frames": []}
    response = client.post("/api/v1/visual/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["metrics"]["frames_analyzed"] == 0
    assert len(data["metrics"]["tracking_notes"]) > 0
