# System architecture

FastAPI exposes versioned health, upload, analysis, retrieval, and report endpoints. SQLAlchemy persists local development records in SQLite and can be pointed at PostgreSQL. Video bytes remain in filesystem storage. Analysis runs as a background task and returns `model_status=unavailable` until a validated checkpoint is configured. The frontend is a Vite/React status dashboard.
