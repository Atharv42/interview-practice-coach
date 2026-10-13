"""Curated interview question repository and mock interview track synthesizer."""

from app.models.questions import (
    CategorySummary,
    InterviewQuestion,
    MockTrackDefinition,
)

QUESTION_REGISTRY: list[InterviewQuestion] = [
    # Behavioral
    InterviewQuestion(
        id="beh-intro-background",
        category="behavioral",
        category_label="Behavioral & Background",
        title="Tell me about yourself, your technical background, and a recent highlight.",
        context_hint=(
            "Focus on a crisp 90-second elevator pitch: current focus, key engineering "
            "strengths, and one concrete milestone you recently delivered."
        ),
        target_duration_seconds=90,
        difficulty="junior",
    ),
    InterviewQuestion(
        id="beh-conflict-resolution",
        category="behavioral",
        category_label="Behavioral & STAR",
        title=(
            "Tell me about a time you handled conflict or a strong technical disagreement "
            "with a teammate."
        ),
        context_hint=(
            "Use STAR: Outline the architectural disagreement (Situation), your goal (Task), "
            "how you evaluated objective trade-offs respectfully (Action), and the "
            "positive team alignment outcome (Result)."
        ),
        target_duration_seconds=120,
        difficulty="mid",
    ),
    InterviewQuestion(
        id="beh-ambiguous-ownership",
        category="behavioral",
        category_label="Behavioral & STAR",
        title="Describe a time you took ownership of a project where requirements were vague.",
        context_hint=(
            "Highlight how you proactively clarified scope with stakeholders, broke down "
            "milestones, and de-risked critical path items."
        ),
        target_duration_seconds=120,
        difficulty="senior",
    ),
    InterviewQuestion(
        id="beh-project-failure",
        category="behavioral",
        category_label="Behavioral & STAR",
        title="Tell me about a project that failed or missed its delivery deadline.",
        context_hint=(
            "Demonstrate psychological safety and accountability: analyze root causes, "
            "immediate mitigation, and lasting guardrails instituted."
        ),
        target_duration_seconds=120,
        difficulty="senior",
    ),
    InterviewQuestion(
        id="beh-production-outage",
        category="behavioral",
        category_label="Behavioral & STAR",
        title="Describe the most severe production incident you responded to.",
        context_hint=(
            "Explain your incident triage thought process: customer impact containment, "
            "blameless post-mortem analysis, and architectural hardening."
        ),
        target_duration_seconds=130,
        difficulty="staff",
    ),
    # System Design & Architecture
    InterviewQuestion(
        id="sys-realtime-notifications",
        category="system_design",
        category_label="System Design",
        title="How would you design a real-time notification engine for millions of active users?",
        context_hint=(
            "Address WebSocket connection state management, message fan-out with pub/sub "
            "(Kafka/Redis), push notification throttling, and delivery guarantees."
        ),
        target_duration_seconds=180,
        difficulty="senior",
    ),
    InterviewQuestion(
        id="sys-cache-stampede",
        category="system_design",
        category_label="System Design",
        title=(
            "How do you handle cache stampedes and thundering herd issues in distributed caching?"
        ),
        context_hint=(
            "Discuss probabilistic early expiration (XFetch), mutex locks on cache misses, "
            "background refresh workers, and warm-up strategies."
        ),
        target_duration_seconds=120,
        difficulty="senior",
    ),
    InterviewQuestion(
        id="sys-api-rate-limiter",
        category="system_design",
        category_label="System Design",
        title="Walk me through designing a multi-tier rate limiter for public developer APIs.",
        context_hint=(
            "Compare Token Bucket, Leaky Bucket, and Sliding Window algorithms. "
            "Discuss distributed Redis state synchronization and header contracts."
        ),
        target_duration_seconds=150,
        difficulty="mid",
    ),
    InterviewQuestion(
        id="sys-distributed-transactions",
        category="system_design",
        category_label="System Design",
        title="How do you maintain data consistency across microservices without 2-phase commit?",
        context_hint=(
            "Explain the Saga pattern (choreography vs orchestration), outbox pattern, "
            "idempotency keys, and compensating transactions."
        ),
        target_duration_seconds=160,
        difficulty="staff",
    ),
    InterviewQuestion(
        id="sys-log-aggregation",
        category="system_design",
        category_label="System Design",
        title="Design a telemetry ingestion and log query pipeline processing 100K events/sec.",
        context_hint=(
            "Address backpressure buffering, partition keys, cold vs hot storage tiering, "
            "and query indexing cost trade-offs."
        ),
        target_duration_seconds=150,
        difficulty="senior",
    ),
    # Technical & Problem Solving
    InterviewQuestion(
        id="tech-microservices-vs-monolith",
        category="technical",
        category_label="Technical Depth",
        title="When would you choose a modular monolith over microservices, and vice versa?",
        context_hint=(
            "Avoid dogmatism: contrast deployment independence against network latency, "
            "operational overhead, debugging complexity, and organization team boundaries."
        ),
        target_duration_seconds=120,
        difficulty="mid",
    ),
    InterviewQuestion(
        id="tech-diagnose-memory-leak",
        category="technical",
        category_label="Technical Depth",
        title="How do you systematically troubleshoot memory leaks and CPU spikes in production?",
        context_hint=(
            "Walk through APM telemetry, heap dumps, flame graphs, thread contention analysis, "
            "and reproducing issues in staging."
        ),
        target_duration_seconds=130,
        difficulty="senior",
    ),
    InterviewQuestion(
        id="tech-db-indexing-strategies",
        category="technical",
        category_label="Technical Depth",
        title="Explain B-tree vs LSM-tree indexing trade-offs for write-heavy database workloads.",
        context_hint=(
            "Discuss read amplification vs write amplification, sequential disk I/O, "
            "compaction costs, and bloom filter lookups."
        ),
        target_duration_seconds=120,
        difficulty="staff",
    ),
    InterviewQuestion(
        id="tech-api-idempotency",
        category="technical",
        category_label="Technical Depth",
        title="How do you guarantee idempotency in mission-critical financial or payment APIs?",
        context_hint=(
            "Explain idempotency key validation, atomic lock acquisitions, state machine "
            "transitions, and returning cached responses on retries."
        ),
        target_duration_seconds=120,
        difficulty="mid",
    ),
    InterviewQuestion(
        id="tech-explain-complex-concept",
        category="technical",
        category_label="Technical Depth",
        title="Explain how database connection pooling works to a non-technical manager.",
        context_hint=(
            "Use a compelling real-world analogy (like library borrowing or taxi fleets) "
            "to explain resource overhead and connection exhaustion."
        ),
        target_duration_seconds=100,
        difficulty="junior",
    ),
    # Leadership & Collaboration
    InterviewQuestion(
        id="lead-mentor-junior",
        category="leadership",
        category_label="Leadership & Mentorship",
        title="How do you mentor and accelerate the career growth of junior software engineers?",
        context_hint=(
            "Detail your approach to pair programming, psychological safety in code reviews, "
            "delegating stretch assignments, and constructive feedback loops."
        ),
        target_duration_seconds=120,
        difficulty="mid",
    ),
    InterviewQuestion(
        id="lead-communicating-tech-debt",
        category="leadership",
        category_label="Leadership & Mentorship",
        title=(
            "How do you convince product managers to prioritize technical debt over new features?"
        ),
        context_hint=(
            "Translate technical risk into business velocity: developer friction, incident MTTR, "
            "customer churn risk, and quantifying engineering ROI."
        ),
        target_duration_seconds=130,
        difficulty="senior",
    ),
    InterviewQuestion(
        id="lead-architectural-consensus",
        category="leadership",
        category_label="Leadership & Mentorship",
        title="How do you drive consensus when leading a multi-team technical migration?",
        context_hint=(
            "Highlight RFC/ADR documentation, establishing objective benchmark criteria, "
            "piloting proof-of-concepts, and aligning disparate roadmaps."
        ),
        target_duration_seconds=140,
        difficulty="staff",
    ),
]

