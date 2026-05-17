"""
theme.py — Color palette, typography, and platform helpers for Shrinkify's GUI.
"""

import ctypes
import sys


_IS_MACOS = sys.platform == 'darwin'


def apply_dark_titlebar(hwnd) -> None:
    """Enable dark mode title bar on Windows 10 1809+ / Windows 11."""
    try:
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, 20, ctypes.byref(ctypes.c_int(1)), ctypes.sizeof(ctypes.c_int)
        )
    except Exception:
        try:
            # Attribute 19 for builds before 20H1
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 19, ctypes.byref(ctypes.c_int(1)), ctypes.sizeof(ctypes.c_int)
            )
        except Exception:
            pass


COLORS = {
    'bg':         '#0c0c0f',
    'surface':    '#13131a',
    'surface2':   '#1a1a24',
    'border':     '#2a2a3a',
    'accent':     '#6ee7b7',
    'accent2':    '#f59e0b',
    'red':        '#f87171',
    'green':      '#4ade80',
    'blue':       '#60a5fa',
    'text':       '#e2e8f0',
    'text_dim':   '#94a3b8',
    'text_muted': '#64748b',
}

# Font sizes — slightly larger on macOS for Retina readability
_B  = 11 if _IS_MACOS else 10   # base
_S  = 10 if _IS_MACOS else 9    # small
_XS = 9  if _IS_MACOS else 8    # label/caption
_M  = 10 if _IS_MACOS else 9    # mono

UI_FONT  = ('TkDefaultFont', _B)
UI_BOLD  = ('TkDefaultFont', _B, 'bold')
UI_SMALL = ('TkDefaultFont', _S)
UI_LABEL = ('TkDefaultFont', _XS)
MONO     = ('TkFixedFont',   _M)
MONO_LG  = ('TkFixedFont',   15 if _IS_MACOS else 14, 'bold')
MONO_TTL = ('TkFixedFont',   15 if _IS_MACOS else 14, 'bold')
