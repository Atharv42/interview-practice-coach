"""Unit tests for visual delivery mechanics and geometric feature extraction."""

from app.models.visual import LandmarkPoint, VisualFrameSample
from app.pipeline.visual_features import (
    ETHICAL_DISCLAIMER_TEXT,
    compute_hand_gestures,
    compute_head_stability,
    compute_visual_metrics,
    estimate_frame_gaze,
)


def test_empty_visual_frames():
    metrics = compute_visual_metrics(frames=[], known_duration_seconds=0.0)
    assert metrics.frames_analyzed == 0
    assert metrics.total_duration_seconds == 0.0
    assert metrics.face_detected_ratio == 0.0
    assert metrics.centered_gaze_ratio == 0.0
    assert len(metrics.tracking_notes) > 0
    assert "No visual frames received" in metrics.tracking_notes[0]
    assert metrics.ethical_disclaimer == ETHICAL_DISCLAIMER_TEXT


def test_gaze_direction_estimates():
    # Helper to construct a frame with left eye landmarks
    def make_gaze_frame(iris_x: float, iris_y: float) -> VisualFrameSample:
        return VisualFrameSample(
            timestamp=0.1,
            left_eye_inner=LandmarkPoint(x=0.4, y=0.5),
            left_eye_outer=LandmarkPoint(x=0.6, y=0.5),
            left_iris=LandmarkPoint(x=iris_x, y=iris_y),
            nose_tip=LandmarkPoint(x=0.5, y=0.5),
        )

    # Eye center is at x = 0.5 (ratio = (0.5 - 0.4) / (0.6 - 0.4) = 0.5) -> center
    frame_center = make_gaze_frame(0.50, 0.50)
    assert estimate_frame_gaze(frame_center) == "center"

    # Pupil near inner corner: x = 0.42 (ratio = 0.1) -> left (< 0.35)
    frame_left = make_gaze_frame(0.42, 0.50)
    assert estimate_frame_gaze(frame_left) == "left"

    # Pupil near outer corner: x = 0.58 (ratio = 0.9) -> right (> 0.65)
    frame_right = make_gaze_frame(0.58, 0.50)
    assert estimate_frame_gaze(frame_right) == "right"

    # Pupil looking up: iris y = 0.44 (offset = 0.44 - 0.50 = -0.06 < -0.035) -> up
    frame_up = make_gaze_frame(0.50, 0.44)
    assert estimate_frame_gaze(frame_up) == "up"

    # Pupil looking down: iris y = 0.56 (offset = 0.56 - 0.50 = +0.06 > 0.035) -> down
    frame_down = make_gaze_frame(0.50, 0.56)
    assert estimate_frame_gaze(frame_down) == "down"


def test_head_stability_static_vs_moving():
    # 1. Perfectly static head
    static_frames = [
        VisualFrameSample(
            timestamp=i * 0.1,
            nose_tip=LandmarkPoint(x=0.5, y=0.5),
        )
        for i in range(10)
    ]
    score_static, var_static = compute_head_stability(static_frames)
    assert score_static == 1.0
    assert var_static == 0.0

    # 2. Moving head
    moving_frames = [
        VisualFrameSample(
            timestamp=i * 0.1,
            nose_tip=LandmarkPoint(x=0.5 + (0.1 if i % 2 == 0 else -0.1), y=0.5),
        )
        for i in range(10)
    ]
    score_moving, var_moving = compute_head_stability(moving_frames)
    assert var_moving > 0.005
    assert score_moving < score_static


def test_hand_gestures_and_visibility():
    # 1. Stationary hands
    stationary_frames = [
        VisualFrameSample(
            timestamp=i * 0.1,
            left_wrist=LandmarkPoint(x=0.3, y=0.8),
            right_wrist=LandmarkPoint(x=0.7, y=0.8),
        )
        for i in range(20)  # 2.0 seconds
    ]
    vis_ratio, gpm, count = compute_hand_gestures(stationary_frames, total_duration_seconds=2.0)
    assert vis_ratio == 1.0
    assert gpm == 0.0
    assert count == 0

    # 2. Moving hands with velocity spikes
    moving_frames = []
    for i in range(20):
        # alternate y rapidly
        y_pos = 0.8 if (i // 5) % 2 == 0 else 0.4
        moving_frames.append(
            VisualFrameSample(
                timestamp=i * 0.1,
                left_wrist=LandmarkPoint(x=0.3, y=y_pos),
            )
        )
    vis_ratio, gpm, count = compute_hand_gestures(moving_frames, total_duration_seconds=2.0)
    assert vis_ratio == 1.0
    assert count > 0
    assert gpm > 0.0


def test_ethical_disclaimer_integrity():
    frames = [
        VisualFrameSample(
            timestamp=0.1,
            nose_tip=LandmarkPoint(x=0.5, y=0.5),
        )
    ]
    metrics = compute_visual_metrics(frames, known_duration_seconds=1.0)
    assert "emotion" in metrics.ethical_disclaimer.lower()
    assert "confidence" in metrics.ethical_disclaimer.lower()
    assert "honesty" in metrics.ethical_disclaimer.lower()
    assert "personality" in metrics.ethical_disclaimer.lower()
