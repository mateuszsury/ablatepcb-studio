# Contributing

Contributions are welcome. Please keep changes focused, local-first, and safe around physical laser control.

1. Fork the repository and create a branch from `main`.
2. Install development dependencies with `python -m pip install -e ".[dev]"`.
3. Add or update tests for conversion behavior.
4. Run `python -m compileall -q app.py gerber2lightburn tests` and `python -m pytest`.
5. For UI changes, validate rendered Polish and English views at desktop and narrow widths.
6. Open a pull request describing the fabrication format, LightBurn version, and verification depth.

Never commit proprietary Gerbers, machine credentials, LightBurn preference backups, or personal filesystem paths. Test fixtures must be redistributable.

Changes to Start, Stop, device movement, or preset application require an explicit safety analysis in the pull request. Tests must not start a physical laser.

