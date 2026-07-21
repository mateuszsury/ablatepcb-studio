# Changelog

All notable changes are documented here. This project follows [Semantic Versioning](https://semver.org/).

## [0.2.3] - 2026-07-22

### Fixed

- Import generated PNG masks into the current LightBurn project and automatically select them.
- Apply and read back image size and position instead of trusting no-op UI Automation writes.
- Verify the resulting image lower-left coordinate after every LightBurn import.

### Added

- Bidirectional navigation between Source, Review, Setup, and Export while preserving the active project.

## [0.2.2] - 2026-07-21

### Fixed

- Fit copper previews to the complete PCB outline without clipping at any window size.
- Derive the preview frame aspect ratio from the analyzed board dimensions.
- Prevent long Gerber paths and preview metrics from causing horizontal overflow on narrow screens.

## [0.2.1] - 2026-07-21

### Fixed

- Replaced the blocking native Windows file picker with an asynchronous Qt picker attached to the application window.

### Added

- Always-visible LightBurn connection, live state, and Pixi preset controls before Gerber import.
- Open-or-focus LightBurn directly from AblatePCB Studio.
- Preset-only mode that updates the active LightBurn layer without changing image geometry when no Gerber project is loaded.

## [0.2.0] - 2026-07-21

### Changed

- Renamed the project to **AblatePCB Studio** so the product name is independent from third-party trademarks.
- Retained LightBurn compatibility and integration wording only as a descriptive interoperability reference.
- Renamed the Python package and command-line entry point to `ablatepcb`.

## [0.1.0] - 2026-07-21

### Added

- Gerber/Excellon detection and deterministic 1270 DPI mask generation.
- TOP/BOTTOM physical flip handling and registration/drill guides.
- Validation for outlines, copper bounds, drills, slots, and via-to-copper alignment.
- PySide6 HTML/JavaScript desktop interface with Polish and English languages.
- Pixi 5 W default profile with configurable universal laser parameters.
- LightBurn UDP and Windows UI Automation integration with live ETA and safety-gated Start.
- CLI, test suite, Windows build script, and public project documentation.
