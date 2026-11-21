# CrashScope AI

CrashScope AI is an experimental, evidence-first traffic incident investigation workspace. It combines a FastAPI backend with a React/Vite dashboard for video registration, asynchronous analysis jobs, evidence retrieval, structured reports, and a citation-aware investigation assistant.

The default installation is intentionally honest about capability: without licensed datasets, a trained checkpoint, or an external LLM key, the application reports those services as unavailable and never fabricates predictions, timestamps, causes, identities, or legal conclusions.

## What is included

- **Video workflow:** local upload, safe filenames, file-size/extension validation, video listing, deletion, and browser preview.
- **Analysis workflow:** CCTV job creation, background processing, status polling, explicit model-unavailable results, and human-review boundaries.
- **Investigation workspace:** timeline and evidence-constrained report panels.
- **Knowledge assistant:** local keyword retrieval and conversational evidence responses with source excerpts.
- **LLM settings:** local OpenAI/OpenRouter provider configuration; API keys are written to `.env` and never returned by the API.
- **Operations:** health/readiness endpoints, SQLite development persistence, Docker Compose services, and automated tests.

## Architecture

```text
React + Vite dashboard
          |
          v
FastAPI REST API ---- SQLAlchemy/SQLite (development)
          | \
          |  \---- local video storage
          \------- retrieval and background analysis services
```

The frontend development server proxies `/api/*` to `http://127.0.0.1:8000`.

## Requirements

- Windows PowerShell, macOS, or Linux
- Python 3.11+ (Python 3.14 is supported by the verified local setup)
- Node.js 20+ and npm
- Docker Desktop is optional

## Local installation

### Backend

From the repository root:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

Run tests:

```powershell
.\.venv\Scripts\pytest.exe -q
```

Start the API:

```powershell
.\.venv\Scripts\uvicorn.exe app.main:app --app-dir backend --reload
```

The API is available at `http://127.0.0.1:8000`; OpenAPI documentation is at `/docs`.

### Frontend

```powershell
Set-Location frontend
npm ci
npm run dev
```

Open `http://localhost:5173`. For a production build:

```powershell
npm run build
npm run lint
```

## API surface

| Area | Routes |
|---|---|
| Health | `GET /api/v1/health`, `GET /api/v1/health/ready`, `GET /api/v1/system/status` |
| Videos | `POST /api/v1/videos/upload`, `GET /api/v1/videos`, `GET /api/v1/videos/{id}`, `DELETE /api/v1/videos/{id}` |
| Analysis | `POST /api/v1/analyses/cctv/{video_id}`, `POST /api/v1/analyses/dashcam/{video_id}`, `GET /api/v1/analyses/{job_id}` |
| Knowledge | `POST /api/v1/documents/upload`, `GET /api/v1/documents`, `POST /api/v1/retrieval/query` |
| Assistant | `POST /api/v1/assistant/chat` |
| Reports | `POST /api/v1/reports/{incident_id}` |
| LLM settings | `GET /api/v1/settings/llm`, `PUT /api/v1/settings/llm` |

## LLM configuration

Use the **LLM settings** section in the dashboard, or configure the endpoint directly:

```powershell
$body = @{
  provider = "openai"
  model = "gpt-4.1-mini"
  api_key = "your-key"
} | ConvertTo-Json
Invoke-RestMethod http://127.0.0.1:8000/api/v1/settings/llm `
  -Method Put -ContentType "application/json" -Body $body
```

For OpenRouter, set `provider` to `openrouter` and use an OpenRouter model identifier such as `openai/gpt-4.1-mini`. Never commit `.env` or paste credentials into source code, screenshots, issues, or logs.

## Docker

The supplied Compose file currently starts the API, Redis, and Qdrant development services:

```powershell
docker compose up --build
```

The backend uses SQLite for this MVP. Redis and Qdrant are included as integration infrastructure; Celery and persistent vector indexing are not enabled in the default lightweight pipeline yet. Docker data is not committed to the repository.

## Data and model status

ACCIDENT and Nexar data are **not bundled or downloaded automatically**. Acquire them only through their official sources and terms. Optional ML dependencies can be installed with:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[ml]"
```

No trained checkpoint is included. The application must report the model as unavailable until a validated checkpoint and dataset evaluation are added.

## Security and privacy

- Upload names are sanitized and path traversal is prevented.
- File extensions and configured size limits are validated.
- Secrets are environment-based and excluded by `.gitignore`.
- The product does not perform face recognition, license-plate identification, or automated fault determination.
- Human review is required for consequential decisions.

## Verification

The verified local checks are:

```text
Backend: 5 passed
Frontend: npm run build passed
Frontend: npm run lint passed
Docker: docker compose config passed
API: health/readiness and upload-to-analysis smoke flow passed
```

## Repository layout

- [`backend/app`](backend/app): FastAPI application, persistence, services, schemas.
- [`frontend`](frontend): React/Vite dashboard.
- [`tests`](tests): backend unit and API tests.
- [`docs`](docs): architecture, limitations, and execution notes.

## License and responsible use

No project license has been declared yet. Dataset and document licenses remain the responsibility of the operator. CrashScope AI is experimental decision-support software, not a certified safety system, forensic authority, or legal-liability engine.
