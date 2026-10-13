import React, { useEffect, useState } from "react";
import {
  TrendingUp,
  Layers,
  Shield,
  Gauge,
  MessageSquare,
  AlertCircle,
  Loader2,
  RefreshCw,
  Info,
} from "lucide-react";
import { AnalyticsDashboardResponse, PCAProjectionPoint } from "../types";
import { api } from "../services/api";

const CLUSTER_COLORS = [
  "#2563eb", // blue
  "#10b981", // emerald
  "#8b5cf6", // purple
  "#f59e0b", // amber
  "#ec4899", // pink
];

export const AnalyticsDashboard: React.FC = () => {
  const [data, setData] = useState<AnalyticsDashboardResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [hoveredPoint, setHoveredPoint] = useState<PCAProjectionPoint | null>(null);

  const fetchAnalytics = async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const response = await api.getAnalyticsSummary();
      setData(response);
    } catch (err: unknown) {
      setErrorMessage(
        `Failed to load analytics: ${err instanceof Error ? err.message : String(err)}`
      );
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics();
  }, []);

  if (isLoading) {
    return (
      <div className="loading-state">
        <Loader2 size={36} className="spinner icon-primary" />
        <p>Calculating 2D PCA projections and longitudinal trends...</p>
      </div>
    );
  }

  if (errorMessage || !data) {
    return (
      <div className="card text-center">
        <AlertCircle size={40} className="text-danger empty-icon" />
        <h3>Analytics Unavailable</h3>
        <p className="text-muted">{errorMessage || "Could not retrieve session analytics."}</p>
        <button type="button" className="btn-secondary" onClick={fetchAnalytics}>
          Retry
        </button>
      </div>
    );
  }

  const { pca, clusters, trends, total_sessions_analyzed, ethical_note } = data;

  // Compute SVG coordinates for PCA scatter plot
  const renderPcaScatterPlot = () => {
    if (pca.is_fallback || pca.points.length === 0) {
      return (
        <div className="pca-fallback-box">
          <Info size={28} className="text-primary" />
          <h4>{pca.status_message}</h4>
          <p className="text-muted">
            Complete at least 3 practice sessions to calculate unsupervised 2D PCA delivery projections and exploratory K-Means clustering.
          </p>
        </div>
      );
    }

    const points = pca.points;
    const padding = 40;
    const width = 500;
    const height = 350;

    // Find min and max for scaling
    const xs = points.map((p) => p.pca_x);
    const ys = points.map((p) => p.pca_y);
    const minX = Math.min(...xs, -1);
    const maxX = Math.max(...xs, 1);
    const minY = Math.min(...ys, -1);
    const maxY = Math.max(...ys, 1);

    const scaleX = (val: number) =>
      padding + ((val - minX) / (maxX - minX || 1)) * (width - 2 * padding);
    const scaleY = (val: number) =>
      height - padding - ((val - minY) / (maxY - minY || 1)) * (height - 2 * padding);

    const originX = scaleX(0);
    const originY = scaleY(0);

    return (
      <div className="pca-plot-wrapper">
        <svg viewBox={`0 0 ${width} ${height}`} className="pca-svg">
          {/* Grid lines and axes */}
          <line
            x1={padding}
            y1={originY}
            x2={width - padding}
            y2={originY}
            stroke="#e2e8f0"
            strokeDasharray="4 4"
          />
          <line
            x1={originX}
            y1={padding}
            x2={originX}
            y2={height - padding}
            stroke="#e2e8f0"
            strokeDasharray="4 4"
          />

          {/* Points */}
          {points.map((pt, idx) => {
            const cx = scaleX(pt.pca_x);
            const cy = scaleY(pt.pca_y);
            const color = CLUSTER_COLORS[pt.cluster_id % CLUSTER_COLORS.length];
            const isHovered = hoveredPoint?.session_id === pt.session_id;

            return (
              <g
                key={idx}
                onMouseEnter={() => setHoveredPoint(pt)}
                onMouseLeave={() => setHoveredPoint(null)}
                className="cursor-pointer"
              >
                <circle
                  cx={cx}
                  cy={cy}
                  r={isHovered ? 8 : 6}
                  fill={color}
                  stroke="#ffffff"
                  strokeWidth={2}
                  className="pca-point"
                />
                <text
                  x={cx + 10}
                  y={cy + 4}
                  fontSize="11"
                  fill="#475569"
                  fontWeight={isHovered ? "bold" : "normal"}
                >
                  #{pt.session_index + 1}
                </text>
              </g>
            );
          })}
        </svg>

        {hoveredPoint && (
          <div className="pca-tooltip">
            <strong>Session #{hoveredPoint.session_index + 1}</strong> ({hoveredPoint.session_id})
            <div>Coordinates: ({hoveredPoint.pca_x.toFixed(2)}, {hoveredPoint.pca_y.toFixed(2)})</div>
            <div style={{ color: CLUSTER_COLORS[hoveredPoint.cluster_id % CLUSTER_COLORS.length] }}>
              {hoveredPoint.cluster_label}
            </div>
          </div>
        )}

        <div className="pca-variance-caption">
          {pca.explained_variance_ratio.length >= 2 && (
            <span>
              Explained Variance: PC1: {(pca.explained_variance_ratio[0] * 100).toFixed(1)}%, PC2:{" "}
              {(pca.explained_variance_ratio[1] * 100).toFixed(1)}%
            </span>
          )}
        </div>
      </div>
    );
  };

  // Render Longitudinal Trend Chart
  const renderTrendChart = (
    points: typeof trends.points,
    field: "words_per_minute" | "filler_words_ratio",
    title: string,
    unit: string,
    isPercentage = false
  ) => {
    if (points.length < 2) {
      return (
        <div className="trend-empty">
          <p className="text-muted">Complete at least 2 sessions to establish trend regressions.</p>
        </div>
      );
    }

    const width = 450;
    const height = 180;
    const padding = 35;

    const values = points.map((p) => p[field]);
    const minVal = Math.min(...values) * 0.9;
    const maxVal = Math.max(...values) * 1.1 || 1;

    const scaleX = (idx: number) =>
      padding + (idx / (points.length - 1)) * (width - 2 * padding);
    const scaleY = (val: number) =>
      height - padding - ((val - minVal) / (maxVal - minVal || 1)) * (height - 2 * padding);

    // Build polyline path
    const pathString = points
      .map((pt, i) => `${i === 0 ? "M" : "L"} ${scaleX(i)} ${scaleY(pt[field])}`)
      .join(" ");

    return (
      <div className="trend-chart-box">
        <div className="trend-chart-header">
          <span className="trend-chart-title">{title}</span>
        </div>
        <svg viewBox={`0 0 ${width} ${height}`} className="trend-svg">
          {/* Baseline */}
          <line
            x1={padding}
            y1={height - padding}
            x2={width - padding}
            y2={height - padding}
            stroke="#cbd5e1"
          />

          {/* Line series */}
          <path d={pathString} fill="none" stroke="#2563eb" strokeWidth="2.5" />

          {/* Points */}
          {points.map((pt, i) => (
            <circle
              key={i}
              cx={scaleX(i)}
              cy={scaleY(pt[field])}
              r="4.5"
              fill="#2563eb"
              stroke="#ffffff"
              strokeWidth="2"
            />
          ))}
        </svg>
        <div className="trend-chart-footer">
          <span>Session #1: {isPercentage ? (values[0] * 100).toFixed(1) : Math.round(values[0])} {unit}</span>
          <span>Session #{points.length}: {isPercentage ? (values[values.length - 1] * 100).toFixed(1) : Math.round(values[values.length - 1])} {unit}</span>
        </div>
      </div>
    );
  };

  return (
    <div className="analytics-container">
      {/* Overview Stat Cards */}
      <div className="analytics-stat-row">
        <div className="card stat-card">
          <span className="stat-label">Total Practice Sessions</span>
          <span className="stat-value">{total_sessions_analyzed}</span>
          <span className="stat-sub">Persisted in local database</span>
        </div>

        <div className="card stat-card">
          <span className="stat-label">Pacing Rate of Change</span>
          <span className="stat-value">
            {trends.wpm_slope >= 0 ? `+${trends.wpm_slope}` : trends.wpm_slope}
          </span>
          <span className="stat-sub">WPM / session slope</span>
        </div>

        <div className="card stat-card">
          <span className="stat-label">Filler Ratio Slope</span>
          <span className="stat-value">
            {(trends.filler_ratio_slope * 100).toFixed(2)}%
          </span>
          <span className="stat-sub">per session slope</span>
        </div>

        <div className="card stat-card">
          <span className="stat-label">Exploratory Clusters</span>
          <span className="stat-value">{clusters.length}</span>
          <span className="stat-sub">Delivery archetypes</span>
        </div>
      </div>

      {/* Main Grid: PCA + Trends */}
      <div className="analytics-main-grid">
        {/* PCA Delivery Space Card */}
        <div className="card pca-card">
          <div className="card-header">
            <div className="card-title-row">
              <Layers className="icon-primary" size={20} />
              <h2 className="card-title">2D PCA Delivery Projection Space</h2>
            </div>
            <button
              type="button"
              className="btn-secondary btn-sm"
              onClick={fetchAnalytics}
              title="Refresh Analytics"
            >
              <RefreshCw size={14} />
            </button>
          </div>
          <p className="card-description">
            Unsupervised principal component reduction capturing delivery mechanics (WPM, fillers, pauses, gaze, head stability).
          </p>
          {renderPcaScatterPlot()}
        </div>

        {/* Longitudinal Trends Card */}
        <div className="card trends-card">
          <div className="card-header">
            <div className="card-title-row">
              <TrendingUp className="icon-primary" size={20} />
              <h2 className="card-title">Longitudinal Delivery Progression</h2>
            </div>
          </div>
          <p className="card-description">
            Statistical regression slopes tracking delivery mechanics across successive practice sessions.
          </p>

          <div className="trend-summary-pills">
            <div className="trend-pill">
              <Gauge size={16} className="icon-primary" />
              <span>{trends.pace_direction_summary}</span>
            </div>
            <div className="trend-pill">
              <MessageSquare size={16} className="icon-primary" />
              <span>{trends.filler_direction_summary}</span>
            </div>
          </div>

          <div className="trend-charts-container">
            {renderTrendChart(trends.points, "words_per_minute", "Speaking Pace Progression (WPM)", "WPM")}
            {renderTrendChart(trends.points, "filler_words_ratio", "Filler Word Ratio Progression (%)", "%", true)}
          </div>
        </div>
      </div>

      {/* Exploratory Clusters Cards */}
      {clusters.length > 0 && (
        <div className="clusters-section">
          <h2 className="section-title">Exploratory Delivery Archetypes</h2>
          <div className="clusters-grid">
            {clusters.map((cluster) => {
              const color = CLUSTER_COLORS[cluster.cluster_id % CLUSTER_COLORS.length];
              return (
                <div
                  key={cluster.cluster_id}
                  className="card cluster-card"
                  style={{ borderTop: `4px solid ${color}` }}
                >
                  <div className="cluster-header">
                    <h3 className="cluster-name">{cluster.cluster_label}</h3>
                    <span className="badge-subtle">{cluster.session_count} session(s)</span>
                  </div>
                  <p className="cluster-desc">{cluster.description}</p>

                  <div className="cluster-features">
                    {cluster.centroid_features["words_per_minute"] && (
                      <div className="feature-row">
                        <span>Centroid Pace:</span>
                        <strong>{Math.round(cluster.centroid_features["words_per_minute"])} WPM</strong>
                      </div>
                    )}
                    {cluster.centroid_features["head_stability_score"] && (
                      <div className="feature-row">
                        <span>Centroid Stability:</span>
                        <strong>
                          {(cluster.centroid_features["head_stability_score"] * 100).toFixed(0)}%
                        </strong>
                      </div>
                    )}
                    {cluster.centroid_features["hand_gestures_per_minute"] && (
                      <div className="feature-row">
                        <span>Centroid Gestures:</span>
                        <strong>
                          {cluster.centroid_features["hand_gestures_per_minute"].toFixed(1)} / min
                        </strong>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Ethical Framework Note */}
      <div className="card ethical-card">
        <div className="ethical-header">
          <Shield size={20} className="text-emerald-600" />
          <h3 className="ethical-title">Ethical Framework Note</h3>
        </div>
        <p className="ethical-text">{ethical_note}</p>
      </div>
    </div>
  );
};
