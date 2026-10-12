"""API endpoints for session feature aggregation, PCA projection, and delivery trend analysis."""


from fastapi import APIRouter, status

from app.models.analytics import (
    AnalyticsDashboardResponse,
    BatchAnalyticsRequest,
    SessionFeatureVector,
)
from app.pipeline.analytics import (
    compute_delivery_trends,
    compute_pca_and_clustering,
    extract_session_feature_vector,
)

router = APIRouter(prefix="/analytics", tags=["Analytics Pipeline"])


@router.post(
    "/aggregate",
    response_model=AnalyticsDashboardResponse,
    status_code=status.HTTP_200_OK,
    summary="Aggregate session delivery metrics and compute PCA, clustering, and trends",
    description=(
        "Combines multimodal session delivery metrics into feature vectors. "
        "Calculates 2D PCA projections and exploratory K-Means delivery archetype clusters. "
        "Provides reproducible regression trend lines showing pacing evolution across sessions."
    ),
)
def aggregate_sessions_analytics(request: BatchAnalyticsRequest) -> AnalyticsDashboardResponse:
    """Aggregate multiple sessions, run PCA & clustering, and evaluate longitudinal trends."""
    feature_vectors: list[SessionFeatureVector] = []

    for idx, item in enumerate(request.sessions):
        vec = extract_session_feature_vector(
            session_id=item.session_id,
            session_index=item.session_index or idx,
            timestamp_iso=item.timestamp_iso,
            audio_metrics=item.audio_metrics,
            visual_metrics=item.visual_metrics,
        )
        feature_vectors.append(vec)

    pca_result, clusters = compute_pca_and_clustering(feature_vectors)
    trends = compute_delivery_trends(feature_vectors)

    return AnalyticsDashboardResponse(
        total_sessions_analyzed=len(feature_vectors),
        pca=pca_result,
        clusters=clusters,
        trends=trends,
    )
