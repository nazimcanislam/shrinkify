<div align="center">
  <img src="assets/icon.png" width="96" alt="Shrinkify icon" />
  <h1>Shrinkify</h1>
  <p>Analyze media files, suggest codec conversions, detect duplicates, and generate a detailed HTML report.</p>

  ![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
  ![ffmpeg](https://img.shields.io/badge/ffmpeg-required-007808?logo=ffmpeg&logoColor=white)
  ![exiftool](https://img.shields.io/badge/exiftool-required-4a90d9?logoColor=white)
  ![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)
  ![License](https://img.shields.io/badge/license-MIT-blue)

  > **Built in collaboration with [Claude](https://claude.ai) (Anthropic).** This project was designed and developed through an iterative conversation between a human developer and Claude. The architecture, code, and documentation were produced together — a genuine human–AI collaboration.
</div>

---

## ✨ Features

- 📊 **Smart Analysis** — ffprobe extracts codec, bitrate, resolution, and format for every file
- 🔄 **Conversion** — H.264 → H.265 (ffmpeg), JPEG → AVIF (ffmpeg + exiftool)
- 🎚️ **Quality Presets** — Maximum Shrink / Balanced / Conservative
- 📁 **Complete Output** — optionally copies unconverted files too, so the output folder is self-contained
- 🔁 **Duplicate Detection** — hash-based detection and deletion
- 📄 **HTML Report** — estimated savings, codec distribution charts, per-file tables
- 🖥️ **CLI + GUI** — terminal and tkinter desktop interface
- 🔒 **Metadata Preserved** — all EXIF metadata (GPS, capture date, camera model, orientation) is fully copied to output files via exiftool
- ⚠️ **Error Resilient** — files that fail to scan are logged and skipped gracefully

> 🎵 **Note:** Shrinkify focuses on photos and videos only. Audio files (MP3, FLAC, AAC, etc.) are not analyzed or converted — that's a separate concern better handled by a dedicated tool.

---

## 🖥️ Platform Note

Shrinkify has been tested on **Windows**. It should work on **Linux** and **macOS** as well (Python and ffmpeg are cross-platform), but this has not been verified. Contributions welcome.

---

## ⚡ GPU Acceleration

Using the `--hw-accel` flag enables hardware-accelerated video encoding. Shrinkify **automatically detects** your GPU and selects the best available encoder:

| Hardware | Encoder |
|---|---|
| NVIDIA | NVENC (H.265) |
| Intel | Quick Sync (QSV) |
| AMD | AMF |
| Apple Silicon | VideoToolbox |

If no compatible GPU is found, it silently falls back to CPU encoding.

**Why use GPU acceleration?**

- ⏱️ **Much faster encoding** — GPU encoders are typically 5–10× faster than CPU (libx265) for large video libraries
- 🔋 **Lower power consumption** — dedicated encoder hardware uses far less energy than running the CPU at full load
- 🌡️ **Less heat** — your system stays cooler, especially on laptops
- 🖥️ **System stays responsive** — your CPU is free for other tasks while the GPU handles encoding

The trade-off is a slight reduction in compression efficiency compared to slow CPU presets — but for most use cases the speed and power savings are well worth it.

> **CPU vs GPU — what to expect:**
> Hardware encoders are significantly faster but produce larger output files
> compared to CPU (libx265). In our tests, converting 11,000 files (60 GB)
> with GPU took around 1–2 hours. The same job with CPU would take many times
> longer. If maximum compression is your priority, use CPU mode. If you want
> to process large collections quickly and are happy with good-enough
> compression, GPU mode is the better choice.

#### 🟥 AMD GPU Acceleration

On AMD iGPU (Ryzen APU) users, the `hevc_amf` encoder may be listed by `ffmpeg` but may not work due to driver restrictions. Shrinkify automatically detects this and switches to CPU-based `libx265` encoding. GPU acceleration generally works on external AMD GPUs.

---

## 📋 Requirements

- Python 3.10+
- ffmpeg + ffprobe (video and image conversion, analysis)
- exiftool (metadata preservation for image conversion)

### Install ffmpeg

**Windows (recommended: WinGet)**

```powershell
winget install Gyan.FFmpeg
```

After installing, **restart your terminal** so the PATH update takes effect, then verify:

```powershell
ffprobe -version
```

> ⚠️ **Common issue:** If you installed ffmpeg but Shrinkify still reports it as missing, the `bin` folder is likely not in your system PATH. WinGet installs ffmpeg to a path like:
> ```
> C:\Users\<YourName>\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_...\ffmpeg-x.x-full_build\bin
> ```
> Add this `bin` folder to your PATH manually via **System Properties → Environment Variables → Path → Edit**, then restart your terminal and the app.

**Windows (manual)**

1. Download the `full_build` zip from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/)
2. Extract it and add the `bin` folder to your system PATH
3. Verify: open a terminal and run `ffprobe -version`

> ⚠️ Windows: If `ffmpeg` is not found, try running **Shrinkify** *as Administrator* (right-click → "Run as administrator"). This is required when `ffmpeg` is installed system-wide but PATH is not available to the current user session.

**macOS**

```bash
brew install ffmpeg
```

**Linux**

```bash
sudo apt install ffmpeg      # Debian / Ubuntu
sudo dnf install ffmpeg      # Fedora
```

### Install exiftool

exiftool is required for image conversion. Without it, image conversion is blocked at startup (no CPU is wasted on a conversion that would lose metadata).

**Windows (recommended: WinGet)**

```powershell
winget install OliverBetz.ExifTool
```

Restart your terminal after installing, then verify:

```powershell
exiftool -ver
```

**Windows (standalone — no install needed)**

1. Download the Windows Executable from [exiftool.org](https://exiftool.org)
2. Rename `exiftool(-k).exe` to `exiftool.exe`
3. Place it next to `gui.py` (project root) — Shrinkify will find it automatically

**macOS**

```bash
brew install exiftool
```

**Linux**

```bash
sudo apt install libimage-exiftool-perl   # Debian / Ubuntu
sudo dnf install perl-Image-ExifTool      # Fedora
```

---

## 🚀 Usage

### GUI

```bash
python gui.py
```

**Workflow:**

1. Select a directory
2. Choose a **quality preset** (Balanced is recommended)
3. Optionally enable **"Copy originals to output folder"** to get a complete self-contained output
4. Click **Analyze** — scans files, detects duplicates, generates HTML report
5. Click **Convert Files** or **Delete Duplicates** independently
6. Use **Dry Run** to preview results without modifying anything

### CLI

```bash
# Analyze only + HTML report
python cli.py "C:\Photos"

# Analyze + convert (balanced preset)
python cli.py "C:\Takeout" --convert

# Convert + copy unconverted files too (complete output folder)
python cli.py "C:\Takeout" --convert --copy-originals

# Maximum compression
python cli.py "C:\Takeout" --convert --preset max

# Delete duplicates
python cli.py "C:\Media" --duplicates

# Simulate everything without modifying any files
python cli.py "C:\Media" --convert --duplicates --dry-run

# GPU-accelerated video conversion (auto-detects NVIDIA / Intel / AMD / Apple Silicon)
python cli.py "C:\Videos" --convert --hw-accel
```

### CLI Options

| Option | Description |
|---|---|
| `--convert` | Convert candidates |
| `--preset <n>` | `max`, `balanced` (default), or `conservative` |
| `--copy-originals` | Also copy unconverted files to output folder |
| `--duplicates` | Delete duplicate files |
| `--dry-run` | Simulate — no files are modified or deleted |
| `--hw-accel` | GPU-accelerated encoding (auto-detects available hardware) |
| `--no-hash` | Skip hash computation (faster, no duplicate detection) |
| `--report <file>` | HTML report filename (default: shrinkify_report.html) |
| `--no-report` | Skip HTML report generation |

---

## 🎚️ Quality Presets

| Preset | Video CRF | Image CRF | Description |
|---|---|---|---|
| `max` | 28 | 38 | Smallest files. Slight quality reduction, unlikely to be noticeable. |
| `balanced` | 24 | 27 | Best trade-off. Recommended default. |
| `conservative` | 20 | 18 | Minimal quality loss. Larger files, safer for archival. |

---

## 📂 Output Folder

Converted files go into `shrinkified/` inside the scanned directory, with **original filenames preserved**. Original files are never modified.

```
C:\Takeout\
├── photo.jpg            ← original, untouched
├── video.mp4            ← original, untouched
└── shrinkified\
    ├── photo.avif       ← converted (AVIF, all metadata preserved)
    └── video.mp4        ← converted (H.265)
```

With **"Copy originals"** enabled, unconverted files are also copied into `shrinkified/`, giving you a complete folder you can use as a drop-in replacement.

---

## 🔄 Conversion Criteria

| Source | Target | Engine | Est. Savings (balanced) |
|---|---|---|---|
| H.264 (AVC) video | H.265 (HEVC) | ffmpeg | ~55% |
| MPEG-4, MPEG-2 video | H.265 (HEVC) | ffmpeg | ~55% |
| JPEG photo | AVIF | ffmpeg + exiftool | ~30–40% |
| HEVC, AV1 video | — | — | Not touched |
| AVIF, HEIF photo | — | — | Not touched |
| Low-bitrate video (<3 Mbps) | — | — | Skipped (already lean) |

---

## 📦 Distributing as a Standalone Executable

Use **PyInstaller** to create a single-file executable with no Python dependency.

### Install PyInstaller

```bash
pip install pyinstaller
```

### Build

**Windows**
```bash
pyinstaller --onefile --windowed --icon=assets/icon.ico --name=Shrinkify gui.py
```

**macOS**
```bash
pyinstaller --onefile --windowed --icon=assets/icon.png --name=Shrinkify gui.py
```

**Linux**
```bash
pyinstaller --onefile --name=Shrinkify gui.py
```

The executable will be in the `dist/` folder.

> 📌 ffmpeg, ffprobe, and exiftool are **not** bundled — users must install them separately. For a fully self-contained build, copy all three binaries next to the `.exe`. Shrinkify automatically searches the directory containing the executable before falling back to PATH.

---

## 🗂️ Project Structure

```
shrinkify/
├── .github/workflows/
├── assets/
│   ├── icon.ico
│   └── icon.png
├── core/
│   ├── scanner.py      # ffprobe analysis + hash/duplicate detection
│   ├── analyzer.py     # conversion decision logic + quality presets
│   ├── converter.py    # ffmpeg + exiftool conversion pipeline
│   ├── reporter.py     # HTML + terminal report
│   └── utils.py        # binary resolution, subprocess helpers
├── docs/
│   └── index.html      # GitHub Pages deployment
├── cli.py              # Command-line interface
├── gui.py              # tkinter GUI
├── version.py
├── CHANGELOG.md
├── requirements.txt
├── .gitignore
└── README.md
```

---

## 🖼️ AVIF & HEVC Compatibility

Before converting your entire library, check whether your devices can open the output files.

### Well-supported ✅

| Platform | AVIF photos | H.265 video |
|---|---|---|
| Windows 10 / 11 | ✅ native (Photos app, Edge) | ✅ (requires free [HEVC Video Extensions](https://apps.microsoft.com/detail/9nmzlz57r3t7)) |
| macOS Ventura (13)+ | ✅ native | ✅ native |
| iOS 16+ | ✅ native | ✅ native |
| Android 10+ | ✅ native | ✅ most devices |
| Modern browsers (Chrome, Firefox, Safari) | ✅ | ✅ |
| VLC (all platforms) | ✅ | ✅ |

### May have issues ⚠️

| Platform | Notes |
|---|---|
| Windows 7 / 8 / 8.1 | No native H.265 support; AVIF requires a modern viewer |
| Android 9 and older | Inconsistent — depends on manufacturer and hardware decoder |
| Old Smart TVs (pre-2018) | Often no H.265 hardware decoder; AVIF unlikely to be supported |
| Some older digital photo frames | AVIF not supported |

> 💡 AVIF is royalty-free and supported natively on all major modern platforms. If you share files with people on older devices, keep the originals or use the **Conservative** preset. For personal archival use on modern devices (2019+), converting is safe.

---

## 📄 License

MIT

---

*Also available in: [🇹🇷 Türkçe](README.tr.md)*
