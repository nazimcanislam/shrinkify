# Changelog

All notable changes to Shrinkify are documented here.

## [0.1.3] — 2026-05-02

### Bug fixes
- GPU encoder detection now probes each candidate with a real null encode before
  selecting it — previously, `detect_hw_encoder()` only checked `ffmpeg -encoders`
  output, which caused `hevc_amf` to be selected on AMD iGPU systems even when the
  driver rejected it at runtime ("Operation not permitted")
- Probe resolution raised from 128×128 to 256×256 — NVENC enforces a minimum frame
  dimension at the hardware level and silently failed the probe, causing `hevc_qsv`
  to be selected instead on systems with both NVIDIA and Intel GPUs
- `hevc_videotoolbox` probe now passes `-color_range tv` explicitly — VideoToolbox
  exits with an error when colour range is unset, causing the encoder to be
  incorrectly marked as unavailable on macOS

### Improvements
- Hardware encoder probe is now verified across all four supported platforms:
  NVIDIA (NVENC), Intel (QSV), AMD (AMF), Apple Silicon (VideoToolbox)
- README and README.tr.md: added CPU vs GPU tradeoff note with real-world benchmark
  data (11,000 files / 60 GB) under the GPU Acceleration section

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
