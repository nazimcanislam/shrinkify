"""
app.py — ShrinkifyApp: main window, UI construction, and action handlers.
"""

import ctypes
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import datetime
import webbrowser
from collections import Counter
from pathlib import Path

from version import __version__
from core.utils import EXIFTOOL_AVAILABLE
from core.analyzer import QUALITY_PRESETS, DEFAULT_PRESET
from core.converter import get_hw_encoder
from core.reporter import _fmt_size

from ui.theme import (
    COLORS, _IS_MACOS, apply_dark_titlebar,
    UI_BOLD, UI_SMALL, UI_LABEL, MONO, MONO_LG, MONO_TTL,
)
from ui.widgets import check_ffmpeg, sep, checkbox, icon_button, small_button
from ui.screens import ModeScreen
from ui.workers import WorkerMixin


class ShrinkifyApp(tk.Tk, WorkerMixin):

    def __init__(self):
        super().__init__()
        self.title(f'Shrinkify {__version__}')
        self.geometry('1080x800' if _IS_MACOS else '1060x780')
        self.minsize(860, 640)
        self.configure(bg=COLORS['bg'])

        # Icon — _MEIPASS when frozen by PyInstaller, project root otherwise.
        # app.py lives one level deep inside ui/, so parent.parent = project root.
        _base = Path(getattr(sys, '_MEIPASS', Path(__file__).parent.parent))
        _icon = _base / 'assets' / 'icon.png'
        if _icon.exists():
            try:
                img = tk.PhotoImage(file=str(_icon))
                self.iconphoto(True, img)
                self._icon_ref = img   # keep a reference to avoid GC
            except Exception:
                pass

        # ── App state ─────────────────────────────────────────────────────────
        self._mode           = None          # 'file' | 'folder'
        self._scan_dir       = tk.StringVar()
        self._opt_dry_run    = tk.BooleanVar(value=False)
        self._opt_hw_accel   = tk.BooleanVar(value=False)
        self._opt_no_hash    = tk.BooleanVar(value=False)
        self._opt_copy_orig  = tk.BooleanVar(value=False)
        self._opt_preserve   = tk.BooleanVar(value=False)
        self._opt_preset     = tk.StringVar(value=DEFAULT_PRESET)

        self._media_files    = []
        self._scan_errors    = []
        self._summary        = None
        self._scan_path      = None          # Path (folder) or file's parent
        self._single_file    = None          # Path | None
        self._running        = False
        self._log_autoscroll = True
        self._ffmpeg_ok      = False

        self.protocol('WM_DELETE_WINDOW', self._on_close_request)

        # Centre on screen
        self.update_idletasks()
        w, h   = self.winfo_width(), self.winfo_height()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f'{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}')

        # Dark title bar (Windows only)
        if sys.platform == 'win32':
            self.update()
            try:
                hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
                apply_dark_titlebar(hwnd)
            except Exception:
                pass

        self._show_mode_screen()

    # ── Window close guard ────────────────────────────────────────────────────

    def _on_close_request(self):
        if self._running:
            if not messagebox.askyesno(
                'Operation in Progress',
                'An operation is currently running.\n\n'
                'If you close now, the process will be interrupted mid-way.\n\n'
                'Close anyway?',
                icon='warning',
            ):
                return
        self.destroy()

    # ── Screen management ─────────────────────────────────────────────────────

    def _clear_screen(self):
        for w in self.winfo_children():
            w.destroy()

    def _show_mode_screen(self):
        self._clear_screen()
        ModeScreen(self, on_choose=self._on_mode_chosen).pack(fill=tk.BOTH, expand=True)

    def _on_mode_chosen(self, mode: str):
        self._mode = mode
        self._clear_screen()
        self._build_main_ui()
        self.after(100, self._check_ffmpeg_and_report)

    # ── Dependency check ──────────────────────────────────────────────────────

    def _check_ffmpeg_and_report(self):
        self._ffmpeg_ok = check_ffmpeg()
        if self._ffmpeg_ok:
            hw = get_hw_encoder()
            self._log_msg('Shrinkify ready.\n', 'accent')
            self._log_msg(
                f'  HW encoder: {hw}\n' if hw else
                '  HW encoder: none (software only)\n',
                'muted')
            self._log_msg(
                '  exiftool: found\n' if EXIFTOOL_AVAILABLE else
                '  exiftool: NOT FOUND — image conversion disabled.\n'
                '  Place exiftool.exe next to gui.py, or run:\n'
                '  winget install OliverBetz.ExifTool\n',
                'muted' if EXIFTOOL_AVAILABLE else 'red')
        else:
            self._log_msg(
                'WARNING: ffmpeg / ffprobe not found in PATH.\n'
                'Video analysis and conversion will not work.\n'
                'Install ffmpeg and make sure it is in your PATH, then restart.\n',
                'red')
            self._progress_label.config(
                text='⚠  ffmpeg not found — video features unavailable')

    # ── Main UI ───────────────────────────────────────────────────────────────

    def _build_main_ui(self):
        self._build_left_panel(is_file_mode=(self._mode == 'file'))
        self._build_right_panel()

    # ── Left panel ────────────────────────────────────────────────────────────

    def _build_left_panel(self, is_file_mode: bool):
        left_w = 310 if _IS_MACOS else 295
        left_outer = tk.Frame(self, bg=COLORS['surface'], width=left_w)
        left_outer.pack(side=tk.LEFT, fill=tk.Y)
        left_outer.pack_propagate(False)

        ttk.Style().configure(
            'LeftPanel.Vertical.TScrollbar',
            background=COLORS['border'], troughcolor=COLORS['surface'],
            arrowcolor=COLORS['text_muted'], bordercolor=COLORS['surface'],
            darkcolor=COLORS['surface'],   lightcolor=COLORS['surface'])

        left_canvas = tk.Canvas(left_outer, bg=COLORS['surface'],
                                highlightthickness=0, bd=0, width=left_w)
        left_sb = ttk.Scrollbar(left_outer, orient=tk.VERTICAL,
                                command=left_canvas.yview,
                                style='LeftPanel.Vertical.TScrollbar')
        left_canvas.configure(yscrollcommand=left_sb.set)
        left_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        left = tk.Frame(left_canvas, bg=COLORS['surface'], width=left_w)
        win_id = left_canvas.create_window((0, 0), window=left, anchor='nw')

        def _on_frame_configure(_):
            left_canvas.configure(scrollregion=left_canvas.bbox('all'))
            if left.winfo_reqheight() > left_canvas.winfo_height():
                left_sb.pack(side=tk.RIGHT, fill=tk.Y)
            else:
                left_sb.pack_forget()

        def _on_canvas_configure(event):
            left_canvas.itemconfig(win_id, width=event.width)
            if left.winfo_reqheight() > event.height:
                left_sb.pack(side=tk.RIGHT, fill=tk.Y)
            else:
                left_sb.pack_forget()

        left.bind('<Configure>', _on_frame_configure)
        left_canvas.bind('<Configure>', _on_canvas_configure)

        def _scroll(event):
            if sys.platform == 'darwin':
                left_canvas.yview_scroll(-1 * int(event.delta), 'units')
            elif event.num == 4:
                left_canvas.yview_scroll(-1, 'units')
            elif event.num == 5:
                left_canvas.yview_scroll(1, 'units')
            else:
                left_canvas.yview_scroll(-1 * int(event.delta / 120), 'units')

        left_outer.bind('<Enter>', lambda _: (
            left_outer.bind_all('<MouseWheel>', _scroll),
            left_outer.bind_all('<Button-4>', _scroll),
            left_outer.bind_all('<Button-5>', _scroll)))
        left_outer.bind('<Leave>', lambda _: (
            left_outer.unbind_all('<MouseWheel>'),
            left_outer.unbind_all('<Button-4>'),
            left_outer.unbind_all('<Button-5>')))

        self._populate_left_panel(left, is_file_mode)

    def _populate_left_panel(self, left: tk.Frame, is_file_mode: bool):
        """Fill the scrollable left-panel frame with controls."""
        # Header
        hdr = tk.Frame(left, bg=COLORS['surface'])
        hdr.pack(fill=tk.X, padx=20, pady=(16, 0))
        tk.Button(hdr, text='← Back', command=self._show_mode_screen,
                  bg=COLORS['surface'], fg=COLORS['text_muted'],
                  relief=tk.FLAT, font=UI_LABEL, cursor='hand2', bd=0
                  ).pack(side=tk.LEFT)
        tk.Label(hdr, text=f'Mode: {"Single File" if is_file_mode else "Folder"}',
                 bg=COLORS['surface'], fg=COLORS['text_muted'],
                 font=UI_LABEL).pack(side=tk.RIGHT)

        tk.Label(left, text='SHRINKIFY',
                 bg=COLORS['surface'], fg=COLORS['accent'],
                 font=MONO_TTL, pady=12).pack(fill=tk.X, padx=20)
        tk.Label(left, text='Media Optimization Tool',
                 bg=COLORS['surface'], fg=COLORS['text_muted'],
                 font=UI_SMALL).pack(padx=20)

        sep(left)

        # File / folder picker
        tk.Label(left, text='FILE' if is_file_mode else 'DIRECTORY',
                 bg=COLORS['surface'], fg=COLORS['text_muted'],
                 font=UI_LABEL, anchor='w').pack(fill=tk.X, padx=20, pady=(12, 4))

        dir_row = tk.Frame(left, bg=COLORS['surface'])
        dir_row.pack(fill=tk.X, padx=20)
        self._dir_entry = tk.Entry(
            dir_row, textvariable=self._scan_dir,
            bg=COLORS['surface2'], fg=COLORS['text'],
            insertbackground=COLORS['accent'],
            relief=tk.FLAT, font=UI_SMALL, bd=0)
        self._dir_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6, padx=(0, 4))
        tk.Button(dir_row, text='…',
                  command=self._browse_file if is_file_mode else self._browse_folder,
                  bg=COLORS['surface2'], fg=COLORS['accent'],
                  relief=tk.FLAT, font=UI_BOLD, cursor='hand2', padx=8
                  ).pack(side=tk.RIGHT)

        sep(left)

        # Quality preset
        tk.Label(left, text='QUALITY PRESET',
                 bg=COLORS['surface'], fg=COLORS['text_muted'],
                 font=UI_LABEL, anchor='w').pack(fill=tk.X, padx=20, pady=(0, 6))
        preset_frame = tk.Frame(left, bg=COLORS['surface'])
        preset_frame.pack(fill=tk.X, padx=20)
        for key, (_, _, label, _) in QUALITY_PRESETS.items():
            row = tk.Frame(preset_frame, bg=COLORS['surface'])
            row.pack(fill=tk.X, pady=1)
            tk.Radiobutton(
                row, variable=self._opt_preset, value=key,
                bg=COLORS['surface'], fg=COLORS['accent'],
                selectcolor=COLORS['surface2'],
                activebackground=COLORS['surface'],
                activeforeground=COLORS['accent'],
                relief=tk.FLAT, bd=0, cursor='hand2').pack(side=tk.LEFT)
            tk.Label(row, text=label,
                     bg=COLORS['surface'], fg=COLORS['text'],
                     font=UI_SMALL).pack(side=tk.LEFT)

        self._preset_desc = tk.Label(
            left, text='',
            bg=COLORS['surface'], fg=COLORS['text_muted'], font=UI_LABEL,
            wraplength=260, justify=tk.LEFT, anchor='w')
        self._preset_desc.pack(fill=tk.X, padx=24, pady=(4, 0))
        self._opt_preset.trace_add('write', self._update_preset_desc)
        self._update_preset_desc()

        sep(left)

        # Options
        tk.Label(left, text='OPTIONS',
                 bg=COLORS['surface'], fg=COLORS['text_muted'],
                 font=UI_LABEL, anchor='w').pack(fill=tk.X, padx=20, pady=(0, 6))

        checkbox(left, self._opt_hw_accel, 'GPU acceleration (auto-detect)', COLORS['blue'])
        if not is_file_mode:
            checkbox(left, self._opt_copy_orig,
                     'Copy originals to output folder', COLORS['accent'])
            checkbox(left, self._opt_preserve,
                     'Preserve folder structure',       COLORS['accent'])
        checkbox(left, self._opt_dry_run, 'Dry run (simulate only)', COLORS['text_dim'])
        if not is_file_mode:
            checkbox(left, self._opt_no_hash,
                     'Skip hash (faster, no dedup)', COLORS['text_muted'])

        tk.Label(left,
                 text='Dry run: shows what would happen\nwithout modifying any files.',
                 bg=COLORS['surface'], fg=COLORS['text_muted'],
                 font=UI_LABEL, justify=tk.LEFT, wraplength=260
                 ).pack(fill=tk.X, padx=28, pady=(2, 0))

        sep(left)

        # Action buttons
        btn_specs = [
            ('_btn_scan',       '🔍', 'Analyze',           self._start_scan,         COLORS['accent'],  True),
            ('_btn_convert',    '⚙️', 'Convert Files',     self._start_convert,      COLORS['accent2'], False),
            ('_btn_duplicates', '🗑', 'Delete Duplicates',  self._start_delete_dupes, COLORS['red'],     False),
            ('_btn_report',     '📄', 'Open Report',        self._open_report,        COLORS['blue'],    False),
        ]
        if is_file_mode:
            btn_specs = [s for s in btn_specs if s[0] != '_btn_duplicates']

        for attr, ico, lbl, cmd, color, enabled in btn_specs:
            btn = icon_button(left, ico, lbl, cmd, color)
            btn.pack(fill=tk.X, padx=20, pady=3)
            if not enabled:
                btn.config(state=tk.DISABLED)
            setattr(self, attr, btn)

        if not hasattr(self, '_btn_duplicates'):
            self._btn_duplicates = None

    # ── Right panel ───────────────────────────────────────────────────────────

    def _build_right_panel(self):
        right = tk.Frame(self, bg=COLORS['bg'])
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Progress
        prog = tk.Frame(right, bg=COLORS['bg'])
        prog.pack(fill=tk.X, padx=20, pady=(20, 0))
        self._progress_label = tk.Label(prog, text='Ready',
                                        bg=COLORS['bg'], fg=COLORS['text_muted'],
                                        font=UI_SMALL, anchor='w')
        self._progress_label.pack(fill=tk.X)
        s = ttk.Style()
        s.theme_use('clam')
        s.configure('TProgressbar',
                    background=COLORS['accent'], troughcolor=COLORS['surface2'],
                    bordercolor=COLORS['border'],
                    lightcolor=COLORS['accent'], darkcolor=COLORS['accent'])
        self._progress = ttk.Progressbar(prog, mode='determinate')
        self._progress.pack(fill=tk.X, pady=(4, 0))

        # Summary cards
        self._summary_frame = tk.Frame(right, bg=COLORS['bg'])
        self._summary_frame.pack(fill=tk.X, padx=20, pady=12)

        # Log header
        log_hdr = tk.Frame(right, bg=COLORS['bg'])
        log_hdr.pack(fill=tk.X, padx=20, pady=(0, 4))
        tk.Label(log_hdr, text='LOG',
                 bg=COLORS['bg'], fg=COLORS['text_muted'],
                 font=UI_LABEL).pack(side=tk.LEFT)
        small_button(log_hdr, '⬇ Save Log', self._save_log,
                     COLORS['text_muted']).pack(side=tk.RIGHT, padx=(4, 0))
        small_button(log_hdr, '⎘ Copy All', self._copy_log,
                     COLORS['text_muted']).pack(side=tk.RIGHT, padx=(4, 0))

        # Log widget
        log_frame = tk.Frame(right, bg=COLORS['surface'], bd=0)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))

        ttk.Style().configure(
            'Dark.Vertical.TScrollbar',
            background=COLORS['border'], troughcolor=COLORS['surface'],
            arrowcolor=COLORS['text_muted'], bordercolor=COLORS['surface'],
            darkcolor=COLORS['surface'],   lightcolor=COLORS['surface'])

        self._scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL,
                                        style='Dark.Vertical.TScrollbar')
        self._log = tk.Text(
            log_frame,
            bg=COLORS['surface'], fg=COLORS['text_dim'],
            font=MONO, relief=tk.FLAT, bd=8,
            insertbackground=COLORS['accent'],
            selectbackground=COLORS['surface2'],
            wrap=tk.WORD, state=tk.DISABLED)
        self._log.config(yscrollcommand=lambda f, l: (
            self._scrollbar.set(f, l), self._track_scroll(f, l)))
        self._scrollbar.config(command=self._log.yview)
        self._scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._log.pack(fill=tk.BOTH, expand=True)

        for tag, color in [
            ('accent', COLORS['accent']),  ('green',  COLORS['green']),
            ('red',    COLORS['red']),     ('yellow', COLORS['accent2']),
            ('muted',  COLORS['text_muted']), ('blue', COLORS['blue']),
            ('ts',     COLORS['text_muted']),
        ]:
            self._log.tag_config(tag, foreground=color)

    # ── Browse ────────────────────────────────────────────────────────────────

    def _browse_folder(self):
        d = filedialog.askdirectory(title='Select Directory')
        if d:
            self._scan_dir.set(d)

    def _browse_file(self):
        f = filedialog.askopenfilename(
            title='Select File',
            filetypes=[
                ('Media files',
                 '*.mp4 *.mov *.avi *.mkv *.wmv '
                 '*.jpg *.jpeg *.png *.heic *.heif *.webp *.tiff *.bmp'),
                ('All files', '*.*'),
            ])
        if f:
            self._scan_dir.set(f)

    # ── Preset ────────────────────────────────────────────────────────────────

    def _update_preset_desc(self, *_):
        key = self._opt_preset.get()
        if key in QUALITY_PRESETS:
            self._preset_desc.config(text=QUALITY_PRESETS[key][3])

    # ── Scroll tracking ───────────────────────────────────────────────────────

    def _track_scroll(self, first, last):
        self._scrollbar.set(first, last)
        try:
            self._log_autoscroll = float(last) >= 0.999
        except Exception:
            pass

    # ── Log ───────────────────────────────────────────────────────────────────

    def _ts(self) -> str:
        return datetime.datetime.now().strftime('%H:%M:%S')

    def _log_msg(self, msg: str, tag: str = '', timestamp: bool = False):
        def _insert():
            self._log.config(state=tk.NORMAL)
            if timestamp:
                self._log.insert(tk.END, f'[{self._ts()}] ', 'ts')
            self._log.insert(tk.END, msg, tag) if tag else self._log.insert(tk.END, msg)
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

    # ── Actions ───────────────────────────────────────────────────────────────

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
            messagebox.showwarning(
                'Nothing Selected',
                f'Please select a {"file" if self._mode == "file" else "directory"} first.')
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

        self._running     = True
        self._media_files = []
        self._summary     = None
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
        dry       = self._opt_dry_run.get()
        hw        = self._opt_hw_accel.get()
        preset    = self._opt_preset.get()
        copy_orig = self._opt_copy_orig.get() if self._mode == 'folder' else False
        preserve  = self._opt_preserve.get()  if self._mode == 'folder' else False

        candidates = [mf for mf in self._media_files
                      if mf.needs_conversion and not mf.is_duplicate]
        if not candidates and not copy_orig:
            messagebox.showinfo('Nothing to Do', 'No conversion candidates found.')
            return

        _, _, preset_label, _ = QUALITY_PRESETS[preset]
        msg = (f"Convert {len(candidates)} file(s)?\n\n"
               f"Preset: {preset_label}\n"
               f"Output: {self._scan_path / 'shrinkified'}\n\n"
               f"Original files will NOT be deleted.")
        if dry:
            msg += '\n\n[DRY RUN — no files will be modified]'
        if not (dry or messagebox.askyesno('Confirm Conversion', msg)):
            return

        self._running = True
        self._btn_convert.config(state=tk.DISABLED, text='Converting…')
        self._log_autoscroll = True
        threading.Thread(
            target=self._run_convert,
            args=(candidates, dry, hw, preset, copy_orig, preserve),
            daemon=True).start()

    def _start_delete_dupes(self):
        if self._running or not self._media_files:
            return
        dry       = self._opt_dry_run.get()
        dup_files = [mf for mf in self._media_files if mf.is_duplicate]
        if not dup_files:
            messagebox.showinfo('No Duplicates', 'No duplicate files found.')
            return
        total_size = sum(mf.size_bytes for mf in dup_files)
        if not (dry or messagebox.askyesno(
            'Confirm Deletion',
            f"Permanently delete {len(dup_files)} duplicate file(s)?\n"
            f"This will free {_fmt_size(total_size)}.\n\n"
            + ('[DRY RUN]' if dry else 'THIS CANNOT BE UNDONE.')
        )):
            return
        self._running = True
        self._btn_duplicates.config(state=tk.DISABLED, text='Deleting…')
        self._log_autoscroll = True
        threading.Thread(
            target=self._run_delete_dupes, args=(dry,), daemon=True).start()

    # ── State helpers ─────────────────────────────────────────────────────────

    def _done_scan(self):
        self._running = False
        self.after(0, lambda: self._btn_scan.config(state=tk.NORMAL, text='Analyze'))

    def _done_action(self, btn, label: str):
        self._running = False
        self.after(0, lambda: btn.config(state=tk.NORMAL, text=label))

    def _set_progress(self, value: int, label: str = ''):
        self._progress['value'] = value
        if label:
            self._progress_label.config(text=label)

    def _clear_summary(self):
        for w in self._summary_frame.winfo_children():
            w.destroy()

    def _show_summary(self, summary):
        self._clear_summary()

        hash_counts = Counter(
            mf.file_hash for mf in self._media_files
            if getattr(mf, 'file_hash', None) and mf.is_duplicate)
        dup_groups = len(hash_counts)

        dup_sub = (
            f"{_fmt_size(summary.duplicate_size_bytes)}"
            f"  ·  {dup_groups} group{'s' if dup_groups != 1 else ''}"
            if dup_groups > 0 else _fmt_size(summary.duplicate_size_bytes)
        )

        cards = [
            (f"{summary.total_files:,}",
             f"{_fmt_size(summary.total_size_bytes)}",
             'Total Files', COLORS['blue']),
            (f"{summary.videos_to_convert + summary.images_to_convert:,}",
             'conversion candidates',
             'Convert', COLORS['accent2']),
            (f"{summary.duplicate_count:,}",
             dup_sub,
             'Duplicates', COLORS['red']),
            (f"−{_fmt_size(summary.total_potential_savings_bytes)}",
             f"{summary.savings_percentage:.1f}% reduction",
             'Est. Savings', COLORS['green']),
        ]
        for val, sub, label, color in cards:
            card = tk.Frame(self._summary_frame,
                            bg=COLORS['surface'], relief=tk.FLAT, bd=0)
            card.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
            tk.Frame(card, bg=color, height=2).pack(fill=tk.X)
            inner = tk.Frame(card, bg=COLORS['surface'])
            inner.pack(fill=tk.BOTH, padx=12, pady=10)
            tk.Label(inner, text=label,
                     bg=COLORS['surface'], fg=COLORS['text_muted'],
                     font=UI_LABEL).pack(anchor='w')
            tk.Label(inner, text=val,
                     bg=COLORS['surface'], fg=color,
                     font=MONO_LG).pack(anchor='w')
            tk.Label(inner, text=sub,
                     bg=COLORS['surface'], fg=COLORS['text_muted'],
                     font=UI_LABEL).pack(anchor='w')
