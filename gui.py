"""
gui.py — Shrinkify GUI (tkinter).
"""

import ctypes
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import datetime
import webbrowser
import subprocess
from pathlib import Path

from version import __version__

# ── DPI awareness (Windows) ───────────────────────────────────
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

def _apply_dark_titlebar(hwnd):
    """Enable dark mode title bar on Windows 10 1809+ / Windows 11."""
    try:
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_USE_IMMERSIVE_DARK_MODE,
            ctypes.byref(ctypes.c_int(1)),
            ctypes.sizeof(ctypes.c_int)
        )
    except Exception:
        # Older Windows builds use attribute 19
        try:
            DWMWA_USE_IMMERSIVE_DARK_MODE_BEFORE_20H1 = 19
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd,
                DWMWA_USE_IMMERSIVE_DARK_MODE_BEFORE_20H1,
                ctypes.byref(ctypes.c_int(1)),
                ctypes.sizeof(ctypes.c_int)
            )
        except Exception:
            pass

# ── macOS font scaling ────────────────────────────────────────
# On Retina displays tkinter uses logical pixels; bump base sizes slightly.
_IS_MACOS = sys.platform == 'darwin'

from core.utils import FFPROBE, EXIFTOOL_AVAILABLE
from core.scanner import scan_directory, scan_file, compute_hashes, find_duplicates
from core.analyzer import analyze_all, QUALITY_PRESETS, DEFAULT_PRESET
from core.converter import (convert_file, copy_unconverted, copy_size_skipped,
                            delete_duplicates, get_hw_encoder, get_hw_probe_failure_reason)
from core.reporter import generate_html_report, _fmt_size

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


# ─────────────────────────────────────────────────────────────
# ffmpeg availability check
# ─────────────────────────────────────────────────────────────
def _check_ffmpeg() -> bool:
    try:
        r = subprocess.run([FFPROBE, '-version'], capture_output=True, timeout=5)
        return r.returncode == 0
    except Exception:
        return False


# ─────────────────────────────────────────────────────────────
# Mode selection screen
# ─────────────────────────────────────────────────────────────
class ModeScreen(tk.Frame):
    """
    Shown at startup. Lets the user choose between single-file and folder mode.
    """
    def __init__(self, master, on_choose):
        super().__init__(master, bg=COLORS['bg'])
        self._on_choose = on_choose
        self._build()

    def _build(self):
        # Centre content vertically
        spacer = tk.Frame(self, bg=COLORS['bg'])
        spacer.pack(expand=True, fill=tk.BOTH)

        # Logo / title
        tk.Label(self, text='SHRINKIFY', bg=COLORS['bg'],
                 fg=COLORS['accent'], font=MONO_TTL).pack(pady=(0, 4))
        tk.Label(self, text='Media Optimization Tool', bg=COLORS['bg'],
                 fg=COLORS['text_muted'], font=UI_SMALL).pack(pady=(0, 40))

        # Cards row
        cards_row = tk.Frame(self, bg=COLORS['bg'])
        cards_row.pack()

        self._make_card(cards_row,
                        icon='📄',
                        title='Single File',
                        desc='Convert or analyze\none media file.',
                        mode='file').pack(side=tk.LEFT, padx=16)

        self._make_card(cards_row,
                        icon='📁',
                        title='Folder',
                        desc='Scan an entire folder\n(and subfolders).',
                        mode='folder').pack(side=tk.LEFT, padx=16)

        spacer2 = tk.Frame(self, bg=COLORS['bg'])
        spacer2.pack(expand=True, fill=tk.BOTH)

    def _make_card(self, parent, icon, title, desc, mode) -> tk.Frame:
        W, H = (200 if _IS_MACOS else 180), (200 if _IS_MACOS else 185)

        card = tk.Frame(parent, bg=COLORS['surface'],
                        width=W, height=H, cursor='hand2')
        card.pack_propagate(False)

        # Top accent bar
        tk.Frame(card, bg=COLORS['accent'], height=2).pack(fill=tk.X)

        inner = tk.Frame(card, bg=COLORS['surface'])
        inner.pack(expand=True, fill=tk.BOTH, padx=20, pady=20)

        tk.Label(inner, text=icon, bg=COLORS['surface'],
                 fg=COLORS['accent'], font=('TkDefaultFont', 28)).pack(pady=(0, 8))
        tk.Label(inner, text=title, bg=COLORS['surface'],
                 fg=COLORS['text'], font=UI_BOLD).pack()
        tk.Label(inner, text=desc, bg=COLORS['surface'],
                 fg=COLORS['text_muted'], font=UI_LABEL,
                 justify=tk.CENTER, wraplength=W - 32).pack(pady=(6, 0))

        def on_enter(_):
            card.config(bg=COLORS['surface2'])
            inner.config(bg=COLORS['surface2'])
            for w in inner.winfo_children():
                try: w.config(bg=COLORS['surface2'])
                except Exception: pass

        def on_leave(_):
            card.config(bg=COLORS['surface'])
            inner.config(bg=COLORS['surface'])
            for w in inner.winfo_children():
                try: w.config(bg=COLORS['surface'])
                except Exception: pass

        def on_click(_):
            self._on_choose(mode)

        for w in [card, inner] + inner.winfo_children():
            w.bind('<Enter>', on_enter)
            w.bind('<Leave>', on_leave)
            w.bind('<Button-1>', on_click)

        return card


