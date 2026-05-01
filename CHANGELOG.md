# Changelog

All notable changes to Shrinkify are documented here.

## [0.1.1] — 2025-05-02

Initial stable release. Previous pre-release builds (1.0.x) are archived and no longer distributed.

### Changes
- Downgraded version number to reflect early-stage status while `ffmpeg` distribution issues are unresolved
- Windows Installer (Inno Setup) removed from CI pipeline

### Bug fixes
- `scan_directory()` now skips the `shrinkified/` output folder — previously, re-scanning a directory would include already-converted files and corrupt the analysis results
- `ffmpeg` availability check in GUI now uses the same binary resolution logic as the scanner (`_find_binary`), eliminating false "ffmpeg not found" warnings on macOS/Windows

### Improvements
- `_find_binary()` and `_no_window()` extracted to `core/utils.py` — previously duplicated across `scanner.py` and `converter.py`
- Hash computation now uses `xxhash` (xxh64) when available, falling back to MD5 — ~3–5x faster on large libraries
- PNG files are no longer flagged as conversion candidates — converting lossless PNGs to HEIF causes quality loss on screenshots and graphics. A note is surfaced in the report instead
- GitHub Actions docs deploy now only triggers on changes to `docs/` — previously any push to `main` redeployed the site
- Left-panel scroll in GUI no longer intercepts scroll events outside the panel
- Removed dead `_FS` variable from `gui.py`
- `Shrinkify.spec` removed from repository (CI uses inline PyInstaller arguments)

## [0.1.2] — 2025-05-02

### Bug fixes
- Icon no longer missing when running as a PyInstaller bundle — `gui.py` now resolves `assets/icon.png` via `sys._MEIPASS` instead of `__file__`
- ffmpeg detection on Windows now searches `winget` install locations (`%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg*`) — previously the app required administrator privileges to find ffmpeg installed via `winget`
