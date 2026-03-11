from fastapi.testclient import TestClient

from src.webapp.app import create_app


def test_app_can_be_created() -> None:
    app = create_app(profile="dev_mock")

    assert app.title == "YYT1771 Web API"
    assert app.state.profile == "dev_mock"


def test_health_returns_basic_status_payload() -> None:
    client = TestClient(create_app(profile="dev_lab"))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "app": "YYT1771 Web API",
        "profile": "dev_lab",
    }
