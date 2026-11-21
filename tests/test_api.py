from fastapi.testclient import TestClient
from app.main import app


def test_health():
    with TestClient(app) as client:
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


def test_upload_rejects_non_video():
    with TestClient(app) as client:
        response = client.post("/api/v1/videos/upload", files={"file": ("notes.txt", b"not a video", "text/plain")})
        assert response.status_code == 400


def test_document_retrieval():
    with TestClient(app) as client:
        uploaded = client.post("/api/v1/documents/upload", files={"file": ("safety.txt", b"road safety collision evidence", "text/plain")})
        assert uploaded.status_code == 201
        response = client.post("/api/v1/retrieval/query", json={"query": "collision evidence"})
        assert response.status_code == 200
        assert response.json()