# ─────────────────────────────────────────────────────────────
# Main application
# ─────────────────────────────────────────────────────────────
class ShrinkifyApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f'Shrinkify {__version__}')
        self.geometry('1080x800' if _IS_MACOS else '1060x780')
        self.minsize(860, 640)
        self.configure(bg=COLORS['bg'])

        _base = Path(getattr(sys, '_MEIPASS', Path(__file__).parent))
        _icon_path = _base / 'assets' / 'icon.png'
        if _icon_path.exists():
            try:
                icon = tk.PhotoImage(file=str(_icon_path))
                self.iconphoto(True, icon)
                self._icon_ref = icon
            except Exception:
                pass

        self._mode            = None   # 'file' or 'folder'
        self._scan_dir        = tk.StringVar()
        self._opt_dry_run     = tk.BooleanVar(value=False)
        self._opt_hw_accel    = tk.BooleanVar(value=False)
        self._opt_no_hash     = tk.BooleanVar(value=False)
        self._opt_copy_orig   = tk.BooleanVar(value=False)
        self._opt_preserve    = tk.BooleanVar(value=False)
        self._opt_preset      = tk.StringVar(value=DEFAULT_PRESET)

        self._media_files     = []
        self._scan_errors     = []
        self._summary         = None
        self._scan_path       = None   # Path (folder) or Path (file's parent)
        self._single_file     = None   # Path | None
        self._running         = False
        self._log_autoscroll  = True
        self._ffmpeg_ok       = False

        self.protocol('WM_DELETE_WINDOW', self._on_close_request)

        # Center window on screen
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f'{w}x{h}+{x}+{y}')

        # Dark title bar on Windows
        if sys.platform == 'win32':
            self.update()
            try:
                hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
                _apply_dark_titlebar(hwnd)
            except Exception:
                pass

        self._show_mode_screen()

    # ── Window close guard ────────────────────────────────────
    def _on_close_request(self):
        if self._running:
            confirm = messagebox.askyesno(
                'Operation in Progress',
                'An operation is currently running.\n\n'
                'If you close now, the process will be interrupted mid-way.\n\n'
                'Close anyway?',
                icon='warning'
            )
            if not confirm:
                return
        self.destroy()

    # ── Screen management ─────────────────────────────────────
    def _clear_screen(self):
        for w in self.winfo_children():
            w.destroy()

    def _show_mode_screen(self):
        self._clear_screen()
        screen = ModeScreen(self, on_choose=self._on_mode_chosen)
        screen.pack(fill=tk.BOTH, expand=True)

    def _on_mode_chosen(self, mode: str):
        self._mode = mode
        self._clear_screen()
        self._build_main_ui()
        # Check ffmpeg after UI is built so we can log to the log widget
        self.after(100, self._check_ffmpeg_and_report)

    # ── Dependency check ──────────────────────────────────────
    def _check_ffmpeg_and_report(self):
        self._ffmpeg_ok = _check_ffmpeg()
        if self._ffmpeg_ok:
            hw = get_hw_encoder()
            hw_label = f'  HW encoder: {hw}' if hw else '  HW encoder: none (software only)'
            self._log_msg('Shrinkify ready.\n', 'accent')
            self._log_msg(f'{hw_label}\n', 'muted')
            if EXIFTOOL_AVAILABLE:
                self._log_msg('  exiftool: found\n', 'muted')
            else:
                self._log_msg(
                    '  exiftool: NOT FOUND — image conversion disabled.\n'
                    '  Place exiftool.exe next to gui.py, or run:\n'
                    '  winget install OliverBetz.ExifTool\n',
                    'red'
                )
        else:
            self._log_msg(
                'WARNING: ffmpeg / ffprobe not found in PATH.\n'
                'Video analysis and conversion will not work.\n'
                'Install ffmpeg and make sure it is in your PATH, then restart.\n',
                'red'
            )
            self._progress_label.config(
                text='\u26a0  ffmpeg not found — video features unavailable')

    # ── Main UI ───────────────────────────────────────────────
    def _build_main_ui(self):
        is_file_mode = (self._mode == 'file')

        # ── Left panel (scrollable) ───────────────────────────
        left_w = 310 if _IS_MACOS else 295
        left_outer = tk.Frame(self, bg=COLORS['surface'], width=left_w)
        left_outer.pack(side=tk.LEFT, fill=tk.Y)
        left_outer.pack_propagate(False)

        _left_sb_style = ttk.Style()
        _left_sb_style.configure('LeftPanel.Vertical.TScrollbar',
                                 background=COLORS['border'],
                                 troughcolor=COLORS['surface'],
                                 arrowcolor=COLORS['text_muted'],
                                 bordercolor=COLORS['surface'],
                                 darkcolor=COLORS['surface'],
                                 lightcolor=COLORS['surface'])
        left_canvas = tk.Canvas(left_outer, bg=COLORS['surface'],
                                highlightthickness=0, bd=0,
                                width=left_w)
        left_scrollbar = ttk.Scrollbar(left_outer, orient=tk.VERTICAL,
                                       command=left_canvas.yview,
                                       style='LeftPanel.Vertical.TScrollbar')
        left_canvas.configure(yscrollcommand=left_scrollbar.set)
        # Scrollbar only shown when needed (grid lets us hide it)
        left_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        left = tk.Frame(left_canvas, bg=COLORS['surface'], width=left_w)
        left_canvas_window = left_canvas.create_window(
            (0, 0), window=left, anchor='nw')

        def _on_left_frame_configure(event):
            left_canvas.configure(scrollregion=left_canvas.bbox('all'))
            # Show scrollbar only when content exceeds canvas height
            if left.winfo_reqheight() > left_canvas.winfo_height():
                left_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            else:
                left_scrollbar.pack_forget()

        def _on_left_canvas_configure(event):
            left_canvas.itemconfig(left_canvas_window, width=event.width)
            # Re-check if scrollbar is needed
            if left.winfo_reqheight() > event.height:
                left_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            else:
                left_scrollbar.pack_forget()

        left.bind('<Configure>', _on_left_frame_configure)
        left_canvas.bind('<Configure>', _on_left_canvas_configure)

        def _left_mousewheel(event):
            if sys.platform == 'darwin':
                left_canvas.yview_scroll(-1 * int(event.delta), 'units')
            elif event.num == 4:
                left_canvas.yview_scroll(-1, 'units')
            elif event.num == 5:
                left_canvas.yview_scroll(1, 'units')
            else:
                left_canvas.yview_scroll(-1 * int(event.delta / 120), 'units')

        # Bind scroll only while the pointer is inside the left panel
        def _bind_left_scroll(_event=None):
            left_outer.bind_all('<MouseWheel>', _left_mousewheel)
            left_outer.bind_all('<Button-4>', _left_mousewheel)
            left_outer.bind_all('<Button-5>', _left_mousewheel)

        def _unbind_left_scroll(_event=None):
            left_outer.unbind_all('<MouseWheel>')
            left_outer.unbind_all('<Button-4>')
            left_outer.unbind_all('<Button-5>')

        left_outer.bind('<Enter>', _bind_left_scroll)
        left_outer.bind('<Leave>', _unbind_left_scroll)

        # Header with back button
        hdr = tk.Frame(left, bg=COLORS['surface'])
        hdr.pack(fill=tk.X, padx=20, pady=(16, 0))
        tk.Button(hdr, text='← Back', command=self._show_mode_screen,
                  bg=COLORS['surface'], fg=COLORS['text_muted'],
                  relief=tk.FLAT, font=UI_LABEL, cursor='hand2', bd=0
                  ).pack(side=tk.LEFT)
        mode_label = 'Single File' if is_file_mode else 'Folder'
        tk.Label(hdr, text=f'Mode: {mode_label}', bg=COLORS['surface'],
                 fg=COLORS['text_muted'], font=UI_LABEL).pack(side=tk.RIGHT)

        tk.Label(left, text='SHRINKIFY', bg=COLORS['surface'],
                 fg=COLORS['accent'], font=MONO_TTL, pady=12).pack(fill=tk.X, padx=20)
        tk.Label(left, text='Media Optimization Tool', bg=COLORS['surface'],
                 fg=COLORS['text_muted'], font=UI_SMALL).pack(padx=20)

        _sep(left)

        # File / folder picker
        pick_label = 'FILE' if is_file_mode else 'DIRECTORY'
        tk.Label(left, text=pick_label, bg=COLORS['surface'],
                 fg=COLORS['text_muted'], font=UI_LABEL, anchor='w'
                 ).pack(fill=tk.X, padx=20, pady=(12, 4))

        dir_frame = tk.Frame(left, bg=COLORS['surface'])
        dir_frame.pack(fill=tk.X, padx=20)
        self._dir_entry = tk.Entry(dir_frame, textvariable=self._scan_dir,
                                   bg=COLORS['surface2'], fg=COLORS['text'],
                                   insertbackground=COLORS['accent'],
                                   relief=tk.FLAT, font=UI_SMALL, bd=0)
        self._dir_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6, padx=(0, 4))
        browse_cmd = self._browse_file if is_file_mode else self._browse_folder
        tk.Button(dir_frame, text='…', command=browse_cmd,
                  bg=COLORS['surface2'], fg=COLORS['accent'],
                  relief=tk.FLAT, font=UI_BOLD, cursor='hand2', padx=8).pack(side=tk.RIGHT)

        _sep(left)

        # Quality preset
        tk.Label(left, text='QUALITY PRESET', bg=COLORS['surface'],
                 fg=COLORS['text_muted'], font=UI_LABEL, anchor='w'
                 ).pack(fill=tk.X, padx=20, pady=(0, 6))
        preset_frame = tk.Frame(left, bg=COLORS['surface'])
        preset_frame.pack(fill=tk.X, padx=20)
        for key, (_, _, label, _) in QUALITY_PRESETS.items():
            row = tk.Frame(preset_frame, bg=COLORS['surface'])
            row.pack(fill=tk.X, pady=1)
            tk.Radiobutton(row, variable=self._opt_preset, value=key,
                           bg=COLORS['surface'], fg=COLORS['accent'],
                           selectcolor=COLORS['surface2'],
                           activebackground=COLORS['surface'],
                           activeforeground=COLORS['accent'],
                           relief=tk.FLAT, bd=0, cursor='hand2').pack(side=tk.LEFT)
            tk.Label(row, text=label, bg=COLORS['surface'],
                     fg=COLORS['text'], font=UI_SMALL).pack(side=tk.LEFT)

        self._preset_desc = tk.Label(left, text='', bg=COLORS['surface'],
                                     fg=COLORS['text_muted'], font=UI_LABEL,
                                     wraplength=260, justify=tk.LEFT, anchor='w')
        self._preset_desc.pack(fill=tk.X, padx=24, pady=(4, 0))
        self._opt_preset.trace_add('write', self._update_preset_desc)
        self._update_preset_desc()

        _sep(left)

        # Options
        tk.Label(left, text='OPTIONS', bg=COLORS['surface'],
                 fg=COLORS['text_muted'], font=UI_LABEL, anchor='w'
                 ).pack(fill=tk.X, padx=20, pady=(0, 6))

        _checkbox(left, self._opt_hw_accel, 'GPU acceleration (auto-detect)', COLORS['blue'])

        if not is_file_mode:
            _checkbox(left, self._opt_copy_orig,
                      'Copy originals to output folder', COLORS['accent'])
            _checkbox(left, self._opt_preserve,
                      'Preserve folder structure', COLORS['accent'])

        _checkbox(left, self._opt_dry_run,  'Dry run (simulate only)',      COLORS['text_dim'])

        if not is_file_mode:
            _checkbox(left, self._opt_no_hash,
                      'Skip hash (faster, no dedup)', COLORS['text_muted'])

        tk.Label(left,
                 text='Dry run: shows what would happen\nwithout modifying any files.',
                 bg=COLORS['surface'], fg=COLORS['text_muted'],
                 font=UI_LABEL, justify=tk.LEFT, wraplength=260
                 ).pack(fill=tk.X, padx=28, pady=(2, 0))

        _sep(left)

        # Action buttons
        btn_data = [
            ('_btn_scan',       '🔍', 'Analyze',          self._start_scan,         COLORS['accent'],  True),
            ('_btn_convert',    '⚙️', 'Convert Files',    self._start_convert,      COLORS['accent2'], False),
            ('_btn_duplicates', '🗑', 'Delete Duplicates', self._start_delete_dupes, COLORS['red'],     False),
            ('_btn_report',     '📄', 'Open Report',       self._open_report,        COLORS['blue'],    False),
        ]
        if is_file_mode:
            # No duplicate deletion in single-file mode
            btn_data = [b for b in btn_data if b[0] != '_btn_duplicates']

        for attr, icon, label, cmd, color, enabled in btn_data:
            btn = _icon_button(left, icon, label, cmd, color)
            btn.pack(fill=tk.X, padx=20, pady=3)
            if not enabled:
                btn.config(state=tk.DISABLED)
            setattr(self, attr, btn)

        # Ensure _btn_duplicates always exists as an attribute
        if not hasattr(self, '_btn_duplicates'):
            self._btn_duplicates = None

        # ── Right panel ───────────────────────────────────────
        right = tk.Frame(self, bg=COLORS['bg'])
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        prog_frame = tk.Frame(right, bg=COLORS['bg'])
        prog_frame.pack(fill=tk.X, padx=20, pady=(20, 0))
        self._progress_label = tk.Label(prog_frame, text='Ready', bg=COLORS['bg'],
                                        fg=COLORS['text_muted'], font=UI_SMALL, anchor='w')
        self._progress_label.pack(fill=tk.X)
        self._progress = ttk.Progressbar(prog_frame, mode='determinate')
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TProgressbar', background=COLORS['accent'],
                        troughcolor=COLORS['surface2'], bordercolor=COLORS['border'],
                        lightcolor=COLORS['accent'], darkcolor=COLORS['accent'])
        self._progress.pack(fill=tk.X, pady=(4, 0))

        self._summary_frame = tk.Frame(right, bg=COLORS['bg'])
        self._summary_frame.pack(fill=tk.X, padx=20, pady=12)

        log_header = tk.Frame(right, bg=COLORS['bg'])
        log_header.pack(fill=tk.X, padx=20, pady=(0, 4))
        tk.Label(log_header, text='LOG', bg=COLORS['bg'],
                 fg=COLORS['text_muted'], font=UI_LABEL).pack(side=tk.LEFT)
        _small_btn(log_header, '⬇ Save Log', self._save_log, COLORS['text_muted']).pack(side=tk.RIGHT, padx=(4, 0))
        _small_btn(log_header, '⎘ Copy All', self._copy_log, COLORS['text_muted']).pack(side=tk.RIGHT, padx=(4, 0))

        log_frame = tk.Frame(right, bg=COLORS['surface'], bd=0)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
        self._log = tk.Text(log_frame, bg=COLORS['surface'], fg=COLORS['text_dim'],
                            font=MONO, relief=tk.FLAT, bd=8,
                            insertbackground=COLORS['accent'],
                            selectbackground=COLORS['surface2'],
                            wrap=tk.WORD, state=tk.DISABLED)
        # Style the scrollbar to match dark theme
        _sb_style = ttk.Style()
        _sb_style.configure('Dark.Vertical.TScrollbar',
                            background=COLORS['border'],
                            troughcolor=COLORS['surface'],
                            arrowcolor=COLORS['text_muted'],
                            bordercolor=COLORS['surface'],
                            darkcolor=COLORS['surface'],
                            lightcolor=COLORS['surface'])
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL,
                                  command=self._log.yview,
                                  style='Dark.Vertical.TScrollbar')
        self._scrollbar = scrollbar
        self._log.config(yscrollcommand=lambda f, l: (
            scrollbar.set(f, l), self._track_scroll(f, l)))
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._log.pack(fill=tk.BOTH, expand=True)

        for tag, color in [
            ('accent', COLORS['accent']), ('green', COLORS['green']),
            ('red', COLORS['red']),       ('yellow', COLORS['accent2']),
            ('muted', COLORS['text_muted']), ('blue', COLORS['blue']),
            ('ts', COLORS['text_muted']),
        ]:
            self._log.tag_config(tag, foreground=color)

    # ── Browse ────────────────────────────────────────────────
    def _browse_folder(self):
        d = filedialog.askdirectory(title='Select Directory')
        if d:
            self._scan_dir.set(d)

    def _browse_file(self):
        f = filedialog.askopenfilename(
            title='Select File',
            filetypes=[
                ('Media files', '*.mp4 *.mov *.avi *.mkv *.wmv *.jpg *.jpeg *.png *.heic *.heif *.webp *.tiff *.bmp'),
                ('All files', '*.*'),
            ])
        if f:
            self._scan_dir.set(f)

    # ── Preset ────────────────────────────────────────────────
    def _update_preset_desc(self, *_):
        key = self._opt_preset.get()
        if key in QUALITY_PRESETS:
            self._preset_desc.config(text=QUALITY_PRESETS[key][3])

    # ── Scroll ────────────────────────────────────────────────
    def _track_scroll(self, first, last):
        self._scrollbar.set(first, last)
        try:
            self._log_autoscroll = float(last) >= 0.999
        except Exception:
            pass

    # ── Log ───────────────────────────────────────────────────
    def _ts(self): return datetime.datetime.now().strftime('%H:%M:%S')

    def _log_msg(self, msg: str, tag: str = '', timestamp: bool = False):
        def _insert():
            self._log.config(state=tk.NORMAL)
            if timestamp:
                self._log.insert(tk.END, f'[{self._ts()}] ', 'ts')
            if tag:
                self._log.insert(tk.END, msg, tag)
            else:
                self._log.insert(tk.END, msg)
            if self._log_autoscroll:
                self._log.see(tk.END)
            self._log.config(state=tk.DISABLED)
        self.after(0, _insert)

    def _log_section(self, t): self._log_msg(f'\n── {t} ──\n', 'accent', timestamp=True)
    def _log_ok(self, m):      self._log_msg(f'  ✓ {m}\n', 'green',  timestamp=True)
    def _log_skip(self, m):    self._log_msg(f'  ○ {m}\n', 'muted',  timestamp=True)
    def _log_err(self, m):     self._log_msg(f'  ✗ {m}\n', 'red',    timestamp=True)
    def _log_info(self, m):    self._log_msg(f'  → {m}\n', '',       timestamp=True)

    def _log_clear(self):
        self._log.config(state=tk.NORMAL)
        self._log.delete('1.0', tk.END)
        self._log.config(state=tk.DISABLED)

    def _copy_log(self):
        self.clipboard_clear()
        self.clipboard_append(self._log.get('1.0', tk.END))
        self._log_msg('  Log copied to clipboard.\n', 'muted')

    def _save_log(self):
        path = filedialog.asksaveasfilename(
            title='Save Log', defaultextension='.txt',
            filetypes=[('Text files', '*.txt'), ('All files', '*.*')],
            initialfile='shrinkify_log.txt')
        if path:
            try:
                Path(path).write_text(self._log.get('1.0', tk.END), encoding='utf-8')
                self._log_info(f'Log saved → {path}')
            except Exception as e:
                self._log_err(f'Could not save log: {e}')

    # ── Actions ───────────────────────────────────────────────
    def _open_report(self):
        report = Path('shrinkify_report.html')
        if report.exists():
            webbrowser.open(report.resolve().as_uri())
        else:
            messagebox.showinfo('Report Not Found', 'Run an analysis first.')

    def _start_scan(self):
        if self._running:
            return
        raw = self._scan_dir.get().strip()
        if not raw:
            label = 'file' if self._mode == 'file' else 'directory'
            messagebox.showwarning('Nothing Selected', f'Please select a {label} first.')
            return

        target = Path(raw)
        if not target.exists():
            messagebox.showerror('Not Found', f'Path not found:\n{target}')
            return

        if self._mode == 'file':
            if not target.is_file():
                messagebox.showerror('Not a File', f'Expected a file:\n{target}')
                return
            self._single_file = target
            self._scan_path   = target.parent
        else:
            if not target.is_dir():
                messagebox.showerror('Not a Directory', f'Expected a directory:\n{target}')
                return
            self._single_file = None
            self._scan_path   = target

        self._running = True
        self._media_files = []
        self._summary = None
        self._btn_scan.config(state=tk.DISABLED, text='Scanning…')
        self._btn_convert.config(state=tk.DISABLED)
        if self._btn_duplicates:
            self._btn_duplicates.config(state=tk.DISABLED)
        self._btn_report.config(state=tk.DISABLED)
        self._clear_summary()
        self._log_clear()
        self._log_autoscroll = True
        threading.Thread(target=self._run_scan, daemon=True).start()

    def _start_convert(self):
        if self._running or not self._media_files:
            return
        dry      = self._opt_dry_run.get()
        hw       = self._opt_hw_accel.get()
        preset   = self._opt_preset.get()
        copy_orig = self._opt_copy_orig.get() if self._mode == 'folder' else False
        preserve  = self._opt_preserve.get()  if self._mode == 'folder' else False

        candidates = [mf for mf in self._media_files if mf.needs_conversion and not mf.is_duplicate]
        if not candidates and not copy_orig:
            messagebox.showinfo('Nothing to Do', 'No conversion candidates found.')
            return

        _, _, preset_label, _ = QUALITY_PRESETS[preset]
        out_dir = self._scan_path / 'shrinkified'
        msg = (f"Convert {len(candidates)} file(s)?\n\n"
               f"Preset: {preset_label}\n"
               f"Output: {out_dir}\n\n"
               f"Original files will NOT be deleted.")
        if dry:
            msg += '\n\n[DRY RUN — no files will be modified]'
        confirm = dry or messagebox.askyesno('Confirm Conversion', msg)
        if not confirm:
            return

        self._running = True
        self._btn_convert.config(state=tk.DISABLED, text='Converting…')
        self._log_autoscroll = True
        threading.Thread(
            target=self._run_convert,
            args=(candidates, dry, hw, preset, copy_orig, preserve),
            daemon=True
        ).start()

    def _start_delete_dupes(self):
        if self._running or not self._media_files:
            return
        dry = self._opt_dry_run.get()
        dup_files = [mf for mf in self._media_files if mf.is_duplicate]
        if not dup_files:
            messagebox.showinfo('No Duplicates', 'No duplicate files found.')
            return
        total_size = sum(mf.size_bytes for mf in dup_files)
        confirm = dry or messagebox.askyesno(
            'Confirm Deletion',
            f"Permanently delete {len(dup_files)} duplicate file(s)?\n"
            f"This will free {_fmt_size(total_size)}.\n\n"
            + ('[DRY RUN]' if dry else 'THIS CANNOT BE UNDONE.'))
        if not confirm:
            return
        self._running = True
        self._btn_duplicates.config(state=tk.DISABLED, text='Deleting…')
        self._log_autoscroll = True
        threading.Thread(target=self._run_delete_dupes, args=(dry,), daemon=True).start()

    # ── Background threads ────────────────────────────────────
    def _run_scan(self):
        try:
            preset = self._opt_preset.get()
            self._log_section('Scanning')

            if self._single_file:
                # Single-file mode
                from core.scanner import scan_file
                mf = scan_file(self._single_file)
                if mf is None:
                    self._log_err(f'Unsupported or empty file: {self._single_file.name}')
                    self._done_scan()
                    return
                media_files = [mf]
                scan_errors = [(self._single_file, mf.scan_error)] if mf.scan_error else []
                self._log_info(f'1 file: {self._single_file.name}')
            else:
                media_files, scan_errors = scan_directory(
                    self._scan_path,
                    progress_callback=lambda c, t, f: self.after(
                        0, lambda p=int(c/t*40) if t else 0, fn=f:
                        self._set_progress(p, f'Scanning: {fn}')),
                    error_callback=lambda path, err:
                        self._log_err(f'Scan error — {path.name}: {err}')
                )
                self._log_info(f'{len(media_files)} media files found.')
                if scan_errors:
                    self._log_msg(f'  → {len(scan_errors)} files had scan errors.\n', 'yellow')

            if not media_files:
                self._log_err('No supported media files found.')
                self._done_scan()
                return

            # Hash (folder mode only)
            if self._mode == 'folder' and not self._opt_no_hash.get():
                self._log_section('Computing hashes')
                compute_hashes(
                    media_files,
                    progress_callback=lambda c, t, f: self.after(
                        0, lambda p=40+int(c/t*20) if t else 40, fn=f:
                        self._set_progress(p, f'Hashing: {fn}')))
                dup_count = find_duplicates(media_files)
                if dup_count > 0:
                    self._log_msg(f'  → {dup_count} duplicates found.\n', 'yellow', timestamp=True)
                else:
                    self._log_info('No duplicates found.')
            else:
                if self._mode == 'folder':
                    self._log_info('Hash skipped.')

            # Analyze
            self._log_section('Analyzing')
            self._set_progress(65, 'Analyzing…')
            summary = analyze_all(media_files, preset)
            self._media_files = media_files
            self._scan_errors = scan_errors
            self._summary     = summary

            convert_count = summary.videos_to_convert + summary.images_to_convert
            self._log_info(f'Total: {summary.total_files:,} files, {_fmt_size(summary.total_size_bytes)}')
            self._log_info(f'Conversion candidates: {convert_count}  (est. −{_fmt_size(summary.estimated_savings_bytes)})')
            if self._mode == 'folder':
                self._log_info(f'Duplicates: {summary.duplicate_count}  (−{_fmt_size(summary.duplicate_savings_bytes)})')
            self._log_info(f'Total potential savings: −{_fmt_size(summary.total_potential_savings_bytes)}  ({summary.savings_percentage:.1f}%)')
            self.after(0, lambda: self._show_summary(summary))

            # Report
            self._set_progress(90, 'Generating report…')
            report_path = Path('shrinkify_report.html')
            generate_html_report(media_files, summary, self._scan_path, report_path)
            self._log_info(f'Report saved → {report_path.resolve()}')
            self.after(0, lambda: self._btn_report.config(state=tk.NORMAL))

            self._set_progress(100, 'Analysis complete ✓')
            self._log_msg('\n✓ Analysis complete.\n', 'accent')

            self.after(0, lambda: self._btn_convert.config(
                state=tk.NORMAL, text='Convert Files'))
            if self._btn_duplicates:
                self.after(0, lambda: self._btn_duplicates.config(
                    state=tk.NORMAL if summary.duplicate_count > 0 else tk.DISABLED,
                    text='Delete Duplicates'))

        except Exception as e:
            self._log_err(f'Unexpected error: {e}')
        finally:
            self._done_scan()

    def _run_convert(self, candidates, dry_run, hw_accel, preset, copy_orig, preserve):
        try:
            shrinkified_dir = self._scan_path / 'shrinkified'
            _, _, preset_label, _ = QUALITY_PRESETS[preset]
            dry_label = ' (DRY RUN)' if dry_run else ''

            if hw_accel:
                hw = get_hw_encoder()
                if hw:
                    enc_info = f'encoder: {hw}'
                else:
                    enc_info = 'encoder: libx265 (no hw found)'
                    failure_reason = get_hw_probe_failure_reason()
                    if failure_reason:
                        self.after(0, lambda r=failure_reason:
                            self._log_err(f'GPU probe failed — {r}'))
            else:
                enc_info = 'encoder: libx265'

            self._log_section(
                f'Converting{dry_label} [{preset_label}, {enc_info}] — {len(candidates)} files')

            total_saved = 0
            success_count = 0
            fail_count = 0
            size_skipped: list = []   # files where output was larger than original

            for i, mf in enumerate(candidates, 1):
                pct = int(i / len(candidates) * (80 if copy_orig else 100))
                self.after(0, lambda p=pct, fn=mf.filename:
                    self._set_progress(p, f'Converting ({p}%): {fn}'))
                result = convert_file(
                    mf, shrinkified_dir=shrinkified_dir,
                    scan_root=self._scan_path, preserve_structure=preserve,
                    use_hw_accel=hw_accel, dry_run=dry_run, preset=preset)
                if result.success:
                    success_count += 1
                    total_saved += result.size_saved_bytes
                    self._log_ok(
                        f'{mf.filename}  '
                        f'{_fmt_size(result.original_size_bytes)} → {_fmt_size(result.final_size_bytes)}'
                        f'  (−{_fmt_size(result.size_saved_bytes)})')
                elif result.skipped_due_to_size:
                    # Conversion was attempted but output was larger — keep original.
                    # If copy_orig is on, these must also land in shrinkified/.
                    size_skipped.append(mf)
                    self._log_skip(f'{mf.filename}: {result.skip_reason}')
                elif result.skipped:
                    self._log_skip(f'{mf.filename}: {result.skip_reason}')
                else:
                    fail_count += 1
                    self._log_err(f'{mf.filename}: {result.error_message[:120]}')

            self._log_info(
                f'Done: {success_count} succeeded, {fail_count} failed, '
                f'saved: {_fmt_size(total_saved)}')

            if copy_orig:
                self._log_section(f'Copying to output folder{dry_label}')
                self._set_progress(85, 'Copying…')

                # 1. Files that were never candidates (already modern format)
                copied1, bytes1 = copy_unconverted(
                    self._media_files, shrinkified_dir,
                    scan_root=self._scan_path, preserve_structure=preserve,
                    dry_run=dry_run)

                # 2. Files that were candidates but kept because output was larger
                copied2, bytes2 = copy_size_skipped(
                    size_skipped, shrinkified_dir,
                    scan_root=self._scan_path, preserve_structure=preserve,
                    dry_run=dry_run)

                total_copied = copied1 + copied2
                total_bytes  = bytes1  + bytes2
                self._log_info(
                    f'{total_copied} files copied ({_fmt_size(total_bytes)})  '
                    f'[{copied1} unconverted + {copied2} kept-as-original]')

            self._set_progress(100, 'Conversion complete ✓')
            self._log_msg('\n✓ Conversion complete.\n', 'accent')
        except Exception as e:
            self._log_err(f'Unexpected error during conversion: {e}')
        finally:
            self._done_action(self._btn_convert, 'Convert Files')

    def _run_delete_dupes(self, dry_run):
        try:
            dry_label = ' (DRY RUN)' if dry_run else ''
            self._log_section(f'Deleting duplicates{dry_label}')
            deleted, saved = delete_duplicates(self._media_files, dry_run=dry_run)
            self._log_info(f'{deleted} files deleted, {_fmt_size(saved)} recovered.')
            self._set_progress(100, 'Deletion complete ✓')
            self._log_msg('\n✓ Duplicate deletion complete.\n', 'accent')
        except Exception as e:
            self._log_err(f'Unexpected error during deletion: {e}')
        finally:
            self._done_action(self._btn_duplicates, 'Delete Duplicates')

    # ── State helpers ─────────────────────────────────────────
    def _done_scan(self):
        self._running = False
        self.after(0, lambda: self._btn_scan.config(state=tk.NORMAL, text='Analyze'))

    def _done_action(self, btn, label):
        self._running = False
        self.after(0, lambda: btn.config(state=tk.NORMAL, text=label))

    def _set_progress(self, value, label=''):
        self._progress['value'] = value
        if label:
            self._progress_label.config(text=label)

    def _clear_summary(self):
        for w in self._summary_frame.winfo_children():
            w.destroy()

    def _show_summary(self, summary):
        self._clear_summary()

        # Count duplicate groups (files sharing the same hash)
        dup_groups = 0
        if self._media_files:
            from collections import Counter
            hash_counts = Counter(
                mf.file_hash for mf in self._media_files
                if getattr(mf, 'file_hash', None) and mf.is_duplicate
            )
            # Each hash that appears as a duplicate represents one group
            dup_groups = len(hash_counts)

        dup_sub = (f"{_fmt_size(summary.duplicate_size_bytes)}"
                   f"  ·  {dup_groups} group{'s' if dup_groups != 1 else ''}"
                   if dup_groups > 0 else _fmt_size(summary.duplicate_size_bytes))

        cards = [
            (f"{summary.total_files:,}", f"{_fmt_size(summary.total_size_bytes)}", 'Total Files', COLORS['blue']),
            (f"{summary.videos_to_convert + summary.images_to_convert:,}", 'conversion candidates', 'Convert', COLORS['accent2']),
            (f"{summary.duplicate_count:,}", dup_sub, 'Duplicates', COLORS['red']),
            (f"−{_fmt_size(summary.total_potential_savings_bytes)}", f"{summary.savings_percentage:.1f}% reduction", 'Est. Savings', COLORS['green']),
        ]
        for val, sub, label, color in cards:
            card = tk.Frame(self._summary_frame, bg=COLORS['surface'], relief=tk.FLAT, bd=0)
            card.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
            tk.Frame(card, bg=color, height=2).pack(fill=tk.X)
            inner = tk.Frame(card, bg=COLORS['surface'])
            inner.pack(fill=tk.BOTH, padx=12, pady=10)
            tk.Label(inner, text=label, bg=COLORS['surface'], fg=COLORS['text_muted'], font=UI_LABEL).pack(anchor='w')
            tk.Label(inner, text=val,   bg=COLORS['surface'], fg=color, font=MONO_LG).pack(anchor='w')
            tk.Label(inner, text=sub,   bg=COLORS['surface'], fg=COLORS['text_muted'], font=UI_LABEL).pack(anchor='w')


