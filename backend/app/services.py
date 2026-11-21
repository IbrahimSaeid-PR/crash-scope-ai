import hashlib
import json
import re
import uuid
from pathlib import Path
from .config import settings
from .db import AnalysisJob, KnowledgeDocument, SessionLocal, Video

ALLOWED_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv"}


def safe_filename(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(name).name)
    return cleaned[:180] or "upload.bin"


def validate_video(name: str, size: int) -> None:
    if Path(name).suffix.lower() not in ALLOWED_EXTENSIONS:
        raise ValueError("Only MP4, MOV, AVI, and MKV videos are supported")
    if size <= 0 or size > settings.max_upload_bytes:
        raise ValueError("Video size is outside the configured limit")


def create_analysis(video: Video, kind: str) -> AnalysisJob:
    job = AnalysisJob(id=str(uuid.uuid4()), video_id=video.id, kind=kind, status="queued")
    with SessionLocal() as db:
        db.add(job)
        db.commit()
    return job


def run_analysis(job_id: str) -> None:
    with SessionLocal() as db:
        job = db.get(AnalysisJob, job_id)
        if not job:
            return
        job.status = "processing"
        db.commit()
        try:
            video = db.get(Video, job.video_id)
            result = {
                "model_status": "unavailable",
                "timeline": [],
                "observations": [],
                "message": "No trained checkpoint is configured; no prediction was generated.",
                "video_id": video.id if video else None,
            }
            job.result_json = json.dumps(result)
            job.status = "completed"
            db.commit()
        except Exception as exc:
            job.status = "failed"
            job.error = str(exc)
            db.commit()


def hash_content(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def search_documents(query: str, top_k: int) -> list[dict]:
    terms = set(re.findall(r"\w+", query.lower()))
    with SessionLocal() as db:
        docs = list(db.query(KnowledgeDocument).all())
    scored = []
    for doc in docs:
        words = set(re.findall(r"\w+", doc.content.lower()))
        score = len(terms & words) / max(len(terms), 1)
        if score > 0:
            scored.append({"document_id": doc.id, "filename": doc.filename, "score": round(score, 4), "excerpt": doc.content[:500]})
    return sorted(scored, key=lambda item: item["score"], reverse=True)[:top_k]
