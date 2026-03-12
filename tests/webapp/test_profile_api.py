from fastapi.testclient import TestClient

from src.webapp.app import create_app


def test_profile_api_returns_runtime_profile_payload() -> None:
    client = TestClient(create_app(profile="prod_win"))

    response = client.get("/api/system/profile")

    assert response.status_code == 200
    assert response.json() == {
        "profile": "prod_win",
        "platform": "windows",
        "mode": "production",
        "webapp": {
            "host": "0.0.0.0",
            "port": 8080,
        },
        "adapters": {
            "camera": "hik_rtsp_opencv",
            "temp": "modbus_temp",
            "plc": "modbus_tcp",
        },
    }