# ─────────────────────────────────────────────────────────────
# Widget helpers
# ─────────────────────────────────────────────────────────────
def _sep(parent):
    tk.Frame(parent, bg=COLORS['border'], height=1).pack(fill=tk.X, padx=20, pady=10)


def _checkbox(parent, var, label, color):
    frame = tk.Frame(parent, bg=COLORS['surface'])
    frame.pack(fill=tk.X, padx=20, pady=2)
    tk.Checkbutton(frame, variable=var, bg=COLORS['surface'],
                   fg=color, selectcolor=COLORS['surface2'],
                   activebackground=COLORS['surface'], activeforeground=color,
                   relief=tk.FLAT, bd=0, cursor='hand2').pack(side=tk.LEFT)
    tk.Label(frame, text=label, bg=COLORS['surface'],
             fg=color, font=UI_SMALL, cursor='hand2').pack(side=tk.LEFT)


def _icon_button(parent, icon: str, label: str, command, color) -> tk.Frame:
    """
    Custom button with icon + label.
    The icon is stored separately so .config(text=...) only updates the label,
    never accidentally appending the icon a second time (the previous bug).
    """
    frame = tk.Frame(parent, bg=COLORS['surface2'], cursor='hand2')

    # Fixed-width icon cell — never changes
    icon_lbl = tk.Label(frame, text=icon, bg=COLORS['surface2'], fg=color,
                        font=UI_FONT, width=3, anchor='center')
    icon_lbl.pack(side=tk.LEFT, padx=(8, 0), pady=8)

    # Text cell — only this one is updated via .config(text=...)
    text_lbl = tk.Label(frame, text=label, bg=COLORS['surface2'], fg=color,
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
            # Only update the text label — icon stays untouched
            text_lbl.config(text=kwargs['text'])

    frame.config = _config
    return frame


def _small_btn(parent, text, command, color):
    return tk.Button(parent, text=text, command=command,
                     bg=COLORS['surface'], fg=color,
                     activebackground=COLORS['surface2'],
                     activeforeground=COLORS['text'],
                     relief=tk.FLAT, font=UI_LABEL,
                     cursor='hand2', padx=6, pady=2, bd=0)


if __name__ == '__main__':
    app = ShrinkifyApp()
    app.mainloop()
