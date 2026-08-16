from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


ROOT = Path(__file__).resolve().parents[2]
README = ROOT / "README.md"
DOCKERFILE = ROOT / "Dockerfile"
COMPOSE = ROOT / "docker-compose.yml"


def test_documented_launch_and_health_urls_use_port_8080():
    readme = README.read_text(encoding="utf-8")

    assert "uvicorn app.main:app --reload --port 8080" in readme
    assert "http://127.0.0.1:8080" in readme
    assert "http://127.0.0.1:8080/health" in readme
    assert "http://127.0.0.1:8000" not in readme


def test_docker_defaults_match_documented_port_8080():
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")
    compose = COMPOSE.read_text(encoding="utf-8")

    assert "EXPOSE 8080" in dockerfile
    assert "--port ${PORT:-8080}" in dockerfile
    assert "8080:8080" in compose
    assert "8000:8000" not in compose
    assert "EXPOSE 8000" not in dockerfile
    assert "--port 8000" not in dockerfile


def test_health_endpoint_matches_documented_contract():
    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "who-am-i",
        "version": "0.2.0",
    }
