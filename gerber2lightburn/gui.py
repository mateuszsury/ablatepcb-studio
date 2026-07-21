from __future__ import annotations

import json
import sys
import threading
from pathlib import Path

import win32gui
from PySide6.QtCore import QObject, QPoint, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices, QIcon
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication, QFileDialog, QMainWindow

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
        path, _ = QFileDialog.getOpenFileName(
            None,
            self._tr("Wybierz archiwum Gerber", "Choose Gerber archive"),
            str(Path.home() / "Downloads"),
            self._tr("Gerber ZIP (*.zip);;Wszystkie pliki (*.*)", "Gerber ZIP (*.zip);;All files (*.*)"),
        )
        if path:
            self.analyzePath(path)

    @Slot()
    def chooseFolder(self) -> None:
        if self._busy:
            return
        path = QFileDialog.getExistingDirectory(None, self._tr("Wybierz katalog z Gerberami", "Choose Gerber folder"), str(Path.home()))
        if path:
            self.analyzePath(path)

    @Slot(str)
    def analyzePath(self, path: str) -> None:
        if self._busy:
            return
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

    @Slot(str)
    def loadGeneratedInLightBurn(self, side: str) -> None:
        if self._lightburn_busy:
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
        self.busyChanged.emit(True, self._tr(f"Wczytuję {side.upper()} do LightBurn…", f"Loading {side.upper()} into LightBurn…"))

        def task() -> None:
            try:
                LightBurnConnector().load_file(source)
                self.lightBurnResult.emit(json.dumps({
                    "action": "load",
                    "message": f"Przekazano {source.name} do LightBurn. Jeśli pojawiło się pytanie o niezapisany projekt, odpowiedz w LightBurn, a następnie zastosuj preset.",
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
        self.setWindowTitle("Gerber2LightBurn PCB")
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
    app.setApplicationName("Gerber2LightBurn PCB")
    app.setOrganizationName("Local PCB Tools")
    window = MainWindow()
    window.place_on_lightburn_screen()
    window.show()
    return app.exec()
