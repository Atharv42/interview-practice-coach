# Interview Practice Coach

An objective, privacy-preserving feedback platform for behavioral and technical interview practice. Evaluates speech delivery mechanics (speaking pace in WPM, pause intervals, filler words) and geometric visual delivery indicators (camera gaze centering, head stability, gesture activity) without inferring psychological traits, emotions, or personality.

---

## Architecture & Completed Milestones

- **Milestone 1: FastAPI Backend Foundation**
  - Modular routers, health checks, strict input schemas, custom error handling, and CORS middleware configured for React/Vite.
- **Milestone 2: Audio Processing Pipeline**
  - Audio transcription via `faster-whisper`, token cleaning, WPM calculation, filler word detection (single & compound), pause detection with configurable duration thresholds, and articulation rate.
- **Milestone 3: Visual Delivery Metrics**
  - Client-side extracted facial and pose landmark proxies (MediaPipe compatible), approximate camera cone gaze orientation, head centroid stability scores, and hand gesture frequency.
- **Milestone 4: Feature Store & Analytics**
  - Unified session feature vectors, unsupervised 2D PCA dimensionality reduction, exploratory K-Means clustering into delivery archetypes, and longitudinal pacing/filler trend regressions.
- **Milestone 5: Persistence & Session Management**
  - Lightweight local SQLite persistence (`practice_coach.db`) with WAL journal mode, cascading foreign keys, CRUD session APIs under `/api/v1/sessions`, and longitudinal analytics directly from stored history.
- **Milestone 6: Frontend Client Application**
  - React 18 + Vite SPA with TypeScript:
    - **Practice Studio**: Webcam framing guide, live microphone recording with animated volume meter, preset/custom interview question selector, and audio file upload alternative.
    - **Session Report**: Visual delivery metric cards, WPM gauge, filler breakdown pills, pause distribution, and full transcript viewer.
    - **Session History**: Paginated, searchable history of previous practice attempts with one-click permanent cascading deletion.
    - **Analytics Dashboard**: Interactive SVG 2D PCA delivery projection scatter plot, exploratory delivery archetype cards, and longitudinal regression trendlines.

---

## Privacy Model

- **No Raw Video Storage**: Video frames are processed client-side. No raw video recordings or facial imagery are ever transmitted or stored on the server.
- **No Raw Audio Retention**: Temporary audio uploads are processed in transient memory/temp storage and unlinked immediately after metric extraction.
- **Objective Delivery Focus**: Strictly measures acoustic and geometric delivery mechanics. Does not perform emotion recognition, confidence scoring, honesty detection, or personality assessments.
- **Candidate Data Control**: Candidates can permanently delete sessions and all associated metrics at any time.

---

## Running the Application

### 1. Backend (FastAPI)

```bash
cd backend
.\.venv\Scripts\python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
- Interactive Swagger API docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- Health check: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

### 2. Frontend (React + Vite)

```bash
cd frontend
npm install
npm run dev
```
- Open [http://localhost:5173](http://localhost:5173) in your browser.