import React, { useState } from "react";
import {
  Clock,
  Gauge,
  MessageSquare,
  Eye,
  Shield,
  Trash2,
  Copy,
  Check,
  ArrowLeft,
  Activity,
  Smile,
  Move,
  Info,
} from "lucide-react";
import { SessionDetailResponse } from "../types";
import { api } from "../services/api";

interface SessionDetailViewProps {
  session: SessionDetailResponse;
  onBack: () => void;
  onSessionDeleted: (sessionId: string) => void;
}

export const SessionDetailView: React.FC<SessionDetailViewProps> = ({
  session,
  onBack,
  onSessionDeleted,
}) => {
  const [copiedTranscript, setCopiedTranscript] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  const audio = session.audio_metrics;
  const visual = session.visual_metrics;

  const handleCopyTranscript = () => {
    if (session.transcript) {
      navigator.clipboard.writeText(session.transcript);
      setCopiedTranscript(true);
      setTimeout(() => setCopiedTranscript(false), 2000);
    }
  };

  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      await api.deleteSession(session.session_id);
      onSessionDeleted(session.session_id);
    } catch (err: unknown) {
      alert(`Failed to delete session: ${err instanceof Error ? err.message : String(err)}`);
      setIsDeleting(false);
      setShowDeleteConfirm(false);
    }
  };

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.round(seconds % 60);
    if (mins === 0) return `${secs}s`;
    return `${mins}m ${secs}s`;
  };

  // Evaluate pace health
  const getPaceStatus = (wpm: number) => {
    if (wpm >= 125 && wpm <= 160) {
      return { label: "Optimal Conversational Pace", color: "badge-green" };
    }
    if (wpm > 160) {
      return { label: "Fast-Paced Delivery", color: "badge-amber" };
    }
    return { label: "Deliberate / Slow Pace", color: "badge-blue" };
  };

  return (
    <div className="session-detail-container">
      {/* Top Navigation */}
      <div className="detail-top-nav">
        <button type="button" className="btn-secondary" onClick={onBack}>
          <ArrowLeft size={16} />
          <span>Back to Studio</span>
        </button>

        <button
          type="button"
          className="btn-outline-danger"
          onClick={() => setShowDeleteConfirm(true)}
          title="Permanently delete this session and all metrics"
        >
          <Trash2 size={16} />
          <span>Delete Session</span>
        </button>
      </div>

      {/* Header Banner */}
      <div className="card detail-header-card">
        <div className="detail-title-group">
          <span className="badge-primary">Session Report</span>
          <h1 className="detail-title">{session.title || "Practice Session"}</h1>
          {session.notes && <p className="detail-notes">{session.notes}</p>}
        </div>

        <div className="detail-meta-grid">
          <div className="meta-item">
            <Clock size={16} className="text-muted" />
            <span>Duration: <strong>{formatDuration(session.duration_seconds)}</strong></span>
          </div>
          <div className="meta-item">
            <Info size={16} className="text-muted" />
            <span>Created: <strong>{new Date(session.created_at).toLocaleString()}</strong></span>
          </div>
          <div className="meta-item">
            <MessageSquare size={16} className="text-muted" />
            <span>Words: <strong>{audio?.total_words || 0}</strong></span>
          </div>
        </div>
      </div>

      {/* Metrics Grid */}
      <div className="metrics-grid">
        {/* Metric 1: Speaking Pace */}
        {audio && (
          <div className="card metric-card">
            <div className="metric-header">
              <span className="metric-title">Speaking Pace (WPM)</span>
              <Gauge size={20} className="icon-primary" />
            </div>
            <div className="metric-value-row">
              <span className="metric-primary-value">{Math.round(audio.words_per_minute)}</span>
              <span className="metric-unit">words / min</span>
            </div>
            <div className={`metric-badge ${getPaceStatus(audio.words_per_minute).color}`}>
              {getPaceStatus(audio.words_per_minute).label}
            </div>
            <p className="metric-description">
              Articulation rate (excluding pauses): <strong>{Math.round(audio.articulation_rate_wpm)} WPM</strong>.
              Typical interview target: 130–160 WPM.
            </p>
          </div>
        )}

        {/* Metric 2: Filler Words */}
        {audio && (
          <div className="card metric-card">
            <div className="metric-header">
              <span className="metric-title">Filler Words</span>
              <MessageSquare size={20} className="icon-primary" />
            </div>
            <div className="metric-value-row">
              <span className="metric-primary-value">{audio.filler_words_count}</span>
              <span className="metric-unit">detected ({(audio.filler_words_ratio * 100).toFixed(1)}%)</span>
            </div>
            <div
              className={`metric-badge ${
                audio.filler_words_ratio <= 0.03
                  ? "badge-green"
                  : audio.filler_words_ratio <= 0.06
                  ? "badge-amber"
                  : "badge-red"
              }`}
            >
              {audio.filler_words_ratio <= 0.03
                ? "Low Filler Usage"
                : audio.filler_words_ratio <= 0.06
                ? "Moderate Filler Usage"
                : "Elevated Filler Usage"}
            </div>

            {Object.keys(audio.filler_words_breakdown).length > 0 ? (
              <div className="filler-breakdown-chips">
                {Object.entries(audio.filler_words_breakdown).map(([word, count]) => (
                  <span key={word} className="filler-chip">
                    "{word}": <strong>{count}</strong>
                  </span>
                ))}
              </div>
            ) : (
              <p className="metric-description">No standard filler words identified.</p>
            )}
          </div>
        )}

        {/* Metric 3: Pause Mechanics */}
        {audio && (
          <div className="card metric-card">
            <div className="metric-header">
              <span className="metric-title">Pause Distribution</span>
              <Clock size={20} className="icon-primary" />
            </div>
            <div className="metric-value-row">
              <span className="metric-primary-value">{audio.pause_count}</span>
              <span className="metric-unit">pauses</span>
            </div>
            <div className="metric-badge badge-blue">
              Avg Pause: {audio.average_pause_duration_seconds.toFixed(2)}s
            </div>
            <p className="metric-description">
              Total pause time: <strong>{audio.total_pause_duration_seconds.toFixed(1)}s</strong>.
              Longest pause: <strong>{audio.longest_pause_duration_seconds.toFixed(1)}s</strong>.
            </p>
          </div>
        )}

        {/* Metric 4: Centered Gaze */}
        {visual && (
          <div className="card metric-card">
            <div className="metric-header">
              <span className="metric-title">Centered Camera Gaze</span>
              <Eye size={20} className="icon-primary" />
            </div>
            <div className="metric-value-row">
              <span className="metric-primary-value">{Math.round(visual.centered_gaze_ratio * 100)}%</span>
              <span className="metric-unit">of session</span>
            </div>
            <div
              className={`metric-badge ${
                visual.centered_gaze_ratio >= 0.70 ? "badge-green" : "badge-amber"
              }`}
            >
              {visual.centered_gaze_ratio >= 0.70 ? "Good Camera Contact" : "Intermittent Gaze Focus"}
            </div>
            <p className="metric-description">
              Face detected in <strong>{Math.round(visual.face_detected_ratio * 100)}%</strong> of frames.
              Approximate geometric line-of-sight estimate.
            </p>
          </div>
        )}

        {/* Metric 5: Head Stability */}
        {visual && (
          <div className="card metric-card">
            <div className="metric-header">
              <span className="metric-title">Head Posture Stability</span>
              <Smile size={20} className="icon-primary" />
            </div>
            <div className="metric-value-row">
              <span className="metric-primary-value">{(visual.head_stability_score * 100).toFixed(0)}</span>
              <span className="metric-unit">/ 100 stability</span>
            </div>
            <div
              className={`metric-badge ${
                visual.head_stability_score >= 0.80 ? "badge-green" : "badge-blue"
              }`}
            >
              {visual.head_stability_score >= 0.80 ? "Composed & Steady" : "Dynamic Posture"}
            </div>
            <p className="metric-description">
              Centroid variance: <strong>{visual.head_movement_variance.toFixed(4)}</strong>.
              Measures camera-framing steadiness.
            </p>
          </div>
        )}

        {/* Metric 6: Hand Gestures */}
        {visual && (
          <div className="card metric-card">
            <div className="metric-header">
              <span className="metric-title">Hand Gesture Activity</span>
              <Move size={20} className="icon-primary" />
            </div>
            <div className="metric-value-row">
              <span className="metric-primary-value">{visual.hand_gestures_per_minute.toFixed(1)}</span>
              <span className="metric-unit">gestures / min</span>
            </div>
            <div className="metric-badge badge-blue">
              Hands in frame: {Math.round(visual.hands_visible_ratio * 100)}%
            </div>
            <p className="metric-description">
              Detects purposeful hand movement and framing visibility for desktop interviews.
            </p>
          </div>
        )}
      </div>

      {/* Transcript Section */}
      <div className="card transcript-card">
        <div className="transcript-header">
          <div className="card-title-row">
            <Activity className="icon-primary" size={20} />
            <h2 className="card-title">Spoken Transcript</h2>
          </div>
          <button
            type="button"
            className="btn-secondary btn-sm"
            onClick={handleCopyTranscript}
            disabled={!session.transcript}
          >
            {copiedTranscript ? <Check size={14} className="text-emerald-500" /> : <Copy size={14} />}
            <span>{copiedTranscript ? "Copied!" : "Copy Transcript"}</span>
          </button>
        </div>

        {session.transcript ? (
          <div className="transcript-body">
            <p className="transcript-text">{session.transcript}</p>
          </div>
        ) : (
          <p className="text-muted">No transcript available for this session.</p>
        )}
      </div>

      {/* Ethical Disclaimer Card */}
      <div className="card ethical-card">
        <div className="ethical-header">
          <Shield size={20} className="text-emerald-600" />
          <h3 className="ethical-title">Ethical Boundaries & Privacy Safeguards</h3>
        </div>
        <p className="ethical-text">
          {visual?.ethical_disclaimer ||
            "This system calculates objective geometric and acoustic mechanics (WPM, pause intervals, filler frequency, camera centering). It strictly refrains from inferring emotions, personality traits, confidence scores, honesty, or candidate qualification."}
        </p>
      </div>

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && (
        <div className="modal-overlay">
          <div className="modal-content">
            <h3 className="modal-title">Delete Practice Session?</h3>
            <p className="modal-status">
              This will permanently delete session <strong>{session.session_id}</strong>, including
              the transcript, acoustic metrics, and visual data from your local storage.
            </p>
            <div className="modal-actions">
              <button
                type="button"
                className="btn-secondary"
                onClick={() => setShowDeleteConfirm(false)}
                disabled={isDeleting}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn-danger"
                onClick={handleDelete}
                disabled={isDeleting}
              >
                {isDeleting ? "Deleting..." : "Permanently Delete"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
