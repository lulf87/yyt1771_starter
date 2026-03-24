import pytest

from src.desktop_app.main import build_parser, main


def test_desktop_main_parser_defaults_to_dev_mock() -> None:
    parser = build_parser()

    args = parser.parse_args([])

    assert args.profile == "dev_mock"


def test_desktop_main_exits_with_clear_message_when_pyside6_is_missing(monkeypatch) -> None:
    monkeypatch.setattr("sys.argv", ["yyt1771-desktop", "--profile", "dev_mock"])

    with pytest.raises(SystemExit, match="PySide6 is not installed"):
        main()
