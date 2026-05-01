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
    Finds an external binary (ffmpeg / ffprobe) more robustly than shutil.which alone.

    When running as a PyInstaller --windowed exe on Windows, double-clicking the app
    may give it a restricted PATH that omits user-installed tools. We therefore also
    check common installation locations and the directory that contains the running
    executable.
    """
    # 1. Standard PATH lookup
    found = shutil.which(name)
    if found:
        return found

    # 2. Same directory as the running executable (useful when bundled or portable)
    exe_dir = Path(sys.executable).parent
    candidate = exe_dir / (name + ('.exe' if sys.platform == 'win32' else ''))
    if candidate.exists():
        return str(candidate)

    # 3. PyInstaller _MEIPASS temp dir (--onefile extracts here at runtime)
    meipass = getattr(sys, '_MEIPASS', None)
    if meipass:
        candidate = Path(meipass) / (name + ('.exe' if sys.platform == 'win32' else ''))
        if candidate.exists():
            return str(candidate)

    # 4. Common Windows installation paths
    if sys.platform == 'win32':
        win_paths = [
            Path(os.environ.get('LOCALAPPDATA', '')) / 'Programs' / 'ffmpeg' / 'bin' / f'{name}.exe',
            Path('C:/ffmpeg/bin') / f'{name}.exe',
            Path('C:/Program Files/ffmpeg/bin') / f'{name}.exe',
            Path('C:/Program Files (x86)/ffmpeg/bin') / f'{name}.exe',
        ]
        for p in win_paths:
            if p.exists():
                return str(p)

    # 5. Common macOS Homebrew paths
    if sys.platform == 'darwin':
        mac_paths = [
            Path('/opt/homebrew/bin') / name,                       # Apple Silicon
            Path('/usr/local/bin') / name,                          # Intel Mac
            Path('/usr/bin') / name,
            Path(os.path.expanduser('~')) / 'homebrew/bin' / name,  # User's homebrew
        ]
        # Also try a PATH lookup with common directories appended,
        # since on macOS the PATH can be very inconsistent depending
        # on how the app is launched (Terminal vs Finder vs PyInstaller).
        extra_env_path = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
        found = shutil.which(name, path=extra_env_path)
        if found:
            return found
        for p in mac_paths:
            if p.exists():
                return str(p)

    # Fallback — return the bare name and let subprocess report the error
    return name


def no_window() -> dict:
    """
    Returns subprocess kwargs that prevent a console window from flashing
    on Windows when running from a GUI / PyInstaller --windowed build.
    On other platforms returns an empty dict (no-op).
    """
    if sys.platform == 'win32':
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = subprocess.SW_HIDE
        return {'startupinfo': si, 'creationflags': subprocess.CREATE_NO_WINDOW}
    return {}


# Resolve once at import time so every subprocess call uses the same path
FFPROBE = find_binary('ffprobe')
FFMPEG  = find_binary('ffmpeg')
