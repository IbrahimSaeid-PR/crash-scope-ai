import json
import uuid
from pathlib import Path
from fastapi import BackgroundTasks, Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from .config import settings
from .db import AnalysisJob, KnowledgeDocument, SessionLocal, Video, init_db
from .schemas import AnalysisOut, ChatRequest, ChatResponse, Health, LLMConfigOut, LLMConfigRequest, Report, RetrievalHit, RetrievalRequest, VideoOut
from .services import create_analysis, hash_content, run_analysis, safe_filename, search_documents, validate_video

app = FastAPI(title="CrashScope AI", version="0.1.0", description="Evidence-first traffic incident analysis API")


def db_session():
    with SessionLocal() as db:
        yield db


@app.on_event("startup")
def startup() -> None:
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    (settings.storage_dir / "videos").mkdir(parents=True, exist_ok=True)
    init_db()


@app.get("/api/v1/health", response_model=Health)
def health() -> Health:
    return Health(status="ok", services={"api": "available", "model": "unavailable", "llm": "configured" if settings.openai_api_key else "unconfigured", "rag": "local-keyword"})


@app.get("/api/v1/health/ready", response_model=Health)
def ready(db: Session = Depends(db_session)) -> Health:
    try:
        db.execute(__import__("sqlalchemy").text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(503, f"Database unavailable: {exc}") from exc
    return Health(status="ready", services={"api": "available", "database": "available"})


@app.get("/api/v1/system/status")
def system_status() -> dict:
    return {"dataset": "unavailable", "model": "not trained", "llm": "unavailable" if not settings.openai_api_key else "configured", "rag": "ready"}


@app.get("/api/v1/settings/llm", response_model=LLMConfigOut)
def get_llm_config() -> LLMConfigOut:
    return LLMConfigOut(provider=settings.llm_provider, model=settings.openai_model, configured=bool(settings.openai_api_key), base_url=settings.openai_base_url)


@app.put("/api/v1/settings/llm", response_model=LLMConfigOut)
def configure_llm(request: LLMConfigRequest) -> LLMConfigOut:
    base_url = request.base_url or (
        "https://openrouter.ai/api/v1" if request.provider == "openrouter" else "https://api.openai.com/v1"
    )
    settings.llm_provider = request.provider
    settings.openai_api_key = request.api_key
    settings.openai_model = request.model
    settings.openai_base_url = base_url
    env_path = Path(".env")
    values = {
        "LLM_PROVIDER": request.provider,
        "OPENAI_API_KEY": request.api_key,
        "OPENAI_MODEL": request.model,
        "OPENAI_BASE_URL": base_url,
    }
    existing = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
    keys = set(values)
    kept = [line for line in existing if not line.split("=", 1)[0].strip() in keys]
    env_path.write_text("\n".join(kept + [f"{key}={value}" for key, value in values.items()]) + "\n", encoding="utf-8")
    return LLMConfigOut(provider=request.provider, model=request.model, configured=True, base_url=base_url)


@app.post("/api/v1/videos/upload", response_model=VideoOut, status_code=201)
async def upload_video(file: UploadFile = File(...), db: Session = Depends(db_session)) -> Video:
    if not file.filename:
        raise HTTPException(400, "A filename is required")
    data = await file.read()
    try:
        validate_video(file.filename, len(data))
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    video_id = str(uuid.uuid4())
    filename = safe_filename(file.filename)
    destination = settings.storage_dir / "videos" / f"{video_id}_{filename}"
    destination.write_bytes(data)
    video = Video(id=video_id, filename=filename, path=str(destination), media_type="cctv", status="uploaded")
    db.add(video)
    db.commit()
    db.refresh(video)
    return video


@app.get("/api/v1/videos", response_model=list[VideoOut])
def list_videos(db: Session = Depends(db_session)) -> list[Video]:
    return list(db.query(Video).order_by(Video.created_at.desc()).all())


@app.get("/api/v1/videos/{video_id}", response_model=VideoOut)
def get_video(video_id: str, db: Session = Depends(db_session)) -> Video:
    video = db.get(Video, video_id)
    if not video:
        raise HTTPException(404, "Video not found")
    return video


@app.delete("/api/v1/videos/{video_id}", status_code=204)
def delete_video(video_id: str, db: Session = Depends(db_session)) -> None:
    video = db.get(Video, video_id)
    if not video:
        raise HTTPException(404, "Video not found")
    path = Path(video.path)
    db.delete(video)
    db.commit()
    if path.exists():
        path.unlink()


def analysis_response(job: AnalysisJob) -> AnalysisOut:
    return AnalysisOut(id=job.id, video_id=job.video_id, kind=job.kind, status=job.status, result=json.loads(job.result_json) if job.result_json else None, error=job.error)


@app.post("/api/v1/analyses/{kind}/{video_id}", response_model=AnalysisOut, status_code=202)
def start_analysis(kind: str, video_id: str, background_tasks: BackgroundTasks, db: Session = Depends(db_session)) -> AnalysisOut:
    if kind not in {"cctv", "dashcam"}:
        raise HTTPException(400, "Analysis kind must be cctv or dashcam")
    video = db.get(Video, video_id)
    if not video:
        raise HTTPException(404, "Video not found")
    job = create_analysis(video, kind)
    background_tasks.add_task(run_analysis, job.id)
    return analysis_response(job)


@app.get("/api/v1/analyses/{job_id}", response_model=AnalysisOut)
def get_analysis(job_id: str, db: Session = Depends(db_session)) -> AnalysisOut:
    job = db.get(AnalysisJob, job_id)
    if not job:
        raise HTTPException(404, "Analysis not found")
    return analysis_response(job)


@app.post("/api/v1/documents/upload", status_code=201)
async def upload_document(file: UploadFile = File(...), db: Session = Depends(db_session)) -> dict:
    content = (await file.read()).decode("utf-8", errors="replace")
    if not content.strip():
        raise HTTPException(400, "Document is empty")
    document = KnowledgeDocument(id=str(uuid.uuid4()), filename=safe_filename(file.filename or "document.txt"), content=content)
    db.add(document)
    db.commit()
    return {"id": document.id, "filename": document.filename, "content_hash": hash_content(content.encode())}


@app.get("/api/v1/documents")
def list_documents(db: Session = Depends(db_session)) -> list[dict]:
    return [{"id": d.id, "filename": d.filename, "created_at": d.created_at} for d in db.query(KnowledgeDocument).all()]


@app.post("/api/v1/retrieval/query", response_model=list[RetrievalHit])
def retrieval_query(request: RetrievalRequest) -> list[RetrievalHit]:
    return [RetrievalHit(**hit) for hit in search_documents(request.query, request.top_k)]


@app.post("/api/v1/assistant/chat", response_model=ChatResponse)
def assistant_chat(request: ChatRequest) -> ChatResponse:
    hits = [RetrievalHit(**hit) for hit in search_documents(request.question, 5)]
    if not hits:
        return ChatResponse(
            answer="I do not have enough indexed evidence to answer that question. Upload permitted safety documents or review the source video manually.",
            evidence_sufficiency="insufficient",
        )
    answer = (
        "Based on the indexed sources, I found related evidence, but this local assistant "
        "does not infer fault, causation, identity, or legal responsibility. Review the cited excerpts "
        "and the source footage before drawing conclusions."
    )
    return ChatResponse(answer=answer, citations=hits, evidence_sufficiency="limited")


@app.post("/api/v1/reports/{incident_id}", response_model=Report)
def generate_report(incident_id: str) -> Report:
    return Report(incident_id=incident_id, summary="Evidence is insufficient for a supported incident conclusion.", uncertainties=["No trained model checkpoint or verified visual evidence is configured."], recommendations=["Review the source video manually and configure a validated model before making consequential decisions."])


@app.get("/api/v1/videos/{video_id}/file")
def video_file(video_id: str, db: Session = Depends(db_session)) -> FileResponse:
    video = db.get(Video, video_id)
    if not video or not Path(video.path).exists():
        raise HTTPException(404, "Video file not found")
    return FileResponse(video.path, media_type="video/mp4", filename=video.filename)
