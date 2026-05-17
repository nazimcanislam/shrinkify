"""
gui.py — Shrinkify entry point.

This file exists solely as the PyInstaller / direct-run target.
All GUI logic lives in the ui/ package.
"""

import ctypes
import sys

# DPI awareness must be set before any Tk window is created.
if sys.platform == 'win32':
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

from ui import ShrinkifyApp  # noqa: E402

if __name__ == '__main__':
    app = ShrinkifyApp()
    app.mainloop()
