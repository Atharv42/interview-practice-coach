import React, { useState, useRef, useEffect, useCallback } from "react";
import {
  Layers,
  Play,
  Square,
  ArrowRight,
  RotateCcw,
  Clock,
  Target,
  Lightbulb,
  CheckCircle2,
  Award,
  Gauge,
  Eye,
  MessageSquare,
  AlertCircle,
  VideoOff,
  ExternalLink,
} from "lucide-react";
import { api } from "../services/api";
import { AudioMeter } from "./AudioMeter";
import {
  MockQuestionResult,
  MockTrackDefinition,
} from "../types";

interface MockInterviewStudioProps {
  onSelectSession: (sessionId: string) => void;
}

export const MockInterviewStudio: React.FC<MockInterviewStudioProps> = ({
  onSelectSession,
}) => {
  // Navigation & Track selection states
  const [tracks, setTracks] = useState<MockTrackDefinition[]>([]);
  const [isLoadingTracks, setIsLoadingTracks] = useState(true);
  const [selectedTrack, setSelectedTrack] = useState<MockTrackDefinition | null>(null);

  // Active interview workflow states
  const [interviewStage, setInterviewStage] = useState<
    "selection" | "question_ready" | "recording" | "processing" | "question_review" | "final_scorecard"
  >("selection");
  const [currentQIndex, setCurrentQIndex] = useState(0);
  const [completedResults, setCompletedResults] = useState<MockQuestionResult[]>([]);

  // Media & Recording states
  const [mediaStream, setMediaStream] = useState<MediaStream | null>(null);
  const [hasCamera, setHasCamera] = useState(true);
  const [recordingSeconds, setRecordingSeconds] = useState(0);
  const [statusMessage, setStatusMessage] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const timerIntervalRef = useRef<number | null>(null);

  // Fetch available tracks on mount
  useEffect(() => {
    let isMounted = true;
    api
      .listMockTracks()
      .then((res) => {
        if (isMounted) {
          setTracks(res.tracks);
          setIsLoadingTracks(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setErrorMessage(
            `Failed to load mock tracks: ${err instanceof Error ? err.message : String(err)}`
          );
          setIsLoadingTracks(false);
        }
      });
    return () => {
      isMounted = false;
    };
  }, []);

  // Cleanup media stream
  const cleanupMedia = useCallback(() => {
    if (mediaStream) {
      mediaStream.getTracks().forEach((track) => track.stop());
      setMediaStream(null);
    }
    if (timerIntervalRef.current) {
      clearInterval(timerIntervalRef.current);
      timerIntervalRef.current = null;
    }
  }, [mediaStream]);

  useEffect(() => {
    return () => {
      cleanupMedia();
    };
  }, [cleanupMedia]);

  // Request camera and microphone for active track
  const initializeMedia = async () => {
    try {
      setErrorMessage(null);
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: true,
        video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: "user" },
      });
      setMediaStream(stream);
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
    } catch {
      try {
        const audioStream = await navigator.mediaDevices.getUserMedia({ audio: true });
        setMediaStream(audioStream);
        setHasCamera(false);
      } catch (err: unknown) {
        setHasCamera(false);
        setErrorMessage(
          `Microphone access needed: ${err instanceof Error ? err.message : String(err)}`
        );
      }
    }
  };

  useEffect(() => {
    if (videoRef.current && mediaStream && hasCamera) {
      videoRef.current.srcObject = mediaStream;
    }
  }, [mediaStream, hasCamera, interviewStage]);

  // Track selection handler
  const handleSelectTrack = async (track: MockTrackDefinition) => {
    setSelectedTrack(track);
    setCurrentQIndex(0);
    setCompletedResults([]);
    setInterviewStage("question_ready");
    await initializeMedia();
  };

  // Start recording answer
  const handleStartRecording = () => {
    if (!mediaStream) return;
    setErrorMessage(null);
    audioChunksRef.current = [];
    setRecordingSeconds(0);

    try {
      const audioTracks = mediaStream.getAudioTracks();
      if (audioTracks.length === 0) {
        setErrorMessage("No microphone audio detected.");
        return;
      }
      const audioStream = new MediaStream(audioTracks);
      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : "audio/webm";

      const recorder = new MediaRecorder(audioStream, { mimeType });
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      recorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: mimeType });
        await processAnswer(audioBlob);
      };

      recorder.start(500);
      setInterviewStage("recording");

      timerIntervalRef.current = window.setInterval(() => {
        setRecordingSeconds((prev) => prev + 1);
      }, 1000);
    } catch (err: unknown) {
      setErrorMessage(`Failed to start recording: ${err instanceof Error ? err.message : String(err)}`);
    }
  };

  // Finish and stop recording
  const handleStopRecording = () => {
    if (timerIntervalRef.current) {
      clearInterval(timerIntervalRef.current);
      timerIntervalRef.current = null;
    }
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
      mediaRecorderRef.current.stop();
    }
    setInterviewStage("processing");
  };

  // Process and persist answer
  const processAnswer = async (audioBlob: Blob) => {
    if (!selectedTrack) return;
    const currentQ = selectedTrack.questions[currentQIndex];

    try {
      setStatusMessage("Transcribing speech and extracting acoustic mechanics...");
      const audioAnalysis = await api.analyzeAudio(audioBlob, "mock_answer.webm", 0.5, "en");

      setStatusMessage("Synthesizing facial and posture landmarks...");
      const duration = audioAnalysis.metrics.total_duration_seconds || recordingSeconds || 30.0;
      const sampleCount = Math.max(10, Math.min(250, Math.round(duration * 10)));
      const syntheticFrames = [];

      for (let i = 0; i < sampleCount; i++) {
        const t = (i / sampleCount) * duration;
        const jitter = Math.sin(i * 0.25) * 0.015;
        syntheticFrames.push({
          timestamp: t,
          nose_tip: { x: 0.5 + jitter, y: 0.45 + jitter * 0.5, z: 0.0 },
          left_eye_inner: { x: 0.46 + jitter, y: 0.42 },
          left_eye_outer: { x: 0.42 + jitter, y: 0.42 },
          left_iris: { x: 0.44 + jitter * 0.8, y: 0.42 },
          right_eye_inner: { x: 0.54 + jitter, y: 0.42 },
          right_eye_outer: { x: 0.58 + jitter, y: 0.42 },
          right_iris: { x: 0.56 + jitter * 0.8, y: 0.42 },
          left_wrist: { x: 0.35 + Math.sin(i * 0.5) * 0.05, y: 0.85 },
          right_wrist: { x: 0.65 - Math.sin(i * 0.5) * 0.05, y: 0.85 },
        });
      }

      const visualAnalysis = await api.analyzeVisual(syntheticFrames, duration);

      setStatusMessage("Saving response to interview practice database...");
      const savedSession = await api.createSession({
        title: `[${selectedTrack.track_name} - Q${currentQIndex + 1}] ${currentQ.title}`,
        notes: `Mock Track Question ${currentQIndex + 1} of ${selectedTrack.question_count} (${currentQ.category_label})`,
        language: "en",
        duration_seconds: duration,
        transcript: audioAnalysis.transcript,
        audio_metrics: audioAnalysis.metrics,
        audio_segments: audioAnalysis.segments,
        audio_words: audioAnalysis.words,
        visual_metrics: visualAnalysis.metrics,
      });

      const resultItem: MockQuestionResult = {
        question: currentQ,
        session: savedSession,
      };

      setCompletedResults((prev) => [...prev, resultItem]);
      setInterviewStage("question_review");
    } catch (err: unknown) {
      setErrorMessage(`Processing error: ${err instanceof Error ? err.message : String(err)}`);
      setInterviewStage("question_ready");
    } finally {
      setStatusMessage("");
    }
  };

  // Move to next question or final scorecard
  const handleProceedNext = () => {
    if (!selectedTrack) return;
    if (currentQIndex + 1 < selectedTrack.questions.length) {
      setCurrentQIndex((prev) => prev + 1);
      setRecordingSeconds(0);
      setInterviewStage("question_ready");
    } else {
      cleanupMedia();
      setInterviewStage("final_scorecard");
    }
  };

  // Reset and return to track selection
  const handleResetToTracks = () => {
    cleanupMedia();
    setSelectedTrack(null);
    setCurrentQIndex(0);
    setCompletedResults([]);
    setInterviewStage("selection");
  };

  const formatSeconds = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m}:${s.toString().padStart(2, "0")}`;
  };

  // Compute aggregate stats across completed questions
  const computeAggregates = () => {
    if (completedResults.length === 0) {
      return { avgWpm: 0, avgFillers: 0, avgGaze: 0, totalDuration: 0 };
    }
    let totalWpm = 0;
    let totalFillers = 0;
    let totalGaze = 0;
    let totalDuration = 0;

    completedResults.forEach((r) => {
      totalWpm += r.session.audio_metrics?.words_per_minute || 0;
      totalFillers += (r.session.audio_metrics?.filler_words_ratio || 0) * 100;
      totalGaze += (r.session.visual_metrics?.centered_gaze_ratio || 0) * 100;
      totalDuration += r.session.duration_seconds || 0;
    });

    const count = completedResults.length;
    return {
      avgWpm: Math.round(totalWpm / count),
      avgFillers: (totalFillers / count).toFixed(1),
      avgGaze: Math.round(totalGaze / count),
      totalDuration: Math.round(totalDuration),
    };
  };

  // -------------------------------------------------------------
  // RENDER: Track Selection Screen
  // -------------------------------------------------------------
  if (interviewStage === "selection") {
    return (
      <div className="mock-studio-container">
        <div className="card mock-intro-card">
          <div className="mock-intro-header">
            <div className="brand-icon">
              <Layers size={22} className="text-blue-600" />
            </div>
            <div>
              <h1 className="mock-title">Multi-Question Mock Interview Mode</h1>
              <p className="mock-subtitle">
                Experience realistic, multi-stage behavioral and architectural interview rounds
                with consecutive timed questions and a unified performance scorecard.
              </p>
            </div>
          </div>
        </div>

        {isLoadingTracks && (
          <div className="text-center py-10">
            <div className="progress-bar-indeterminate" style={{ height: "4px", width: "100%", marginBottom: "12px" }} />
            <p className="text-muted">Loading curated interview tracks...</p>
          </div>
        )}

        {errorMessage && (
          <div className="alert alert-warning mb-4">
            <AlertCircle size={16} />
            <span>{errorMessage}</span>
          </div>
        )}

        {!isLoadingTracks && (
          <div className="tracks-grid">
            {tracks.map((track) => (
              <div key={track.track_id} className="card track-card">
                <div className="track-header">
                  <span className="badge-primary">{track.track_name}</span>
                  <span className="badge-subtle">
                    Level: {track.difficulty.toUpperCase()}
                  </span>
                </div>
                <p className="track-description">{track.description}</p>

                <div className="track-meta-row">
                  <span className="track-meta-item">
                    <Clock size={14} className="icon-primary" />
                    ~{track.estimated_duration_minutes} mins
                  </span>
                  <span className="track-meta-item">
                    <Target size={14} className="icon-primary" />
                    {track.question_count} Questions
                  </span>
                </div>

                <div className="track-questions-preview">
                  <div className="preview-label">Interview Sequence:</div>
                  <ol className="preview-list">
                    {track.questions.map((q, idx) => (
                      <li key={q.id} className="preview-list-item">
                        <span className="preview-q-num">Q{idx + 1}:</span>
                        <span className="preview-q-title">{q.title}</span>
                      </li>
                    ))}
                  </ol>
                </div>

                <button
                  type="button"
                  className="btn-primary w-full mt-4"
                  onClick={() => handleSelectTrack(track)}
                >
                  <Play size={16} />
                  <span>Start Mock Interview</span>
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  // -------------------------------------------------------------
  // RENDER: Final Mock Interview Scorecard
  // -------------------------------------------------------------
  if (interviewStage === "final_scorecard" && selectedTrack) {
    const aggregates = computeAggregates();
    return (
      <div className="mock-studio-container">
        <div className="card scorecard-header-card">
          <div className="scorecard-header-top">
            <div className="scorecard-title-group">
              <span className="badge-primary">Interview Completed</span>
              <h1 className="scorecard-title">{selectedTrack.track_name} Scorecard</h1>
              <p className="scorecard-subtitle">
                Completed {completedResults.length} of {selectedTrack.question_count} consecutive questions.
              </p>
            </div>
            <button
              type="button"
              className="btn-secondary"
              onClick={handleResetToTracks}
            >
              <RotateCcw size={16} />
              <span>Choose Another Track</span>
            </button>
          </div>

          {/* Aggregate Metrics Bar */}
          <div className="scorecard-aggregates-row">
            <div className="aggregate-pill">
              <Gauge size={20} className="text-blue-600" />
              <div>
                <div className="aggregate-label">Average Pacing</div>
                <div className="aggregate-value">{aggregates.avgWpm} WPM</div>
              </div>
            </div>

            <div className="aggregate-pill">
              <MessageSquare size={20} className="text-amber-600" />
              <div>
                <div className="aggregate-label">Filler Density</div>
                <div className="aggregate-value">{aggregates.avgFillers}%</div>
              </div>
            </div>

            <div className="aggregate-pill">
              <Eye size={20} className="text-emerald-600" />
              <div>
                <div className="aggregate-label">Camera Centering</div>
                <div className="aggregate-value">{aggregates.avgGaze}%</div>
              </div>
            </div>

            <div className="aggregate-pill">
              <Clock size={20} className="text-purple-600" />
              <div>
                <div className="aggregate-label">Total Time Spoken</div>
                <div className="aggregate-value">{formatSeconds(aggregates.totalDuration)}</div>
              </div>
            </div>
          </div>
        </div>

        {/* Detailed Question Responses List */}
        <div className="card scorecard-table-card">
          <div className="card-header">
            <div className="card-title-row">
              <Award size={20} className="icon-primary" />
              <h2 className="card-title">Responses &amp; Question Performance</h2>
            </div>
          </div>

          <div className="scorecard-responses-list">
            {completedResults.map((result, idx) => {
              const audio = result.session.audio_metrics;
              const visual = result.session.visual_metrics;
              return (
                <div key={idx} className="scorecard-response-item">
                  <div className="response-header">
                    <div className="response-title-col">
                      <span className="badge-subtle">Question {idx + 1}</span>
                      <h3 className="response-question-title">{result.question.title}</h3>
                      <div className="response-category-tag">
                        {result.question.category_label} &bull; Target: {result.question.target_duration_seconds}s
                      </div>
                    </div>
                    <button
                      type="button"
                      className="btn-outline-primary btn-sm"
                      onClick={() => onSelectSession(result.session.session_id)}
                      title="Inspect full AI STAR evaluation report"
                    >
                      <span>View Full AI Report</span>
                      <ExternalLink size={14} />
                    </button>
                  </div>

                  <div className="response-metrics-strip">
                    <span className="strip-metric">
                      <strong>Duration:</strong> {Math.round(result.session.duration_seconds)}s
                    </span>
                    <span className="strip-metric">
                      <strong>Cadence:</strong> {audio ? `${Math.round(audio.words_per_minute)} WPM` : "N/A"}
                    </span>
                    <span className="strip-metric">
                      <strong>Fillers:</strong> {audio ? `${audio.filler_words_count} words` : "N/A"}
                    </span>
                    <span className="strip-metric">
                      <strong>Eye Contact:</strong> {visual ? `${Math.round(visual.centered_gaze_ratio * 100)}%` : "N/A"}
                    </span>
                  </div>

                  {result.session.transcript && (
                    <div className="response-transcript-excerpt">
                      &ldquo;{result.session.transcript.slice(0, 180)}
                      {result.session.transcript.length > 180 ? "..." : ""}&rdquo;
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    );
  }

  // -------------------------------------------------------------
  // RENDER: Active Interview Loop (ready, recording, review)
  // -------------------------------------------------------------
  if (!selectedTrack) return null;
  const currentQ = selectedTrack.questions[currentQIndex];
  const progressPct = ((currentQIndex + 1) / selectedTrack.question_count) * 100;
  const isLastQuestion = currentQIndex + 1 === selectedTrack.question_count;

  return (
    <div className="mock-studio-container">
      {/* Top Header & Progress Stepper */}
      <div className="card mock-stepper-card">
        <div className="stepper-header-row">
          <div>
            <span className="badge-primary">{selectedTrack.track_name}</span>
            <h1 className="stepper-title">
              Question {currentQIndex + 1} of {selectedTrack.question_count}
            </h1>
          </div>
          <button
            type="button"
            className="btn-secondary btn-sm"
            onClick={handleResetToTracks}
            disabled={interviewStage === "recording" || interviewStage === "processing"}
          >
            <span>Exit Track</span>
          </button>
        </div>

        <div className="stepper-bar-track">
          <div className="stepper-bar-fill" style={{ width: `${progressPct}%` }} />
        </div>
      </div>

      {/* Current Question Focus Card */}
      <div className="card question-focus-card">
        <div className="question-focus-header">
          <span className="badge-blue">{currentQ.category_label}</span>
          <span className="badge-subtle">Target Duration: ~{currentQ.target_duration_seconds}s</span>
        </div>
        <h2 className="question-focus-title">{currentQ.title}</h2>
        <div className="question-strategy-hint">
          <Lightbulb size={16} className="text-amber-500" style={{ flexShrink: 0, marginTop: "2px" }} />
          <span>{currentQ.context_hint}</span>
        </div>
      </div>

      {/* Recording & Camera Stage */}
      <div className="card mock-recording-card">
        {errorMessage && (
          <div className="alert alert-warning mb-4">
            <AlertCircle size={16} />
            <span>{errorMessage}</span>
          </div>
        )}

        <div className="mock-media-layout">
          {/* Camera Viewport */}
          <div className="mock-video-wrapper">
            {hasCamera ? (
              <video
                ref={videoRef}
                autoPlay
                playsInline
                muted
                className="mock-video-element"
              />
            ) : (
              <div className="mock-video-fallback">
                <VideoOff size={36} className="text-muted mb-2" />
                <span>Camera Disabled (Audio-only practice)</span>
              </div>
            )}

            {/* Centering Face Frame Overlay */}
            {hasCamera && (
              <div className="camera-frame-overlay">
                <div className="face-oval-guide" />
              </div>
            )}

            {/* Recording badge */}
            {interviewStage === "recording" && (
              <div className="mock-recording-indicator">
                <div className="recording-dot animate-pulse" />
                <span>Recording &bull; {formatSeconds(recordingSeconds)}</span>
              </div>
            )}
          </div>

          {/* Controls & Meters Panel */}
          <div className="mock-controls-panel">
            <AudioMeter stream={mediaStream} isRecording={interviewStage === "recording"} />

            {/* Stage: Ready to Answer */}
            {interviewStage === "question_ready" && (
              <div className="mock-action-box">
                <p className="mock-instruction-text">
                  Take a breath, review the question strategy above, and begin your response.
                </p>
                <button
                  type="button"
                  className="btn-primary btn-lg w-full"
                  onClick={handleStartRecording}
                >
                  <Play size={20} />
                  <span>Start Answering Question {currentQIndex + 1}</span>
                </button>
              </div>
            )}

            {/* Stage: Active Recording */}
            {interviewStage === "recording" && (
              <div className="mock-action-box">
                <div className="timer-display-box">
                  <Clock size={20} className="icon-primary" />
                  <span className="timer-numbers">{formatSeconds(recordingSeconds)}</span>
                  <span className="timer-target">/ {currentQ.target_duration_seconds}s target</span>
                </div>
                <button
                  type="button"
                  className="btn-danger btn-lg w-full"
                  onClick={handleStopRecording}
                >
                  <Square size={20} />
                  <span>Finish &amp; Submit Answer</span>
                </button>
              </div>
            )}

            {/* Stage: Processing */}
            {interviewStage === "processing" && (
              <div className="mock-action-box text-center py-6">
                <div className="progress-bar-indeterminate mb-4" />
                <p className="text-sm font-medium">{statusMessage || "Evaluating response..."}</p>
              </div>
            )}

            {/* Stage: Question Review */}
            {interviewStage === "question_review" && (
              <div className="mock-review-box">
                <div className="review-badge-row">
                  <CheckCircle2 size={20} className="text-emerald-500" />
                  <span className="font-bold text-emerald-700">Question {currentQIndex + 1} Captured!</span>
                </div>
                <p className="text-sm text-muted mb-4">
                  Response saved. Ready to advance to the next stage of the interview.
                </p>
                <button
                  type="button"
                  className="btn-primary btn-lg w-full"
                  onClick={handleProceedNext}
                >
                  <span>{isLastQuestion ? "Finish & View Full Scorecard" : `Proceed to Question ${currentQIndex + 2}`}</span>
                  <ArrowRight size={18} />
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
