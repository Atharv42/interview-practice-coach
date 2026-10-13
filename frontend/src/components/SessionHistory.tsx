import React, { useEffect, useState, useCallback } from "react";
import {
  History,
  Clock,
  Gauge,
  MessageSquare,
  Eye,
  Trash2,
  ExternalLink,
  Search,
  RefreshCw,
  AlertCircle,
  Loader2,
} from "lucide-react";
import { SessionSummary } from "../types";
import { api } from "../services/api";

interface SessionHistoryProps {
  onSelectSession: (sessionId: string) => void;
  onNavigateToStudio: () => void;
}

export const SessionHistory: React.FC<SessionHistoryProps> = ({
  onSelectSession,
  onNavigateToStudio,
}) => {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [order, setOrder] = useState<"desc" | "asc">("desc");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const fetchSessions = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const data = await api.listSessions(100, 0, order);
      setSessions(data.sessions);
      setTotalCount(data.total);
    } catch (err: unknown) {
      setErrorMessage(
        `Failed to load session history: ${err instanceof Error ? err.message : String(err)}`
      );
    } finally {
      setIsLoading(false);
    }
  }, [order]);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  const handleDelete = async (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!window.confirm(`Permanently delete practice session '${sessionId}'?`)) {
      return;
    }

    setDeletingId(sessionId);
    try {
      await api.deleteSession(sessionId);
      setSessions((prev) => prev.filter((s) => s.session_id !== sessionId));
      setTotalCount((prev) => Math.max(0, prev - 1));
    } catch (err: unknown) {
      alert(`Delete failed: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setDeletingId(null);
    }
  };

  const filteredSessions = sessions.filter((s) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      (s.title && s.title.toLowerCase().includes(q)) ||
      (s.transcript_snippet && s.transcript_snippet.toLowerCase().includes(q)) ||
      s.session_id.toLowerCase().includes(q)
    );
  });

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.round(seconds % 60);
    if (mins === 0) return `${secs}s`;
    return `${mins}m ${secs}s`;
  };

  return (
    <div className="history-container">
      {/* Top Controls Bar */}
      <div className="card history-controls-card">
        <div className="controls-row">
          <div className="search-box">
            <Search size={18} className="search-icon" />
            <input
              type="text"
              className="search-input"
              placeholder="Search by prompt, transcript snippet, or ID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>

          <div className="controls-actions">
            <select
              className="form-select select-compact"
              value={order}
              onChange={(e) => setOrder(e.target.value as "desc" | "asc")}
            >
              <option value="desc">Newest First</option>
              <option value="asc">Oldest First</option>
            </select>

            <button
              type="button"
              className="btn-secondary btn-icon-only"
              onClick={fetchSessions}
              title="Refresh sessions"
              disabled={isLoading}
            >
              <RefreshCw size={16} className={isLoading ? "spinner" : ""} />
            </button>
          </div>
        </div>

        <div className="history-stat-bar">
          <span>Total Saved Sessions: <strong>{totalCount}</strong></span>
          {searchQuery && (
            <span>Showing: <strong>{filteredSessions.length}</strong> matches</span>
          )}
        </div>
      </div>

      {errorMessage && (
        <div className="alert-error">
          <AlertCircle size={20} />
          <div>{errorMessage}</div>
        </div>
      )}

      {/* Loading State */}
      {isLoading ? (
        <div className="loading-state">
          <Loader2 size={36} className="spinner icon-primary" />
          <p>Loading historical sessions...</p>
        </div>
      ) : filteredSessions.length === 0 ? (
        /* Empty State */
        <div className="card empty-state-card text-center">
          <History size={48} className="text-muted empty-icon" />
          <h3>No Practice Sessions Found</h3>
          <p className="text-muted">
            {searchQuery
              ? "No sessions match your search query."
              : "You haven't recorded any practice sessions yet. Start practicing to unlock pacing and delivery insights!"}
          </p>
          <button type="button" className="btn-primary" onClick={onNavigateToStudio}>
            Start Practice Session
          </button>
        </div>
      ) : (
        /* Sessions List */
        <div className="sessions-list">
          {filteredSessions.map((session) => (
            <div
              key={session.session_id}
              className="card session-card"
              onClick={() => onSelectSession(session.session_id)}
            >
              <div className="session-card-header">
                <div>
                  <h3 className="session-card-title">{session.title || "Practice Session"}</h3>
                  <div className="session-card-meta">
                    <span className="meta-tag">
                      <Clock size={13} /> {formatDuration(session.duration_seconds)}
                    </span>
                    <span className="meta-tag">
                      {new Date(session.created_at).toLocaleDateString()} at{" "}
                      {new Date(session.created_at).toLocaleTimeString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </span>
                    <span className="meta-tag badge-subtle">{session.session_id}</span>
                  </div>
                </div>

                <div className="session-card-actions">
                  <button
                    type="button"
                    className="btn-icon-subtle text-danger"
                    title="Delete session"
                    onClick={(e) => handleDelete(session.session_id, e)}
                    disabled={deletingId === session.session_id}
                  >
                    {deletingId === session.session_id ? (
                      <Loader2 size={16} className="spinner" />
                    ) : (
                      <Trash2 size={16} />
                    )}
                  </button>
                </div>
              </div>

              {/* Metrics Highlights Pills */}
              <div className="session-pills-row">
                {session.words_per_minute !== null && session.words_per_minute !== undefined && (
                  <span className="metric-pill">
                    <Gauge size={14} className="icon-primary" />
                    <span><strong>{Math.round(session.words_per_minute)}</strong> WPM</span>
                  </span>
                )}

                {session.filler_words_count !== null && session.filler_words_count !== undefined && (
                  <span className="metric-pill">
                    <MessageSquare size={14} className="icon-primary" />
                    <span><strong>{session.filler_words_count}</strong> fillers</span>
                  </span>
                )}

                {session.centered_gaze_ratio !== null && session.centered_gaze_ratio !== undefined && (
                  <span className="metric-pill">
                    <Eye size={14} className="icon-primary" />
                    <span><strong>{Math.round(session.centered_gaze_ratio * 100)}%</strong> gaze</span>
                  </span>
                )}
              </div>

              {/* Transcript Snippet */}
              {session.transcript_snippet && (
                <p className="session-snippet">
                  "{session.transcript_snippet}"
                </p>
              )}

              <div className="session-card-footer">
                <span className="view-report-link">
                  <span>View Delivery Report</span>
                  <ExternalLink size={14} />
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
