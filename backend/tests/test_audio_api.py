"""Integration and API tests for the audio processing pipeline endpoints."""

import io

from fastapi.testclient import TestClient

from app.api.audio import get_transcriber
from app.main import app
from app.models.audio import AudioSegment, WordTimestamp

client = TestClient(app)


class MockTranscriber:
    """Mock transcriber to test audio pipeline quickly and deterministically."""

    def transcribe(self, audio_path: str, language: str = "en"):
        words = [
            WordTimestamp(word="Um,", start=0.2, end=0.6, probability=0.95),
            WordTimestamp(word="I", start=0.7, end=0.9, probability=0.99),
            WordTimestamp(word="am", start=1.0, end=1.2, probability=0.99),
            WordTimestamp(word="ready", start=1.3, end=1.8, probability=0.98),
            WordTimestamp(word="for", start=1.9, end=2.1, probability=0.99),
            WordTimestamp(word="the", start=2.2, end=2.4, probability=0.99),
            WordTimestamp(word="interview.", start=2.5, end=3.2, probability=0.97),
        ]
        segments = [
            AudioSegment(
                id=0,
                start=0.2,
                end=3.2,
                text="Um, I am ready for the interview.",
                words=words,
            )
        ]
        return "Um, I am ready for the interview.", "en", 0.99, segments, words


class FailingTranscriber:
    """Transcriber simulator that raises an internal processing error."""

    def transcribe(self, audio_path: str, language: str = "en"):
        raise RuntimeError("Corrupted audio data encountered during decoding")


def test_reject_unsupported_file_extension():
    fake_file = io.BytesIO(b"Hello world, this is a plain text file, not audio.")
    response = client.post(
        "/api/v1/audio/analyze",
        files={"file": ("notes.txt", fake_file, "text/plain")},
    )
    assert response.status_code == 400
    data = response.json()
    assert "Unsupported file format" in data["detail"]


def test_reject_empty_audio_file():
    empty_file = io.BytesIO(b"")
    response = client.post(
        "/api/v1/audio/analyze",
        files={"file": ("empty.wav", empty_file, "audio/wav")},
    )
    assert response.status_code == 400
    data = response.json()
    assert "empty or corrupted" in data["detail"]


def test_successful_audio_analysis_with_mock():
    app.dependency_overrides[get_transcriber] = lambda: MockTranscriber()

    try:
        # Create minimal valid WAV header + dummy bytes (> 100 bytes)
        wav_header = b"RIFF" + (144).to_bytes(4, "little") + b"WAVEfmt "
        dummy_data = wav_header + b"\x00" * 150
        audio_stream = io.BytesIO(dummy_data)

        response = client.post(
            "/api/v1/audio/analyze",
            files={"file": ("practice.wav", audio_stream, "audio/wav")},
            data={"pause_threshold": 0.5, "language": "en"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["filename"] == "practice.wav"
        assert data["transcript"] == "Um, I am ready for the interview."
        assert data["language"] == "en"
        assert len(data["segments"]) == 1
        assert len(data["words"]) == 7

        metrics = data["metrics"]
        assert metrics["total_words"] == 7
        assert metrics["filler_words_count"] == 1
        assert "um" in metrics["filler_words_breakdown"]
        assert metrics["filler_words_breakdown"]["um"] == 1
        assert metrics["words_per_minute"] > 0
        assert metrics["total_duration_seconds"] == 3.2

    finally:
        app.dependency_overrides.pop(get_transcriber, None)


def test_transcription_failure_handling():
    app.dependency_overrides[get_transcriber] = lambda: FailingTranscriber()

    try:
        dummy_wav = b"RIFF" + (144).to_bytes(4, "little") + b"WAVE" + (b"\x00" * 150)
        response = client.post(
            "/api/v1/audio/analyze",
            files={"file": ("broken.wav", io.BytesIO(dummy_wav), "audio/wav")},
        )
        assert response.status_code == 500
        data = response.json()
        assert "An error occurred while processing audio recording" in data["detail"]
    finally:
        app.dependency_overrides.pop(get_transcriber, None)
