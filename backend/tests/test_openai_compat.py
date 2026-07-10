from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app

client = TestClient(app)
headers = {"Authorization": f"Bearer {settings.ctv_ai_api_key}"}


def test_models_requires_api_key() -> None:
    response = client.get("/v1/models")
    assert response.status_code == 401


def test_models_lists_specialists() -> None:
    response = client.get("/v1/models", headers=headers)
    assert response.status_code == 200

    model_ids = {item["id"] for item in response.json()["data"]}
    assert model_ids == {
        "ctv-ai-general",
        "ctv-ai-production",
        "ctv-ai-graphics",
        "ctv-ai-drone",
        "ctv-ai-it",
    }
