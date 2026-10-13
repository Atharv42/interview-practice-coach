"""Exploratory Data Analysis (EDA) and Model Prototyping for Interview Practice Coach.

Demonstrates:
1. Feature extraction from synthetic multimodal interview delivery sessions
2. Standard scaling across acoustic and visual delivery features
3. 2D Principal Component Analysis (PCA) projection
4. K-Means clustering for exploratory delivery archetype discovery
5. Chronological pacing regression trend analysis

Can be executed as a standalone Python script or imported into Jupyter / Marimo.
"""

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

FEATURE_NAMES = [
    "words_per_minute",
    "articulation_rate_wpm",
    "filler_words_ratio",
    "average_pause_duration_seconds",
    "pause_frequency_per_minute",
    "centered_gaze_ratio",
    "head_stability_score",
    "hand_gestures_per_minute",
]


def generate_synthetic_practice_sessions(n_sessions: int = 15, seed: int = 42) -> pd.DataFrame:
    """Generate representative candidate interview practice attempts across archetypes."""
    np.random.seed(seed)
    records = []

    for i in range(n_sessions):
        # Progressively improve pace stability and reduce fillers
        progression_factor = i / n_sessions
        base_wpm = 120.0 + (progression_factor * 25.0) + np.random.normal(0, 5.0)
        filler_ratio = max(0.01, 0.08 - (progression_factor * 0.05) + np.random.normal(0, 0.01))
        avg_pause = max(0.3, 1.2 - (progression_factor * 0.4) + np.random.normal(0, 0.1))
        gaze_ratio = min(0.95, 0.60 + (progression_factor * 0.25) + np.random.normal(0, 0.05))
        stability = min(0.98, 0.70 + (progression_factor * 0.20) + np.random.normal(0, 0.04))

        record = {
            "session_id": f"session_{i + 1:03d}",
            "session_index": i,
            "words_per_minute": round(base_wpm, 1),
            "articulation_rate_wpm": round(base_wpm * 1.15, 1),
            "filler_words_ratio": round(filler_ratio, 4),
            "average_pause_duration_seconds": round(avg_pause, 2),
            "pause_frequency_per_minute": round(5.0 + np.random.uniform(0, 3.0), 1),
            "centered_gaze_ratio": round(gaze_ratio, 2),
            "head_stability_score": round(stability, 2),
            "hand_gestures_per_minute": round(4.0 + np.random.uniform(0, 6.0), 1),
        }
        records.append(record)

    return pd.DataFrame(records)


def run_delivery_analysis(df: pd.DataFrame):
    """Run StandardScaler, 2D PCA, and K-Means clustering."""
    X = df[FEATURE_NAMES].values

    # 1. Standardize features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # 2. 2D Principal Component Analysis
    pca = PCA(n_components=2, random_state=42)
    coords_2d = pca.fit_transform(X_scaled)
    var_ratio = pca.explained_variance_ratio_

    # 3. K-Means clustering (3 archetypes)
    kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
    clusters = kmeans.fit_predict(X_scaled)

    df["pca_x"] = coords_2d[:, 0].round(3)
    df["pca_y"] = coords_2d[:, 1].round(3)
    df["cluster"] = clusters

    # 4. Chronological WPM slope
    slope, intercept = np.polyfit(df["session_index"], df["words_per_minute"], 1)

    print("=" * 60)
    print("INTERVIEW PRACTICE COACH — EXPLORATORY DELIVERY ANALYSIS")
    print("=" * 60)
    print(f"Total Sessions Analyzed: {len(df)}")
    print(f"PCA Variance Explained: PC1={var_ratio[0]:.2%}, PC2={var_ratio[1]:.2%}")
    print(f"Longitudinal WPM Slope: {slope:+.2f} WPM per session")
    print("\nCluster Centroids:")
    centroids = df.groupby("cluster")[FEATURE_NAMES].mean().round(2)
    print(centroids.to_string())
    print("\nSample Projections (First 5 sessions):")
    print(df[["session_id", "words_per_minute", "filler_words_ratio", "pca_x", "pca_y", "cluster"]].head().to_string())
    print("=" * 60)

    return df, pca, kmeans


if __name__ == "__main__":
    df_sessions = generate_synthetic_practice_sessions()
    run_delivery_analysis(df_sessions)
