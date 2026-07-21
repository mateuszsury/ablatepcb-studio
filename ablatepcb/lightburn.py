from __future__ import annotations

import re
import ctypes
import math
import os
import shutil
import socket
import subprocess
import time
from pathlib import Path
from dataclasses import asdict, dataclass
from typing import Any

import win32gui
import win32process


IDS = {
    "status": "MainWindow.dwLaser.dockWidgetContents_2.lsLaserStatus.lblStatus",
    "start": "MainWindow.dwLaser.dockWidgetContents_2.pbStart",
    "stop": "MainWindow.dwLaser.dockWidgetContents_2.pbStop",
    "pause": "MainWindow.dwLaser.dockWidgetContents_2.pbPause",
    "frame": "MainWindow.dwLaser.dockWidgetContents_2.pbFrame",
    "origin": "MainWindow.dwLaser.dockWidgetContents_2.cbCutOrigin",
    "console": "MainWindow.ConsoleWidget.dockWidgetContents.container.teConsole",
    "speed": "MainWindow.dwCuts.dockWidgetContents.stackCutInfo.gbCutInfoBox.sbSpeed",
    "power": "MainWindow.dwCuts.dockWidgetContents.stackCutInfo.gbCutInfoBox.sbMaxPower",
    "passes": "MainWindow.dwCuts.dockWidgetContents.stackCutInfo.gbCutInfoBox.sbNumberOfPasses",
    "interval": "MainWindow.dwCuts.dockWidgetContents.stackCutInfo.gbCutInfoBox.sbInterval",
}


@dataclass(slots=True)
class LiveStatus:
    connected: bool = False
    title: str = "LightBurn niedostępny"
    ui_status: str = "Offline"
    controller: str = "Unknown"
    elapsed: str = "—"
    remaining: str = "—"
    progress: float = 0.0
    x: float | None = None
    y: float | None = None
    feed: float | None = None
    power: float | None = None
    layer_speed: float | None = None
    layer_power: float | None = None
    layer_passes: int | None = None
    layer_interval: float | None = None
    message: str = "Uruchom LightBurn, aby połączyć aplikację."

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _time_seconds(value: str) -> int:
    parts = [int(item) for item in value.split(":")]
    total = 0
    for part in parts:
        total = total * 60 + part
    return total


