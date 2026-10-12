"""Privacy-first geometric visual delivery calculations.

Measures:
- Approximate gaze-direction orientation relative to the camera cone
- Head centroid stability and movement variance
- Hand gesture frequency and visibility

Important Ethical & Scientific Boundaries:
- These measurements are purely geometric coordinates and motion proxies.
- They do NOT detect, infer, or evaluate emotions, honesty, confidence, or personality.
- Raw video frames are discarded or kept entirely in the user's browser.
"""

from __future__ import annotations

import math

from app.models.visual import VisualFrameSample, VisualMetrics

ETHICAL_DISCLAIMER_TEXT = (
    "These visual measurements represent approximate geometric estimates (e.g. 2D pupil offsets, "
    "head displacement variance, and wrist movement velocity). They do NOT measure, infer, "
    "or evaluate emotion, confidence, honesty, intelligence, competence, or personality. "
    "Webcam tracking is sensitive to camera position, lighting, and angle."
)

# Gaze ratio bounds relative to eye canthi
CENTER_GAZE_MIN_X = 0.35
CENTER_GAZE_MAX_X = 0.65
VERTICAL_GAZE_THRESHOLD = 0.035

# Velocity threshold for significant hand movement (normalized units per second)
HAND_VELOCITY_THRESHOLD = 0.15


def estimate_frame_gaze(frame: VisualFrameSample) -> str | None:
    """Estimate discrete gaze direction for a single frame using pupil geometric position.

    Returns:
        One of 'center', 'left', 'right', 'up', 'down', or None if landmarks are missing.
    """
    # Prefer left eye or right eye if available
    ratios: list[float] = []
    vert_offsets: list[float] = []

    # Check left eye
    if frame.left_iris and frame.left_eye_inner and frame.left_eye_outer:
        x_min = min(frame.left_eye_inner.x, frame.left_eye_outer.x)
        x_max = max(frame.left_eye_inner.x, frame.left_eye_outer.x)
        eye_width = x_max - x_min
        if eye_width > 0.002:
            h_ratio = (frame.left_iris.x - x_min) / eye_width
            ratios.append(h_ratio)
            eye_y_center = (frame.left_eye_inner.y + frame.left_eye_outer.y) / 2.0
            vert_offsets.append(frame.left_iris.y - eye_y_center)

    # Check right eye
    if frame.right_iris and frame.right_eye_inner and frame.right_eye_outer:
        x_min = min(frame.right_eye_inner.x, frame.right_eye_outer.x)
        x_max = max(frame.right_eye_inner.x, frame.right_eye_outer.x)
        eye_width = x_max - x_min
        if eye_width > 0.002:
            h_ratio = (frame.right_iris.x - x_min) / eye_width
            ratios.append(h_ratio)
            eye_y_center = (frame.right_eye_inner.y + frame.right_eye_outer.y) / 2.0
            vert_offsets.append(frame.right_iris.y - eye_y_center)

    if not ratios:
        return None

    avg_ratio = sum(ratios) / len(ratios)
    avg_vert = sum(vert_offsets) / len(vert_offsets) if vert_offsets else 0.0

    if avg_vert < -VERTICAL_GAZE_THRESHOLD:
        return "up"
    if avg_vert > VERTICAL_GAZE_THRESHOLD:
        return "down"
    if avg_ratio < CENTER_GAZE_MIN_X:
        return "left"
    if avg_ratio > CENTER_GAZE_MAX_X:
        return "right"
    return "center"


def compute_head_stability(
    frames: list[VisualFrameSample],
) -> tuple[float, float]:
    """Calculate head centroid position variance and normalized stability score.

    Returns:
        Tuple of (stability_score [0.0 - 1.0], displacement_variance).
    """
    valid_coords = [(f.nose_tip.x, f.nose_tip.y) for f in frames if f.nose_tip]
    if len(valid_coords) < 2:
        return 1.0, 0.0

    mean_x = sum(pt[0] for pt in valid_coords) / len(valid_coords)
    mean_y = sum(pt[1] for pt in valid_coords) / len(valid_coords)

    var_x = sum((pt[0] - mean_x) ** 2 for pt in valid_coords) / len(valid_coords)
    var_y = sum((pt[1] - mean_y) ** 2 for pt in valid_coords) / len(valid_coords)
    total_var = var_x + var_y

    # Normalize: variance of 0 -> score 1.0; high variance -> approaches 0.0
    stability_score = round(1.0 / (1.0 + 80.0 * total_var), 3)
    return stability_score, round(total_var, 6)


