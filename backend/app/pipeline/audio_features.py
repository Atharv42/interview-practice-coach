"""Deterministic acoustic and lexical feature calculations for interview practice.

Calculates:
- Speaking pace (Words Per Minute / WPM)
- Articulation rate (pace excluding pauses)
- Filler-word frequencies and ratios using a configurable lexicon
- Pauses, pause counts, pause durations, and intervals using timestamp gaps

All formulas are deterministic and decoupled from transcription engines.
"""

from __future__ import annotations

import re
import string

from app.models.audio import AudioMetrics, PauseDetail, WordTimestamp

DEFAULT_FILLER_LEXICON: set[str] = {
    "um",
    "uh",
    "er",
    "ah",
    "like",
    "you know",
    "i mean",
    "so",
    "actually",
    "basically",
    "right",
    "sort of",
    "kind of",
    "honestly",
    "literally",
}

DEFAULT_PAUSE_THRESHOLD_SECONDS = 0.5


def clean_token(token: str) -> str:
    """Normalize a token by converting to lowercase and stripping punctuation."""
    cleaned = token.lower().strip()
    cleaned = cleaned.strip(string.punctuation)
    # Remove any internal extra whitespace
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def detect_filler_words(
    words: list[WordTimestamp],
    lexicon: set[str] | None = None,
) -> tuple[int, dict[str, int], float]:
    """Detect filler words and multi-word phrases from tokenized timestamps.

    Args:
        words: List of WordTimestamp objects.
        lexicon: Set of lowercase filler tokens and multi-word phrases.

    Returns:
        Tuple of (total_filler_count, filler_breakdown_dict, filler_ratio).
    """
    if not words:
        return 0, {}, 0.0

    active_lexicon = {k.lower() for k in (lexicon or DEFAULT_FILLER_LEXICON)}
    single_word_fillers = {item for item in active_lexicon if " " not in item}
    multi_word_fillers = {item for item in active_lexicon if " " in item}

    tokens = [clean_token(w.word) for w in words]
    total_words = len([t for t in tokens if t])
    if total_words == 0:
        return 0, {}, 0.0

    counts: dict[str, int] = {}
    matched_indices: set[int] = set()

    # 1. Match multi-word phrases first (e.g. 2-gram or 3-gram)
    for phrase in sorted(multi_word_fillers, key=lambda p: len(p.split()), reverse=True):
        phrase_parts = phrase.split()
        phrase_len = len(phrase_parts)
        for i in range(len(tokens) - phrase_len + 1):
            if any(idx in matched_indices for idx in range(i, i + phrase_len)):
                continue
            window = tokens[i : i + phrase_len]
            if window == phrase_parts:
                counts[phrase] = counts.get(phrase, 0) + 1
                for idx in range(i, i + phrase_len):
                    matched_indices.add(idx)

    # 2. Match single-word fillers
    for i, token in enumerate(tokens):
        if i in matched_indices or not token:
            continue
        if token in single_word_fillers:
            counts[token] = counts.get(token, 0) + 1
            matched_indices.add(i)

    total_fillers = sum(counts.values())
    ratio = round(min(1.0, total_fillers / total_words), 4)

    return total_fillers, counts, ratio


