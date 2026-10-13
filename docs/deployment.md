# Deployment Guide — Interview Practice Coach

This guide details how to build, configure, containerize, and deploy the **Interview Practice Coach** in production and local multi-service container environments.

---

## 1. System Architecture Overview

```
                                +---------------------------+
                                |      Candidate Client     |
                                |  (Browser: React 18 + TS) |
                                +-------------+-------------+
                                              |
                     HTTP / REST              |              WebSocket
                  (JSON & Audio Chunks)       |        (Landmarks & Audio)
                                              |
                                              v
+-----------------------------------------------------------------------------------------+
|                                Reverse Proxy / Nginx (Port 80)                          |
|  - SPA Static Routing (index.html fallback)                                             |
|  - Gzip Asset Compression                                                               |
|  - Reverse Proxy /api/ -> backend:8000                                                   |
|  - WebSocket Upgrade /api/v1/ws/ -> backend:8000                                        |
+---------------------------------------------+-------------------------------------------+
                                              |
                                              v
+-----------------------------------------------------------------------------------------+
|                             Backend Container (Port 8000)                               |
|  - FastAPI (Python 3.11-slim)                                                           |
|  - Non-privileged execution (`appuser:1000`)                                            |
|  - faster-whisper (CPU / int8 quantized)                                                |
|  - SQLite (WAL mode, persistent volume `/app/data/practice_coach.db`)                   |
|  - Model Cache (persistent volume `/app/models_cache`)                                  |
+-----------------------------------------------------------------------------------------+
```

---

## 2. Environment Variables

### Backend Configuration

| Variable | Default | Description |
|---|---|---|
| `HOST` | `0.0.0.0` | IP address to bind server |
| `PORT` | `8000` | Port to expose |
| `ALLOWED_ORIGINS` | `http://localhost:5173,http://localhost:3000` | Comma-separated CORS origins |
| `PRACTICE_COACH_DB_PATH` | `practice_coach.db` | Path to SQLite database file |
| `WHISPER_MODEL_SIZE` | `tiny` | faster-whisper model variant (`tiny`, `base`, `small`, `medium`) |
| `WHISPER_DEVICE` | `cpu` | Inference device (`cpu` or `cuda`) |
| `WHISPER_COMPUTE_TYPE` | `int8` | Model precision (`int8`, `float16`, `float32`) |
| `HF_HOME` | `~/.cache/huggingface` | Hugging Face / faster-whisper cache directory |

### Frontend Configuration

| Variable | Default | Description |
|---|---|---|
| `VITE_API_BASE_URL` | `http://localhost:8000` | REST API target. Leave empty in Docker reverse proxy. |
| `VITE_WS_URL` | `ws://localhost:8000` | WebSocket endpoint base. |

---

## 3. Local Multi-Service Development (Docker Compose)

Docker Compose provisions both services with unified networking and persistent volumes:

### Start All Services
```bash
docker compose up --build
```

- **Frontend App**: [http://localhost:80](http://localhost:80)
- **Backend API & Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Backend Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

### Persistent Volumes
- `interview_coach_db_data`: Houses `practice_coach.db` and SQLite WAL files across container restarts.
- `interview_coach_model_cache`: Persists downloaded `faster-whisper` model weights across runs.

### Stop Services
```bash
docker compose down
```

---

## 4. Production Container Deployment

### A. Backend Container

The backend container is based on `python:3.11-slim`, installs `ffmpeg` and `curl`, runs as non-root user `appuser`, and includes an active Docker health check.

#### Build Image
```bash
cd backend
docker build -t interview-coach-backend:latest .
```

#### Run Container
```bash
docker run -d \
  --name coach-backend \
  -p 8000:8000 \
  -v coach-data:/app/data \
  -v coach-models:/app/models_cache \
  -e ALLOWED_ORIGINS="https://yourdomain.com" \
  -e WHISPER_MODEL_SIZE="tiny" \
  interview-coach-backend:latest
```

### B. Frontend Container

The frontend container uses a multi-stage build: compiles Vite + TypeScript with Node 20, then serves static assets via Nginx 1.25 Alpine with reverse-proxy support.

#### Build Image
```bash
cd frontend
docker build -t interview-coach-frontend:latest .
```

#### Run Container
```bash
docker run -d \
  --name coach-frontend \
  -p 80:80 \
  interview-coach-frontend:latest
```

---

## 5. Cloud Platform Deployment Recipes

### 1. Render / Railway / Fly.io

- **Backend**:
  - Build command: `pip install -r backend/requirements.txt`
  - Start command: `python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT`
  - Mount persistent disk at `/app/data` to preserve the SQLite database.
  - Set `WHISPER_MODEL_SIZE=tiny` for free/starter CPU tiers.

- **Frontend**:
  - Build command: `npm install && npm run build`
  - Publish directory: `frontend/dist`
  - Set `VITE_API_BASE_URL` and `VITE_WS_URL` to point to backend URL.

---

## 6. Operational & Security Checklist

- [x] **Zero Raw Media Retention**: No raw video or audio is stored on disk or in the database.
- [x] **Temporary File Cleanup**: Uploaded audio is written to temporary files and cleaned up immediately in `finally` blocks.
- [x] **File Size Limits**: Enforced 50 MB upload limit on audio endpoints.
- [x] **Non-Root Execution**: Docker containers run under dedicated unprivileged users (`appuser`).
- [x] **Health Check Endpoints**: Dedicated `GET /health` responding with 200 OK and version info.
- [x] **Graceful Fallbacks**: Audio pipeline handles empty or malformed files; analytics pipeline includes sample size fallbacks.
