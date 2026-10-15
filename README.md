# Sentinel AI / ERA IncidentGuard

Sentinel AI is an incident reporting, triage, and governance portal designed for tracking AI system failures, harmful outputs, privacy breaches, discriminatory decisions, security incidents, and reliability anomalies.

The application features a **unified production architecture**: a modern React + TypeScript single-page application (SPA) with a sleek dark/charcoal design system, served alongside a robust Python FastAPI backend that powers AI triage, incident lifecycle workflows, reporting, and model observatory analytics.

---

## Architecture Overview

```
                        ┌─────────────────────────────────────────┐
                        │      Client Browser (Single URL)        │
                        │        http://localhost:8000            │
                        └────────────────────┬────────────────────┘
                                             │
                                             ▼
                        ┌─────────────────────────────────────────┐
                        │        FastAPI Unified Server           │
                        │           (Port 8000)                   │
                        ├────────────────────┬────────────────────┤
                        │  React SPA Static  │   REST API Layer   │
                        │  (frontend/dist)   │      (/api/*)      │
                        └────────────────────┴──────────┬─────────┘
                                                        │
                         ┌──────────────────────────────┴──────────────┐
                         ▼                                             ▼
              ┌─────────────────────┐                       ┌─────────────────────┐
              │  Sentinel Services  │                       │  AI Triage Provider │
              │  - Incident Service │                       │  - Deterministic    │
              │  - Analytics        │                       │    (Demo Mode)      │
              │  - Model Intel      │                       │  - OpenAI GPT-4     │
              │  - Audit Logging    │                       │    (Live Mode)      │
              └──────────┬──────────┘                       └─────────────────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │   SQLite Database   │
              │ (data/sentinel.db)  │
              └─────────────────────┘

  * Fallback Interface: Streamlit dashboard remains available at http://localhost:8501
```

- **Unified Single-Origin Server**: FastAPI serves the React production build and API endpoints from `http://localhost:8000`. No CORS issues or separate proxy layers required in production.
- **Primary Frontend (React + Vite)**: Modern responsive dark-theme dashboard with interactive visualizations, incident explorer, guided incident reporting, AI triage workbench, AI Model Observatory, and audit logs.
- **Backend (Python 3.10+ / FastAPI)**: Domain models, Pydantic schemas, thread-safe SQLite persistence with WAL mode, and atomic transactions.
- **Fallback Interface (Streamlit)**: Preserved on port 8501 for backward compatibility and emergency operations.

---

## Key Features

1. **Overview Dashboard** — Key incident metrics, severity breakdown, category distribution, and incident reporting trends over time.
2. **Incident Reporting** — Guided submission form with strict Pydantic validation and client-side confirmation review.
3. **Incident Explorer** — Real-time search, multi-factor filtering (status, category, severity, verification, provider, date ranges), sorting, and pagination.
4. **Incident Details & Lifecycle Management** — Complete incident dossier, status lifecycle transitions (Submitted → Under Review → Action Required/Resolved → Closed), reviewer notes, corrective actions, and immutable audit history.
5. **AI-Assisted Triage** — Deterministic offline keyword-based assessment (demo mode) or live OpenAI-powered triage with data minimization and prompt injection defenses.
6. **AI Model Observatory** — Model-specific incident intelligence: exact model/version leaderboard, comparison workspace, category/severity matrices, and synthetic vs. genuine data segmentation.
7. **Export & Reporting** — Markdown and PDF exports with configurable reporter PII redaction.
8. **Safe Demo Data** — Isolated synthetic demo data (`is_demo=True`) with idempotent seeding and safe one-click reset that never touches genuine reports.

---

## Technology Stack

- **Frontend**: React 19, TypeScript, Vite, Tailwind CSS, Lucide Icons, Canvas Confetti
- **Backend**: FastAPI, Uvicorn, Python 3.10+, Pydantic v2
- **Database**: SQLite 3 (WAL mode, parameterized queries, immediate transactions)
- **AI Integration**: OpenAI Python SDK (GPT-4 / GPT-4o mini) with deterministic offline fallback
- **Exports**: ReportLab (PDF), Plotly, CSV
- **Fallback UI**: Streamlit 1.39+

---

## Prerequisites

- **Python**: 3.10 or later (Python 3.12 recommended)
- **Node.js**: 18.x or later (with `npm`)

---

## Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/SARVESHBHARAT/Sentinel-AI.git
cd Sentinel-AI
```

### 2. Configure Python Backend
Create an isolated virtual environment and install dependencies:

```bash
# Create and activate virtual environment
python -m venv .venv

# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# macOS / Linux:
source .venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

