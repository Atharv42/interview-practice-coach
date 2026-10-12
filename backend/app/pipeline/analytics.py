"""Multimodal delivery feature aggregation, PCA projection, clustering, and trend analysis.

Combines acoustic and geometric visual delivery mechanics into unified session vectors.
Applies unsupervised PCA and K-Means to discover exploratory delivery groupings.
"""

from __future__ import annotations

import numpy as np
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

from app.models.analytics import (
    ClusterSummary,
    PCAProjectionPoint,
    PCAResult,
    SessionFeatureVector,
    TrendAnalysis,
    TrendPoint,
)
from app.models.audio import AudioMetrics
from app.models.visual import VisualMetrics

# Numeric feature column names in canonical order
FEATURE_NAMES: list[str] = [
    "words_per_minute",
    "articulation_rate_wpm",
    "filler_words_ratio",
    "average_pause_duration_seconds",
    "pause_frequency_per_minute",
    "centered_gaze_ratio",
    "head_stability_score",
    "hand_gestures_per_minute",
]

# Neutral baseline defaults used when a modality was not recorded
NEUTRAL_AUDIO_DEFAULTS = {
    "words_per_minute": 135.0,
    "articulation_rate_wpm": 150.0,
    "filler_words_ratio": 0.03,
    "average_pause_duration_seconds": 0.6,
    "pause_frequency_per_minute": 6.0,
}

NEUTRAL_VISUAL_DEFAULTS = {
    "centered_gaze_ratio": 0.70,
    "head_stability_score": 0.85,
    "hand_gestures_per_minute": 5.0,
}


def extract_session_feature_vector(
    session_id: str,
    session_index: int = 0,
    timestamp_iso: str | None = None,
    audio_metrics: AudioMetrics | None = None,
    visual_metrics: VisualMetrics | None = None,
) -> SessionFeatureVector:
    """Aggregate audio and visual delivery metrics into a normalized session feature vector.

    Imputes neutral baseline values if either modality is unavailable.
    """
    has_audio = audio_metrics is not None
    has_visual = visual_metrics is not None

    if has_audio and audio_metrics is not None:
        duration_min = max(0.1, audio_metrics.total_duration_seconds / 60.0)
        pause_freq = round(audio_metrics.pause_count / duration_min, 2)
        wpm = audio_metrics.words_per_minute
        articulation_wpm = audio_metrics.articulation_rate_wpm
        filler_ratio = audio_metrics.filler_words_ratio
        avg_pause = audio_metrics.average_pause_duration_seconds
    else:
        wpm = NEUTRAL_AUDIO_DEFAULTS["words_per_minute"]
        articulation_wpm = NEUTRAL_AUDIO_DEFAULTS["articulation_rate_wpm"]
        filler_ratio = NEUTRAL_AUDIO_DEFAULTS["filler_words_ratio"]
        avg_pause = NEUTRAL_AUDIO_DEFAULTS["average_pause_duration_seconds"]
        pause_freq = NEUTRAL_AUDIO_DEFAULTS["pause_frequency_per_minute"]

    if has_visual and visual_metrics is not None:
        centered_gaze = visual_metrics.centered_gaze_ratio
        head_stability = visual_metrics.head_stability_score
        hand_gestures = visual_metrics.hand_gestures_per_minute
    else:
        centered_gaze = NEUTRAL_VISUAL_DEFAULTS["centered_gaze_ratio"]
        head_stability = NEUTRAL_VISUAL_DEFAULTS["head_stability_score"]
        hand_gestures = NEUTRAL_VISUAL_DEFAULTS["hand_gestures_per_minute"]

    return SessionFeatureVector(
        session_id=session_id,
        session_index=session_index,
        timestamp_iso=timestamp_iso,
        has_audio=has_audio,
        has_visual=has_visual,
        words_per_minute=wpm,
        articulation_rate_wpm=articulation_wpm,
        filler_words_ratio=filler_ratio,
        average_pause_duration_seconds=avg_pause,
        pause_frequency_per_minute=pause_freq,
        centered_gaze_ratio=centered_gaze,
        head_stability_score=head_stability,
        hand_gestures_per_minute=hand_gestures,
    )


