from types import SimpleNamespace

from src.webapp import serve


def test_browser_url_for_server_uses_loopback_for_wildcard_hosts() -> None:
    assert serve.browser_url_for_server(host="0.0.0.0", port=8080) == "http://127.0.0.1:8080/"
    assert serve.browser_url_for_server(host="::", port=8080) == "http://127.0.0.1:8080/"


def test_main_accepts_process_only_host_port_override(monkeypatch) -> None:
    calls: dict[str, object] = {}
    app = SimpleNamespace(
        state=SimpleNamespace(
            runtime_config=SimpleNamespace(
                webapp=SimpleNamespace(host="127.0.0.1", port=8000),
            )
        )
    )
    monkeypatch.setattr(serve, "create_app", lambda profile: app)
    monkeypatch.setattr(
        serve.uvicorn,
        "run",
        lambda app_arg, *, host, port: calls.update({"app": app_arg, "host": host, "port": port}),
    )
    monkeypatch.setattr(
        "sys.argv",
        ["yyt1771-web", "--profile", "dev_lab", "--host", "0.0.0.0", "--port", "8123"],
    )

    serve.main()

    assert calls == {"app": app, "host": "0.0.0.0", "port": 8123}


def test_main_schedules_browser_open_when_requested(monkeypatch) -> None:
    calls: dict[str, object] = {}
    app = SimpleNamespace(
        state=SimpleNamespace(
            runtime_config=SimpleNamespace(
                webapp=SimpleNamespace(host="0.0.0.0", port=8080),
            )
        )
    )
    monkeypatch.setattr(serve, "create_app", lambda profile: app)
    monkeypatch.setattr(
        serve.uvicorn,
        "run",
        lambda app_arg, *, host, port: calls.update({"app": app_arg, "host": host, "port": port}),
    )
    monkeypatch.setattr(serve, "_schedule_browser_open", lambda *, host, port: calls.update({"browser": (host, port)}))
    monkeypatch.setattr("sys.argv", ["yyt1771-web", "--profile", "dev_lab", "--open-browser"])

    serve.main()

    assert calls == {"browser": ("0.0.0.0", 8080), "app": app, "host": "0.0.0.0", "port": 8080}
