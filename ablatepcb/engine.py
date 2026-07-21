from __future__ import annotations

import base64
import hashlib
import io
import json
import math
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageOps
from pygerber.gerberx3.api.v2 import (
    DEFAULT_ALPHA_COLOR_MAP,
    FileTypeEnum,
    GerberFile,
    ImageFormatEnum,
    PixelFormatEnum,
)

from .detect import coordinate_bounds, copy_sources, discover_layers, prepare_input
from .excellon import merge_drills, parse_excellon
from .models import Analysis, Bounds, Check, GenerationOptions, LayerFile
from .report import build_report, build_text_instructions


def _gerber_info(path: Path, file_type: FileTypeEnum) -> tuple[object, Bounds]:
    parsed = GerberFile.from_file(path, file_type=file_type).parse()
    info = parsed.get_info()
    bounds = Bounds(float(info.min_x_mm), float(info.min_y_mm), float(info.max_x_mm), float(info.max_y_mm))
    return parsed, bounds


def _smallest_aperture(paths: list[Path]) -> float | None:
    values: list[float] = []
    pattern = re.compile(r"%ADD\d+C,([\d.]+)", re.IGNORECASE)
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="ignore")
        values.extend(float(item) for item in pattern.findall(text) if float(item) >= 0.05)
    return min(values, default=None)


def _render_copper(layer: LayerFile, board: Bounds, dpmm: int) -> tuple[Image.Image, Bounds]:
    parsed, copper_bounds = _gerber_info(layer.path, FileTypeEnum.COPPER)
    buffer = io.BytesIO()
    parsed.render_raster(
        buffer,
        color_scheme=DEFAULT_ALPHA_COLOR_MAP[FileTypeEnum.COPPER],
        dpmm=dpmm,
        pixel_format=PixelFormatEnum.RGBA,
        image_format=ImageFormatEnum.PNG,
        quality=100,
    )
    source = Image.open(io.BytesIO(buffer.getvalue())).convert("RGBA")
    alpha = source.getchannel("A")
    width = max(1, round(board.width * dpmm))
    height = max(1, round(board.height * dpmm))
    result = Image.new("L", (width, height), 0)
    x = round((copper_bounds.min_x - board.min_x) * dpmm)
    y = round((board.max_y - copper_bounds.max_y) * dpmm)
    result.paste(alpha, (x, y))
    return result, copper_bounds


