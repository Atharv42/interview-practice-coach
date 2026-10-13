"""Repository layer for practice sessions, delivery metrics, and historical analytics."""

import json
import uuid
from datetime import UTC, datetime

from app.models.analytics import (
    AnalyticsDashboardResponse,
    SessionFeatureVector,
)
from app.models.audio import (
    AudioMetrics,
    AudioSegment,
    PauseDetail,
    WordTimestamp,
)
from app.models.session import (
    SessionCreateRequest,
    SessionDetailResponse,
    SessionSummary,
)
from app.models.visual import VisualMetrics
from app.pipeline.analytics import (
    compute_delivery_trends,
    compute_pca_and_clustering,
    extract_session_feature_vector,
)
from app.storage.database import Database, get_database


class SessionAlreadyExistsError(Exception):
    """Raised when attempting to insert a session with an ID that already exists."""


class SessionNotFoundError(Exception):
    """Raised when a requested session cannot be found in the database."""


class SessionRepository:
    """Provides data access and lifecycle operations for practice sessions."""

    def __init__(self, db: Database | None = None) -> None:
        self.db = db or get_database()

    def create_session(self, request: SessionCreateRequest) -> SessionDetailResponse:
        """Create and persist a new practice session and its extracted metrics.

        Calculates a consolidated multimodal feature vector and stores all metrics
        transactionally. Strictly preserves privacy: no raw media files are stored.
        """
        # 1. Resolve session ID
        session_id = (request.session_id or "").strip()
        if not session_id:
            session_id = f"sess_{uuid.uuid4().hex[:12]}"

        # 2. Resolve creation timestamp
        created_at = request.created_at or datetime.now(UTC).isoformat()

        # 3. Unpack audio parameters (directly or from audio_analysis)
        transcript = request.transcript
        audio_metrics = request.audio_metrics
        audio_segments = list(request.audio_segments)
        audio_words = list(request.audio_words)

        audio_analysis = request.audio_analysis
        if audio_analysis is not None:
            if not transcript:
                transcript = audio_analysis.transcript
            if audio_metrics is None:
                audio_metrics = audio_analysis.metrics
            if not audio_segments:
                audio_segments = list(audio_analysis.segments)
            if not audio_words:
                audio_words = list(audio_analysis.words)

        # Resolve language: explicit request > audio_analysis detected > default 'en'
        language = (
            request.language
            or (audio_analysis.language if audio_analysis and audio_analysis.language else None)
            or "en"
        )
        language_probability = (
            audio_analysis.language_probability
            if audio_analysis and audio_analysis.language_probability is not None
            else 1.0
        )

        # 4. Unpack visual parameters (directly or from visual_analysis)
        visual_metrics = request.visual_metrics
        if request.visual_analysis is not None and visual_metrics is None:
            visual_metrics = request.visual_analysis.metrics

        # 5. Resolve duration
        if request.duration_seconds is not None:
            duration_seconds = max(0.0, float(request.duration_seconds))
        else:
            audio_dur = audio_metrics.total_duration_seconds if audio_metrics else 0.0
            visual_dur = visual_metrics.total_duration_seconds if visual_metrics else 0.0
            duration_seconds = max(audio_dur, visual_dur, 0.0)
            if duration_seconds == 0.0:
                if audio_segments:
                    duration_seconds = max((s.end for s in audio_segments), default=0.0)
                elif audio_words:
                    duration_seconds = max((w.end for w in audio_words), default=0.0)

        has_audio = (
            (audio_metrics is not None)
            or bool(transcript)
            or bool(audio_segments)
            or bool(audio_words)
        )
        has_visual = visual_metrics is not None

        # 6. Compute multimodal feature vector
        feature_vector = extract_session_feature_vector(
            session_id=session_id,
            session_index=0,
            timestamp_iso=created_at,
            audio_metrics=audio_metrics,
            visual_metrics=visual_metrics,
        )

        with self.db.connection() as conn:
            # Check for conflict
            existing = conn.execute(
                "SELECT session_id FROM sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            if existing:
                raise SessionAlreadyExistsError(f"Session with ID '{session_id}' already exists.")

            # Insert metadata
            conn.execute(
                """
                INSERT INTO sessions (
                    session_id, title, notes, created_at, duration_seconds, language
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    request.title,
                    request.notes,
                    created_at,
                    duration_seconds,
                    language,
                ),
            )

            # Insert audio metrics if present
            if has_audio:
                has_metrics_val = 1 if audio_metrics is not None else 0
                filler_breakdown_json = (
                    json.dumps(audio_metrics.filler_words_breakdown) if audio_metrics else "{}"
                )
                pauses_json = (
                    json.dumps([p.model_dump() for p in audio_metrics.pauses])
                    if audio_metrics
                    else "[]"
                )
                segments_json = json.dumps([s.model_dump() for s in audio_segments])
                words_json = json.dumps([w.model_dump() for w in audio_words])

                total_dur = (
                    audio_metrics.total_duration_seconds if audio_metrics else duration_seconds
                )
                speaking_dur = (
                    audio_metrics.speaking_duration_seconds if audio_metrics else duration_seconds
                )
                tot_words = (
                    audio_metrics.total_words if audio_metrics else len((transcript or "").split())
                )
                wpm = audio_metrics.words_per_minute if audio_metrics else 0.0
                articulation_wpm = audio_metrics.articulation_rate_wpm if audio_metrics else 0.0
                filler_cnt = audio_metrics.filler_words_count if audio_metrics else 0
                filler_ratio = audio_metrics.filler_words_ratio if audio_metrics else 0.0
                pause_cnt = audio_metrics.pause_count if audio_metrics else 0
                tot_pause_dur = audio_metrics.total_pause_duration_seconds if audio_metrics else 0.0
                avg_pause_dur = (
                    audio_metrics.average_pause_duration_seconds if audio_metrics else 0.0
                )
                longest_pause_dur = (
                    audio_metrics.longest_pause_duration_seconds if audio_metrics else 0.0
                )
                pause_thresh = audio_metrics.pause_threshold_seconds if audio_metrics else 0.5

                conn.execute(
                    """
                    INSERT INTO audio_metrics (
                        session_id, has_metrics, transcript, language, language_probability,
                        total_duration_seconds, speaking_duration_seconds, total_words,
                        words_per_minute, articulation_rate_wpm, filler_words_count,
                        filler_words_ratio, filler_words_breakdown_json, pause_count,
                        total_pause_duration_seconds, average_pause_duration_seconds,
                        longest_pause_duration_seconds, pause_threshold_seconds,
                        pauses_json, segments_json, words_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session_id,
                        has_metrics_val,
                        transcript or "",
                        language,
                        language_probability,
                        total_dur,
                        speaking_dur,
                        tot_words,
                        wpm,
                        articulation_wpm,
                        filler_cnt,
                        filler_ratio,
                        filler_breakdown_json,
                        pause_cnt,
                        tot_pause_dur,
                        avg_pause_dur,
                        longest_pause_dur,
                        pause_thresh,
                        pauses_json,
                        segments_json,
                        words_json,
                    ),
                )

            # Insert visual metrics if present
            if has_visual and visual_metrics is not None:
                gaze_dist_json = json.dumps(visual_metrics.gaze_distribution)
                notes_json = json.dumps(visual_metrics.tracking_notes)

                conn.execute(
                    """
                    INSERT INTO visual_metrics (
                        session_id, total_duration_seconds, frames_analyzed,
                        face_detected_ratio, centered_gaze_ratio, gaze_distribution_json,
                        head_stability_score, head_movement_variance, hands_visible_ratio,
                        hand_gestures_per_minute, tracking_notes_json, ethical_disclaimer
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session_id,
                        visual_metrics.total_duration_seconds,
                        visual_metrics.frames_analyzed,
                        visual_metrics.face_detected_ratio,
                        visual_metrics.centered_gaze_ratio,
                        gaze_dist_json,
                        visual_metrics.head_stability_score,
                        visual_metrics.head_movement_variance,
                        visual_metrics.hands_visible_ratio,
                        visual_metrics.hand_gestures_per_minute,
                        notes_json,
                        visual_metrics.ethical_disclaimer,
                    ),
                )

            # Insert feature vector
            conn.execute(
                """
                INSERT INTO session_feature_vectors (
                    session_id, session_index, timestamp_iso, has_audio, has_visual,
                    words_per_minute, articulation_rate_wpm, filler_words_ratio,
                    average_pause_duration_seconds, pause_frequency_per_minute,
                    centered_gaze_ratio, head_stability_score, hand_gestures_per_minute
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    feature_vector.session_index,
                    feature_vector.timestamp_iso,
                    1 if feature_vector.has_audio else 0,
                    1 if feature_vector.has_visual else 0,
                    feature_vector.words_per_minute,
                    feature_vector.articulation_rate_wpm,
                    feature_vector.filler_words_ratio,
                    feature_vector.average_pause_duration_seconds,
                    feature_vector.pause_frequency_per_minute,
                    feature_vector.centered_gaze_ratio,
                    feature_vector.head_stability_score,
                    feature_vector.hand_gestures_per_minute,
                ),
            )

        return SessionDetailResponse(
            session_id=session_id,
            title=request.title,
            notes=request.notes,
            created_at=created_at,
            duration_seconds=duration_seconds,
            language=language,
            has_audio=has_audio,
            has_visual=has_visual,
            transcript=transcript,
            audio_metrics=audio_metrics,
            audio_segments=audio_segments,
            audio_words=audio_words,
            visual_metrics=visual_metrics,
            feature_vector=feature_vector,
        )

    def get_session(self, session_id: str) -> SessionDetailResponse | None:
        """Retrieve detailed session metrics by unique identifier."""
        with self.db.connection() as conn:
            sess_row = conn.execute(
                "SELECT * FROM sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            if not sess_row:
                return None

            # Fetch audio metrics
            audio_row = conn.execute(
                "SELECT * FROM audio_metrics WHERE session_id = ?",
                (session_id,),
            ).fetchone()

            transcript: str | None = None
            audio_metrics: AudioMetrics | None = None
            audio_segments: list[AudioSegment] = []
            audio_words: list[WordTimestamp] = []
            has_audio = False

            if audio_row:
                has_audio = True
                transcript = audio_row["transcript"] or None
                segments_raw = json.loads(audio_row["segments_json"] or "[]")
                words_raw = json.loads(audio_row["words_json"] or "[]")

                audio_segments = [AudioSegment(**s) for s in segments_raw]
                audio_words = [WordTimestamp(**w) for w in words_raw]

                if audio_row["has_metrics"]:
                    breakdown = json.loads(audio_row["filler_words_breakdown_json"] or "{}")
                    pauses_raw = json.loads(audio_row["pauses_json"] or "[]")
                    pauses = [PauseDetail(**p) for p in pauses_raw]

                    audio_metrics = AudioMetrics(
                        total_duration_seconds=audio_row["total_duration_seconds"],
                        speaking_duration_seconds=audio_row["speaking_duration_seconds"],
                        total_words=audio_row["total_words"],
                        words_per_minute=audio_row["words_per_minute"],
                        articulation_rate_wpm=audio_row["articulation_rate_wpm"],
                        filler_words_count=audio_row["filler_words_count"],
                        filler_words_ratio=audio_row["filler_words_ratio"],
                        filler_words_breakdown=breakdown,
                        pause_count=audio_row["pause_count"],
                        total_pause_duration_seconds=audio_row["total_pause_duration_seconds"],
                        average_pause_duration_seconds=audio_row["average_pause_duration_seconds"],
                        longest_pause_duration_seconds=audio_row["longest_pause_duration_seconds"],
                        pause_threshold_seconds=audio_row["pause_threshold_seconds"],
                        pauses=pauses,
                    )
                else:
                    audio_metrics = None

            # Fetch visual metrics
            visual_row = conn.execute(
                "SELECT * FROM visual_metrics WHERE session_id = ?",
                (session_id,),
            ).fetchone()

            visual_metrics: VisualMetrics | None = None
            has_visual = False

            if visual_row:
                has_visual = True
                gaze_dist = json.loads(visual_row["gaze_distribution_json"] or "{}")
                notes = json.loads(visual_row["tracking_notes_json"] or "[]")

                visual_metrics = VisualMetrics(
                    total_duration_seconds=visual_row["total_duration_seconds"],
                    frames_analyzed=visual_row["frames_analyzed"],
                    face_detected_ratio=visual_row["face_detected_ratio"],
                    centered_gaze_ratio=visual_row["centered_gaze_ratio"],
                    gaze_distribution=gaze_dist,
                    head_stability_score=visual_row["head_stability_score"],
                    head_movement_variance=visual_row["head_movement_variance"],
                    hands_visible_ratio=visual_row["hands_visible_ratio"],
                    hand_gestures_per_minute=visual_row["hand_gestures_per_minute"],
                    tracking_notes=notes,
                    ethical_disclaimer=visual_row["ethical_disclaimer"],
                )

            # Fetch feature vector
            fv_row = conn.execute(
                "SELECT * FROM session_feature_vectors WHERE session_id = ?",
                (session_id,),
            ).fetchone()

            feature_vector: SessionFeatureVector | None = None
            if fv_row:
                feature_vector = SessionFeatureVector(
                    session_id=fv_row["session_id"],
                    session_index=fv_row["session_index"],
                    timestamp_iso=fv_row["timestamp_iso"],
                    has_audio=bool(fv_row["has_audio"]),
                    has_visual=bool(fv_row["has_visual"]),
                    words_per_minute=fv_row["words_per_minute"],
                    articulation_rate_wpm=fv_row["articulation_rate_wpm"],
                    filler_words_ratio=fv_row["filler_words_ratio"],
                    average_pause_duration_seconds=fv_row["average_pause_duration_seconds"],
                    pause_frequency_per_minute=fv_row["pause_frequency_per_minute"],
                    centered_gaze_ratio=fv_row["centered_gaze_ratio"],
                    head_stability_score=fv_row["head_stability_score"],
                    hand_gestures_per_minute=fv_row["hand_gestures_per_minute"],
                )
            elif has_audio or has_visual:
                # Re-extract if vector missing
                feature_vector = extract_session_feature_vector(
                    session_id=session_id,
                    session_index=0,
                    timestamp_iso=sess_row["created_at"],
                    audio_metrics=audio_metrics,
                    visual_metrics=visual_metrics,
                )

            return SessionDetailResponse(
                session_id=sess_row["session_id"],
                title=sess_row["title"],
                notes=sess_row["notes"],
                created_at=sess_row["created_at"],
                duration_seconds=sess_row["duration_seconds"],
                language=sess_row["language"],
                has_audio=has_audio,
                has_visual=has_visual,
                transcript=transcript,
                audio_metrics=audio_metrics,
                audio_segments=audio_segments,
                audio_words=audio_words,
                visual_metrics=visual_metrics,
                feature_vector=feature_vector,
            )

    def list_sessions(
        self,
        limit: int = 50,
        offset: int = 0,
        order: str = "desc",
    ) -> tuple[list[SessionSummary], int]:
        """List historical practice sessions with summaries, ordering, and pagination."""
        safe_order = "ASC" if order.lower() == "asc" else "DESC"

        with self.db.connection() as conn:
            total_count_row = conn.execute("SELECT COUNT(*) AS total FROM sessions").fetchone()
            total_count = total_count_row["total"] if total_count_row else 0

            query = f"""
                SELECT
                    s.session_id,
                    s.title,
                    s.notes,
                    s.created_at,
                    s.duration_seconds,
                    s.language,
                    (CASE WHEN a.session_id IS NOT NULL THEN 1 ELSE 0 END) AS has_audio,
                    (CASE WHEN v.session_id IS NOT NULL THEN 1 ELSE 0 END) AS has_visual,
                    (CASE
                        WHEN a.session_id IS NOT NULL AND a.has_metrics = 1
                        THEN a.words_per_minute ELSE NULL
                    END) AS words_per_minute,
                    (CASE
                        WHEN a.session_id IS NOT NULL AND a.has_metrics = 1
                        THEN a.filler_words_count ELSE NULL
                    END) AS filler_words_count,
                    (CASE
                        WHEN a.session_id IS NOT NULL AND a.has_metrics = 1
                        THEN a.filler_words_ratio ELSE NULL
                    END) AS filler_words_ratio,
                    a.transcript,
                    v.centered_gaze_ratio,
                    v.head_stability_score,
                    v.hand_gestures_per_minute
                FROM sessions s
                LEFT JOIN audio_metrics a ON s.session_id = a.session_id
                LEFT JOIN visual_metrics v ON s.session_id = v.session_id
                ORDER BY s.created_at {safe_order}, s.session_id {safe_order}
                LIMIT ? OFFSET ?
            """
            rows = conn.execute(query, (limit, offset)).fetchall()

            summaries: list[SessionSummary] = []
            for row in rows:
                transcript_text = row["transcript"]
                snippet: str | None = None
                if transcript_text:
                    stripped = transcript_text.strip()
                    if len(stripped) > 100:
                        snippet = stripped[:97] + "..."
                    else:
                        snippet = stripped

                summaries.append(
                    SessionSummary(
                        session_id=row["session_id"],
                        title=row["title"],
                        notes=row["notes"],
                        created_at=row["created_at"],
                        duration_seconds=row["duration_seconds"],
                        language=row["language"],
                        has_audio=bool(row["has_audio"]),
                        has_visual=bool(row["has_visual"]),
                        words_per_minute=row["words_per_minute"],
                        filler_words_count=row["filler_words_count"],
                        filler_words_ratio=row["filler_words_ratio"],
                        centered_gaze_ratio=row["centered_gaze_ratio"],
                        head_stability_score=row["head_stability_score"],
                        hand_gestures_per_minute=row["hand_gestures_per_minute"],
                        transcript_snippet=snippet,
                    )
                )

            return summaries, total_count

    def delete_session(self, session_id: str) -> bool:
        """Permanently delete a session and all its associated metrics.

        Foreign keys automatically cascade deletion across audio, visual,
        and feature vector tables. Returns True if deleted, False if not found.
        """
        with self.db.connection() as conn:
            cursor = conn.execute(
                "DELETE FROM sessions WHERE session_id = ?",
                (session_id,),
            )
            return cursor.rowcount > 0

    def get_all_feature_vectors(self, order: str = "asc") -> list[SessionFeatureVector]:
        """Fetch chronological session feature vectors for analytics processing."""
        safe_order = "DESC" if order.lower() == "desc" else "ASC"
        with self.db.connection() as conn:
            query = f"""
                SELECT
                    fv.session_id,
                    s.created_at,
                    fv.has_audio,
                    fv.has_visual,
                    fv.words_per_minute,
                    fv.articulation_rate_wpm,
                    fv.filler_words_ratio,
                    fv.average_pause_duration_seconds,
                    fv.pause_frequency_per_minute,
                    fv.centered_gaze_ratio,
                    fv.head_stability_score,
                    fv.hand_gestures_per_minute
                FROM sessions s
                JOIN session_feature_vectors fv ON s.session_id = fv.session_id
                ORDER BY s.created_at {safe_order}, s.session_id {safe_order}
            """
            rows = conn.execute(query).fetchall()

            total_count = len(rows)
            vectors: list[SessionFeatureVector] = []
            for idx, row in enumerate(rows):
                chronological_index = idx if safe_order == "ASC" else (total_count - 1 - idx)
                vectors.append(
                    SessionFeatureVector(
                        session_id=row["session_id"],
                        session_index=chronological_index,
                        timestamp_iso=row["created_at"],
                        has_audio=bool(row["has_audio"]),
                        has_visual=bool(row["has_visual"]),
                        words_per_minute=row["words_per_minute"],
                        articulation_rate_wpm=row["articulation_rate_wpm"],
                        filler_words_ratio=row["filler_words_ratio"],
                        average_pause_duration_seconds=row["average_pause_duration_seconds"],
                        pause_frequency_per_minute=row["pause_frequency_per_minute"],
                        centered_gaze_ratio=row["centered_gaze_ratio"],
                        head_stability_score=row["head_stability_score"],
                        hand_gestures_per_minute=row["hand_gestures_per_minute"],
                    )
                )
            return vectors

    def compute_analytics_summary(self) -> AnalyticsDashboardResponse:
        """Compute PCA projections, clusters, and longitudinal trends directly from database."""
        vectors = self.get_all_feature_vectors(order="asc")
        pca_result, clusters = compute_pca_and_clustering(vectors)
        trends = compute_delivery_trends(vectors)

        return AnalyticsDashboardResponse(
            total_sessions_analyzed=len(vectors),
            pca=pca_result,
            clusters=clusters,
            trends=trends,
        )
