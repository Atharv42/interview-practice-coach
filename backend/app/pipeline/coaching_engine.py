"""AI Coaching engine evaluating STAR, content clarity, and delivery advice."""

import re

from app.models.audio import AudioMetrics
from app.models.coaching import (
    CoachingEvaluationResponse,
    ContentClarityScore,
    DeliveryCoachingAdvice,
    STARFrameworkAnalysis,
)
from app.models.visual import VisualMetrics

# Common STAR method indicator phrases
SITUATION_PATTERNS = [
    r"\bwhen i was\b",
    r"\bat my previous\b",
    r"\bin my (last|previous|recent) (role|company|job|team)\b",
    r"\bduring (a|my|the) project\b",
    r"\bwe were facing\b",
    r"\bthe team was\b",
    r"\bour company needed\b",
    r"\bthe context was\b",
    r"\bwe had (a|an) (issue|problem|challenge)\b",
    r"\bin one instance\b",
    r"\ba client (needed|approached|requested)\b",
]

TASK_PATTERNS = [
    r"\bmy (task|role|responsibility|goal|objective) was\b",
    r"\bi was tasked with\b",
    r"\bi was responsible for\b",
    r"\bwe needed to\b",
    r"\bthe goal was to\b",
    r"\bi had to (ensure|deliver|design|fix|manage)\b",
    r"\bour challenge was to\b",
    r"\bthe target was\b",
]

ACTION_PATTERNS = [
    r"\bi (implemented|built|created|developed|designed|led|refactored|organized|diagnosed)\b",
    r"\bi decided to\b",
    r"\bi proposed\b",
    r"\bi started by\b",
    r"\bi collaborated with\b",
    r"\bi established\b",
    r"\bi investigated\b",
    r"\bi took initiative to\b",
    r"\bwhat i did was\b",
    r"\bi gathered the team\b",
]

RESULT_PATTERNS = [
    r"\bas a result\b",
    r"\bresulting in\b",
    r"\bthe outcome was\b",
    r"\bwe achieved\b",
    r"\bsuccessfully (delivered|launched|resolved|completed)\b",
    r"\b(improved|increased|reduced|saved) (by|over)\b",
    r"\b\d+%\b",
    r"\bthe client was (satisfied|happy|impressed)\b",
    r"\bin the end\b",
    r"\bwe met our (deadline|goal|target)\b",
]


def _match_pattern_and_extract_snippet(text: str, patterns: list[str]) -> tuple[bool, str | None]:
    """Find the first matching pattern in text and extract a contextual sentence snippet."""
    sentences = re.split(r"[.!?]+", text)
    for pattern in patterns:
        for s in sentences:
            cleaned = s.strip()
            if cleaned and re.search(pattern, cleaned, re.IGNORECASE):
                # Trim snippet if needed
                snippet = cleaned if len(cleaned) <= 120 else cleaned[:117] + "..."
                return True, snippet
    return False, None


def evaluate_star_framework(transcript: str) -> STARFrameworkAnalysis:
    """Evaluate response structure against the Situation, Task, Action, Result framework."""
    if not transcript or len(transcript.strip().split()) < 10:
        return STARFrameworkAnalysis(
            situation_detected=False,
            situation_snippet=None,
            task_detected=False,
            task_snippet=None,
            action_detected=False,
            action_snippet=None,
            result_detected=False,
            result_snippet=None,
            overall_star_score=15.0,
            star_summary=(
                "Answer was very brief. To structure compelling behavioral answers, use STAR: "
                "set the Situation, state your Task, describe your Action, "
                "and conclude with Result."
            ),
        )

    has_s, snip_s = _match_pattern_and_extract_snippet(transcript, SITUATION_PATTERNS)
    has_t, snip_t = _match_pattern_and_extract_snippet(transcript, TASK_PATTERNS)
    has_a, snip_a = _match_pattern_and_extract_snippet(transcript, ACTION_PATTERNS)
    has_r, snip_r = _match_pattern_and_extract_snippet(transcript, RESULT_PATTERNS)

    detected_count = sum([has_s, has_t, has_a, has_r])
    base_score = detected_count * 25.0

    # Qualitative summary
    missing = []
    if not has_s:
        missing.append("Situation (context)")
    if not has_t:
        missing.append("Task (your responsibility)")
    if not has_a:
        missing.append("Action (specific steps you took)")
    if not has_r:
        missing.append("Result (quantifiable impact or takeaway)")

    if detected_count == 4:
        summary = (
            "Excellent structure! All four STAR components were articulated, giving your answer "
            "a complete narrative arc with clear context, action, and measurable impact."
        )
    elif detected_count >= 2:
        missing_str = ", ".join(missing)
        summary = (
            f"Good progress on structure, but consider explicitly articulating {missing_str} "
            "to give interviewers the complete picture."
        )
    else:
        summary = (
            "Your answer is currently missing formal STAR structure. Lead with the context, "
            "clarify your specific task, detail your personal actions, and emphasize the outcome."
        )

    return STARFrameworkAnalysis(
        situation_detected=has_s,
        situation_snippet=snip_s,
        task_detected=has_t,
        task_snippet=snip_t,
        action_detected=has_a,
        action_snippet=snip_a,
        result_detected=has_r,
        result_snippet=snip_r,
        overall_star_score=base_score,
        star_summary=summary,
    )