def vector_to_matrix(vectors: list[SessionFeatureVector]) -> np.ndarray:
    """Convert a list of SessionFeatureVector objects into a 2D NumPy array."""
    data = []
    for vec in vectors:
        row = [getattr(vec, fname) for fname in FEATURE_NAMES]
        data.append(row)
    return np.array(data, dtype=float)


def generate_cluster_archetype_label(
    centroid: dict[str, float], cluster_idx: int
) -> tuple[str, str]:
    """Generate a neutral, descriptive statistical profile label for a cluster centroid."""
    pace = centroid.get("words_per_minute", 130.0)
    stability = centroid.get("head_stability_score", 0.8)
    gestures = centroid.get("hand_gestures_per_minute", 5.0)

    # Pace description
    if pace > 155.0:
        pace_desc = "Fast-Paced"
    elif pace < 115.0:
        pace_desc = "Deliberate"
    else:
        pace_desc = "Moderate-Paced"

    # Movement description
    if stability >= 0.85 and gestures <= 8.0:
        motion_desc = "Composed Posture"
    elif gestures > 10.0:
        motion_desc = "Expressive Gestures"
    else:
        motion_desc = "Balanced Posture"

    label = f"Cluster {cluster_idx}: {pace_desc}, {motion_desc}"
    detail = (
        f"Statistical profile averaging {pace:.1f} WPM, {stability:.2f} stability score, "
        f"and {gestures:.1f} gestures/min."
    )
    return label, detail


def compute_pca_and_clustering(
    vectors: list[SessionFeatureVector],
    random_state: int = 42,
) -> tuple[PCAResult, list[ClusterSummary]]:
    """Compute 2D PCA projection and K-Means exploratory cluster groupings.

    Requires at least 3 sessions to fit a 2D projection safely.
    """
    n_samples = len(vectors)

    if n_samples < 3:
        # Fallback state: return neutral placeholder points without fitting
        points = [
            PCAProjectionPoint(
                session_id=vec.session_id,
                session_index=vec.session_index,
                pca_x=0.0,
                pca_y=0.0,
                cluster_id=0,
                cluster_label="Preliminary Session",
            )
            for vec in vectors
        ]
        fallback_pca = PCAResult(
            is_fallback=True,
            status_message=(
                f"Insufficient sessions ({n_samples}/3). "
                "Complete at least 3 practice sessions to calculate 2D PCA delivery projections."
            ),
            explained_variance_ratio=[],
            feature_loadings={},
            points=points,
        )
        return fallback_pca, []

    X = vector_to_matrix(vectors)

    # 1. Feature scaling
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # 2. PCA 2D projection
    pca = PCA(n_components=2, random_state=random_state)
    coords_2d = pca.fit_transform(X_scaled)
    explained_var = [round(float(v), 4) for v in pca.explained_variance_ratio_]

    # Feature loadings for PC1 and PC2
    loadings: dict[str, dict[str, float]] = {}
    for i, fname in enumerate(FEATURE_NAMES):
        loadings[fname] = {
            "PC1": round(float(pca.components_[0, i]), 4),
            "PC2": round(float(pca.components_[1, i]), 4),
        }

    # 3. K-Means clustering
    n_clusters = 2 if n_samples < 6 else 3
    kmeans = KMeans(n_clusters=n_clusters, random_state=random_state, n_init=10)
    cluster_labels = kmeans.fit_predict(X_scaled)

    # 4. Generate cluster summaries
    cluster_summaries: list[ClusterSummary] = []
    cluster_name_map: dict[int, str] = {}

    for c_id in range(n_clusters):
        member_indices = np.where(cluster_labels == c_id)[0]
        member_count = len(member_indices)
        if member_count > 0:
            mean_vector = X[member_indices].mean(axis=0)
            centroid_dict = {
                fname: round(float(val), 3)
                for fname, val in zip(FEATURE_NAMES, mean_vector, strict=False)
            }
        else:
            centroid_dict = {}

        label, detail = generate_cluster_archetype_label(centroid_dict, c_id)
        cluster_name_map[c_id] = label

        cluster_summaries.append(
            ClusterSummary(
                cluster_id=c_id,
                cluster_label=label,
                session_count=member_count,
                centroid_features=centroid_dict,
                description=detail,
            )
        )

    # 5. Populate projection points
    projection_points: list[PCAProjectionPoint] = []
    for vec, coord, c_id in zip(vectors, coords_2d, cluster_labels, strict=False):
        projection_points.append(
            PCAProjectionPoint(
                session_id=vec.session_id,
                session_index=vec.session_index,
                pca_x=round(float(coord[0]), 3),
                pca_y=round(float(coord[1]), 3),
                cluster_id=int(c_id),
                cluster_label=cluster_name_map[int(c_id)],
            )
        )

    pca_result = PCAResult(
        is_fallback=False,
        status_message=(
            f"Exploratory PCA and K-Means calculated across {n_samples} sessions."
        ),
        explained_variance_ratio=explained_var,
        feature_loadings=loadings,
        points=projection_points,
    )

    return pca_result, cluster_summaries


