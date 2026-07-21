from __future__ import annotations

import html
import json
from typing import Any

from .models import Analysis, GenerationOptions


def build_text_instructions(analysis: Analysis, options: GenerationOptions, position: dict[str, float]) -> str:
    flip = "lewo-prawo (jak kartkę książki)" if options.flip == "left_right" else "góra-dół (jak kartkę kalendarza)"
    return f"""GERBER2LIGHTBURN PCB — INSTRUKCJA
===================================

Płytka projektu: {analysis.board_bounds.width:.3f} x {analysis.board_bounds.height:.3f} mm
Surowy laminat: {options.blank_width:.3f} x {options.blank_height:.3f} mm
Lewy dolny róg laminatu na stole: X={options.origin_x:.3f}, Y={options.origin_y:.3f}

POZYCJA OBRAZU W LIGHTBURN (kotwica środkowa):
X={position['imageCenterX']:.3f} mm
Y={position['imageCenterY']:.3f} mm
W={position['imageWidth']:.3f} mm
H={position['imageHeight']:.3f} mm

USTAWIENIA STARTOWE PIXI 5 W / FARBOWANA MIEDŹ:
Tryb obrazu: Threshold
Prędkość: {options.speed:.0f} mm/min
Moc maksymalna: {options.power:.1f}%
Interwał: {options.interval:.3f} mm
Przejścia: {options.passes}
Overscan: {options.overscan:.1f}%
Negative Image: wyłączone

DOLNA STRONA:
Wybrany sposób przewrócenia: {flip}
Użyj 02_BOTTOM_selected_ablation.png.

WAŻNE:
- białe obszary pozostają chronione farbą; czarne są wypalane,
- wykonaj Frame przed każdym Start,
- nie uruchamiaj lasera bez nadzoru i wentylacji,
- otwory wykonaj osobno według DRILL_GUIDE.svg,
- przelotki wymagają drutu/nitów i połączenia obu stron,
- wykonaj DRC projektu w programie EDA; ten raport sprawdza konwersję, nie schemat.
"""


def build_report(analysis: Analysis, options: GenerationOptions, position: dict[str, float], manifest: dict[str, Any]) -> str:
    rows = "".join(
        f'<tr><td><span class="{check.level}">{check.level.upper()}</span></td><td>{html.escape(check.title)}</td><td>{html.escape(check.detail)}</td></tr>'
        for check in analysis.checks
    )
    layers = "".join(
        f"<li><strong>{html.escape(layer.kind)}</strong> — {html.escape(layer.relative_name)}</li>"
        for layer in analysis.layers
        if layer.kind != "other"
    )
    manifest_text = html.escape(json.dumps(manifest, indent=2, ensure_ascii=False))
    return f'''<!doctype html><html lang="pl"><head><meta charset="utf-8"><title>Raport Gerber2LightBurn</title>
<style>body{{font:15px system-ui;max-width:1050px;margin:40px auto;padding:0 24px;color:#17212b}}h1{{font-size:28px}}table{{border-collapse:collapse;width:100%}}td,th{{border-bottom:1px solid #dce3ea;padding:10px;text-align:left}}.ok{{color:#087f5b}}.warning{{color:#b25c00}}.error{{color:#c92a2a}}code,pre{{background:#f3f5f7;padding:3px 6px;border-radius:5px}}pre{{overflow:auto;padding:16px}}.metric{{display:inline-block;margin:6px 20px 6px 0}}</style></head><body>
<h1>Raport przygotowania PCB</h1>
<p><span class="metric"><b>Płytka:</b> {analysis.board_bounds.width:.3f} × {analysis.board_bounds.height:.3f} mm</span><span class="metric"><b>Laminat:</b> {options.blank_width:.3f} × {options.blank_height:.3f} mm</span></p>
<h2>Pozycja LightBurn</h2><p>Kotwica środkowa: <b>X={position['imageCenterX']:.3f}, Y={position['imageCenterY']:.3f}</b>; W={position['imageWidth']:.3f}, H={position['imageHeight']:.3f} mm.</p>
<h2>Kontrole</h2><table><thead><tr><th>Stan</th><th>Kontrola</th><th>Wynik</th></tr></thead><tbody>{rows}</tbody></table>
<h2>Rozpoznane warstwy</h2><ul>{layers}</ul>
<h2>Ograniczenia procesu</h2><p>Konwerter potwierdza zgodność geometrii Gerbera z maskami. Nie zastępuje DRC/netlisty. Przelotki trzeba wywiercić i połączyć elektrycznie po obu stronach.</p>
<details><summary>Manifest techniczny</summary><pre>{manifest_text}</pre></details>
</body></html>'''