def _data_uri(image: Image.Image, max_width: int = 1100) -> str:
    preview = image.copy()
    if preview.width > max_width:
        height = round(preview.height * max_width / preview.width)
        preview = preview.resize((max_width, height), Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    preview.save(buffer, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


def _mark_drills(image: Image.Image, analysis: Analysis, dpmm: int) -> Image.Image:
    rgb = image.convert("RGB")
    draw = ImageDraw.Draw(rgb)
    board = analysis.board_bounds
    for hit in analysis.drills:
        x = (hit.x - board.min_x) * dpmm
        y = (board.max_y - hit.y) * dpmm
        radius = max(2.5, hit.diameter * dpmm / 2)
        color = {"via": "#ffb000", "pth": "#00c2ff", "npth": "#ff4d77"}[hit.category]
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), outline=color, width=max(1, dpmm // 16))
        draw.line((x - radius, y, x + radius, y), fill=color, width=1)
        draw.line((x, y - radius, x, y + radius), fill=color, width=1)
    return rgb


def _overlay(top: Image.Image, bottom: Image.Image) -> Image.Image:
    t = np.asarray(top, dtype=np.float32) / 255.0
    b = np.asarray(bottom, dtype=np.float32) / 255.0
    canvas = np.full((top.height, top.width, 3), 245.0, dtype=np.float32)
    canvas[..., 0] = np.minimum(canvas[..., 0], 245 - 190 * t)
    canvas[..., 1] = np.minimum(canvas[..., 1], 245 - 205 * b)
    canvas[..., 2] = np.minimum(canvas[..., 2], 245 - 190 * b)
    canvas[..., 0] += 145 * b
    return Image.fromarray(np.clip(canvas, 0, 255).astype(np.uint8), "RGB")


class Converter:
    def __init__(self) -> None:
        self._temporary: tempfile.TemporaryDirectory[str] | None = None
        self.analysis: Analysis | None = None

    def close(self) -> None:
        if self._temporary is not None:
            self._temporary.cleanup()
            self._temporary = None

    def analyze(self, source: str | Path) -> Analysis:
        self.close()
        source_path = Path(source).resolve()
        root, temporary = prepare_input(source_path)
        self._temporary = temporary
        layers = discover_layers(root)
        selected = {kind: max((x for x in layers if x.kind == kind), key=lambda x: x.confidence, default=None) for kind in ("top_copper", "bottom_copper", "outline")}
        checks: list[Check] = []
        if selected["outline"] is None:
            raise ValueError("Nie znaleziono warstwy obrysu PCB.")
        board = coordinate_bounds(selected["outline"].path)
        if board.width <= 0 or board.height <= 0:
            raise ValueError("Obrys PCB ma nieprawidłowe wymiary.")
        checks.append(Check("ok", "Obrys PCB", f"{board.width:.3f} × {board.height:.3f} mm"))
        if selected["top_copper"] is None:
            checks.append(Check("error", "Brak górnej miedzi", "Nie wykryto warstwy TOP copper."))
        if selected["bottom_copper"] is None:
            checks.append(Check("warning", "Brak dolnej miedzi", "Projekt zostanie potraktowany jako jednostronny."))

        groups = []
        for layer in layers:
            if layer.kind.startswith("drill_"):
                category = {"drill_via": "via", "drill_pth": "pth", "drill_npth": "npth"}[layer.kind]
                groups.append(parse_excellon(layer.path, category))
        drills, slots = merge_drills(groups)
        vias = [item for item in drills if item.category == "via"]
        if vias:
            checks.append(Check("ok", "Przelotki", f"Wykryto {len(vias)} unikalnych przelotek."))
        else:
            checks.append(Check("warning", "Brak osobnej listy Via", "Nie znaleziono osobnego pliku wierceń przelotek."))
        tiny = [item for item in drills if 0 < item.diameter < 0.4]
        if tiny:
            checks.append(Check("warning", "Bardzo małe otwory", f"{len(tiny)} otworów ma średnicę poniżej 0,4 mm; wiercenie ręczne będzie trudne."))

        copper_paths = [item.path for item in layers if item.kind in ("top_copper", "bottom_copper")]
        min_feature = _smallest_aperture(copper_paths)
        if min_feature is not None:
            checks.append(Check("ok", "Najmniejsza apertura miedzi", f"Około {min_feature:.3f} mm."))

        analysis = Analysis(source_path, root, layers, board, {}, drills, slots, checks, min_feature)
        rendered: dict[str, Image.Image] = {}
        for side, kind in (("top", "top_copper"), ("bottom", "bottom_copper")):
            layer = selected[kind]
            if layer is not None:
                mask, bounds = _render_copper(layer, board, 20)
                rendered[side] = mask
                analysis.copper_bounds[side] = bounds
                if bounds.min_x < board.min_x - 0.05 or bounds.max_x > board.max_x + 0.05 or bounds.min_y < board.min_y - 0.05 or bounds.max_y > board.max_y + 0.05:
                    analysis.checks.append(Check("warning", f"Miedź {side.upper()} poza obrysem", "Część renderu wychodzi poza obrys o więcej niż 0,05 mm."))

        if "top" in rendered:
            analysis.preview_data["top"] = _data_uri(_mark_drills(ImageOps.invert(rendered["top"]), analysis, 20))
        if "bottom" in rendered:
            analysis.preview_data["bottom"] = _data_uri(_mark_drills(ImageOps.invert(rendered["bottom"]), analysis, 20))
        if "top" in rendered and "bottom" in rendered:
            analysis.preview_data["overlay"] = _data_uri(_mark_drills(_overlay(rendered["top"], rendered["bottom"]), analysis, 20))
            self._validate_vias(analysis, rendered["top"], rendered["bottom"], 20)
        self.analysis = analysis
        return analysis

    @staticmethod
    def _validate_vias(analysis: Analysis, top: Image.Image, bottom: Image.Image, dpmm: int) -> None:
        top_array = np.asarray(top)
        bottom_array = np.asarray(bottom)
        bad: list[tuple[float, float]] = []
        for hit in analysis.drills:
            if hit.category != "via":
                continue
            x = round((hit.x - analysis.board_bounds.min_x) * dpmm)
            y = round((analysis.board_bounds.max_y - hit.y) * dpmm)
            if not (0 <= x < top.width and 0 <= y < top.height) or top_array[y, x] < 128 or bottom_array[y, x] < 128:
                bad.append((hit.x, hit.y))
        if bad:
            analysis.checks.append(Check("error", "Przelotka bez miedzi", f"{len(bad)} przelotek nie trafia w miedź obu stron."))
        elif any(item.category == "via" for item in analysis.drills):
            analysis.checks.append(Check("ok", "Pola przelotek", "Każda przelotka trafia w chronioną miedź TOP i BOTTOM."))

    def generate(self, values: dict[str, object], output_parent: str | Path | None = None) -> Path:
        if self.analysis is None:
            raise RuntimeError("Najpierw przeanalizuj projekt.")
        analysis = self.analysis
        if not analysis.can_generate:
            raise RuntimeError("Projekt zawiera błędy blokujące generowanie.")
        options = GenerationOptions.from_dict(values, analysis.board_bounds)
        source_parent = analysis.source.parent if analysis.source.is_file() else analysis.source.parent
        parent = Path(output_parent).resolve() if output_parent else source_parent
        parent.mkdir(parents=True, exist_ok=True)
        stem = re.sub(r"[^A-Za-z0-9._-]+", "_", analysis.source.stem or analysis.source.name).strip("._") or "pcb"
        destination = parent / f"{stem}_AblatePCB"
        counter = 2
        while destination.exists():
            destination = parent / f"{stem}_AblatePCB_{counter}"
            counter += 1

        with tempfile.TemporaryDirectory(prefix="ablatepcb_output_", dir=parent) as temp_name:
            temp = Path(temp_name)
            top_layer = analysis.selected("top_copper")
            bottom_layer = analysis.selected("bottom_copper")
            masks: dict[str, Image.Image] = {}
            copper_bounds: dict[str, Bounds] = {}
            if top_layer is not None:
                masks["top"], copper_bounds["top"] = _render_copper(top_layer, analysis.board_bounds, options.dpmm)
            if bottom_layer is not None:
                masks["bottom"], copper_bounds["bottom"] = _render_copper(bottom_layer, analysis.board_bounds, options.dpmm)
            dpi = options.dpmm * 25.4
            hashes: dict[str, str] = {}

            def save(image: Image.Image, name: str) -> None:
                path = temp / name
                image.save(path, "PNG", dpi=(dpi, dpi), optimize=True)
                hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()

            if "top" in masks:
                save(masks["top"], "01_TOP_ablation.png")
                save(ImageOps.invert(masks["top"]), "PREVIEW_TOP_copper_black.png")
            if "bottom" in masks:
                chosen = ImageOps.mirror(masks["bottom"]) if options.flip == "left_right" else ImageOps.flip(masks["bottom"])
                save(chosen, "02_BOTTOM_selected_ablation.png")
                alternatives = temp / "alternatives"
                alternatives.mkdir()
                ImageOps.mirror(masks["bottom"]).save(alternatives / "BOTTOM_flip_left_right.png", "PNG", dpi=(dpi, dpi), optimize=True)
                ImageOps.flip(masks["bottom"]).save(alternatives / "BOTTOM_flip_top_bottom.png", "PNG", dpi=(dpi, dpi), optimize=True)
                save(ImageOps.invert(masks["bottom"]), "PREVIEW_BOTTOM_unflipped_copper_black.png")
            if "top" in masks and "bottom" in masks:
                overlay = _mark_drills(_overlay(masks["top"], masks["bottom"]), analysis, options.dpmm)
                save(overlay, "PREVIEW_OVERLAY.png")

            self._write_drill_svg(temp / "DRILL_GUIDE.svg", analysis, options)
            self._write_registration_svg(temp / "REGISTRATION_GUIDE.svg", analysis, options)
            copy_sources(analysis.layers, temp)

            board_left = options.origin_x + (options.blank_width - analysis.board_bounds.width) / 2
            board_bottom = options.origin_y + (options.blank_height - analysis.board_bounds.height) / 2
            position = {
                "boardLeft": board_left,
                "boardBottom": board_bottom,
                "imageCenterX": board_left + analysis.board_bounds.width / 2,
                "imageCenterY": board_bottom + analysis.board_bounds.height / 2,
                "imageWidth": analysis.board_bounds.width,
                "imageHeight": analysis.board_bounds.height,
            }
            manifest = {
                "schema": "ablatepcb.pcb-package.v1",
                "createdUtc": datetime.now(timezone.utc).isoformat(),
                "source": str(analysis.source),
                "board": analysis.board_bounds.to_dict(),
                "options": {
                    "dpmm": options.dpmm,
                    "dpi": dpi,
                    "blankWidth": options.blank_width,
                    "blankHeight": options.blank_height,
                    "originX": options.origin_x,
                    "originY": options.origin_y,
                    "flip": options.flip,
                    "speed": options.speed,
                    "power": options.power,
                    "interval": options.interval,
                    "passes": options.passes,
                    "overscan": options.overscan,
                },
                "lightBurnPosition": position,
                "drills": {
                    "via": sum(item.category == "via" for item in analysis.drills),
                    "pth": sum(item.category == "pth" for item in analysis.drills),
                    "npth": sum(item.category == "npth" for item in analysis.drills),
                    "slots": len(analysis.slots),
                },
                "checks": [item.to_dict() for item in analysis.checks],
                "sha256": hashes,
            }
            (temp / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
            (temp / "INSTRUKCJA.txt").write_text(build_text_instructions(analysis, options, position), encoding="utf-8")
            (temp / "RAPORT.html").write_text(build_report(analysis, options, position, manifest), encoding="utf-8")
            temp.rename(destination)
        return destination

    @staticmethod
    def _write_drill_svg(path: Path, analysis: Analysis, options: GenerationOptions) -> None:
        board = analysis.board_bounds
        circles = []
        colors = {"via": "#ff9f1c", "pth": "#00a8e8", "npth": "#e71d36"}
        for hit in analysis.drills:
            x = hit.x - board.min_x
            y = board.max_y - hit.y
            radius = max(hit.diameter / 2, 0.1)
            circles.append(f'<circle cx="{x:.5f}" cy="{y:.5f}" r="{radius:.5f}" fill="none" stroke="{colors[hit.category]}" stroke-width="0.08"/>')
            circles.append(f'<path d="M {x-0.25:.5f} {y:.5f} H {x+0.25:.5f} M {x:.5f} {y-0.25:.5f} V {y+0.25:.5f}" stroke="{colors[hit.category]}" stroke-width="0.05"/>')
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{board.width:.5f}mm" height="{board.height:.5f}mm" viewBox="0 0 {board.width:.5f} {board.height:.5f}">
<rect width="{board.width:.5f}" height="{board.height:.5f}" fill="white" stroke="black" stroke-width="0.1"/>
{''.join(circles)}
</svg>'''
        path.write_text(svg, encoding="utf-8")

    @staticmethod
    def _write_registration_svg(path: Path, analysis: Analysis, options: GenerationOptions) -> None:
        board = analysis.board_bounds
        dx = (options.blank_width - board.width) / 2
        dy = (options.blank_height - board.height) / 2
        candidates = [item for item in analysis.drills if item.category in ("npth", "pth")]
        if len(candidates) < 2:
            candidates = analysis.drills
        selected = []
        if candidates:
            first = candidates[0]
            second = max(candidates[1:] or candidates, key=lambda item: math.hypot(item.x - first.x, item.y - first.y))
            selected = [first, second]
        markers = []
        for hit in selected:
            x = dx + hit.x - board.min_x
            y = dy + board.max_y - hit.y
            markers.append(f'<circle cx="{x:.5f}" cy="{y:.5f}" r="{max(0.3, hit.diameter/2):.5f}" fill="none" stroke="#ff006e" stroke-width="0.12"/>')
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{options.blank_width:.5f}mm" height="{options.blank_height:.5f}mm" viewBox="0 0 {options.blank_width:.5f} {options.blank_height:.5f}">
<rect width="{options.blank_width:.5f}" height="{options.blank_height:.5f}" fill="white" stroke="black" stroke-width="0.12"/>
<rect x="{dx:.5f}" y="{dy:.5f}" width="{board.width:.5f}" height="{board.height:.5f}" fill="none" stroke="#0057ff" stroke-width="0.1"/>
{''.join(markers)}
</svg>'''
        path.write_text(svg, encoding="utf-8")
