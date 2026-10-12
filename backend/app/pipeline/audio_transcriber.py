"""Audio transcription service powered by faster-whisper.

Provides lazy model initialization, word-level timestamp alignment,
and robust handling of silence and corrupt files.
"""

from __future__ import annotations

import logging
import os
import threading

from app.models.audio import AudioSegment, WordTimestamp

logger = logging.getLogger(__name__)

# Default model configuration for fast local CPU inference
DEFAULT_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "tiny")
DEFAULT_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
DEFAULT_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")


class AudioTranscriber:
    """Thread-safe, lazily initialized transcription service using faster-whisper."""

    _instance: AudioTranscriber | None = None
    _lock = threading.Lock()

    def __init__(
        self,
        model_size: str = DEFAULT_MODEL_SIZE,
        device: str = DEFAULT_DEVICE,
        compute_type: str = DEFAULT_COMPUTE_TYPE,
    ) -> None:
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._model = None
        self._model_init_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> AudioTranscriber:
        """Singleton accessor to prevent loading multiple model instances into memory."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def _get_model(self):
        """Lazily initialize the faster-whisper model on first actual transcription request."""
        if self._model is None:
            with self._model_init_lock:
                if self._model is None:
                    from faster_whisper import WhisperModel

                    logger.info(
                        "Loading faster-whisper model (size: %s, device: %s, compute_type: %s)...",
                        self.model_size,
                        self.device,
                        self.compute_type,
                    )
                    self._model = WhisperModel(
                        self.model_size,
                        device=self.device,
                        compute_type=self.compute_type,
                    )
                    logger.info("faster-whisper model loaded successfully.")
        return self._model

    def transcribe(
        self,
        audio_path: str,
        language: str | None = "en",
    ) -> tuple[str, str, float, list[AudioSegment], list[WordTimestamp]]:
        """Transcribe an audio file and extract word-level timestamps.

        Args:
            audio_path: Local path to audio file on disk.
            language: Target language code or None for auto-detection.

        Returns:
            Tuple of (full_transcript, detected_language, language_probability, segments, words).

        Raises:
            RuntimeError: If transcription fails or audio cannot be decoded.
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        model = self._get_model()

        try:
            segments_generator, info = model.transcribe(
                audio_path,
                beam_size=5,
                language=language,
                word_timestamps=True,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=500),
            )

            all_segments: list[AudioSegment] = []
            all_words: list[WordTimestamp] = []
            transcript_parts: list[str] = []

            for seg in segments_generator:
                text_clean = seg.text.strip()
                if text_clean:
                    transcript_parts.append(text_clean)

                seg_words: list[WordTimestamp] = []
                if hasattr(seg, "words") and seg.words:
                    for w in seg.words:
                        word_clean = w.word.strip()
                        if word_clean:
                            word_obj = WordTimestamp(
                                word=word_clean,
                                start=round(float(w.start), 3),
                                end=round(float(w.end), 3),
                                probability=round(float(getattr(w, "probability", 1.0)), 4),
                            )
                            seg_words.append(word_obj)
                            all_words.append(word_obj)

                all_segments.append(
                    AudioSegment(
                        id=seg.id,
                        start=round(float(seg.start), 3),
                        end=round(float(seg.end), 3),
                        text=text_clean,
                        words=seg_words,
                    )
                )

            full_transcript = " ".join(transcript_parts)
            detected_lang = info.language or "en"
            lang_prob = round(float(info.language_probability or 1.0), 4)

            return full_transcript, detected_lang, lang_prob, all_segments, all_words

        except Exception as e:
            logger.error("Whisper transcription failed for %s: %s", audio_path, str(e))
            raise RuntimeError(f"Transcription processing failed: {e}") from e
