/**
 * TypeScript data models matching Interview Practice Coach backend schemas.
 */

export interface WordTimestamp {
  word: string;
  start: number;
  end: number;
  probability: number;
}

export interface AudioSegment {
  id: number;
  start: number;
  end: number;
  text: string;
  words: WordTimestamp[];
}

export interface PauseDetail {
  start: number;
  end: number;
  duration: number;
  preceding_word?: string | null;
  following_word?: string | null;
}

export interface AudioMetrics {
  total_duration_seconds: number;
  speaking_duration_seconds: number;
  total_words: number;
  words_per_minute: number;
  articulation_rate_wpm: number;
  filler_words_count: number;
  filler_words_ratio: number;
  filler_words_breakdown: Record<string, number>;
  pause_count: number;
  total_pause_duration_seconds: number;
  average_pause_duration_seconds: number;
  longest_pause_duration_seconds: number;
  pause_threshold_seconds: number;
  pauses: PauseDetail[];
}

export interface AudioAnalysisResponse {
  filename: string;
  transcript: string;
  language: string;
  language_probability: number;
  metrics: AudioMetrics;
  segments: AudioSegment[];
  words: WordTimestamp[];
}

export interface VisualMetrics {
  total_duration_seconds: number;
  frames_analyzed: number;
  face_detected_ratio: number;
  centered_gaze_ratio: number;
  gaze_distribution: Record<string, number>;
  head_stability_score: number;
  head_movement_variance: number;
  hands_visible_ratio: number;
  hand_gestures_per_minute: number;
  tracking_notes: string[];
  ethical_disclaimer: string;
}

export interface VisualAnalysisResponse {
  status: string;
  metrics: VisualMetrics;
  recommendations: string[];
}

export interface SessionFeatureVector {
  session_id: string;
  session_index: number;
  timestamp_iso?: string | null;
  has_audio: boolean;
  has_visual: boolean;
  words_per_minute: number;
  articulation_rate_wpm: number;
  filler_words_ratio: number;
  average_pause_duration_seconds: number;
  pause_frequency_per_minute: number;
  centered_gaze_ratio: number;
  head_stability_score: number;
  hand_gestures_per_minute: number;
}

export interface PCAProjectionPoint {
  session_id: string;
  session_index: number;
  pca_x: number;
  pca_y: number;
  cluster_id: number;
  cluster_label: string;
}

export interface PCAResult {
  is_fallback: boolean;
  status_message: string;
  explained_variance_ratio: number[];
  feature_loadings: Record<string, Record<string, number>>;
  points: PCAProjectionPoint[];
}

export interface ClusterSummary {
  cluster_id: number;
  cluster_label: string;
  session_count: number;
  centroid_features: Record<string, number>;
  description: string;
}

export interface TrendPoint {
  session_index: number;
  session_id: string;
  timestamp_iso?: string | null;
  words_per_minute: number;
  filler_words_ratio: number;
  average_pause_duration_seconds: number;
  centered_gaze_ratio: number;
  head_stability_score: number;
  hand_gestures_per_minute: number;
}

export interface TrendAnalysis {
  points: TrendPoint[];
  wpm_slope: number;
  filler_ratio_slope: number;
  pace_direction_summary: string;
  filler_direction_summary: string;
}

export interface AnalyticsDashboardResponse {
  total_sessions_analyzed: number;
  pca: PCAResult;
  clusters: ClusterSummary[];
  trends: TrendAnalysis;
  ethical_note: string;
}

export interface SessionSummary {
  session_id: string;
  title?: string | null;
  notes?: string | null;
  created_at: string;
  duration_seconds: number;
  language: string;
  has_audio: boolean;
  has_visual: boolean;
  words_per_minute?: number | null;
  filler_words_count?: number | null;
  filler_words_ratio?: number | null;
  centered_gaze_ratio?: number | null;
  head_stability_score?: number | null;
  hand_gestures_per_minute?: number | null;
  transcript_snippet?: string | null;
}

export interface SessionListResponse {
  total: number;
  limit: number;
  offset: number;
  sessions: SessionSummary[];
}

export interface SessionDetailResponse {
  session_id: string;
  title?: string | null;
  notes?: string | null;
  created_at: string;
  duration_seconds: number;
  language: string;
  has_audio: boolean;
  has_visual: boolean;
  transcript?: string | null;
  audio_metrics?: AudioMetrics | null;
  audio_segments: AudioSegment[];
  audio_words: WordTimestamp[];
  visual_metrics?: VisualMetrics | null;
  feature_vector?: SessionFeatureVector | null;
}

export interface SessionCreateRequest {
  session_id?: string;
  title?: string;
  notes?: string;
  language?: string;
  duration_seconds?: number;
  created_at?: string;
  transcript?: string;
  audio_metrics?: AudioMetrics;
  audio_segments?: AudioSegment[];
  audio_words?: WordTimestamp[];
  visual_metrics?: VisualMetrics;
  audio_analysis?: AudioAnalysisResponse;
  visual_analysis?: VisualAnalysisResponse;
}

export interface SessionDeleteResponse {
  session_id: string;
  deleted: boolean;
  message: string;
}

export interface HealthResponse {
  status: string;
  version: string;
  service: string;
}

export interface DeliveryAlert {
  timestamp_seconds: number;
  alert_type: string;
  message: string;
  severity: "info" | "warning" | "caution";
}

export interface LiveMetricsUpdate {
  elapsed_seconds: number;
  current_wpm_estimate?: number | null;
  recent_filler_count: number;
  current_pause_seconds: number;
  centered_gaze_ratio?: number | null;
  head_stability_score?: number | null;
  face_detected: boolean;
}

export interface StreamFinalReport {
  session_id: string;
  total_duration_seconds: number;
  audio_metrics?: AudioMetrics | null;
  visual_metrics?: VisualMetrics | null;
  transcript?: string | null;
  alerts_triggered_count: number;
  saved_to_db: boolean;
}
