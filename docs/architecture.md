# Architecture

## Components

```text
Gerber ZIP/folder
      |
      v
detect.py -> Excellon parser -> PyGerber renderer
      |                |               |
      +----------------+---------------+
                       v
              validation + masks
                       |
           +-----------+-----------+
           |                       |
      HTML report              PNG/SVG/JSON
           |                       |
           +-----------+-----------+
                       v
            PySide6 QWebEngine UI
                       |
          localhost UDP + Windows UIA
                       |
                    LightBurn
```

`engine.py` owns analysis and deterministic generation. `detect.py` assigns semantic layer kinds using names and Gerber content. `excellon.py` parses drill tools, hits, and slots. `report.py` writes human-readable production artifacts.

The desktop shell in `gui.py` exposes a deliberately small QWebChannel bridge to the HTML/JavaScript UI. Time-consuming conversion and LightBurn polling run outside the Qt GUI thread.

`lightburn.py` separates two integration paths:

- the documented localhost UDP interface for liveness, file loading, status, and Start;
- Windows UI Automation for detailed telemetry and controls not exposed through UDP.

No fabrication file is sent over the network.

## Coordinate model

The user enters the lower-left coordinate of the physical blank. The mask is centered within that blank. LightBurn receives the resulting center coordinate while width and height remain the exact PCB outline dimensions.

For a 62 × 30 mm board placed directly at X=10, Y=10, the image center is X=41, Y=25.

## Two-sided orientation

Both bottom variants are always generated. `left_right` models turning the board like a book page; `top_bottom` models turning it like a calendar page. The selected variant is copied to `02_BOTTOM_selected_ablation.png` and recorded in the manifest.

