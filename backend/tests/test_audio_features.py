"""Unit tests for deterministic audio metrics, pace, filler words, and pauses."""

from app.models.audio import WordTimestamp
from app.pipeline.audio_features import (
    clean_token,
    compute_audio_metrics,
    detect_filler_words,
    detect_pauses,
)


def test_clean_token():
    assert clean_token("Hello,") == "hello"
    assert clean_token("  ...like!  ") == "like"
    assert clean_token("Um?") == "um"
    assert clean_token("YOU KNOW") == "you know"


def test_empty_words_metrics():
    metrics = compute_audio_metrics(words=[], total_audio_duration=0.0)
    assert metrics.total_words == 0
    assert metrics.words_per_minute == 0.0
    assert metrics.articulation_rate_wpm == 0.0
    assert metrics.filler_words_count == 0
    assert metrics.filler_words_ratio == 0.0
    assert metrics.pause_count == 0
    assert metrics.total_pause_duration_seconds == 0.0


def test_words_per_minute_calculation():
    # 25 words spoken evenly across 10 seconds -> 25 / (10/60) = 150 WPM
    words = []
    current_time = 0.0
    for i in range(25):
        words.append(
            WordTimestamp(
                word=f"word{i}",
                start=round(current_time, 2),
                end=round(current_time + 0.3, 2),
            )
        )
        current_time += 0.4  # 0.1s gap (less than default pause threshold 0.5s)

    metrics = compute_audio_metrics(words=words, total_audio_duration=10.0)
    assert metrics.total_words == 25
    assert metrics.words_per_minute == 150.0
    assert metrics.pause_count == 0
    assert metrics.filler_words_count == 0


def test_filler_words_single_and_multiword():
    words = [
        WordTimestamp(word="Um,", start=0.0, end=0.4),
        WordTimestamp(word="I", start=0.5, end=0.7),
        WordTimestamp(word="wanted", start=0.75, end=1.0),
        WordTimestamp(word="to", start=1.05, end=1.2),
        WordTimestamp(word="say,", start=1.25, end=1.5),
        WordTimestamp(word="like,", start=1.6, end=1.8),
        WordTimestamp(word="you", start=1.9, end=2.1),
        WordTimestamp(word="know,", start=2.15, end=2.3),
        WordTimestamp(word="it", start=2.4, end=2.6),
        WordTimestamp(word="was", start=2.65, end=2.8),
        WordTimestamp(word="actually", start=2.85, end=3.2),
        WordTimestamp(word="good.", start=3.3, end=3.6),
    ]

    total_fillers, counts, ratio = detect_filler_words(words)
    # Expected fillers: 'um' (1), 'like' (1), 'you know' (1), 'actually' (1) -> 4 fillers
    assert total_fillers == 4
    assert counts.get("um") == 1
    assert counts.get("like") == 1
    assert counts.get("you know") == 1
    assert counts.get("actually") == 1
    assert ratio == round(4 / 12, 4)


def test_pause_detection_and_threshold():
    words = [
        # Spoken at 1.0 to 1.5 -> initial silence is 1.0s (>= 0.5s threshold)
        WordTimestamp(word="First", start=1.0, end=1.5),
        # Gap of 0.8s between 1.5 and 2.3 -> pause of 0.8s
        WordTimestamp(word="second", start=2.3, end=2.8),
        # Gap of 0.2s between 2.8 and 3.0 -> NOT a pause (< 0.5s threshold)
        WordTimestamp(word="third", start=3.0, end=3.5),
        # Gap of 1.5s between 3.5 and 5.0 -> pause of 1.5s
        WordTimestamp(word="fourth", start=5.0, end=5.5),
    ]
    # Total audio duration is 6.5s -> trailing silence is 1.0s (>= 0.5s threshold)
    pauses, total_pause_dur = detect_pauses(
        words, total_audio_duration=6.5, pause_threshold_seconds=0.5
    )

    # Pauses: initial (1.0s), gap1 (0.8s), gap2 (1.5s), trailing (1.0s) -> 4 pauses
    assert len(pauses) == 4
    assert total_pause_dur == round(1.0 + 0.8 + 1.5 + 1.0, 3)

    metrics = compute_audio_metrics(
        words=words, total_audio_duration=6.5, pause_threshold_seconds=0.5
    )
    assert metrics.pause_count == 4
    assert metrics.total_pause_duration_seconds == total_pause_dur
    assert metrics.speaking_duration_seconds == round(6.5 - total_pause_dur, 3)
    assert metrics.longest_pause_duration_seconds == 1.5


def test_articulation_rate_vs_wpm():
    # 10 words in 10 seconds total:
    # 5 seconds speech, 5 seconds pauses
    words = [
        WordTimestamp(word="Word", start=0.0, end=0.5),
        WordTimestamp(word="Word", start=5.5, end=6.0),  # 5.0s pause in between
    ]
    metrics = compute_audio_metrics(words=words, total_audio_duration=6.0)
    # Total duration = 6.0s (0.1 min) -> WPM = 2 / 0.1 = 20 WPM
    # Speaking duration = 6.0 - 5.0 = 1.0s (0.01667 min) -> Articulation rate = 2 / (1/60) = 120 WPM
    assert metrics.words_per_minute == 20.0
    assert metrics.articulation_rate_wpm == 120.0