def detect_pauses(
    words: list[WordTimestamp],
    total_audio_duration: float,
    pause_threshold_seconds: float = DEFAULT_PAUSE_THRESHOLD_SECONDS,
) -> tuple[list[PauseDetail], float]:
    """Detect pauses from gaps between consecutive word timestamps and boundaries.

    Args:
        words: Ordered list of WordTimestamp objects.
        total_audio_duration: Total audio duration in seconds.
        pause_threshold_seconds: Minimum gap duration in seconds to qualify as a pause.

    Returns:
        Tuple of (list_of_pauses, total_pause_duration_seconds).
    """
    if not words:
        if total_audio_duration >= pause_threshold_seconds:
            pause = PauseDetail(
                start=0.0,
                end=round(total_audio_duration, 3),
                duration=round(total_audio_duration, 3),
                preceding_word=None,
                following_word=None,
            )
            return [pause], round(total_audio_duration, 3)
        return [], 0.0

    pauses: list[PauseDetail] = []
    threshold = max(0.1, pause_threshold_seconds)

    # Initial silence (start of recording to first spoken word)
    if words[0].start >= threshold:
        p_dur = round(words[0].start, 3)
        pauses.append(
            PauseDetail(
                start=0.0,
                end=round(words[0].start, 3),
                duration=p_dur,
                preceding_word=None,
                following_word=clean_token(words[0].word),
            )
        )

    # Gaps between consecutive words
    for i in range(len(words) - 1):
        curr_word = words[i]
        next_word = words[i + 1]
        gap = next_word.start - curr_word.end
        if gap >= threshold:
            p_dur = round(gap, 3)
            pauses.append(
                PauseDetail(
                    start=round(curr_word.end, 3),
                    end=round(next_word.start, 3),
                    duration=p_dur,
                    preceding_word=clean_token(curr_word.word),
                    following_word=clean_token(next_word.word),
                )
            )

    # Trailing silence (last spoken word to end of recording)
    last_end = words[-1].end
    if total_audio_duration > last_end:
        trailing_gap = total_audio_duration - last_end
        if trailing_gap >= threshold:
            p_dur = round(trailing_gap, 3)
            pauses.append(
                PauseDetail(
                    start=round(last_end, 3),
                    end=round(total_audio_duration, 3),
                    duration=p_dur,
                    preceding_word=clean_token(words[-1].word),
                    following_word=None,
                )
            )

    total_pause_duration = round(sum(p.duration for p in pauses), 3)
    return pauses, total_pause_duration


def compute_audio_metrics(
    words: list[WordTimestamp],
    total_audio_duration: float | None = None,
    pause_threshold_seconds: float = DEFAULT_PAUSE_THRESHOLD_SECONDS,
    lexicon: set[str] | None = None,
) -> AudioMetrics:
    """Compute consolidated acoustic and lexical delivery metrics.

    Formulas:
    - total_duration = total_audio_duration or max(word.end)
    - total_words = count of non-empty words
    - WPM = (total_words / total_duration_seconds) * 60.0
    - speaking_duration = max(0.0, total_duration - total_pause_duration)
    - articulation_rate_wpm = (total_words / speaking_duration_seconds) * 60.0
    - filler_words_ratio = filler_words_count / total_words

    Args:
        words: List of WordTimestamp objects.
        total_audio_duration: Total audio duration in seconds.
        pause_threshold_seconds: Threshold for pause detection (seconds).
        lexicon: Optional custom set of filler words.

    Returns:
        Populated AudioMetrics object.
    """
    valid_words = [w for w in words if clean_token(w.word)]
    total_words = len(valid_words)

    # Derive total audio duration
    if total_audio_duration is not None and total_audio_duration > 0.0:
        duration = float(total_audio_duration)
    elif valid_words:
        duration = float(max(w.end for w in valid_words))
    else:
        duration = 0.0

    duration = round(duration, 3)

    # Detect pauses
    pauses, total_pause_duration = detect_pauses(
        valid_words,
        total_audio_duration=duration,
        pause_threshold_seconds=pause_threshold_seconds,
    )
    pause_count = len(pauses)
    avg_pause = round(total_pause_duration / pause_count, 3) if pause_count > 0 else 0.0
    longest_pause = round(max((p.duration for p in pauses), default=0.0), 3)

    # Speaking duration (total duration minus pauses)
    speaking_duration = round(max(0.0, duration - total_pause_duration), 3)

    # Words per minute (overall pace)
    if duration > 0.0:
        wpm = round((total_words / (duration / 60.0)), 2)
    else:
        wpm = 0.0

    # Articulation rate (pace during active speech only)
    if speaking_duration > 0.0:
        articulation_wpm = round((total_words / (speaking_duration / 60.0)), 2)
    else:
        articulation_wpm = 0.0

    # Filler words
    filler_count, filler_breakdown, filler_ratio = detect_filler_words(valid_words, lexicon=lexicon)

    return AudioMetrics(
        total_duration_seconds=duration,
        speaking_duration_seconds=speaking_duration,
        total_words=total_words,
        words_per_minute=wpm,
        articulation_rate_wpm=articulation_wpm,
        filler_words_count=filler_count,
        filler_words_ratio=filler_ratio,
        filler_words_breakdown=filler_breakdown,
        pause_count=pause_count,
        total_pause_duration_seconds=total_pause_duration,
        average_pause_duration_seconds=avg_pause,
        longest_pause_duration_seconds=longest_pause,
        pause_threshold_seconds=pause_threshold_seconds,
        pauses=pauses,
    )
