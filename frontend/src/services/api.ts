/**
 * HTTP client communicating with Interview Practice Coach FastAPI backend.
 */

import {
  AnalyticsDashboardResponse,
  AudioAnalysisResponse,
  HealthResponse,
  SessionCreateRequest,
  SessionDeleteResponse,
  SessionDetailResponse,
  SessionListResponse,
  VisualAnalysisResponse,
  CoachingEvaluationRequest,
  CoachingEvaluationResponse,
  CategorySummary,
  CustomTrackRequest,
  InterviewQuestion,
  MockTrackDefinition,
  MockTrackListResponse,
  QuestionListResponse,
} from "../types";

const API_BASE = "";

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errorMessage = `HTTP ${res.status}: ${res.statusText}`;
    try {
      const errorJson = await res.json();
      if (errorJson.detail) {
        errorMessage = typeof errorJson.detail === "string" 
          ? errorJson.detail 
          : JSON.stringify(errorJson.detail);
      } else if (errorJson.error) {
        errorMessage = `${errorJson.error}: ${errorJson.detail || ""}`;
      }
    } catch {
      // Non-JSON error
    }
    throw new Error(errorMessage);
  }
  return res.json() as Promise<T>;
}

export const api = {
  /**
   * Health check probe
   */
  async checkHealth(): Promise<HealthResponse> {
    const res = await fetch(`${API_BASE}/health`);
    return handleResponse<HealthResponse>(res);
  },

  /**
   * Upload audio recording for transcription and acoustic mechanics analysis
   */
  async analyzeAudio(
    file: File | Blob,
    filename: string = "recording.wav",
    pauseThreshold: number = 0.5,
    language?: string
  ): Promise<AudioAnalysisResponse> {
    const formData = new FormData();
    formData.append("file", file, filename);
    formData.append("pause_threshold", pauseThreshold.toString());
    if (language) {
      formData.append("language", language);
    }

    const res = await fetch(`${API_BASE}/api/v1/audio/analyze`, {
      method: "POST",
      body: formData,
    });
    return handleResponse<AudioAnalysisResponse>(res);
  },

  /**
   * Analyze client-side extracted visual landmark frames
   */
  async analyzeVisual(
    frames: Array<unknown> = [],
    durationSeconds?: number
  ): Promise<VisualAnalysisResponse> {
    const res = await fetch(`${API_BASE}/api/v1/visual/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        recording_duration_seconds: durationSeconds,
        frames,
      }),
    });
    return handleResponse<VisualAnalysisResponse>(res);
  },

  /**
   * Persist practice session and metrics to backend SQLite database
   */
  async createSession(payload: SessionCreateRequest): Promise<SessionDetailResponse> {
    const res = await fetch(`${API_BASE}/api/v1/sessions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return handleResponse<SessionDetailResponse>(res);
  },

  /**
   * List historical sessions with pagination and ordering
   */
  async listSessions(
    limit: number = 50,
    offset: number = 0,
    order: "asc" | "desc" = "desc"
  ): Promise<SessionListResponse> {
    const params = new URLSearchParams({
      limit: limit.toString(),
      offset: offset.toString(),
      order,
    });
    const res = await fetch(`${API_BASE}/api/v1/sessions?${params}`);
    return handleResponse<SessionListResponse>(res);
  },

  /**
   * Retrieve full session details by ID
   */
  async getSession(sessionId: string): Promise<SessionDetailResponse> {
    const res = await fetch(`${API_BASE}/api/v1/sessions/${encodeURIComponent(sessionId)}`);
    return handleResponse<SessionDetailResponse>(res);
  },

  /**
   * Permanently delete a session and all its cascading records
   */
  async deleteSession(sessionId: string): Promise<SessionDeleteResponse> {
    const res = await fetch(`${API_BASE}/api/v1/sessions/${encodeURIComponent(sessionId)}`, {
      method: "DELETE",
    });
    return handleResponse<SessionDeleteResponse>(res);
  },

  /**
   * Compute aggregate 2D PCA, K-Means clustering, and longitudinal trends
   */
  async getAnalyticsSummary(): Promise<AnalyticsDashboardResponse> {
    const res = await fetch(`${API_BASE}/api/v1/sessions/analytics/summary`);
    return handleResponse<AnalyticsDashboardResponse>(res);
  },

  /**
   * Resolve WebSocket URL for real-time practice streaming
   */
  getWebSocketUrl(sessionId?: string): string {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    return `${protocol}//${host}/api/v1/ws/practice${sessionId ? `/${encodeURIComponent(sessionId)}` : ""}`;
  },

  /**
   * Request comprehensive STAR framework and delivery coaching evaluation
   */
  async getCoachingEvaluation(
    payload: CoachingEvaluationRequest
  ): Promise<CoachingEvaluationResponse> {
    const res = await fetch(`${API_BASE}/api/v1/coaching/evaluate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return handleResponse<CoachingEvaluationResponse>(res);
  },

  /**
   * Retrieve AI coaching advice directly for an existing saved session
   */
  async getSessionCoaching(sessionId: string): Promise<CoachingEvaluationResponse> {
    const res = await fetch(`${API_BASE}/api/v1/coaching/sessions/${encodeURIComponent(sessionId)}`);
    return handleResponse<CoachingEvaluationResponse>(res);
  },

  /**
   * List curated interview questions with optional filtering
   */
  async listQuestions(
    category?: string,
    difficulty?: string,
    search?: string
  ): Promise<QuestionListResponse> {
    const params = new URLSearchParams();
    if (category) params.append("category", category);
    if (difficulty) params.append("difficulty", difficulty);
    if (search) params.append("search", search);
    const qs = params.toString();
    const res = await fetch(`${API_BASE}/api/v1/questions${qs ? `?${qs}` : ""}`);
    return handleResponse<QuestionListResponse>(res);
  },

  /**
   * List available question categories and counts
   */
  async listCategories(): Promise<CategorySummary[]> {
    const res = await fetch(`${API_BASE}/api/v1/questions/categories`);
    return handleResponse<CategorySummary[]>(res);
  },

  /**
   * Get single question by ID
   */
  async getQuestion(questionId: string): Promise<InterviewQuestion> {
    const res = await fetch(`${API_BASE}/api/v1/questions/${encodeURIComponent(questionId)}`);
    return handleResponse<InterviewQuestion>(res);
  },

  /**
   * List pre-configured multi-question mock interview tracks
   */
  async listMockTracks(): Promise<MockTrackListResponse> {
    const res = await fetch(`${API_BASE}/api/v1/questions/tracks/available`);
    return handleResponse<MockTrackListResponse>(res);
  },

  /**
   * Retrieve a specific mock interview track by ID
   */
  async getMockTrack(trackId: string): Promise<MockTrackDefinition> {
    const res = await fetch(`${API_BASE}/api/v1/questions/tracks/${encodeURIComponent(trackId)}`);
    return handleResponse<MockTrackDefinition>(res);
  },

  /**
   * Create a dynamic custom mock interview track
   */
  async createCustomMockTrack(payload: CustomTrackRequest): Promise<MockTrackDefinition> {
    const res = await fetch(`${API_BASE}/api/v1/questions/tracks/custom`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return handleResponse<MockTrackDefinition>(res);
  },
};


