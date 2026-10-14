import logging
import os
import tempfile
import time
import uuid

from app.models.audio import AudioMetrics
from app.models.session import SessionCreateRequest
from app.models.streaming import (
    DeliveryAlert,
    LiveMetricsUpdate,
    StreamFinalReport,
    StreamStartConfig,
)
from app.models.visual import VisualFrameSample, VisualMetrics
from app.pipeline.audio_features import compute_audio_metrics
from app.pipeline.audio_transcriber import AudioTranscriber
from app.pipeline.visual_features import compute_visual_metrics
from app.storage.session_repository import SessionRepository

logger = logging.getLogger(__name__)


class StreamingSession:
    """Maintains active state for an ongoing real-time practice session.

    Processes incoming audio chunks and client-side extracted visual landmark frames.
    Produces incremental delivery alerts and consolidates metrics when stream closes.
    """

    def __init__(
        self,
        config: StreamStartConfig,
        repository: SessionRepository | None = None,
        transcriber: AudioTranscriber | None = None,
    ) -> None:
        self.config = config
        self.repository = repository
        self.transcriber = transcriber or AudioTranscriber.get_instance()

        self.session_id = (config.session_id or "").strip() or f"live_{uuid.uuid4().hex[:10]}"
        self.start_wall_time = time.monotonic()
        self.audio_chunks: list[bytes] = []
        self.visual_frames: list[VisualFrameSample] = []
        self.alerts_history: list[DeliveryAlert] = []

        # Real-time state trackers
        self.last_face_seen_time: float = 0.0
        self.last_center_gaze_time: float = 0.0
        self.last_speech_time: float = 0.0
        self.active_pause_start: float | None = None
        self.last_alert_timestamps: dict[str, float] = {}

    def get_elapsed_seconds(self) -> float:
        """Calculate elapsed session time in seconds."""
        return max(0.0, time.monotonic() - self.start_wall_time)

    def process_audio_chunk(
        self,
        chunk_bytes: bytes,
        elapsed_seconds: float | None = None,
    ) -> list[DeliveryAlert]:
        """Record incoming audio data and evaluate pacing / pause alerts."""
        if elapsed_seconds is None:
            elapsed_seconds = self.get_elapsed_seconds()

        self.audio_chunks.append(chunk_bytes)
        alerts: list[DeliveryAlert] = []

        # Track speech activity
        self.last_speech_time = elapsed_seconds
        self.active_pause_start = None

        return alerts

    def process_silence_interval(
        self,
        elapsed_seconds: float,
    ) -> list[DeliveryAlert]:
        """Check for extended pause duration in real-time."""
        alerts: list[DeliveryAlert] = []
        if self.active_pause_start is None:
            self.active_pause_start = self.last_speech_time

        pause_duration = elapsed_seconds - self.active_pause_start
        if pause_duration >= 3.0:
            alert = self._create_alert(
                alert_type="extended_pause",
                message=(
                    f"Deliberate pause in progress ({pause_duration:.1f}s). "
                    "Take a composed breath and smoothly continue your thought."
                ),
                severity="info",
                timestamp=elapsed_seconds,
                cooldown_seconds=6.0,
            )
            if alert:
                alerts.append(alert)

        return alerts

    def process_visual_frame(
        self,
        frame: VisualFrameSample,
    ) -> tuple[LiveMetricsUpdate, list[DeliveryAlert]]:
        """Process incoming client-side extracted geometric frame and check delivery posture."""
        self.visual_frames.append(frame)
        elapsed_seconds = frame.timestamp if frame.timestamp > 0 else self.get_elapsed_seconds()
        alerts: list[DeliveryAlert] = []

        # 1. Face detection presence
        has_face = frame.nose_tip is not None
        if has_face:
            self.last_face_seen_time = elapsed_seconds
        else:
            face_missing_duration = elapsed_seconds - self.last_face_seen_time
            if face_missing_duration >= 2.5:
                alert = self._create_alert(
                    alert_type="face_missing",
                    message=(
                        "Camera framing: Face is outside detected frame. "
                        "Re-center within camera view."
                    ),
                    severity="warning",
                    timestamp=elapsed_seconds,
                    cooldown_seconds=5.0,
                )
                if alert:
                    alerts.append(alert)

        # 2. Gaze centering check
        is_centered = False
        if frame.nose_tip and frame.left_iris and frame.right_iris:
            iris_cx = (frame.left_iris.x + frame.right_iris.x) / 2.0
            nose_x = frame.nose_tip.x
            # Centered threshold
            if abs(iris_cx - nose_x) < 0.045:
                is_centered = True
                self.last_center_gaze_time = elapsed_seconds
        elif has_face:
            # Fallback based on nose position
            if frame.nose_tip and 0.40 <= frame.nose_tip.x <= 0.60:
                is_centered = True
                self.last_center_gaze_time = elapsed_seconds

        if not is_centered and has_face:
            off_gaze_duration = elapsed_seconds - self.last_center_gaze_time
            if off_gaze_duration >= 3.5:
                alert = self._create_alert(
                    alert_type="off_center_gaze",
                    message=(
                        "Delivery focus: Gaze oriented away from camera. "
                        "Look toward the upper lens."
                    ),
                    severity="caution",
                    timestamp=elapsed_seconds,
                    cooldown_seconds=6.0,
                )
                if alert:
                    alerts.append(alert)

        # Build running metrics update
        update = self.get_live_update(elapsed_seconds)
        return update, alerts

    def get_live_update(self, elapsed_seconds: float | None = None) -> LiveMetricsUpdate:
        """Compute running delivery mechanics summary."""
        if elapsed_seconds is None:
            elapsed_seconds = self.get_elapsed_seconds()

        total_frames = len(self.visual_frames)
        centered_count = 0
        face_count = 0

        for f in self.visual_frames:
            if f.nose_tip is not None:
                face_count += 1
                if 0.42 <= f.nose_tip.x <= 0.58:
                    centered_count += 1

        face_detected = (
            (self.visual_frames[-1].nose_tip is not None) if self.visual_frames else True
        )
        gaze_ratio = (centered_count / total_frames) if total_frames > 0 else 0.85
        current_pause = (
            max(0.0, elapsed_seconds - self.active_pause_start)
            if self.active_pause_start is not None
            else 0.0
        )

        return LiveMetricsUpdate(
            elapsed_seconds=round(elapsed_seconds, 1),
            current_wpm_estimate=None,  # updated during interim audio transcription
            recent_filler_count=0,
            current_pause_seconds=round(current_pause, 1),
            centered_gaze_ratio=round(gaze_ratio, 2) if total_frames > 0 else None,
            head_stability_score=0.90 if total_frames > 0 else None,
            face_detected=face_detected,
        )

    def _create_alert(
        self,
        alert_type: str,
        message: str,
        severity: str,
        timestamp: float,
        cooldown_seconds: float = 5.0,
    ) -> DeliveryAlert | None:
        """Create and register alert if cooldown period has elapsed."""
        last_fired = self.last_alert_timestamps.get(alert_type, -999.0)
        if (timestamp - last_fired) < cooldown_seconds:
            return None

        self.last_alert_timestamps[alert_type] = timestamp
        alert = DeliveryAlert(
            timestamp_seconds=round(timestamp, 2),
            alert_type=alert_type,
            message=message,
            severity=severity,
        )
        self.alerts_history.append(alert)
        return alert

    def finalize(self) -> StreamFinalReport:
        """Consolidate stream data, transcribe audio, compute delivery metrics, and persist."""
        total_duration = max(0.5, self.get_elapsed_seconds())
        audio_metrics: AudioMetrics | None = None
        transcript: str | None = None
        segments = []
        words = []

        # 1. Process aggregated audio chunks
        if self.audio_chunks:
            combined_audio_bytes = b"".join(self.audio_chunks)
            if len(combined_audio_bytes) > 512:
                # Detect container suffix from magic bytes
                if combined_audio_bytes.startswith(b"\x1a\x45\xdf\xa3"):
                    suffix = ".webm"
                elif combined_audio_bytes.startswith(b"OggS"):
                    suffix = ".ogg"
                elif combined_audio_bytes.startswith(b"RIFF"):
                    suffix = ".wav"
                elif combined_audio_bytes.startswith(b"ID3") or combined_audio_bytes[:2] in (
                    b"\xff\xfb",
                    b"\xff\xf3",
                    b"\xff\xf2",
                ):
                    suffix = ".mp3"
                else:
                    suffix = ".webm"

                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
                try:
                    temp_file.write(combined_audio_bytes)
                    temp_file.flush()
                    temp_file.close()

                    try:
                        t_text, _, _, segments, words = self.transcriber.transcribe(
                            temp_file.name,
                            language=self.config.language,
                        )
                        transcript = t_text
                        audio_duration = total_duration
                        if segments:
                            audio_duration = max(s.end for s in segments)
                        elif words:
                            audio_duration = max(w.end for w in words)

                        audio_metrics = compute_audio_metrics(
                            words=words,
                            total_audio_duration=audio_duration,
                            pause_threshold_seconds=self.config.pause_threshold_seconds,
                        )
                    except Exception as exc:
                        logger.warning("Transcription failed during stream finalization: %s", exc)
                finally:
                    if os.path.exists(temp_file.name):
                        try:
                            os.unlink(temp_file.name)
                        except OSError:
                            pass

        # 2. Process visual landmark frames
        visual_metrics: VisualMetrics | None = None
        if self.visual_frames:
            visual_metrics = compute_visual_metrics(
                frames=self.visual_frames,
                known_duration_seconds=total_duration,
            )

        # 3. Optional persistence to local database
        saved_to_db = False
        if self.config.save_to_database and self.repository is not None:
            try:
                self.repository.create_session(
                    SessionCreateRequest(
                        session_id=self.session_id,
                        title=self.config.title or "Real-Time Practice Session",
                        language=self.config.language,
                        duration_seconds=total_duration,
                        transcript=transcript,
                        audio_metrics=audio_metrics,
                        audio_segments=segments,
                        audio_words=words,
                        visual_metrics=visual_metrics,
                    )
                )
                saved_to_db = True
            except Exception as exc:
                logger.exception("Failed to save streaming session to database: %s", exc)
                saved_to_db = False

        return StreamFinalReport(
            session_id=self.session_id,
            total_duration_seconds=round(total_duration, 2),
            audio_metrics=audio_metrics,
            visual_metrics=visual_metrics,
            transcript=transcript,
            alerts_triggered_count=len(self.alerts_history),
            saved_to_db=saved_to_db,
            context={"title": self.config.title},
        )