CATEGORY_LABELS: dict[str, str] = {
    "behavioral": "Behavioral & STAR",
    "system_design": "System Design & Architecture",
    "technical": "Technical Depth & Decisions",
    "leadership": "Leadership & Communication",
}


def get_all_questions(
    category: str | None = None,
    difficulty: str | None = None,
    search: str | None = None,
) -> list[InterviewQuestion]:
    """Retrieve questions filtered by category, difficulty, or search keyword."""
    filtered = QUESTION_REGISTRY

    if category:
        cat_lower = category.lower().strip()
        filtered = [q for q in filtered if q.category.lower() == cat_lower]

    if difficulty:
        diff_lower = difficulty.lower().strip()
        filtered = [q for q in filtered if q.difficulty.lower() == diff_lower]

    if search:
        s_lower = search.lower().strip()
        filtered = [
            q
            for q in filtered
            if s_lower in q.title.lower()
            or s_lower in q.context_hint.lower()
            or s_lower in q.category_label.lower()
        ]

    return filtered


def get_question_by_id(question_id: str) -> InterviewQuestion | None:
    """Fetch an individual interview question by slug ID."""
    clean_id = question_id.strip()
    for q in QUESTION_REGISTRY:
        if q.id == clean_id:
            return q
    return None


def get_category_summaries() -> list[CategorySummary]:
    """Compute question counts grouped by category."""
    counts: dict[str, int] = {}
    for q in QUESTION_REGISTRY:
        counts[q.category] = counts.get(q.category, 0) + 1

    return [
        CategorySummary(
            category=cat_key,
            label=CATEGORY_LABELS.get(cat_key, cat_key.capitalize()),
            count=count,
        )
        for cat_key, count in sorted(counts.items())
    ]


