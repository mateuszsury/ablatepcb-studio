# Contributing

Contributions are welcome. Please keep changes focused, local-first, and safe around physical laser control.

1. Fork the repository and create a branch from `main`.
2. Install development dependencies with `python -m pip install -e ".[dev]"`.
3. Add or update tests for conversion behavior.
4. Run `python -m compileall -q app.py ablatepcb tests` and `python -m pytest`.
5. For UI changes, validate rendered Polish and English views at desktop and narrow widths.
6. Open a pull request describing the fabrication format, LightBurn version, and verification depth.

Never commit proprietary Gerbers, machine credentials, LightBurn preference backups, or personal filesystem paths. Test fixtures must be redistributable.

Changes to Start, Stop, device movement, or preset application require an explicit safety analysis in the pull request. Tests must not start a physical laser.

## Authorship and contributions

Project-maintained changes use the Git identity `Mateusz Sury
<66475105+mateuszsury@users.noreply.github.com>`. Configure it locally before
committing:

```sh
git config user.name "Mateusz Sury"
git config user.email "66475105+mateuszsury@users.noreply.github.com"
git config user.useConfigOnly true
```

The maintainer takes responsibility for tool-assisted changes. Do not add AI
tools as authors or co-authors. Preserve genuine human contributions, upstream
history, copyright notices and third-party licenses. Keep release provenance
and checksums intact. Describe the purpose of each change and record relevant
validation; avoid generic upload messages and environment-specific worktree names.