def evaluate_content_clarity(
    transcript: str, audio_metrics: AudioMetrics | None = None
) -> ContentClarityScore:
    """Evaluate clarity, word economy, and verbal precision."""
    words = [w for w in re.split(r"\s+", transcript.strip()) if w]
    word_count = len(words)

    if word_count == 0:
        return ContentClarityScore(
            score=20,
            word_count=0,
            conciseness_rating="Too Brief",
            filler_density_percent=0.0,
            observations=["No speech was detected to evaluate."],
        )

    # Filler density
    if audio_metrics is not None and audio_metrics.total_words > 0:
        filler_pct = round(audio_metrics.filler_words_ratio * 100, 1)
    else:
        # Heuristic count from text
        filler_tokens = {"um", "uh", "like", "you know", "actually", "basically"}
        count = sum(1 for w in words if w.lower().strip(".,!?") in filler_tokens)
        filler_pct = round((count / max(1, word_count)) * 100, 1)

    # Score calculation
    score = 90
    observations = []

    if filler_pct > 6.0:
        score -= 20
        observations.append(
            f"Filler word density is elevated ({filler_pct}%). "
            "Substituting silent pauses will increase authority."
        )
    elif filler_pct > 3.0:
        score -= 10
        observations.append(f"Moderate filler density ({filler_pct}%). Aim to bring this below 3%.")
    else:
        observations.append(f"Clean verbal delivery with low filler word ratio ({filler_pct}%).")

    # Length and conciseness
    if word_count < 35:
        score -= 25
        rating = "Very Brief"
        observations.append("Answer was too concise; elaborate with concrete examples.")
    elif word_count <= 220:
        rating = "Well-Balanced & Focused"
        observations.append("Optimal response length (1–2 minutes) maintaining listener attention.")
    else:
        score -= 10
        rating = "Extended / Wandering"
        observations.append(
            "Answer is slightly long; tighten your phrasing to stay under 2 minutes."
        )

    clamped_score = max(20, min(100, score))

    return ContentClarityScore(
        score=clamped_score,
        word_count=word_count,
        conciseness_rating=rating,
        filler_density_percent=filler_pct,
        observations=observations,
    )


def generate_delivery_advice(
    audio_metrics: AudioMetrics | None, visual_metrics: VisualMetrics | None
) -> DeliveryCoachingAdvice:
    """Synthesize acoustic and geometric indicators into actionable coaching feedback."""
    # 1. Pacing advice
    if audio_metrics:
        wpm = audio_metrics.words_per_minute
        if wpm > 165.0:
            pacing = (
                f"Your speaking pace was fast ({wpm:.0f} WPM). "
                "Slow down toward 135–155 WPM to ensure "
                "interviewers catch complex technical points."
            )
        elif wpm < 115.0:
            pacing = (
                f"Your pace was deliberate ({wpm:.0f} WPM). "
                "Try picking up the tempo slightly to project energy."
            )
        else:
            pacing = (
                f"Great cadence ({wpm:.0f} WPM)! This falls right into the ideal "
                "conversational interview range (130–160 WPM)."
            )
    else:
        pacing = "Pacing metrics were not recorded for this session."

    # 2. Pause advice
    if audio_metrics:
        longest = audio_metrics.longest_pause_duration_seconds
        avg_pause = audio_metrics.average_pause_duration_seconds
        if longest >= 3.5:
            pause = (
                f"An extended pause of {longest:.1f}s was detected. "
                "If you need time to structure thoughts, "
                "use a smooth verbal bridge like 'Let me break that down into three key aspects.'"
            )
        elif audio_metrics.pause_count <= 1:
            pause = (
                "You had very few pauses. Taking a 1–2 second deliberate pause before critical "
                "conclusions adds gravitas and lets points sink in."
            )
        else:
            pause = (
                f"Healthy pause rhythm (average {avg_pause:.1f}s). "
                "Good balance between active speech and breathing pauses."
            )
    else:
        pause = "Pause distribution not recorded."

    # 3. Filler advice
    if audio_metrics:
        ratio_pct = audio_metrics.filler_words_ratio * 100
        breakdown = audio_metrics.filler_words_breakdown
        top_word = max(breakdown, key=breakdown.get) if breakdown else None
        if top_word and ratio_pct > 3.0:
            filler = (
                f"Your most frequent filler was '{top_word}' ({breakdown[top_word]} occurrences). "
                f"Practice pausing silently whenever you feel the instinct to say '{top_word}'."
            )
        elif ratio_pct <= 3.0:
            filler = "Low filler word count. Your speech was crisp and intentional."
        else:
            filler = "Try substituting silent pauses in place of filler tokens."
    else:
        filler = "Filler breakdown not recorded."

    # 4. Visual advice
    if visual_metrics:
        gaze_pct = visual_metrics.centered_gaze_ratio * 100
        stability = visual_metrics.head_stability_score
        if gaze_pct < 65.0:
            visual = (
                f"Your camera contact was intermittent ({gaze_pct:.0f}% centered). "
                "Position your interview prompt window directly beneath your webcam lens."
            )
        elif stability < 0.70:
            visual = (
                "Frequent head movement observed. "
                "Stabilize your seated posture for a composed desktop presence."
            )
        else:
            visual = (
                f"Strong camera gaze ({gaze_pct:.0f}%) and "
                f"steady head posture ({stability:.2f} score)."
            )
    else:
        visual = "Visual metrics not recorded."

    # Overall summary
    summary = (
        "Maintain this delivery foundation while fine-tuning pace moderation "
        "and STAR structural clarity."
    )

    return DeliveryCoachingAdvice(
        pacing_feedback=pacing,
        pause_feedback=pause,
        filler_feedback=filler,
        visual_feedback=visual,
        overall_delivery_summary=summary,
    )


