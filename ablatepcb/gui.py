from __future__ import annotations

import json
import ctypes
import sys
import threading
from pathlib import Path

import win32gui
from PySide6.QtCore import QDir, QObject, QPoint, QSettings, QStandardPaths, Qt, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices, QIcon
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication, QFileDialog, QListView, QMainWindow, QWidget

from .engine import Converter
from .lightburn import LightBurnConnector


class DropWebView(QWebEngineView):
    fileDropped = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        urls = event.mimeData().urls()
        if urls and urls[0].isLocalFile():
            event.acceptProposedAction()
            self.page().runJavaScript("window.setDropActive && window.setDropActive(true)")
            return
        super().dragEnterEvent(event)

    def dragLeaveEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        self.page().runJavaScript("window.setDropActive && window.setDropActive(false)")
        super().dragLeaveEvent(event)

    def dropEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        urls = event.mimeData().urls()
        self.page().runJavaScript("window.setDropActive && window.setDropActive(false)")
        if urls and urls[0].isLocalFile():
            self.fileDropped.emit(urls[0].toLocalFile())
            event.acceptProposedAction()
            return
        super().dropEvent(event)


class Bridge(QObject):
    analysisReady = Signal(str)
    generationReady = Signal(str)
    errorOccurred = Signal(str)
    busyChanged = Signal(bool, str)
    lightBurnStatus = Signal(str)
    lightBurnResult = Signal(str)
    activateRequested = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.converter = Converter()
        self.output_path: Path | None = None
        self._busy = False
        self._lightburn_busy = False
        self._polling = False
        self._language = "pl"
        self._picker: QFileDialog | None = None
        self._settings = QSettings("AblatePCB", "AblatePCBStudio")
        self._monitor = QTimer(self)
        self._monitor.setInterval(1500)
        self._monitor.timeout.connect(self.pollLightBurn)
        self._monitor.start()
        QTimer.singleShot(350, self.pollLightBurn)

    def _set_busy(self, value: bool, message: str = "") -> None:
        self._busy = value
        self.busyChanged.emit(value, message)

    def _tr(self, polish: str, english: str) -> str:
        return english if self._language == "en" else polish

    @Slot(str)
    def setLanguage(self, language: str) -> None:
        self._language = "en" if language == "en" else "pl"

    @Slot()
    def chooseInput(self) -> None:
        if self._busy:
            return
        dialog = self._new_picker(self._tr("Wybierz archiwum Gerber", "Choose Gerber archive"))
        dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptOpen)
        dialog.setDirectory(str(self._preferred_input_directory()))
        dialog.setNameFilters([
            self._tr("Archiwa Gerber (*.zip)", "Gerber archives (*.zip)"),
            self._tr("Wszystkie pliki (*.*)", "All files (*.*)"),
        ])
        dialog.fileSelected.connect(self._input_selected)
        dialog.open()

    @Slot()
    def chooseFolder(self) -> None:
        if self._busy:
            return
        dialog = self._new_picker(self._tr("Wybierz katalog z Gerberami", "Choose Gerber folder"))
        dialog.setFileMode(QFileDialog.FileMode.Directory)
        dialog.setOption(QFileDialog.Option.ShowDirsOnly, True)
        dialog.setDirectory(str(self._preferred_input_directory()))
        dialog.fileSelected.connect(self._folder_selected)
        dialog.open()

    def _preferred_input_directory(self) -> Path:
        saved = self._settings.value("inputDirectory", "", type=str)
        candidates = [
            Path(saved) if saved else None,
            Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation)),
            Path.home() / "Downloads",
            Path.home(),
        ]
        return next((candidate for candidate in candidates if candidate is not None and candidate.is_dir()), Path.home())

    @Slot(str)
    def _input_selected(self, path: str) -> None:
        self._settings.setValue("inputDirectory", str(Path(path).parent))
        self.analyzePath(path)

    @Slot(str)
    def _folder_selected(self, path: str) -> None:
        self._settings.setValue("inputDirectory", path)
        self.analyzePath(path)

    def _new_picker(self, title: str) -> QFileDialog:
        if self._picker is not None:
            self._picker.show()
            self._picker.raise_()
            self._picker.activateWindow()
            return self._picker
        parent = self.parent() if isinstance(self.parent(), QWidget) else None
        dialog = QFileDialog(parent, title)
        # The Qt picker avoids Windows shell/COM hangs. Drive shortcuts are
        # discovered at runtime, so no machine-specific path is hard-coded.
        dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
        dialog.setWindowModality(Qt.WindowModality.WindowModal)
        preferred = QUrl.fromLocalFile(str(self._preferred_input_directory()))
        locations = [preferred, *self._drive_urls(), *dialog.sidebarUrls()]
        unique_locations: list[QUrl] = []
        for location in locations:
            if location not in unique_locations:
                unique_locations.append(location)
        dialog.setSidebarUrls(unique_locations)
        dialog.resize(960, 640)
        sidebar = dialog.findChild(QListView, "sidebar")
        if sidebar is not None:
            sidebar.setMinimumWidth(210)
        dialog.finished.connect(self._picker_finished)
        dialog.finished.connect(dialog.deleteLater)
        self._picker = dialog
        return dialog

    @staticmethod
    def _drive_urls() -> list[QUrl]:
        drives = QDir.drives()
        if sys.platform != "win32":
            return [QUrl.fromLocalFile(info.absoluteFilePath()) for info in drives]
        get_drive_type = ctypes.WinDLL("kernel32", use_last_error=True).GetDriveTypeW
        get_drive_type.argtypes = [ctypes.c_wchar_p]
        get_drive_type.restype = ctypes.c_uint
        # Removable, fixed, optical, and RAM disks. Disconnected network
        # mappings are omitted because merely resolving their icon can freeze
        # the Windows shell; accessible network paths can still be entered.
        usable_types = {2, 3, 5, 6}
        result: list[QUrl] = []
        for info in drives:
            root = info.absoluteFilePath()
            native_root = root.replace("/", "\\")
            if get_drive_type(native_root) in usable_types:
                result.append(QUrl.fromLocalFile(root))
        return result

    @Slot(int)
    def _picker_finished(self, _result: int) -> None:
        self._picker = None

    @Slot(str)
    def analyzePath(self, path: str) -> None:
        if self._busy:
            return
        self.output_path = None
        self._set_busy(True, self._tr("Analizuję Gerbery, otwory i obrys…", "Analyzing Gerbers, drills, and outline…"))

        def task() -> None:
            try:
                analysis = self.converter.analyze(path)
                self.analysisReady.emit(json.dumps(analysis.to_dict(), ensure_ascii=False))
            except Exception as exc:  # noqa: BLE001 - error is shown in the UI
                self.errorOccurred.emit(str(exc))
            finally:
                self._set_busy(False, "")

        threading.Thread(target=task, daemon=True).start()

    @Slot(str)
    def generate(self, options_json: str) -> None:
        if self._busy:
            return
        try:
            options = json.loads(options_json)
        except json.JSONDecodeError:
            self.errorOccurred.emit("Nieprawidłowe ustawienia generowania.")
            return
        self._set_busy(True, self._tr("Renderuję maski 1270 DPI i buduję raport…", "Rendering 1270 DPI masks and building the report…"))

        def task() -> None:
            try:
                output = self.converter.generate(options)
                self.output_path = output
                self.generationReady.emit(json.dumps({"path": str(output)}, ensure_ascii=False))
            except Exception as exc:  # noqa: BLE001
                self.errorOccurred.emit(str(exc))
            finally:
                self._set_busy(False, "")

        threading.Thread(target=task, daemon=True).start()

    @Slot()
    def openOutput(self) -> None:
        if self.output_path and self.output_path.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.output_path)))

    @Slot()
    def openReport(self) -> None:
        if self.output_path:
            report = self.output_path / "RAPORT.html"
            if report.exists():
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(report)))

    @Slot(str, str)
    def loadGeneratedInLightBurn(self, side: str, options_json: str) -> None:
        if self._lightburn_busy:
            return
        try:
            options = json.loads(options_json)
            options["includeGeometry"] = True
            options["selectCenteredGraphic"] = True
        except (json.JSONDecodeError, TypeError):
            self.errorOccurred.emit("Nieprawidłowe ustawienia położenia LightBurn.")
            return
        if self.output_path is None:
            self.errorOccurred.emit("Najpierw wygeneruj pakiet LightBurn.")
            return
        names = {
            "top": "01_TOP_ablation.png",
            "bottom": "02_BOTTOM_selected_ablation.png",
        }
        if side not in names:
            self.errorOccurred.emit("Nieznana strona płytki.")
            return
        source = self.output_path / names[side]
        self._lightburn_busy = True
        self.busyChanged.emit(True, self._tr(
            f"Wczytuję {side.upper()} i ustawiam pozycję w LightBurn…",
            f"Loading {side.upper()} and setting its LightBurn position…",
        ))

        def task() -> None:
            try:
                connector = LightBurnConnector()
                connector.load_file(source)
                result = connector.apply_preset(options)
                lower_left = result["imageLowerLeft"]
                self.lightBurnResult.emit(json.dumps({
                    "action": "load_and_position",
                    **result,
                    "message": self._tr(
                        f"Wczytano {source.name} i zweryfikowano lewy dolny róg obrazu: X {lower_left['x']:.3f} / Y {lower_left['y']:.3f} mm.",
                        f"Loaded {source.name} and verified the image lower-left corner at X {lower_left['x']:.3f} / Y {lower_left['y']:.3f} mm.",
                    ),
                }, ensure_ascii=False))
            except Exception as exc:  # noqa: BLE001
                self.errorOccurred.emit(str(exc))
            finally:
                self._lightburn_busy = False
                self.busyChanged.emit(False, "")
                self.activateRequested.emit()

        threading.Thread(target=task, daemon=True).start()

    @Slot()
    def pollLightBurn(self) -> None:
        if self._polling or self._lightburn_busy:
            return
        self._polling = True

        def task() -> None:
            try:
                status = LightBurnConnector().status()
                self.lightBurnStatus.emit(json.dumps(status.to_dict(), ensure_ascii=False))
            finally:
                self._polling = False

        threading.Thread(target=task, daemon=True).start()

    @Slot()
    def openLightBurn(self) -> None:
        if self._lightburn_busy:
            return
        self._lightburn_busy = True
        self.busyChanged.emit(True, self._tr("Otwieram LightBurn…", "Opening LightBurn…"))

        def task() -> None:
            try:
                result = LightBurnConnector().open_or_focus()
                result["message"] = self._tr(
                    "LightBurn został otwarty lub przeniesiony na pierwszy plan.",
                    "LightBurn was opened or brought to the foreground.",
                )
                self.lightBurnResult.emit(json.dumps(result, ensure_ascii=False))
            except Exception as exc:  # noqa: BLE001
                self.errorOccurred.emit(str(exc))
            finally:
                self._lightburn_busy = False
                self.busyChanged.emit(False, "")
                QTimer.singleShot(800, self.pollLightBurn)

        threading.Thread(target=task, daemon=True).start()

    @Slot(str)
    def applyLightBurnPreset(self, options_json: str) -> None:
        if self._lightburn_busy:
            return
        try:
            options = json.loads(options_json)
        except json.JSONDecodeError:
            self.errorOccurred.emit("Nieprawidłowy preset LightBurn.")
            return
        self._lightburn_busy = True
        self.busyChanged.emit(True, self._tr("Nakładam preset na aktywną warstwę LightBurn…", "Applying preset to the active LightBurn layer…"))

        def task() -> None:
            try:
                result = LightBurnConnector().apply_preset(options)
                self.lightBurnResult.emit(json.dumps({"action": "preset", **result}, ensure_ascii=False))
            except Exception as exc:  # noqa: BLE001
                self.errorOccurred.emit(str(exc))
            finally:
                self._lightburn_busy = False
                self.busyChanged.emit(False, "")
                self.activateRequested.emit()
                QTimer.singleShot(250, self.pollLightBurn)

        threading.Thread(target=task, daemon=True).start()

    @Slot(str, bool)
    def lightBurnAction(self, action: str, armed: bool) -> None:
        if self._lightburn_busy:
            return
        self._lightburn_busy = True

        def task() -> None:
            try:
                LightBurnConnector().action(action, armed)
                self.lightBurnResult.emit(json.dumps({"action": action, "message": f"Polecenie {action} przekazane do LightBurn."}, ensure_ascii=False))
            except Exception as exc:  # noqa: BLE001
                self.errorOccurred.emit(str(exc))
            finally:
                self._lightburn_busy = False
                self.activateRequested.emit()
                QTimer.singleShot(350, self.pollLightBurn)

        threading.Thread(target=task, daemon=True).start()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("AblatePCB Studio")
        self.resize(1380, 880)
        self.setMinimumSize(980, 680)
        self.view = DropWebView(self)
        self.bridge = Bridge(self)
        self.bridge.activateRequested.connect(self._activate_after_lightburn)
        self.view.fileDropped.connect(self.bridge.analyzePath)
        channel = QWebChannel(self.view.page())
        channel.registerObject("backend", self.bridge)
        self.view.page().setWebChannel(channel)
        self._channel = channel
        settings = self.view.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        web_file = Path(__file__).resolve().parent / "web" / "index.html"
        self.setWindowIcon(QIcon(str(web_file.parent / "logo.png")))
        self.view.load(QUrl.fromLocalFile(str(web_file)))
        self.setCentralWidget(self.view)

    def _activate_after_lightburn(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()

    def place_on_lightburn_screen(self) -> None:
        """Place this window on the monitor currently occupied by LightBurn."""
        if sys.platform != "win32":
            return
        found = LightBurnConnector.find_window()
        if found is None:
            return
        left, top, right, bottom = win32gui.GetWindowRect(found[0])
        screen = QApplication.screenAt(QPoint((left + right) // 2, (top + bottom) // 2))
        if screen is None:
            return
        area = screen.availableGeometry()
        margin = 18
        self.setGeometry(area.x() + margin, area.y() + margin, max(980, area.width() - margin * 2), max(680, area.height() - margin * 2))

    def closeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        self.bridge.converter.close()
        super().closeEvent(event)


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("AblatePCB Studio")
    app.setOrganizationName("Local PCB Tools")
    window = MainWindow()
    window.place_on_lightburn_screen()
    window.show()
    return app.exec()
