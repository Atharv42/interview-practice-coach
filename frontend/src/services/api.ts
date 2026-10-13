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
};
