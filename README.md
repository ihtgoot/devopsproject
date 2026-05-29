# Gemma Fine-Tune Platform — DevOps Class Project

A production-style ML orchestration system demonstrating **Docker**, **Docker Compose**, and **Jenkins CI/CD** across three containerised services.

## Architecture

```
Client (Browser)
      │
      ▼
┌─────────────────┐
│  NGINX Frontend │  :80   HTML/CSS/JS — Upload dataset, view jobs, run inference
└────────┬────────┘
         │ /api/*  (proxied)
         ▼
┌─────────────────┐
│   Go API        │  :8080  Job orchestrator — Go channels, goroutine worker pool
│  ┌───────────┐  │
│  │ chan Queue │  │         Async job scheduling without Redis
│  └─────┬─────┘  │
└────────┼────────┘
         │ HTTP (internal Docker network only)
         ▼
┌─────────────────┐
│ Python Trainer  │  :8000  Flask API — Gemma 3 fine-tuning via unsloth + LoRA
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Shared Volume  │         /data — datasets, model checkpoints, logs
└─────────────────┘
```

## Services

| Service | Stack | Port |
|---------|-------|------|
| `frontend` | NGINX + HTML/CSS/JS | 80 |
| `api` | Go 1.21, gorilla/mux | 8080 |
| `trainer` | Python 3, Flask, unsloth, LoRA | 8000 (internal) |

## Go API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/train` | Submit training job (returns job ID immediately) |
| `GET` | `/status/:id` | Poll job status |
| `GET` | `/jobs` | List all jobs |
| `POST` | `/inference` | Run inference on fine-tuned model |
| `GET` | `/health` | Health check |

## Python Trainer Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/train` | Start training (called by Go API only) |
| `GET` | `/status/:job_id` | Training progress |
| `POST` | `/inference` | Run model inference |
| `GET` | `/health` | Health check |

## Quick Start

### Prerequisites
- Docker & Docker Compose installed
- (Optional) NVIDIA GPU + nvidia-docker for real training

### Run with Docker Compose

```bash
# Clone and start all services
git clone <repo>
cd devopsproject
docker compose up --build
```

Then open **http://localhost** in your browser.

### Run Go backend locally

```bash
cd backend-go
go run cmd/main.go
```

### Run Python trainer locally

```bash
cd trainer
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

## Jenkins CI/CD Pipeline

The `Jenkinsfile` defines 6 stages:

```
Checkout → Lint (Go + Python) → Test → Build Images → Deploy → Health Checks
```

**Post actions:**
- Always archives Docker Compose logs
- On failure: tears down services
- Cleanup: always runs `docker compose down`

### Setup Jenkins

1. Install plugins: **Docker**, **Docker Compose**, **Pipeline**
2. Create a new Pipeline job
3. Point it at this repo — Jenkins will auto-detect `Jenkinsfile`

## Project Structure

```
devopsproject/
├── frontend/
│   ├── index.html        # Single-page UI
│   ├── app.js            # Job submission, polling, inference
│   ├── nginx.conf        # Reverse proxy to Go API
│   └── Dockerfile
│
├── backend-go/
│   ├── cmd/main.go       # Entry point
│   ├── internal/
│   │   ├── api/          # REST handlers + CORS middleware
│   │   ├── queue/        # Go channel job queue + goroutine worker
│   │   └── models/       # TrainingJob struct
│   ├── go.mod
│   └── Dockerfile
│
├── trainer/
│   ├── app.py            # Flask API (train / inference / health)
│   ├── train.py          # unsloth + LoRA fine-tuning logic
│   ├── test.py           # Inference test script
│   ├── requirements.txt
│   └── Dockerfile
│
├── docker-compose.yml    # Orchestrates all 3 services + shared volume
├── Jenkinsfile           # CI/CD pipeline
└── .gitignore
```

## Key DevOps Concepts Demonstrated

| Concept | Where |
|---------|-------|
| Containerisation | All 3 services have Dockerfiles |
| Service isolation | Trainer not publicly exposed |
| Internal networking | Docker bridge network `ml_net` |
| Shared volumes | `model_store` for datasets + models |
| Async job processing | Go channels + goroutine worker |
| CI/CD pipeline | Jenkins 6-stage pipeline |
| Parallel stages | Lint & Test stages run Go + Python in parallel |
| Health checks | Jenkins calls `/health` on all services |
| Artifact archiving | Jenkins archives `compose_logs.txt` |

## GPU Support

To enable GPU for real Gemma training, uncomment the `deploy` block in `docker-compose.yml`:

```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: all
          capabilities: [gpu]
```

Requires `nvidia-docker` runtime installed on the host.
