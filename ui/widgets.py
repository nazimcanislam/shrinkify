"""
widgets.py — Reusable Tkinter widget factories and the ffmpeg availability check.
"""

import subprocess
import tkinter as tk
from tkinter import ttk

from core.utils import FFPROBE
from ui.theme import COLORS, UI_FONT, UI_BOLD, UI_SMALL, UI_LABEL


def check_ffmpeg() -> bool:
    try:
        r = subprocess.run([FFPROBE, '-version'], capture_output=True, timeout=5)
        return r.returncode == 0
    except Exception:
        return False


def sep(parent) -> None:
    """Horizontal separator line."""
    tk.Frame(parent, bg=COLORS['border'], height=1).pack(fill=tk.X, padx=20, pady=10)


def checkbox(parent, var, label: str, color: str) -> None:
    """Labeled checkbox row."""
    frame = tk.Frame(parent, bg=COLORS['surface'])
    frame.pack(fill=tk.X, padx=20, pady=2)
    tk.Checkbutton(frame, variable=var,
                   bg=COLORS['surface'], fg=color,
                   selectcolor=COLORS['surface2'],
                   activebackground=COLORS['surface'], activeforeground=color,
                   relief=tk.FLAT, bd=0, cursor='hand2').pack(side=tk.LEFT)
    tk.Label(frame, text=label,
             bg=COLORS['surface'], fg=color,
             font=UI_SMALL, cursor='hand2').pack(side=tk.LEFT)


def icon_button(parent, icon: str, label: str, command, color: str) -> tk.Frame:
    """
    Custom button with a fixed icon cell and a separate text label cell.

    The icon is stored in its own Label so that .config(text=...) never
    accidentally prepends the icon again (the previous bug).
    """
    frame = tk.Frame(parent, bg=COLORS['surface2'], cursor='hand2')

    icon_lbl = tk.Label(frame, text=icon,
                        bg=COLORS['surface2'], fg=color,
                        font=UI_FONT, width=3, anchor='center')
    icon_lbl.pack(side=tk.LEFT, padx=(8, 0), pady=8)

    text_lbl = tk.Label(frame, text=label,
                        bg=COLORS['surface2'], fg=color,
                        font=UI_BOLD, anchor='w')
    text_lbl.pack(side=tk.LEFT, padx=(4, 8), pady=8, fill=tk.X, expand=True)

    def on_enter(_):
        if frame.cget('cursor') != 'arrow':
            for w in (frame, icon_lbl, text_lbl):
                w.config(bg=COLORS['surface'])

    def on_leave(_):
        for w in (frame, icon_lbl, text_lbl):
            w.config(bg=COLORS['surface2'])

    def on_click(_):
        if frame.cget('cursor') != 'arrow':
            command()

    for w in (frame, icon_lbl, text_lbl):
        w.bind('<Enter>', on_enter)
        w.bind('<Leave>', on_leave)
        w.bind('<Button-1>', on_click)

    def _config(**kwargs):
        if 'state' in kwargs:
            disabled = kwargs['state'] == tk.DISABLED
            frame.config(cursor='arrow' if disabled else 'hand2')
            fg = COLORS['text_muted'] if disabled else color
            icon_lbl.config(fg=fg)
            text_lbl.config(fg=fg)
        if 'text' in kwargs:
            text_lbl.config(text=kwargs['text'])

    frame.config = _config
    return frame


def small_button(parent, text: str, command, color: str) -> tk.Button:
    return tk.Button(parent, text=text, command=command,
                     bg=COLORS['surface'], fg=color,
                     activebackground=COLORS['surface2'],
                     activeforeground=COLORS['text'],
                     relief=tk.FLAT, font=UI_LABEL,
                     cursor='hand2', padx=6, pady=2, bd=0)
