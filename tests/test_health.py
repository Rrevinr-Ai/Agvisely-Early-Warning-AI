from fastapi.testclient import TestClient


def test_root_health():
    from app.main import app

    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
