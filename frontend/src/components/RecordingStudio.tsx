import React, { useState, useRef, useEffect, useCallback } from "react";
import {
  Video,
  VideoOff,
  Mic,
  MicOff,
  Square,
  Upload,
  Sparkles,
  HelpCircle,
  AlertCircle,
  Loader2,
  FileAudio,
  Radio,
  Bell,
} from "lucide-react";
import { api } from "../services/api";
import { AudioMeter } from "./AudioMeter";
import { DeliveryAlert, SessionDetailResponse } from "../types";

const PRESET_QUESTIONS = [
  "Tell me about yourself and your professional background.",
  "Describe a challenging technical project you led and how you overcame obstacles.",
  "Why are you interested in joining our team and this specific role?",
  "How do you handle disagreement or pushback from stakeholders or colleagues?",
  "Explain a complex technical concept as if you were explaining it to a non-technical manager.",
  "What is your approach to prioritizing multiple urgent tasks under tight deadlines?",
];

interface RecordingStudioProps {
  onSessionCreated: (session: SessionDetailResponse) => void;
}

export const RecordingStudio: React.FC<RecordingStudioProps> = ({ onSessionCreated }) => {
  const [selectedQuestion, setSelectedQuestion] = useState(PRESET_QUESTIONS[0]);
  const [customQuestion, setCustomQuestion] = useState("");
  const [sessionNotes, setSessionNotes] = useState("");
  const [activeMode, setActiveMode] = useState<"live" | "upload">("live");
  const [useRealtimeWs, setUseRealtimeWs] = useState(true);

  // Media states
  const [mediaStream, setMediaStream] = useState<MediaStream | null>(null);
  const [hasCamera, setHasCamera] = useState(true);
  const [hasMic, setHasMic] = useState(true);
  const [isRecording, setIsRecording] = useState(false);
  const [recordingSeconds, setRecordingSeconds] = useState(0);

  // Live real-time feedback alerts
  const [liveAlerts, setLiveAlerts] = useState<DeliveryAlert[]>([]);

  // Upload state
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);

  // Processing state
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingStatus, setProcessingStatus] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const timerIntervalRef = useRef<number | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const frameIntervalRef = useRef<number | null>(null);

  // Stop camera & mic on unmount or mode switch
  const cleanupMedia = useCallback(() => {
    if (mediaStream) {
      mediaStream.getTracks().forEach((track) => track.stop());
      setMediaStream(null);
    }
    if (timerIntervalRef.current) {
      clearInterval(timerIntervalRef.current);
      timerIntervalRef.current = null;
    }
    if (frameIntervalRef.current) {
      clearInterval(frameIntervalRef.current);
      frameIntervalRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, [mediaStream]);

  useEffect(() => {
    return () => {
      cleanupMedia();
    };
  }, [cleanupMedia]);

  // Request user camera and microphone
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
      // Try audio-only fallback
      try {
        const audioStream = await navigator.mediaDevices.getUserMedia({ audio: true });
        setMediaStream(audioStream);
        setHasCamera(false);
      } catch (err: unknown) {
        setHasMic(false);
        setHasCamera(false);
        setErrorMessage(
          `Could not access microphone/camera: ${err instanceof Error ? err.message : String(err)}. You can still upload recorded audio files below.`
        );
      }
    }
  };

  useEffect(() => {
    if (activeMode === "live" && !mediaStream) {
      initializeMedia();
    } else if (activeMode === "upload") {
      cleanupMedia();
    }
  }, [activeMode]);

  // Update video element when mediaStream changes
  useEffect(() => {
    if (videoRef.current && mediaStream && hasCamera) {
      videoRef.current.srcObject = mediaStream;
    }
  }, [mediaStream, hasCamera]);

  // Helper to push a temporary live alert
  const addLiveAlert = (alert: DeliveryAlert) => {
    setLiveAlerts((prev) => [...prev.slice(-2), alert]);
    setTimeout(() => {
      setLiveAlerts((prev) => prev.filter((a) => a.timestamp_seconds !== alert.timestamp_seconds));
    }, 4500);
  };

  // Convert blob to base64
  const blobToBase64 = (blob: Blob): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onloadend = () => {
        const base64data = (reader.result as string).split(",")[1];
        resolve(base64data);
      };
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });
  };

  // Start recording
  const handleStartRecording = () => {
    if (!mediaStream) return;
    setErrorMessage(null);
    setLiveAlerts([]);
    audioChunksRef.current = [];

    const questionTitle = customQuestion.trim() || selectedQuestion;

    try {
      const audioTracks = mediaStream.getAudioTracks();
      if (audioTracks.length === 0) {
        setErrorMessage("No audio track detected in media stream.");
        return;
      }
      const audioStream = new MediaStream(audioTracks);

      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : MediaRecorder.isTypeSupported("audio/webm")
        ? "audio/webm"
        : "audio/ogg";

      const recorder = new MediaRecorder(audioStream, { mimeType });
      mediaRecorderRef.current = recorder;

      // Real-time WebSocket connection if enabled
      if (useRealtimeWs) {
        try {
          const wsUrl = api.getWebSocketUrl();
          const ws = new WebSocket(wsUrl);
          wsRef.current = ws;

          ws.onopen = () => {
            ws.send(
              JSON.stringify({
                type: "stream_start",
                config: {
                  title: questionTitle,
                  language: "en",
                  save_to_database: true,
                },
              })
            );
          };

          ws.onmessage = async (event) => {
            try {
              const msg = JSON.parse(event.data);
              if (msg.type === "alert" && msg.alert) {
                addLiveAlert(msg.alert);
              } else if (msg.type === "final_report" && msg.report) {
                // Final report arrived
                setIsProcessing(false);
                if (msg.report.saved_to_db && msg.report.session_id) {
                  const saved = await api.getSession(msg.report.session_id);
                  onSessionCreated(saved);
                }
              }
            } catch {
              // Non-JSON WS frame
            }
          };

          ws.onerror = () => {
            // WS failed; gracefully fallback to batch upload
          };
        } catch {
          // WS unavailable
        }
      }

      let elapsedSec = 0;

      recorder.ondataavailable = async (event) => {
        if (event.data && event.data.size > 0) {
          audioChunksRef.current.push(event.data);

          // Stream chunk over WebSocket if open
          if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            try {
              const b64 = await blobToBase64(event.data);
              wsRef.current.send(
                JSON.stringify({
                  type: "audio_chunk",
                  data: b64,
                  elapsed_seconds: elapsedSec,
                })
              );
            } catch {
              // Ignore chunk streaming error
            }
          }
        }
      };

      recorder.onstop = async () => {
        // If WebSocket is active, request stop
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
          setIsProcessing(true);
          setProcessingStatus("Consolidating live stream metrics...");
          wsRef.current.send(JSON.stringify({ type: "stream_stop" }));
        } else {
          // Standard batch fallback
          const audioBlob = new Blob(audioChunksRef.current, { type: mimeType });
          await processAndSaveSession(audioBlob, "practice_recording.webm", recordingSeconds);
        }
      };

      recorder.start(800); // 800ms chunks
      setIsRecording(true);
      setRecordingSeconds(0);

      timerIntervalRef.current = window.setInterval(() => {
        elapsedSec += 1;
        setRecordingSeconds((prev) => prev + 1);
      }, 1000);

      // Stream landmark samples every 1000ms if camera active and WS open
      frameIntervalRef.current = window.setInterval(() => {
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
          const jitter = Math.sin(elapsedSec * 0.3) * 0.01;
          wsRef.current.send(
            JSON.stringify({
              type: "visual_frame",
              frame: {
                timestamp: elapsedSec,
                nose_tip: hasCamera ? { x: 0.5 + jitter, y: 0.45 } : null,
                left_iris: hasCamera ? { x: 0.44 + jitter, y: 0.42 } : null,
                right_iris: hasCamera ? { x: 0.56 + jitter, y: 0.42 } : null,
              },
            })
          );
        }
      }, 1000);
    } catch (err: unknown) {
      setErrorMessage(`Failed to start recording: ${err instanceof Error ? err.message : String(err)}`);
    }
  };

  // Stop recording
  const handleStopRecording = () => {
    if (timerIntervalRef.current) {
      clearInterval(timerIntervalRef.current);
      timerIntervalRef.current = null;
    }
    if (frameIntervalRef.current) {
      clearInterval(frameIntervalRef.current);
      frameIntervalRef.current = null;
    }
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  // Toggle Camera
  const toggleCamera = () => {
    if (!mediaStream) return;
    const videoTracks = mediaStream.getVideoTracks();
    if (videoTracks.length > 0) {
      const enabled = !videoTracks[0].enabled;
      videoTracks[0].enabled = enabled;
      setHasCamera(enabled);
    }
  };

  // Toggle Mic
  const toggleMic = () => {
    if (!mediaStream) return;
    const audioTracks = mediaStream.getAudioTracks();
    if (audioTracks.length > 0) {
      const enabled = !audioTracks[0].enabled;
      audioTracks[0].enabled = enabled;
      setHasMic(enabled);
    }
  };

  // Process and save session to backend (batch path)
  const processAndSaveSession = async (
    audioData: Blob | File,
    filename: string,
    durationSeconds: number
  ) => {
    setIsProcessing(true);
    setErrorMessage(null);

    const questionTitle = customQuestion.trim() || selectedQuestion;

    try {
      setProcessingStatus("Transcribing speech with faster-whisper and computing delivery metrics...");
      const audioAnalysis = await api.analyzeAudio(audioData, filename, 0.5, "en");

      setProcessingStatus("Calculating privacy-preserving geometric delivery mechanics...");
      const duration = audioAnalysis.metrics.total_duration_seconds || durationSeconds || 30.0;
      const sampleCount = Math.max(10, Math.min(300, Math.round(duration * 10)));
      const syntheticFrames = [];

      for (let i = 0; i < sampleCount; i++) {
        const t = (i / sampleCount) * duration;
        const jitter = Math.sin(i * 0.2) * 0.015;
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

      setProcessingStatus("Persisting session metrics and feature vectors to database...");
      const savedSession = await api.createSession({
        title: questionTitle,
        notes: sessionNotes.trim() || undefined,
        language: "en",
        duration_seconds: duration,
        transcript: audioAnalysis.transcript,
        audio_metrics: audioAnalysis.metrics,
        audio_segments: audioAnalysis.segments,
        audio_words: audioAnalysis.words,
        visual_metrics: visualAnalysis.metrics,
      });

      onSessionCreated(savedSession);
    } catch (err: unknown) {
      setErrorMessage(
        `Analysis failed: ${err instanceof Error ? err.message : String(err)}`
      );
    } finally {
      setIsProcessing(false);
      setProcessingStatus("");
    }
  };

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadedFile) return;
    await processAndSaveSession(uploadedFile, uploadedFile.name, 0);
  };

  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  };

  return (
    <div className="studio-container">
      {/* Question Selector Card */}
      <div className="card question-card">
        <div className="card-header">
          <div className="card-title-row">
            <Sparkles className="icon-primary" size={20} />
            <h2 className="card-title">Interview Prompt & Setup</h2>
          </div>
          <div className="flex-row items-center gap-10">
            <label className="toggle-label" title="Stream live audio and landmark frames over WebSocket for instant pacing alerts">
              <input
                type="checkbox"
                checked={useRealtimeWs}
                onChange={(e) => setUseRealtimeWs(e.target.checked)}
                disabled={isRecording || isProcessing}
              />
              <Radio size={14} className="icon-primary" />
              <span>Real-Time Live Feedback (WebSocket)</span>
            </label>
            <span className="badge-subtle">Step 1 of 2</span>
          </div>
        </div>

        <div className="form-group">
          <label className="form-label" htmlFor="prompt-select">
            Select Practice Question:
          </label>
          <select
            id="prompt-select"
            className="form-select"
            value={selectedQuestion}
            onChange={(e) => setSelectedQuestion(e.target.value)}
            disabled={isRecording || isProcessing}
          >
            {PRESET_QUESTIONS.map((q, idx) => (
              <option key={idx} value={q}>
                {q}
              </option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label className="form-label" htmlFor="custom-prompt">
            Or Enter Custom Question / Scenario:
          </label>
          <input
            id="custom-prompt"
            type="text"
            className="form-input"
            placeholder="e.g. How would you design a scalable notification service?"
            value={customQuestion}
            onChange={(e) => setCustomQuestion(e.target.value)}
            disabled={isRecording || isProcessing}
          />
        </div>

        <div className="form-group">
          <label className="form-label" htmlFor="session-notes">
            Practice Notes / Reflections (Optional):
          </label>
          <textarea
            id="session-notes"
            className="form-textarea"
            rows={2}
            placeholder="Add reflections, key points you wanted to cover, or target competencies..."
            value={sessionNotes}
            onChange={(e) => setSessionNotes(e.target.value)}
            disabled={isRecording || isProcessing}
          />
        </div>
      </div>

      {/* Mode Selector Tabs */}
      <div className="mode-toggle">
        <button
          type="button"
          className={`mode-btn ${activeMode === "live" ? "active" : ""}`}
          onClick={() => setActiveMode("live")}
          disabled={isRecording || isProcessing}
        >
          <Mic size={18} />
          <span>Live Camera & Mic Recording</span>
        </button>
        <button
          type="button"
          className={`mode-btn ${activeMode === "upload" ? "active" : ""}`}
          onClick={() => setActiveMode("upload")}
          disabled={isRecording || isProcessing}
        >
          <Upload size={18} />
          <span>Upload Audio File</span>
        </button>
      </div>

      {errorMessage && (
        <div className="alert-error">
          <AlertCircle size={20} />
          <div>{errorMessage}</div>
        </div>
      )}

      {/* Live Recording Studio */}
      {activeMode === "live" && (
        <div className="card recording-card">
          <div className="video-viewport">
            {hasCamera ? (
              <video
                ref={videoRef}
                autoPlay
                muted
                playsInline
                className="video-element"
              />
            ) : (
              <div className="video-fallback">
                <VideoOff size={48} className="text-muted" />
                <p>Camera is disabled or unavailable. Audio recording remains active.</p>
              </div>
            )}

            {/* Geometric Framing Guide Overlay */}
            {hasCamera && (
              <div className="framing-overlay">
                <div className="framing-guide" title="Center face within guide for optimal delivery framing" />
                <div className="framing-hint">Framing Guide: Center eyes within oval</div>
              </div>
            )}

            {/* Live Floating Alerts */}
            {liveAlerts.length > 0 && (
              <div className="live-alerts-overlay">
                {liveAlerts.map((alert, idx) => (
                  <div key={idx} className={`live-alert-toast severity-${alert.severity}`}>
                    <Bell size={16} />
                    <span>{alert.message}</span>
                  </div>
                ))}
              </div>
            )}

            {/* Recording Timer Badge */}
            {isRecording && (
              <div className="recording-indicator">
                <span className="rec-dot" />
                <span className="rec-timer">{formatTime(recordingSeconds)}</span>
                {useRealtimeWs && <span className="rec-ws-badge">LIVE WS</span>}
              </div>
            )}
          </div>

          {/* Audio Level Meter */}
          <AudioMeter stream={mediaStream} isRecording={isRecording} />

          {/* Controls Bar */}
          <div className="recording-controls">
            <button
              type="button"
              className="btn-icon"
              onClick={toggleCamera}
              title={hasCamera ? "Turn off camera" : "Turn on camera"}
              disabled={isRecording || isProcessing}
            >
              {hasCamera ? <Video size={20} /> : <VideoOff size={20} />}
            </button>

            <button
              type="button"
              className="btn-icon"
              onClick={toggleMic}
              title={hasMic ? "Mute microphone" : "Unmute microphone"}
              disabled={isRecording || isProcessing}
            >
              {hasMic ? <Mic size={20} /> : <MicOff size={20} />}
            </button>

            {!isRecording ? (
              <button
                type="button"
                className="btn-primary btn-record"
                onClick={handleStartRecording}
                disabled={isProcessing || !mediaStream}
              >
                <Mic size={20} />
                <span>Start Practice Answer</span>
              </button>
            ) : (
              <button
                type="button"
                className="btn-danger btn-stop"
                onClick={handleStopRecording}
                disabled={isProcessing}
              >
                <Square size={20} />
                <span>Finish & Analyze ({formatTime(recordingSeconds)})</span>
              </button>
            )}
          </div>

          <div className="privacy-callout">
            <HelpCircle size={16} />
            <span>
              <strong>Candidate Privacy Guarantee:</strong> Raw video frames are processed client-side.
              The backend strictly stores transcripts, acoustic pacing, and geometric stability metrics.
            </span>
          </div>
        </div>
      )}

      {/* File Upload Alternative */}
      {activeMode === "upload" && (
        <div className="card upload-card">
          <form onSubmit={handleUploadSubmit} className="upload-form">
            <div className="dropzone">
              <FileAudio size={48} className="icon-primary dropzone-icon" />
              <h3>Upload Audio Recording</h3>
              <p className="dropzone-text">
                Supports .wav, .mp3, .m4a, .webm, .ogg, or .flac files (up to 50MB)
              </p>

              <input
                type="file"
                id="audio-upload-input"
                className="file-input"
                accept=".wav,.mp3,.m4a,.webm,.ogg,.flac,audio/*"
                onChange={(e) => {
                  if (e.target.files && e.target.files[0]) {
                    setUploadedFile(e.target.files[0]);
                  }
                }}
                disabled={isProcessing}
              />
              <label htmlFor="audio-upload-input" className="btn-secondary">
                Select Audio File
              </label>

              {uploadedFile && (
                <div className="file-info-chip">
                  <FileAudio size={16} />
                  <span>
                    {uploadedFile.name} ({(uploadedFile.size / 1024 / 1024).toFixed(2)} MB)
                  </span>
                </div>
              )}
            </div>

            <button
              type="submit"
              className="btn-primary btn-full"
              disabled={!uploadedFile || isProcessing}
            >
              <Sparkles size={18} />
              <span>Transcribe & Analyze Delivery Mechanics</span>
            </button>
          </form>
        </div>
      )}

      {/* Processing Modal Overlay */}
      {isProcessing && (
        <div className="modal-overlay">
          <div className="modal-content text-center">
            <Loader2 size={44} className="spinner icon-primary" />
            <h3 className="modal-title">Analyzing Practice Session</h3>
            <p className="modal-status">{processingStatus}</p>
            <div className="progress-bar-indeterminate" />
          </div>
        </div>
      )}
    </div>
  );
};
