from __future__ import annotations

import re
import shutil
import tempfile
import zipfile
from pathlib import Path

from .models import Bounds, LayerFile, LayerKind


GERBER_EXTENSIONS = {
    ".gbr",
    ".ger",
    ".pho",
    ".art",
    ".gtl",
    ".gbl",
    ".gko",
    ".gm1",
    ".gml",
    ".gto",
    ".gbo",
    ".gts",
    ".gbs",
    ".gtp",
    ".gbp",
}
DRILL_EXTENSIONS = {".drl", ".xln", ".exc"}


def prepare_input(source: Path) -> tuple[Path, tempfile.TemporaryDirectory[str] | None]:
    source = source.resolve()
    if source.is_dir():
        return source, None
    if not source.is_file() or source.suffix.lower() != ".zip":
        raise ValueError("Wybierz katalog Gerberów albo archiwum ZIP.")

    temporary = tempfile.TemporaryDirectory(prefix="ablatepcb_")
    root = Path(temporary.name)
    with zipfile.ZipFile(source) as archive:
        members = archive.infolist()
        if len(members) > 1000:
            temporary.cleanup()
            raise ValueError("Archiwum zawiera zbyt wiele plików.")
        total = sum(item.file_size for item in members)
        if total > 250 * 1024 * 1024:
            temporary.cleanup()
            raise ValueError("Rozpakowane archiwum przekroczyłoby 250 MB.")
        for item in members:
            candidate = (root / item.filename).resolve()
            if root not in candidate.parents and candidate != root:
                temporary.cleanup()
                raise ValueError("Archiwum zawiera niebezpieczną ścieżkę.")
        archive.extractall(root)
    return root, temporary


def _read_head(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")[:12000]
    except OSError:
        return ""


def classify(path: Path, root: Path) -> LayerFile:
    name = path.name.lower()
    suffix = path.suffix.lower()
    text = _read_head(path).lower()
    relative = str(path.relative_to(root))
    candidates: list[tuple[int, LayerKind, str]] = []

    def add(score: int, kind: LayerKind, reason: str) -> None:
        candidates.append((score, kind, reason))

    if suffix in DRILL_EXTENSIONS or text.startswith("m48"):
        if "via" in name or "through_via" in text:
            add(100, "drill_via", "nazwa/komentarz Via")
        elif "npth" in name or "non-plated" in text or "non plated" in text:
            add(100, "drill_npth", "nazwa/komentarz NPTH")
        else:
            add(80, "drill_pth", "plik Excellon")

    tokens = re.sub(r"[^a-z0-9]+", "_", name)
    if suffix == ".gtl" or "toplayer" in tokens or "f_cu" in tokens or "top_copper" in tokens:
        add(100, "top_copper", "rozszerzenie/nazwa górnej miedzi")
    if suffix == ".gbl" or "bottomlayer" in tokens or "b_cu" in tokens or "bottom_copper" in tokens:
        add(100, "bottom_copper", "rozszerzenie/nazwa dolnej miedzi")
    if suffix in {".gko", ".gm1", ".gml"} or any(x in tokens for x in ("boardoutline", "edge_cuts", "outline", "profile")):
        add(95, "outline", "nazwa/rozszerzenie obrysu")
    if suffix == ".gto" or "top_silk" in tokens or "topsilkscreen" in tokens:
        add(90, "top_silk", "górny opis")
    if suffix == ".gbo" or "bottom_silk" in tokens or "bottomsilkscreen" in tokens:
        add(90, "bottom_silk", "dolny opis")
    if suffix == ".gts" or "top_soldermask" in tokens or "f_mask" in tokens:
        add(90, "top_mask", "górna soldermaska")
    if suffix == ".gbs" or "bottom_soldermask" in tokens or "b_mask" in tokens:
        add(90, "bottom_mask", "dolna soldermaska")

    file_function = re.search(r"%tf\.filefunction,([^*]+)", text, re.IGNORECASE)
    if file_function:
        value = file_function.group(1).lower()
        if "copper" in value and "top" in value:
            add(110, "top_copper", "atrybut FileFunction")
        elif "copper" in value and ("bot" in value or "bottom" in value):
            add(110, "bottom_copper", "atrybut FileFunction")
        elif "profile" in value or "route" in value:
            add(110, "outline", "atrybut FileFunction")

    if not candidates:
        return LayerFile(path, relative, "other", 0, "nierozpoznany")
    score, kind, reason = max(candidates, key=lambda item: item[0])
    return LayerFile(path, relative, kind, score, reason)


def discover_layers(root: Path) -> list[LayerFile]:
    result: list[LayerFile] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.stat().st_size == 0:
            continue
        suffix = path.suffix.lower()
        if suffix in GERBER_EXTENSIONS | DRILL_EXTENSIONS or _read_head(path).startswith("M48"):
            result.append(classify(path, root))
    return result


def coordinate_bounds(path: Path) -> Bounds:
    """Return center-line coordinate bounds from a common RS-274X outline."""
    text = path.read_text(encoding="utf-8", errors="ignore")
    fmt = re.search(r"%FSL[AT]X(\d)(\d)Y(\d)(\d)\*%", text, re.IGNORECASE)
    x_dec = int(fmt.group(2)) if fmt else 5
    y_dec = int(fmt.group(4)) if fmt else 5
    units = 25.4 if "%MOIN" in text.upper() else 1.0
    x_values: list[float] = []
    y_values: list[float] = []
    for match in re.finditer(r"(?:X([+-]?\d+))?(?:Y([+-]?\d+))?D0[123]", text, re.IGNORECASE):
        if match.group(1) is not None:
            x_values.append(int(match.group(1)) / (10**x_dec) * units)
        if match.group(2) is not None:
            y_values.append(int(match.group(2)) / (10**y_dec) * units)
    if len(x_values) < 2 or len(y_values) < 2:
        raise ValueError(f"Nie można odczytać współrzędnych obrysu: {path.name}")
    return Bounds(min(x_values), min(y_values), max(x_values), max(y_values))


def copy_sources(layers: list[LayerFile], destination: Path) -> None:
    source_dir = destination / "source"
    source_dir.mkdir(parents=True, exist_ok=True)
    used: set[str] = set()
    for layer in layers:
        name = layer.path.name
        if name.lower() in used:
            name = f"{layer.kind}_{name}"
        used.add(name.lower())
        shutil.copy2(layer.path, source_dir / name)