def compute_hand_gestures(
    frames: list[VisualFrameSample],
    total_duration_seconds: float,
) -> tuple[float, float, int]:
    """Detect hand visibility and count significant movement episodes.

    Returns:
        Tuple of (hands_visible_ratio, gestures_per_minute, total_gestures).
    """
    if not frames or total_duration_seconds <= 0:
        return 0.0, 0.0, 0

    visible_frames = sum(1 for f in frames if f.left_wrist or f.right_wrist)
    visible_ratio = round(visible_frames / len(frames), 3)

    if visible_frames < 2:
        return visible_ratio, 0.0, 0

    # Calculate wrist velocity between adjacent frames
    gestures_detected = 0
    in_gesture = False

    for i in range(len(frames) - 1):
        f1, f2 = frames[i], frames[i + 1]
        dt = f2.timestamp - f1.timestamp
        if dt <= 0 or dt > 1.0:  # Skip dropped / disconnected intervals
            continue

        velocities = []
        if f1.left_wrist and f2.left_wrist:
            dist = math.hypot(f2.left_wrist.x - f1.left_wrist.x, f2.left_wrist.y - f1.left_wrist.y)
            velocities.append(dist / dt)
        if f1.right_wrist and f2.right_wrist:
            dist = math.hypot(
                f2.right_wrist.x - f1.right_wrist.x, f2.right_wrist.y - f1.right_wrist.y
            )
            velocities.append(dist / dt)

        if not velocities:
            in_gesture = False
            continue

        max_vel = max(velocities)
        if max_vel >= HAND_VELOCITY_THRESHOLD and not in_gesture:
            gestures_detected += 1
            in_gesture = True
        elif max_vel < (HAND_VELOCITY_THRESHOLD * 0.6):
            in_gesture = False

    duration_minutes = total_duration_seconds / 60.0
    gpm = round(gestures_detected / duration_minutes, 2) if duration_minutes > 0 else 0.0

    return visible_ratio, gpm, gestures_detected


def compute_visual_metrics(
    frames: list[VisualFrameSample],
    known_duration_seconds: float | None = None,
) -> VisualMetrics:
    """Compute consolidated, objective visual delivery metrics from landmark timeseries.

    Handles empty frames, missing landmarks, and degraded tracking gracefully.
    """
    total_frames = len(frames)
    tracking_notes: list[str] = []

    # 1. Determine duration
    if known_duration_seconds is not None and known_duration_seconds > 0:
        total_duration = round(float(known_duration_seconds), 2)
    elif frames:
        total_duration = round(
            max(f.timestamp for f in frames) - min(f.timestamp for f in frames), 2
        )
        if total_duration == 0.0:
            total_duration = round(total_frames / 30.0, 2)  # Assuming standard 30fps
    else:
        total_duration = 0.0

    if total_frames == 0:
        tracking_notes.append("No visual frames received for analysis.")
        return VisualMetrics(
            total_duration_seconds=0.0,
            frames_analyzed=0,
            face_detected_ratio=0.0,
            centered_gaze_ratio=0.0,
            gaze_distribution={"center": 0.0, "left": 0.0, "right": 0.0, "up": 0.0, "down": 0.0},
            head_stability_score=1.0,
            head_movement_variance=0.0,
            hands_visible_ratio=0.0,
            hand_gestures_per_minute=0.0,
            tracking_notes=tracking_notes,
            ethical_disclaimer=ETHICAL_DISCLAIMER_TEXT,
        )

    # 2. Face detection tracking
    face_frames = [f for f in frames if f.nose_tip]
    face_ratio = round(len(face_frames) / total_frames, 3)

    if face_ratio == 0.0:
        tracking_notes.append(
            "No face landmarks detected in any frame. Check camera position and lighting."
        )
    elif face_ratio < 0.6:
        tracking_notes.append(
            f"Face detected in only {int(face_ratio * 100)}% of frames. "
            "Gaze and head stability estimates may be limited."
        )

    # 3. Gaze direction estimation
    gaze_counts: dict[str, int] = {"center": 0, "left": 0, "right": 0, "up": 0, "down": 0}
    gaze_frames_total = 0

    for f in frames:
        direction = estimate_frame_gaze(f)
        if direction:
            gaze_counts[direction] += 1
            gaze_frames_total += 1

    if gaze_frames_total > 0:
        gaze_distribution = {k: round(v / gaze_frames_total, 3) for k, v in gaze_counts.items()}
        centered_gaze_ratio = gaze_distribution["center"]
    else:
        gaze_distribution = {"center": 0.0, "left": 0.0, "right": 0.0, "up": 0.0, "down": 0.0}
        centered_gaze_ratio = 0.0
        if face_ratio > 0.0:
            tracking_notes.append("Iris landmarks were not visible or could not be tracked.")

    # 4. Head stability
    stability_score, head_var = compute_head_stability(frames)

    # 5. Hand gestures
    hands_ratio, gpm, _ = compute_hand_gestures(frames, total_duration)
    if hands_ratio == 0.0:
        tracking_notes.append(
            "No hand landmarks observed. Hands may be resting outside the camera frame."
        )

    return VisualMetrics(
        total_duration_seconds=total_duration,
        frames_analyzed=total_frames,
        face_detected_ratio=face_ratio,
        centered_gaze_ratio=centered_gaze_ratio,
        gaze_distribution=gaze_distribution,
        head_stability_score=stability_score,
        head_movement_variance=head_var,
        hands_visible_ratio=hands_ratio,
        hand_gestures_per_minute=gpm,
        tracking_notes=tracking_notes,
        ethical_disclaimer=ETHICAL_DISCLAIMER_TEXT,
    )
