import React, { useState, useEffect } from "react";
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
  Sparkles,
  RefreshCw,
  Award,
  CheckCircle2,
  AlertCircle,
  Lightbulb,
  ThumbsUp,
  BookOpen,
} from "lucide-react";
import { SessionDetailResponse, CoachingEvaluationResponse } from "../types";
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
  const [coaching, setCoaching] = useState<CoachingEvaluationResponse | null>(null);
  const [isLoadingCoaching, setIsLoadingCoaching] = useState(false);
  const [coachingError, setCoachingError] = useState<string | null>(null);

  const audio = session.audio_metrics;
  const visual = session.visual_metrics;

  const fetchCoaching = async () => {
    setIsLoadingCoaching(true);
    setCoachingError(null);
    try {
      const res = await api.getSessionCoaching(session.session_id);
      setCoaching(res);
    } catch (err: unknown) {
      setCoachingError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsLoadingCoaching(false);
    }
  };

  useEffect(() => {
    fetchCoaching();
  }, [session.session_id]);

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

        {!audio && !visual && (
          <div className="card empty-state-card text-center" style={{ gridColumn: "1 / -1", padding: "2rem" }}>
            <AlertCircle size={36} className="text-warning empty-icon" />
            <h3>No Delivery Metrics Detected</h3>
            <p className="text-muted">
              Audio and visual delivery metrics were not captured during this recording or speech was below detection thresholds.
            </p>
          </div>
        )}
      </div>

      {/* AI Coaching & STAR Evaluation Section */}
      <div className="card coaching-card">
        <div className="coaching-header-top">
          <div className="coaching-header-title">
            <Sparkles className="icon-primary" size={24} />
            <div>
              <h2>AI Practice Coach &amp; STAR Evaluation</h2>
              <p>Automated behavioral response structuring and objective delivery feedback</p>
            </div>
          </div>
          <button
            type="button"
            className="btn-secondary btn-sm"
            onClick={fetchCoaching}
            disabled={isLoadingCoaching}
          >
            <RefreshCw size={14} className={isLoadingCoaching ? "animate-spin" : ""} />
            <span>{isLoadingCoaching ? "Evaluating..." : "Refresh Advice"}</span>
          </button>
        </div>

        {isLoadingCoaching && !coaching && (
          <div className="text-center py-6">
            <div
              className="progress-bar-indeterminate"
              style={{ height: "4px", width: "100%", marginBottom: "12px" }}
            />
            <p className="text-muted text-sm">Synthesizing STAR methodology &amp; delivery recommendations...</p>
          </div>
        )}

        {coachingError && (
          <div className="alert alert-warning mb-4">
            <AlertCircle size={16} />
            <span>Coaching evaluation note: {coachingError}</span>
          </div>
        )}

        {coaching && (
          <div>
            {/* Top Score Badges */}
            <div className="coaching-score-pills">
              <div className="coaching-score-pill">
                <Award size={18} className="text-blue-600" />
                <div>
                  <div className="coaching-pill-label">STAR Alignment</div>
                  <div className="coaching-pill-value">
                    {coaching.star_analysis.overall_star_score.toFixed(0)} / 100
                  </div>
                </div>
              </div>

              <div className="coaching-score-pill">
                <Gauge size={18} className="text-emerald-600" />
                <div>
                  <div className="coaching-pill-label">Content Clarity</div>
                  <div className="coaching-pill-value">
                    {coaching.clarity.score} / 100 ({coaching.clarity.conciseness_rating})
                  </div>
                </div>
              </div>

              <div className="coaching-score-pill">
                <MessageSquare size={18} className="text-amber-600" />
                <div>
                  <div className="coaching-pill-label">Spoken Volume</div>
                  <div className="coaching-pill-value">
                    {coaching.clarity.word_count} words ({coaching.clarity.filler_density_percent.toFixed(1)}% fillers)
                  </div>
                </div>
              </div>
            </div>

            {/* STAR Framework Analysis Grid */}
            <div className="star-section">
              <div className="star-section-title">
                <BookOpen size={18} className="icon-primary" />
                <span>Behavioral Framework: STAR Breakdown</span>
              </div>
              <div className="star-grid">
                {/* Situation */}
                <div className="star-step-card">
                  <div className="star-step-header">
                    <div className="star-letter-badge star-badge-s">S</div>
                    <span className="star-step-label">Situation</span>
                    {coaching.star_analysis.situation_detected ? (
                      <span className="metric-badge badge-green">
                        <Check size={12} style={{ display: "inline", marginRight: "4px" }} /> Detected
                      </span>
                    ) : (
                      <span className="metric-badge badge-amber">Missing</span>
                    )}
                  </div>
                  {coaching.star_analysis.situation_snippet ? (
                    <div className="star-snippet-box">"{coaching.star_analysis.situation_snippet}"</div>
                  ) : (
                    <div className="star-missing-tip">Set the context, team environment, or initial problem clearly.</div>
                  )}
                </div>

                {/* Task */}
                <div className="star-step-card">
                  <div className="star-step-header">
                    <div className="star-letter-badge star-badge-t">T</div>
                    <span className="star-step-label">Task</span>
                    {coaching.star_analysis.task_detected ? (
                      <span className="metric-badge badge-green">
                        <Check size={12} style={{ display: "inline", marginRight: "4px" }} /> Detected
                      </span>
                    ) : (
                      <span className="metric-badge badge-amber">Missing</span>
                    )}
                  </div>
                  {coaching.star_analysis.task_snippet ? (
                    <div className="star-snippet-box">"{coaching.star_analysis.task_snippet}"</div>
                  ) : (
                    <div className="star-missing-tip">Define your specific responsibility or the primary hurdle.</div>
                  )}
                </div>

                {/* Action */}
                <div className="star-step-card">
                  <div className="star-step-header">
                    <div className="star-letter-badge star-badge-a">A</div>
                    <span className="star-step-label">Action</span>
                    {coaching.star_analysis.action_detected ? (
                      <span className="metric-badge badge-green">
                        <Check size={12} style={{ display: "inline", marginRight: "4px" }} /> Detected
                      </span>
                    ) : (
                      <span className="metric-badge badge-amber">Missing</span>
                    )}
                  </div>
                  {coaching.star_analysis.action_snippet ? (
                    <div className="star-snippet-box">"{coaching.star_analysis.action_snippet}"</div>
                  ) : (
                    <div className="star-missing-tip">Detail the concrete steps, engineering choices, and initiatives you executed.</div>
                  )}
                </div>

                {/* Result */}
                <div className="star-step-card">
                  <div className="star-step-header">
                    <div className="star-letter-badge star-badge-r">R</div>
                    <span className="star-step-label">Result</span>
                    {coaching.star_analysis.result_detected ? (
                      <span className="metric-badge badge-green">
                        <Check size={12} style={{ display: "inline", marginRight: "4px" }} /> Detected
                      </span>
                    ) : (
                      <span className="metric-badge badge-amber">Missing</span>
                    )}
                  </div>
                  {coaching.star_analysis.result_snippet ? (
                    <div className="star-snippet-box">"{coaching.star_analysis.result_snippet}"</div>
                  ) : (
                    <div className="star-missing-tip">Provide measurable business metrics, latency drops, or stakeholder outcomes.</div>
                  )}
                </div>
              </div>

              {/* STAR Qualitative Summary */}
              <div className="star-summary-banner">
                <Info size={16} className="icon-primary" style={{ flexShrink: 0, marginTop: "2px" }} />
                <span>{coaching.star_analysis.star_summary}</span>
              </div>
            </div>

            {/* Polished Executive Excerpt */}
            {coaching.sample_polished_excerpt && (
              <div className="polished-excerpt-box">
                <div className="polished-header">
                  <Sparkles size={16} />
                  <span>Executive Rephrase Demonstration</span>
                </div>
                <div className="polished-quote">"{coaching.sample_polished_excerpt}"</div>
              </div>
            )}

            {/* Delivery Coaching Grid */}
            <div className="delivery-advice-section">
              <div className="star-section-title">
                <Gauge size={18} className="icon-primary" />
                <span>Personalized Delivery Advice</span>
              </div>
              <div className="delivery-advice-grid">
                <div className="advice-card">
                  <div className="advice-card-title">
                    <Clock size={14} /> Pacing &amp; Cadence
                  </div>
                  <div className="advice-card-body">{coaching.delivery_advice.pacing_feedback}</div>
                </div>

                <div className="advice-card">
                  <div className="advice-card-title">
                    <Activity size={14} /> Pausing Rhythm
                  </div>
                  <div className="advice-card-body">{coaching.delivery_advice.pause_feedback}</div>
                </div>

                <div className="advice-card">
                  <div className="advice-card-title">
                    <MessageSquare size={14} /> Filler Word Control
                  </div>
                  <div className="advice-card-body">{coaching.delivery_advice.filler_feedback}</div>
                </div>

                <div className="advice-card">
                  <div className="advice-card-title">
                    <Eye size={14} /> Visual &amp; Eye Contact
                  </div>
                  <div className="advice-card-body">{coaching.delivery_advice.visual_feedback}</div>
                </div>
              </div>
            </div>

            {/* Strengths & Growth Areas */}
            <div className="strengths-growth-grid">
              <div className="strengths-card">
                <div className="list-card-title strengths-title">
                  <ThumbsUp size={16} /> Top Performance Strengths
                </div>
                <ul className="coaching-bullet-list">
                  {coaching.top_strengths.map((str, idx) => (
                    <li key={idx} className="coaching-bullet-item">
                      <CheckCircle2 size={16} className="bullet-icon-strength" />
                      <span>{str}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="growth-card">
                <div className="list-card-title growth-title">
                  <Lightbulb size={16} /> Key Areas for Improvement
                </div>
                <ul className="coaching-bullet-list">
                  {coaching.areas_for_improvement.map((area, idx) => (
                    <li key={idx} className="coaching-bullet-item">
                      <AlertCircle size={16} className="bullet-icon-growth" />
                      <span>{area}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            {/* Coaching Disclaimer */}
            <div className="coaching-disclaimer-box">
              <Shield size={14} />
              <span>{coaching.ethical_disclaimer}</span>
            </div>
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
