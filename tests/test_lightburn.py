from pathlib import Path

from ablatepcb.lightburn import LightBurnConnector


def _capture_command(monkeypatch, source: Path) -> str:  # type: ignore[no-untyped-def]
    connector = LightBurnConnector()
    commands: list[str] = []
    monkeypatch.setattr(connector, "find_window", lambda: (1, 2, "LightBurn"))
    monkeypatch.setattr(connector, "_udp_command", lambda command: commands.append(command) or "OK")
    connector.load_file(source)
    return commands[0]


def test_png_is_imported_without_replacing_current_project(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    source = tmp_path / "mask.png"
    source.write_bytes(b"png")
    assert _capture_command(monkeypatch, source) == f"IMPORT:{source.resolve()}"


def test_lightburn_project_uses_loadfile(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    source = tmp_path / "project.lbrn2"
    source.write_text("project", encoding="utf-8")
    assert _capture_command(monkeypatch, source) == f"LOADFILE:{source.resolve()}"