def generate_polished_excerpt(transcript: str) -> str | None:
    """Generate a clean, high-impact rephrased opening sentence demonstration."""
    if not transcript or len(transcript.split()) < 10:
        return None

    sentences = [s.strip() for s in re.split(r"[.!?]+", transcript) if s.strip()]
    if not sentences:
        return None

    first = sentences[0]
    # Remove filler words
    cleaned = re.sub(
        r"\b(um|uh|like|you know|basically|actually)\b", "", first, flags=re.IGNORECASE
    )
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    if len(cleaned.split()) >= 6:
        # Prepend polished executive framing
        return f'Polished framing: "{cleaned[0].upper() + cleaned[1:]}."'
    return None


def evaluate_coaching(
    transcript: str | None,
    question_prompt: str | None = None,
    session_id: str | None = None,
    audio_metrics: AudioMetrics | None = None,
    visual_metrics: VisualMetrics | None = None,
) -> CoachingEvaluationResponse:
    """Comprehensive evaluation uniting STAR structure, content clarity, and delivery mechanics."""
    text = transcript or ""
    star_analysis = evaluate_star_framework(text)
    clarity = evaluate_content_clarity(text, audio_metrics)
    delivery_advice = generate_delivery_advice(audio_metrics, visual_metrics)
    polished = generate_polished_excerpt(text)

    # Derive Top Strengths
    strengths: list[str] = []
    if star_analysis.action_detected and star_analysis.result_detected:
        strengths.append("Clearly highlighted personal actions and outcomes.")
    if clarity.filler_density_percent <= 3.0:
        strengths.append("High verbal clarity with minimal filler words.")
    if audio_metrics and 125.0 <= audio_metrics.words_per_minute <= 165.0:
        strengths.append(f"Conversational pacing ({audio_metrics.words_per_minute:.0f} WPM).")
    if visual_metrics and visual_metrics.centered_gaze_ratio >= 0.75:
        strengths.append("Consistent eye contact oriented toward the camera cone.")
    if not strengths:
        strengths.append("Addressed the prompt directly with good enthusiasm.")

    # Derive Actionable Improvement Areas
    improvements: list[str] = []
    if not star_analysis.result_detected:
        improvements.append(
            "Quantify the outcome (mention metrics, team impact, or tangible results achieved)."
        )
    if not star_analysis.situation_detected:
        improvements.append(
            "Spend the first 15 seconds establishing the business context "
            "and problem before jumping into action."
        )
    if audio_metrics and audio_metrics.words_per_minute > 165.0:
        improvements.append("Slow speaking pace by ~15 WPM on key technical points.")
    if clarity.filler_density_percent > 4.0:
        improvements.append(
            "Substitute deliberate silent pauses whenever tempted to use filler words."
        )
    if not improvements:
        improvements.append(
            "Practice delivering this answer in under 90 seconds for tighter conciseness."
        )

    return CoachingEvaluationResponse(
        session_id=session_id,
        question_prompt=question_prompt,
        clarity=clarity,
        star_analysis=star_analysis,
        delivery_advice=delivery_advice,
        top_strengths=strengths[:3],
        areas_for_improvement=improvements[:3],
        sample_polished_excerpt=polished,
    )