### 3. Configure Frontend
Install frontend packages and generate the production build:

```bash
cd frontend
npm install
npm run build
cd ..
```

### 4. Configure Environment Variables
Copy `.env.example` to `.env` (never commit `.env` to Git):

```bash
cp .env.example .env
```

| Variable | Default | Purpose |
| :--- | :--- | :--- |
| `SENTINEL_DATABASE_PATH` | `data/sentinel.db` | Path to the SQLite database file |
| `SENTINEL_DEMO_MODE` | `true` | When `true`, uses deterministic offline triage (no API calls) |
| `SENTINEL_OPENAI_MODEL` | `gpt-4.1-mini` | Model identifier for OpenAI triage |
| `SENTINEL_OPENAI_MODEL_VERSION` | *unset* | Explicit model version override |
| `SENTINEL_MODEL_INTEL_MIN_SAMPLE` | `5` | Minimum reports required before comparison displays |
| `SENTINEL_READ_ONLY` | `false` | Blocks all write operations when set to `true` |
| `SENTINEL_SUBMISSION_RATE_LIMIT` | `20` | Max submissions per window per instance |
| `SENTINEL_SUBMISSION_RATE_WINDOW` | `3600` | Rate-limit window in seconds |
| `OPENAI_API_KEY` | *unset* | OpenAI API credential (required only if `SENTINEL_DEMO_MODE=false`) |

---

## Running the Application

### Option A: Unified Launcher (Recommended)

Run the unified production server with a single command:

```bash
python scripts/start.py
```

This starts the unified FastAPI server which serves both the API and the React production build:
- **Application URL**: [http://localhost:8000](http://localhost:8000)
- **Interactive API Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **API Health Check**: [http://localhost:8000/api/health](http://localhost:8000/api/health)

### Option B: Development Mode (FastAPI + Vite HMR)

For active frontend development with hot-module reloading:

```bash
python scripts/start.py --dev
```

- **Frontend (Vite HMR)**: [http://localhost:5173](http://localhost:5173)
- **Backend API**: [http://localhost:8000](http://localhost:8000)

### Option C: Streamlit Fallback

The original Streamlit interface is preserved for operational fallback:

```bash
streamlit run app.py --server.port 8501
```
- **Streamlit URL**: [http://localhost:8501](http://localhost:8501)

---

## Running Tests & Quality Checks

### Backend Unit & Regression Tests
```bash
pytest
```

### Frontend Typecheck & Build Verification
```bash
cd frontend
npm run build
cd ..
```

### Code Formatting & Linting
```bash
ruff check src tests
```

---

## Database Management & Backups

- **Database Location**: Local SQLite file at `data/sentinel.db`. The database is automatically initialized with tables and indexes on first run.
- **Git Protection**: All SQLite database files (`*.db`, `*.sqlite`, `*.db-journal`, `sentinel.db`, etc.) are explicitly excluded in `.gitignore` to prevent committing incident records.
- **Backups**: Run the safe SQLite online-backup utility:
  ```bash
  python scripts/backup_db.py --db data/sentinel.db --out-dir data --keep 7
  ```
- **Restoration**: Stop the server, copy the backup file over `data/sentinel.db`, and restart the server.

---

## Demo Dataset & Synthetic Data Isolation

- **Synthetic Records**: The application includes a pre-seeded synthetic dataset of demonstration incidents labelled with `is_demo=True`.
- **Isolation**: Demo records are tagged with `[DEMO]` in titles and marked as synthetic in all exports.
- **Safe Reset**: In the Settings page, "Reset Demo Records" deletes only records where `is_demo=True`. Genuine user submissions are strictly protected from deletion.

---

## Security Notes & Limitations

> ⚠️ **No Authentication / Authorization Built-In**
>
> Sentinel AI is designed for internal network operations and trusted environments. It does not implement user login, sessions, or role-based access control. Do not expose port 8000 or 8501 directly to the public internet without an authentication proxy (such as Cloudflare Access, OAuth2-Proxy, or VPN).

- **Data Minimization**: AI triage payloads include only essential incident details (title, description, category, provider, evidence). Reporter identity and customer PII are strictly excluded.
- **Prompt Injection Defense**: System prompts instruct the LLM to treat incident descriptions as untrusted text evidence and never execute embedded instructions.
- **Read-Only Mode**: Set `SENTINEL_READ_ONLY=true` in `.env` to enforce complete write-blocking at the repository layer.
- **Safe Parameterization**: All SQL queries use strictly parameterized SQLite bindings to prevent SQL injection.
- **Secrets Protection**: API keys are loaded solely through environment variables and never logged or persisted in the database.