def compute_delivery_trends(
    vectors: list[SessionFeatureVector],
) -> TrendAnalysis:
    """Compute chronological metric trends and linear regression slopes across sessions."""
    if not vectors:
        return TrendAnalysis(
            points=[],
            wpm_slope=0.0,
            filler_ratio_slope=0.0,
            pace_direction_summary="No session history recorded yet.",
            filler_direction_summary="No session history recorded yet.",
        )

    # Sort chronologically by session index
    sorted_vectors = sorted(vectors, key=lambda v: v.session_index)

    points: list[TrendPoint] = []
    wpm_series: list[float] = []
    filler_series: list[float] = []

    for vec in sorted_vectors:
        points.append(
            TrendPoint(
                session_index=vec.session_index,
                session_id=vec.session_id,
                timestamp_iso=vec.timestamp_iso,
                words_per_minute=round(vec.words_per_minute, 1),
                filler_words_ratio=round(vec.filler_words_ratio, 4),
                average_pause_duration_seconds=round(vec.average_pause_duration_seconds, 2),
                centered_gaze_ratio=round(vec.centered_gaze_ratio, 2),
                head_stability_score=round(vec.head_stability_score, 2),
                hand_gestures_per_minute=round(vec.hand_gestures_per_minute, 1),
            )
        )
        wpm_series.append(vec.words_per_minute)
        filler_series.append(vec.filler_words_ratio)

    n = len(points)
    if n < 2:
        return TrendAnalysis(
            points=points,
            wpm_slope=0.0,
            filler_ratio_slope=0.0,
            pace_direction_summary="Complete additional sessions to establish pacing trends.",
            filler_direction_summary="Complete additional sessions to establish filler trends.",
        )

    x = np.arange(n, dtype=float)
    # Fit simple linear slope: y = mx + c
    wpm_slope, _ = np.polyfit(x, np.array(wpm_series, dtype=float), 1)
    filler_slope, _ = np.polyfit(x, np.array(filler_series, dtype=float), 1)

    wpm_slope = round(float(wpm_slope), 2)
    filler_slope = round(float(filler_slope), 4)

    # Qualitative summaries
    if abs(wpm_slope) < 2.0:
        pace_summary = "Pacing has remained steady and consistent across practice sessions."
    elif wpm_slope > 2.0:
        pace_summary = (
            f"Speaking pace is accelerating by approximately {wpm_slope:+.1f} WPM per session."
        )
    else:
        pace_summary = (
            f"Speaking pace is becoming more deliberate by {abs(wpm_slope):.1f} WPM per session."
        )

    if filler_slope <= -0.005:
        filler_summary = (
            "Filler word usage shows a downward improvement trend over successive sessions."
        )
    elif filler_slope >= 0.005:
        filler_summary = (
            "Filler word frequency has slightly increased; try using deliberate pauses instead."
        )
    else:
        filler_summary = "Filler word ratio has remained stable across sessions."

    return TrendAnalysis(
        points=points,
        wpm_slope=wpm_slope,
        filler_ratio_slope=filler_slope,
        pace_direction_summary=pace_summary,
        filler_direction_summary=filler_summary,
    )
