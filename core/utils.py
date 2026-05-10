"""
utils.py — Shared utilities for Shrinkify core modules.
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path


def find_binary(name: str) -> str:
    """
    Finds an external binary (ffmpeg / ffprobe / exiftool) more robustly than
    shutil.which alone.

    Search order:
      1. Standard PATH lookup
      2. Script directory (project root when running 'python gui.py')
      3. Current working directory
      4. sys.executable directory (PyInstaller --onedir)
      5. PyInstaller _MEIPASS (--onefile extraction dir)
      6. Common platform-specific installation paths
    """
    ext = '.exe' if sys.platform == 'win32' else ''

    # 1. Standard PATH lookup
    found = shutil.which(name)
    if found:
        return found

    # 2. Script directory — project root when running 'python gui.py' or 'python cli.py'
    script_dir = Path(sys.argv[0]).resolve().parent
    for fname in [name + ext, f'{name}(-k){ext}']:   # also catches exiftool(-k).exe
        candidate = script_dir / fname
        if candidate.exists():
            return str(candidate)

    # 3. Current working directory
    for fname in [name + ext, f'{name}(-k){ext}']:
        candidate = Path.cwd() / fname
        if candidate.exists():
            return str(candidate)

    # 4. sys.executable directory (PyInstaller --onedir builds)
    exe_dir = Path(sys.executable).parent
    candidate = exe_dir / (name + ext)
    if candidate.exists():
        return str(candidate)

    # 5. PyInstaller _MEIPASS (--onefile extraction dir)
    meipass = getattr(sys, '_MEIPASS', None)
    if meipass:
        candidate = Path(meipass) / (name + ext)
        if candidate.exists():
            return str(candidate)

    # 6a. Common Windows paths
    if sys.platform == 'win32':
        localappdata = os.environ.get('LOCALAPPDATA', '')
        winget_base = Path(localappdata) / 'Microsoft' / 'WinGet' / 'Packages'

        if winget_base.exists():
            for pattern in [
                f'Gyan.FFmpeg*/**/bin/{name}.exe',          # ffmpeg via winget
                f'OliverBetz.ExifTool*/**/{name}.exe',       # exiftool via winget
            ]:
                for match in winget_base.glob(pattern):
                    return str(match)

        win_paths = [
            Path(localappdata) / 'Programs' / 'ffmpeg' / 'bin' / f'{name}.exe',
            Path('C:/ffmpeg/bin') / f'{name}.exe',
            Path('C:/Program Files/ffmpeg/bin') / f'{name}.exe',
            Path('C:/Program Files (x86)/ffmpeg/bin') / f'{name}.exe',
            Path('C:/Windows') / f'{name}.exe',
            Path('C:/Program Files/ExifTool') / f'{name}.exe',
        ]
        for p in win_paths:
            if p.exists():
                return str(p)

    # 6b. Common macOS Homebrew paths
    if sys.platform == 'darwin':
        extra_path = '/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin'
        found = shutil.which(name, path=extra_path)
        if found:
            return found
        for p in [
            Path('/opt/homebrew/bin') / name,
            Path('/usr/local/bin') / name,
            Path('/usr/bin') / name,
            Path(os.path.expanduser('~')) / 'homebrew/bin' / name,
        ]:
            if p.exists():
                return str(p)

    # Fallback — return bare name, subprocess will report the error
    return name


def _probe_binary(path: str) -> bool:
    """Returns True if the binary at *path* runs and exits cleanly."""
    try:
        r = subprocess.run(
            [path, '-version' if 'ffprobe' in path or 'ffmpeg' in path else '-ver'],
            capture_output=True, timeout=5,
        )
        return r.returncode == 0
    except Exception:
        return False


def no_window() -> dict:
    """
    Returns subprocess kwargs that suppress the console window on Windows
    (GUI / PyInstaller --windowed builds). No-op on other platforms.
    """
    if sys.platform == 'win32':
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = subprocess.SW_HIDE
        return {'startupinfo': si, 'creationflags': subprocess.CREATE_NO_WINDOW}
    return {}


# Resolve once at import time
FFPROBE          = find_binary('ffprobe')
FFMPEG           = find_binary('ffmpeg')
EXIFTOOL         = find_binary('exiftool')

# Availability flags — checked by GUI at startup and by converter before each job
FFMPEG_AVAILABLE    = _probe_binary(FFPROBE)   # ffprobe is the reliable check
EXIFTOOL_AVAILABLE  = _probe_binary(EXIFTOOL)