class LightBurnConnector:
    @staticmethod
    def _udp_command(command: str, timeout: float = 2.0) -> str:
        """Use LightBurn's documented local UDP automation interface."""
        outgoing = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        incoming = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        incoming.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        incoming.settimeout(timeout)
        try:
            incoming.bind(("127.0.0.1", 19841))
            outgoing.sendto(command.encode("utf-8"), ("127.0.0.1", 19840))
            response, _address = incoming.recvfrom(1024)
            return response.decode("utf-8", errors="replace").strip()
        except OSError as exc:
            raise RuntimeError(f"Brak odpowiedzi interfejsu LightBurn UDP: {exc}") from exc
        finally:
            incoming.close()
            outgoing.close()

    @staticmethod
    def _process_executable(pid: int) -> str:
        """Return the executable name without depending on psutil.

        Matching the process is important because this application also has
        "LightBurn" in its own window title.
        """
        process_query_limited_information = 0x1000
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
        kernel32.OpenProcess.restype = ctypes.c_void_p
        kernel32.QueryFullProcessImageNameW.argtypes = [
            ctypes.c_void_p,
            ctypes.c_ulong,
            ctypes.c_wchar_p,
            ctypes.POINTER(ctypes.c_ulong),
        ]
        kernel32.QueryFullProcessImageNameW.restype = ctypes.c_int
        kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
        kernel32.CloseHandle.restype = ctypes.c_int
        handle = kernel32.OpenProcess(process_query_limited_information, False, pid)
        if not handle:
            return ""
        try:
            size = ctypes.c_ulong(32768)
            buffer = ctypes.create_unicode_buffer(size.value)
            if not kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
                return ""
            return Path(buffer.value).name.lower()
        finally:
            kernel32.CloseHandle(handle)

    @staticmethod
    def find_window() -> tuple[int, int, str] | None:
        result: list[tuple[int, int, str]] = []

        def callback(hwnd: int, _extra: object) -> None:
            if not win32gui.IsWindowVisible(hwnd):
                return
            title = win32gui.GetWindowText(hwnd)
            if "lightburn" not in title.lower():
                return
            _thread, pid = win32process.GetWindowThreadProcessId(hwnd)
            if LightBurnConnector._process_executable(pid) == "lightburn.exe":
                result.append((hwnd, pid, title))

        win32gui.EnumWindows(callback, None)
        return result[0] if result else None

    def _window(self):  # type: ignore[no-untyped-def]
        # Import lazily so pywinauto cannot change the GUI thread's COM mode
        # before Qt initializes the native Windows file picker.
        from pywinauto import Application

        found = self.find_window()
        if found is None:
            raise RuntimeError("LightBurn nie jest uruchomiony.")
        hwnd, pid, _title = found
        app = Application(backend="uia").connect(process=pid, timeout=3)
        return app, app.window(handle=hwnd), found

    def open_or_focus(self) -> dict[str, Any]:
        found = self.find_window()
        if found is not None:
            hwnd, _pid, _title = found
            try:
                win32gui.ShowWindow(hwnd, 9)  # SW_RESTORE
                win32gui.BringWindowToTop(hwnd)
                win32gui.SetForegroundWindow(hwnd)
            except Exception:
                pass
            return {"action": "focus", "launched": False}

        candidates: list[Path] = []
        from_path = shutil.which("LightBurn.exe")
        if from_path:
            candidates.append(Path(from_path))
        for variable in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA"):
            root = os.environ.get(variable)
            if root:
                candidates.extend((Path(root) / "LightBurn" / "LightBurn.exe", Path(root) / "LightBurn Software" / "LightBurn.exe"))
        for executable in candidates:
            if executable.is_file():
                subprocess.Popen([str(executable)], cwd=str(executable.parent), close_fds=True)  # noqa: S603
                return {"action": "launch", "launched": True, "path": str(executable)}
        raise FileNotFoundError("Nie znaleziono instalacji LightBurn. Uruchom LightBurn ręcznie lub zainstaluj go w standardowym katalogu.")

    @staticmethod
    def _legacy_number(control) -> float | None:  # type: ignore[no-untyped-def]
        try:
            raw = control.legacy_properties().get("Value", control.window_text())
            return float(str(raw).replace(" ", "").replace(",", "."))
        except (TypeError, ValueError):
            return None

    def status(self) -> LiveStatus:
        try:
            _app, window, found = self._window()
            ui_status = window.child_window(auto_id=IDS["status"]).wrapper_object().window_text().strip() or "Unknown"
            result = LiveStatus(connected=True, title=found[2], ui_status=ui_status, message="Połączenie lokalne z LightBurn aktywne.")
            time_match = re.search(r"(\d+(?::\d+)+)\s*\((\d+(?::\d+)+)\)", ui_status)
            if time_match:
                result.elapsed, result.remaining = time_match.group(1), time_match.group(2)
                elapsed_s, remaining_s = _time_seconds(result.elapsed), _time_seconds(result.remaining)
                result.progress = elapsed_s / max(1, elapsed_s + remaining_s)
            for key, attribute in (("speed", "layer_speed"), ("power", "layer_power"), ("interval", "layer_interval")):
                control = window.child_window(auto_id=IDS[key]).wrapper_object()
                setattr(result, attribute, self._legacy_number(control))
            passes = self._legacy_number(window.child_window(auto_id=IDS["passes"]).wrapper_object())
            result.layer_passes = int(passes) if passes is not None else None

            if ui_status.lower().startswith(("busy", "ready", "paused", "hold")):
                console = window.child_window(auto_id=IDS["console"]).wrapper_object().window_text()
                tail = console[-50000:]
                states = list(re.finditer(r"<(Idle|Run|Hold:[^|>]+|Alarm:[^|>]+)\|MPos:([^|>]+).*?\|FS:([\d.]+),([\d.]+)", tail))
                if states:
                    latest = states[-1]
                    result.controller = latest.group(1)
                    coords = latest.group(2).split(",")
                    result.x = float(coords[0])
                    result.y = float(coords[1])
                    result.feed = float(latest.group(3))
                    result.power = float(latest.group(4))
            return result
        except Exception as exc:  # noqa: BLE001 - status must degrade to offline
            return LiveStatus(message=str(exc))

    def _range_set(self, control, value: float) -> None:  # type: ignore[no-untyped-def]
        from pywinauto.uia_defines import IUIA

        uia = IUIA()
        unknown = control.element_info.element.GetCurrentPattern(uia.UIA_dll.UIA_RangeValuePatternId)
        pattern = unknown.QueryInterface(uia.UIA_dll.IUIAutomationRangeValuePattern)
        if pattern.CurrentIsReadOnly:
            raise RuntimeError("Pole LightBurn jest tylko do odczytu.")
        if value < pattern.CurrentMinimum or value > pattern.CurrentMaximum:
            raise ValueError(f"Wartość {value} jest poza zakresem LightBurn.")
        pattern.SetValue(float(value))

    def _numeric_set(self, control, value: float) -> None:  # type: ignore[no-untyped-def]
        """Set a Qt numeric field and verify that LightBurn accepted the value."""
        try:
            self._range_set(control, value)
            if self._wait_for_numeric_value(control, value, 0.25):
                return
        except Exception:
            pass
        try:
            from pywinauto.uia_defines import IUIA

            uia = IUIA()
            unknown = control.element_info.element.GetCurrentPattern(uia.UIA_dll.UIA_LegacyIAccessiblePatternId)
            pattern = unknown.QueryInterface(uia.UIA_dll.IUIAutomationLegacyIAccessiblePattern)
            pattern.SetValue((f"{value:g}").replace(".", ","))
            if self._wait_for_numeric_value(control, value, 0.25):
                return
        except Exception:
            pass

        # LightBurn's Qt spin boxes can report success for both UIA patterns
        # without changing their value. Keyboard entry is the reliable final
        # path, but only after the selected graphic makes the field editable.
        if not control.is_enabled():
            raise RuntimeError("Pole położenia LightBurn jest nieaktywne. Nie udało się zaznaczyć wczytanej grafiki.")
        from pywinauto import keyboard

        control.click_input()
        keyboard.send_keys("^a")
        keyboard.send_keys((f"{value:g}").replace(".", ","), with_spaces=True)
        keyboard.send_keys("{ENTER}")
        if not self._wait_for_numeric_value(control, value, 1.0):
            actual = self._legacy_number(control)
            raise RuntimeError(f"LightBurn nie przyjął wartości {value:g}; odczytano {actual!r}.")

    def _wait_for_numeric_value(self, control, expected: float, timeout: float) -> bool:  # type: ignore[no-untyped-def]
        deadline = time.monotonic() + timeout
        while True:
            actual = self._legacy_number(control)
            if actual is not None and math.isclose(actual, expected, rel_tol=1e-6, abs_tol=0.001):
                return True
            if time.monotonic() >= deadline:
                return False
            time.sleep(0.05)

    @staticmethod
    def _position_controls(window):  # type: ignore[no-untyped-def]
        x_controls = sorted(
            [item for item in window.descendants(control_type="Spinner") if item.element_info.automation_id == "MainWindow.tbNumericEdits.QXYControl.sbX"],
            key=lambda item: item.rectangle().left,
        )
        y_controls = sorted(
            [item for item in window.descendants(control_type="Spinner") if item.element_info.automation_id == "MainWindow.tbNumericEdits.QXYControl.sbY"],
            key=lambda item: item.rectangle().left,
        )
        return x_controls, y_controls

    def _select_centered_graphic(self, window, force: bool = False) -> tuple[list[Any], list[Any]]:  # type: ignore[no-untyped-def]
        x_controls, y_controls = self._position_controls(window)
        if len(x_controls) < 2 or len(y_controls) < 2:
            raise RuntimeError("Nie znaleziono kontrolek położenia obrazu w LightBurn.")
        if not force and x_controls[0].is_enabled() and y_controls[0].is_enabled():
            return x_controls, y_controls

        # LightBurn IMPORT places the image in the center of the edit area.
        # Clicking the exact canvas center selects that image without relying
        # on a language-specific menu or keyboard focus.
        canvas = window.child_window(auto_id="MainWindow.centralWidget.ewEdit").wrapper_object()
        rect = canvas.rectangle()
        canvas.click_input(coords=((rect.right - rect.left) // 2, (rect.bottom - rect.top) // 2))
        deadline = time.monotonic() + 3.0
        while time.monotonic() < deadline:
            x_controls, y_controls = self._position_controls(window)
            if len(x_controls) >= 2 and len(y_controls) >= 2 and x_controls[0].is_enabled() and y_controls[0].is_enabled():
                return x_controls, y_controls
            time.sleep(0.1)
        raise RuntimeError("Maska została wczytana, ale LightBurn nie pozwolił jej zaznaczyć i ustawić pozycji.")

    def apply_preset(self, options: dict[str, Any]) -> dict[str, Any]:
        app, window, _found = self._window()
        current = window.child_window(auto_id=IDS["status"]).wrapper_object().window_text()
        if current.lower().startswith(("busy", "paused", "hold")):
            raise RuntimeError("Nie można zmieniać presetu podczas pracy lasera.")
        values = {
            "speed": float(options.get("speed", 3000)),
            "power": float(options.get("power", 50)),
            "passes": float(options.get("passes", 2)),
            "interval": float(options.get("interval", 0.05)),
        }
        for key, value in values.items():
            self._numeric_set(window.child_window(auto_id=IDS[key]).wrapper_object(), value)

        include_geometry = bool(options.get("includeGeometry", True))
        position_applied = False
        if include_geometry:
            # Selected image: first X/Y pair is position, second pair is width/height.
            x_controls, y_controls = self._select_centered_graphic(window, force=bool(options.get("selectCenteredGraphic", False)))
        else:
            x_controls, y_controls = [], []
        if include_geometry and len(x_controls) >= 2 and len(y_controls) >= 2:
            board_w = float(options.get("boardWidth", 0))
            board_h = float(options.get("boardHeight", 0))
            blank_w = max(board_w, float(options.get("blankWidth", board_w)))
            blank_h = max(board_h, float(options.get("blankHeight", board_h)))
            center_x = float(options.get("originX", 10)) + blank_w / 2
            center_y = float(options.get("originY", 10)) + blank_h / 2

            # Coordinate fields must describe the image center, independent
            # of the anchor the user previously selected in LightBurn.
            center_anchor = window.child_window(auto_id="MainWindow.tbNumericEdits.OriginWidget.grpOrigin.rb_MM").wrapper_object()
            center_anchor.click_input()
            self._numeric_set(x_controls[1], board_w)
            self._numeric_set(y_controls[1], board_h)
            self._numeric_set(x_controls[0], center_x)
            self._numeric_set(y_controls[0], center_y)

            actual_x = self._legacy_number(x_controls[0])
            actual_y = self._legacy_number(y_controls[0])
            actual_w = self._legacy_number(x_controls[1])
            actual_h = self._legacy_number(y_controls[1])
            expected = (center_x, center_y, board_w, board_h)
            actual = (actual_x, actual_y, actual_w, actual_h)
            position_applied = all(
                value is not None and math.isclose(value, target, rel_tol=1e-6, abs_tol=0.001)
                for value, target in zip(actual, expected, strict=True)
            )
            if not position_applied:
                raise RuntimeError(f"Weryfikacja pozycji LightBurn nie powiodła się: oczekiwano {expected}, odczytano {actual}.")

        if include_geometry:
            # Absolute coordinates are required for deterministic placement.
            origin = window.child_window(auto_id=IDS["origin"]).wrapper_object()
            try:
                origin.select("Współrzędne bezwzględne")
            except Exception:
                pass

        return {
            "numericPreset": True,
            "imagePreset": "lightburn_default",
            "positionApplied": position_applied,
            "center": {"x": center_x, "y": center_y} if include_geometry else None,
            "imageLowerLeft": {
                "x": center_x - float(options.get("boardWidth", 0)) / 2,
                "y": center_y - float(options.get("boardHeight", 0)) / 2,
            } if include_geometry else None,
            "message": (
                "Zastosowano prędkość, moc, interwał, liczbę przejść, rozmiar i pozycję. Ustawienia obrazu korzystają z zapisanego profilu LightBurn."
                if include_geometry
                else "Zastosowano prędkość, moc, interwał i liczbę przejść do aktywnej warstwy LightBurn. Geometria nie została zmieniona."
            ),
        }

    def load_file(self, path: str | Path) -> None:
        source = Path(path).resolve()
        if not source.is_file():
            raise FileNotFoundError(f"Nie znaleziono pliku: {source}")
        if source.suffix.lower() not in {".png", ".lbrn", ".lbrn2"}:
            raise ValueError("Do LightBurn można wczytać tylko PNG, LBRN lub LBRN2.")
        if self.find_window() is None:
            raise RuntimeError("LightBurn nie jest uruchomiony.")
        # PNG is artwork, so import it into the current project instead of
        # replacing that project and triggering an unsaved-changes dialog.
        command = "IMPORT" if source.suffix.lower() == ".png" else "LOADFILE"
        response = self._udp_command(f"{command}:{source}")
        if response != "OK":
            raise RuntimeError(f"LightBurn odrzucił plik ({response or 'brak odpowiedzi'}).")

    def action(self, name: str, armed: bool = False) -> None:
        _app, window, _found = self._window()
        current = window.child_window(auto_id=IDS["status"]).wrapper_object().window_text().lower()
        if name == "start":
            if not armed:
                raise RuntimeError("Start wymaga potwierdzenia bezpieczeństwa.")
            if not current.startswith("ready"):
                raise RuntimeError(f"LightBurn nie jest gotowy do Start: {current}")
            response = self._udp_command("START")
            if response != "OK":
                raise RuntimeError(f"LightBurn odrzucił Start ({response or 'brak odpowiedzi'}).")
            return
        if name == "frame" and not current.startswith("ready"):
            raise RuntimeError(f"Frame jest dostępny tylko w stanie Ready: {current}")
        if name not in ("start", "stop", "pause", "frame"):
            raise ValueError("Nieznana akcja LightBurn.")
        window.child_window(auto_id=IDS[name]).wrapper_object().invoke()
