"""API endpoints for audio upload, transcription, and delivery metric analysis."""

import os
import tempfile

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.models.audio import AudioAnalysisResponse
from app.pipeline.audio_features import (
    DEFAULT_PAUSE_THRESHOLD_SECONDS,
    compute_audio_metrics,
)
from app.pipeline.audio_transcriber import AudioTranscriber
from app.pipeline.audio_validator import save_and_validate_upload

router = APIRouter(prefix="/audio", tags=["Audio Pipeline"])


def get_transcriber() -> AudioTranscriber:
    """Dependency provider for transcription service."""
    return AudioTranscriber.get_instance()


@router.post(
    "/analyze",
    response_model=AudioAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Transcribe practice audio and extract delivery metrics",
    description=(
        "Upload a supported audio file (.wav, .mp3, .m4a, .ogg, .webm, .flac). "
        "Transcribes speech using faster-whisper and computes objective delivery mechanics "
        "including speaking pace (WPM), pause frequency and duration, and filler word counts."
    ),
)
async def analyze_audio(
    file: UploadFile = File(..., description="Audio recording file"),
    pause_threshold: float = Form(
        default=DEFAULT_PAUSE_THRESHOLD_SECONDS,
        ge=0.1,
        le=5.0,
        description="Minimum duration in seconds to consider a pause (default 0.5s)",
    ),
    language: str | None = Form(
        default="en",
        description="Audio language code (e.g. 'en') or leave blank for auto-detect",
    ),
    transcriber: AudioTranscriber = Depends(get_transcriber),
) -> AudioAnalysisResponse:
    """Handle audio upload, stream to safe temp storage, transcribe, and compute metrics."""
    temp_dir = tempfile.gettempdir()
    temp_file_path: str | None = None

    try:
        # 1. Validate file format and size, then stream to temporary file
        temp_file_path, _ = await save_and_validate_upload(file, temp_dir)

        # 2. Run transcription with word timestamps
        transcript, detected_lang, lang_prob, segments, words = transcriber.transcribe(
            temp_file_path,
            language=language if language else None,
        )

        # 3. Derive total audio duration from segments or word timestamps
        total_duration = 0.0
        if segments:
            total_duration = max(seg.end for seg in segments)
        elif words:
            total_duration = max(w.end for w in words)

        # 4. Compute deterministic delivery metrics
        metrics = compute_audio_metrics(
            words=words,
            total_audio_duration=total_duration,
            pause_threshold_seconds=pause_threshold,
        )

        return AudioAnalysisResponse(
            filename=file.filename or "recording",
            transcript=transcript,
            language=detected_lang,
            language_probability=lang_prob,
            metrics=metrics,
            segments=segments,
            words=words,
        )

    except HTTPException:
        # Re-raise known HTTP exceptions (e.g. format validation, file size)
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while processing audio recording: {e}",
        ) from e

    finally:
        # Always remove temporary file from disk
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except OSError:
                pass