def _build_track(
    track_id: str,
    track_name: str,
    description: str,
    difficulty: str,
    q_ids: list[str],
) -> MockTrackDefinition:
    """Helper to assemble a MockTrackDefinition from question IDs."""
    questions = []
    total_sec = 0
    for qid in q_ids:
        q = get_question_by_id(qid)
        if q:
            questions.append(q)
            total_sec += q.target_duration_seconds

    # Duration with buffer for transitions
    est_minutes = max(3, (total_sec + 60 * len(questions)) // 60)

    return MockTrackDefinition(
        track_id=track_id,
        track_name=track_name,
        description=description,
        difficulty=difficulty,
        estimated_duration_minutes=est_minutes,
        question_count=len(questions),
        questions=questions,
    )


def get_all_mock_tracks() -> list[MockTrackDefinition]:
    """Retrieve all pre-configured multi-question mock interview tracks."""
    return [
        _build_track(
            track_id="behavioral-core",
            track_name="Behavioral Core (3 Questions)",
            description=(
                "Standard behavioral round evaluating background introduction, "
                "interpersonal conflict resolution, and technical initiative under ambiguity."
            ),
            difficulty="mid",
            q_ids=[
                "beh-intro-background",
                "beh-conflict-resolution",
                "beh-ambiguous-ownership",
            ],
        ),
        _build_track(
            track_id="senior-engineering",
            track_name="Senior Engineer Round (3 Questions)",
            description=(
                "Rigorous interview simulation targeting high-scale architecture, "
                "production resilience, and cross-functional technical debt advocacy."
            ),
            difficulty="senior",
            q_ids=[
                "sys-realtime-notifications",
                "beh-production-outage",
                "lead-communicating-tech-debt",
            ],
        ),
        _build_track(
            track_id="staff-architect",
            track_name="Staff / Principal Architect Round (4 Questions)",
            description=(
                "Executive technical leadership evaluation assessing distributed data consistency, "
                "database storage engine selection, and multi-team consensus."
            ),
            difficulty="staff",
            q_ids=[
                "sys-distributed-transactions",
                "tech-db-indexing-strategies",
                "lead-architectural-consensus",
                "beh-project-failure",
            ],
        ),
        _build_track(
            track_id="rapid-fire-delivery",
            track_name="Delivery Cadence Sprint (3 Questions)",
            description=(
                "Pacing and verbal conciseness sprint testing fast, crisp technical communication "
                "and conceptual clarity under strict time targets."
            ),
            difficulty="mid",
            q_ids=[
                "tech-explain-complex-concept",
                "sys-api-rate-limiter",
                "tech-microservices-vs-monolith",
            ],
        ),
    ]


def get_mock_track_by_id(track_id: str) -> MockTrackDefinition | None:
    """Find a mock interview track by ID."""
    clean_id = track_id.strip()
    for track in get_all_mock_tracks():
        if track.track_id == clean_id:
            return track
    return None


def create_custom_track(name: str, question_ids: list[str]) -> MockTrackDefinition | None:
    """Construct an on-the-fly custom interview track from selected question slugs."""
    valid_ids = [qid for qid in question_ids if get_question_by_id(qid) is not None]
    if not valid_ids:
        return None
    return _build_track(
        track_id="custom-user-track",
        track_name=name.strip() or "Custom Practice Track",
        description="Candidate-curated mock interview practice sequence.",
        difficulty="custom",
        q_ids=valid_ids,
    )
