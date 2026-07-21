# Changelog

All notable changes are documented here. This project follows [Semantic Versioning](https://semver.org/).

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
