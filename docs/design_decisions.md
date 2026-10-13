# Engineering Design Decisions Log

This document records the foundational architectural, ethical, and algorithmic decisions made during the design and implementation of the **Interview Practice Coach**.

---

## Decision 1: Unsupervised Dimensionality Reduction & Clustering Before Any Supervised Model

### Context
Many commercial interview preparation tools market supervised "hireability", "confidence", or "competence" scores. These models typically rely on subjective, noisy, or biased human ratings.

### Decision
We intentionally chose **unsupervised PCA (2D latent projection) and K-Means delivery clustering** as our analytical core rather than training a supervised classifier or regression score.

### Rationale
1. **Lack of Ground-Truth Objectivity**: There is no universal, scientifically validated label for what constitutes an "ideal" interview delivery. Pacing that works in technical deep-dives (deliberate, reflective pauses) differs from executive overviews (brisk, structured summaries).
2. **Avoiding Feedback Traps**: Supervised scoring models reward candidates who mimic the specific training demographic and penalize diverse communication styles, regional accents, or neurodivergent delivery patterns.
3. **Exploratory Archetypes**: By projecting sessions onto PC1 and PC2, candidates can visually see their delivery style shift across sessions (e.g. moving from a high-variability quadrant toward composed, steady pacing) without being branded with an arbitrary "grade".

---

## Decision 2: Client-Side Geometric Visual Tracking & Strict Privacy Boundaries

### Context
Video contains sensitive biometric and environmental information. Sending raw video frames over the network introduces privacy risks, GDPR/CCPA storage liabilities, and high bandwidth costs.

### Decision
1. **No Raw Video Storage or Server Ingestion**: All facial and pose landmarks are extracted in the candidate's browser via MediaPipe. The backend only ever receives normalized geometric coordinate samples.
2. **Absolute Refusal of Emotion or Personality Inference**: The application strictly refuses to predict emotions, confidence, honesty, intelligence, or likeability.
3. **Geometric Proxy Presentation**: Measurements are explicitly surfaced as physical geometric proxies:
   - Gaze: 2D pupil-to-canthus bounding ratio relative to the camera cone.
   - Head Stability: Centroid variance over time ($1 / (1 + 80 \cdot \sigma^2)$).
   - Hand Movement: Inter-frame wrist velocity spikes.

---

## Decision 3: Local faster-whisper with CPU int8 Quantization

### Context
Transcription is the most computationally demanding step in speech delivery analysis. External APIs (OpenAI Whisper API, Google Speech) require recurring costs and transmit candidate audio to third-party cloud infrastructure.

### Decision
We selected **faster-whisper** (CTranslate2-based Whisper implementation) configured by default with the `tiny` model, running on `cpu` with `int8` quantization.

### Rationale
1. **Zero Recurring Cost**: Candidates and recruiters can run the entire platform locally without an API key or credit card.
2. **Speed**: CTranslate2 achieves up to $4\times$ faster inference than vanilla PyTorch Whisper on standard CPU architectures.
3. **Word-Level Timestamp Fidelity**: faster-whisper natively extracts word alignment boundaries, which are critical for our deterministic pause and WPM formulas.
4. **Lazy Initialization**: The Whisper model weights are not loaded at FastAPI application boot; they load on-demand upon the first transcription request to ensure rapid test runs and low idle memory footprints.

---

## Decision 4: SQLite with Write-Ahead Logging (WAL) and Cascading Deletion

### Context
The application needs persistence for session metadata, transcripts, acoustic metrics, and visual metrics across browser sessions.

### Decision
We selected SQLite with `PRAGMA journal_mode = WAL;` and cascading foreign keys (`PRAGMA foreign_keys = ON;`), isolated behind a repository pattern.

### Rationale
1. **Zero-Configuration Local Development**: Requires no separate database daemon or container (PostgreSQL/MySQL), simplifying local setup for student and portfolio reviewers.
2. **User-Driven Deletion (Right to be Forgotten)**: Deleting a session record automatically and atomically cascades across `audio_metrics`, `visual_metrics`, and `session_feature_vectors`.
3. **Extensibility**: The repository pattern abstracts database operations, allowing a simple switch to PostgreSQL for enterprise multi-tenant deployments via SQLAlchemy if desired.

---

## Decision 5: Bidirectional WebSocket Protocol for Live Practice Alerts

### Context
Providing delivery feedback only *after* a 3-minute answer forces candidates to review mistakes retroactively without tactile awareness during delivery.

### Decision
We implemented a bidirectional WebSocket endpoint (`/api/v1/ws/practice`) that processes incoming audio chunks and landmark frames concurrently, broadcasting real-time tactical alerts for extended pauses (>3.0s), persistent off-center gaze (>3.5s), and camera framing loss.
