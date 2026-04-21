"""
gui.py — Shrinkify GUI (tkinter).
"""

import ctypes
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import datetime
import webbrowser
from pathlib import Path

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

from core.scanner import scan_directory, compute_hashes, find_duplicates
from core.analyzer import analyze_all, QUALITY_PRESETS, DEFAULT_PRESET
from core.converter import convert_file, copy_unconverted, delete_duplicates
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

UI_FONT  = ('TkDefaultFont', 10)
UI_BOLD  = ('TkDefaultFont', 10, 'bold')
UI_SMALL = ('TkDefaultFont', 9)
UI_LABEL = ('TkDefaultFont', 8)
MONO     = ('TkFixedFont', 9)
MONO_LG  = ('TkFixedFont', 14, 'bold')
MONO_TTL = ('TkFixedFont', 14, 'bold')


class ShrinkifyApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Shrinkify')
        self.geometry('1060x780')
        self.minsize(860, 640)
        self.configure(bg=COLORS['bg'])

        # Set window icon
        _icon_path = Path(__file__).parent / 'icon.png'
        if _icon_path.exists():
            try:
                icon = tk.PhotoImage(file=str(_icon_path))
                self.iconphoto(True, icon)
                self._icon_ref = icon  # keep reference
            except Exception:
                pass

        self._scan_dir          = tk.StringVar()
        self._opt_dry_run       = tk.BooleanVar(value=False)
        self._opt_hw_accel      = tk.BooleanVar(value=False)
        self._opt_no_hash       = tk.BooleanVar(value=False)
        self._opt_copy_original = tk.BooleanVar(value=False)
        self._opt_preset        = tk.StringVar(value=DEFAULT_PRESET)

        self._media_files    = []
        self._scan_errors    = []
        self._summary        = None
        self._scan_path      = None
        self._running        = False
        self._log_autoscroll = True

        self._build_ui()

    # ─────────────────────────────────────────────────────────
    def _build_ui(self):
        left = tk.Frame(self, bg=COLORS['surface'], width=295)
        left.pack(side=tk.LEFT, fill=tk.Y)
        left.pack_propagate(False)

        tk.Label(left, text='SHRINKIFY', bg=COLORS['surface'],
                 fg=COLORS['accent'], font=MONO_TTL, pady=20).pack(fill=tk.X, padx=20)
        tk.Label(left, text='Media Optimization Tool', bg=COLORS['surface'],
                 fg=COLORS['text_muted'], font=UI_SMALL).pack(padx=20)

        _sep(left)

        # Directory
        tk.Label(left, text='DIRECTORY', bg=COLORS['surface'],
                 fg=COLORS['text_muted'], font=UI_LABEL, anchor='w'
                 ).pack(fill=tk.X, padx=20, pady=(12, 4))
        dir_frame = tk.Frame(left, bg=COLORS['surface'])
        dir_frame.pack(fill=tk.X, padx=20)
        self._dir_entry = tk.Entry(
            dir_frame, textvariable=self._scan_dir,
            bg=COLORS['surface2'], fg=COLORS['text'],
            insertbackground=COLORS['accent'],
            relief=tk.FLAT, font=UI_SMALL, bd=0)
        self._dir_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6, padx=(0, 4))
        tk.Button(dir_frame, text='…', command=self._browse,
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
            tk.Radiobutton(
                row, variable=self._opt_preset, value=key,
                bg=COLORS['surface'], fg=COLORS['accent'],
                selectcolor=COLORS['surface2'],
                activebackground=COLORS['surface'],
                activeforeground=COLORS['accent'],
                relief=tk.FLAT, bd=0, cursor='hand2'
            ).pack(side=tk.LEFT)
            tk.Label(row, text=label, bg=COLORS['surface'],
                     fg=COLORS['text'], font=UI_SMALL).pack(side=tk.LEFT)

        self._preset_desc = tk.Label(
            left, text='', bg=COLORS['surface'],
            fg=COLORS['text_muted'], font=UI_LABEL,
            wraplength=250, justify=tk.LEFT, anchor='w')
        self._preset_desc.pack(fill=tk.X, padx=24, pady=(4, 0))
        self._opt_preset.trace_add('write', self._update_preset_desc)
        self._update_preset_desc()

        _sep(left)

        # Options
        tk.Label(left, text='OPTIONS', bg=COLORS['surface'],
                 fg=COLORS['text_muted'], font=UI_LABEL, anchor='w'
                 ).pack(fill=tk.X, padx=20, pady=(0, 6))

        _checkbox(left, self._opt_copy_original,
                  'Copy originals to output folder', COLORS['accent'])
        tk.Label(left,
                 text='Copies unconverted files too,\nso the output folder is complete.',
                 bg=COLORS['surface'], fg=COLORS['text_muted'],
                 font=UI_LABEL, justify=tk.LEFT, wraplength=250
                 ).pack(fill=tk.X, padx=28, pady=(0, 6))

        _checkbox(left, self._opt_dry_run,  'Dry run (simulate only)',      COLORS['text_dim'])
        _checkbox(left, self._opt_hw_accel, 'GPU acceleration (NVENC)',     COLORS['blue'])
        _checkbox(left, self._opt_no_hash,  'Skip hash (faster, no dedup)', COLORS['text_muted'])

        tk.Label(left,
                 text='Dry run: shows what would happen\nwithout modifying any files.',
                 bg=COLORS['surface'], fg=COLORS['text_muted'],
                 font=UI_LABEL, justify=tk.LEFT, wraplength=250
                 ).pack(fill=tk.X, padx=28, pady=(2, 0))

        _sep(left)

        # Buttons
        btn_data = [
            ('_btn_scan',       '🔍', 'Analyze',          self._start_scan,         COLORS['accent'],  True),
            ('_btn_convert',    '⚙️', 'Convert Files',    self._start_convert,      COLORS['accent2'], False),
            ('_btn_duplicates', '🗑', 'Delete Duplicates', self._start_delete_dupes, COLORS['red'],     False),
            ('_btn_report',     '📄', 'Open Report',       self._open_report,        COLORS['blue'],    False),
        ]
        for attr, icon, label, cmd, color, enabled in btn_data:
            btn = _icon_button(left, icon, label, cmd, color)
            btn.pack(fill=tk.X, padx=20, pady=3)
            if not enabled:
                btn.config(state=tk.DISABLED)
            setattr(self, attr, btn)

        # ── Right panel ───────────────────────────────────────
        right = tk.Frame(self, bg=COLORS['bg'])
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        prog_frame = tk.Frame(right, bg=COLORS['bg'])
        prog_frame.pack(fill=tk.X, padx=20, pady=(20, 0))
        self._progress_label = tk.Label(
            prog_frame, text='Ready', bg=COLORS['bg'],
            fg=COLORS['text_muted'], font=UI_SMALL, anchor='w')
        self._progress_label.pack(fill=tk.X)
        self._progress = ttk.Progressbar(prog_frame, mode='determinate')
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TProgressbar',
                        background=COLORS['accent'], troughcolor=COLORS['surface2'],
                        bordercolor=COLORS['border'], lightcolor=COLORS['accent'],
                        darkcolor=COLORS['accent'])
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
        self._log = tk.Text(
            log_frame, bg=COLORS['surface'], fg=COLORS['text_dim'],
            font=MONO, relief=tk.FLAT, bd=8,
            insertbackground=COLORS['accent'],
            selectbackground=COLORS['surface2'],
            wrap=tk.WORD, state=tk.DISABLED)
        scrollbar = tk.Scrollbar(log_frame, command=self._log.yview,
                                 bg=COLORS['surface2'], troughcolor=COLORS['surface'])
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

        self._log_msg('Shrinkify ready. Select a directory and click Analyze.\n', 'accent')

    # ─────────────────────────────────────────────────────────
    def _update_preset_desc(self, *_):
        key = self._opt_preset.get()
        if key in QUALITY_PRESETS:
            self._preset_desc.config(text=QUALITY_PRESETS[key][3])

    def _track_scroll(self, first, last):
        self._scrollbar.set(first, last)
        try:
            self._log_autoscroll = float(last) >= 0.999
        except Exception:
            pass

    # ─────────────────────────────────────────────────────────
    # LOG
    # ─────────────────────────────────────────────────────────
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

    def _log_section(self, title): self._log_msg(f'\n── {title} ──\n', 'accent', timestamp=True)
    def _log_ok(self, msg):        self._log_msg(f'  ✓ {msg}\n', 'green',  timestamp=True)
    def _log_skip(self, msg):      self._log_msg(f'  ○ {msg}\n', 'muted',  timestamp=True)
    def _log_err(self, msg):       self._log_msg(f'  ✗ {msg}\n', 'red',    timestamp=True)
    def _log_info(self, msg):      self._log_msg(f'  → {msg}\n', '',       timestamp=True)

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

    # ─────────────────────────────────────────────────────────
    # ACTIONS
    # ─────────────────────────────────────────────────────────
    def _browse(self):
        d = filedialog.askdirectory(title='Select Directory')
        if d:
            self._scan_dir.set(d)

    def _open_report(self):
        report = Path('shrinkify_report.html')
        if report.exists():
            webbrowser.open(report.resolve().as_uri())
        else:
            messagebox.showinfo('Report Not Found', 'Run an analysis first.')

    def _start_scan(self):
        if self._running:
            return
        d = self._scan_dir.get().strip()
        if not d:
            messagebox.showwarning('No Directory', 'Please select a directory.')
            return
        scan_path = Path(d)
        if not scan_path.exists():
            messagebox.showerror('Error', f'Directory not found:\n{scan_path}')
            return
        self._running = True
        self._scan_path = scan_path
        self._media_files = []
        self._summary = None
        self._btn_scan.config(state=tk.DISABLED, text='Scanning…')
        self._btn_convert.config(state=tk.DISABLED)
        self._btn_duplicates.config(state=tk.DISABLED)
        self._btn_report.config(state=tk.DISABLED)
        self._clear_summary()
        self._log_clear()
        self._log_autoscroll = True
        threading.Thread(target=self._run_scan, args=(scan_path,), daemon=True).start()

    def _start_convert(self):
        if self._running or not self._media_files:
            return
        dry    = self._opt_dry_run.get()
        hw     = self._opt_hw_accel.get()
        preset = self._opt_preset.get()
        copy_orig = self._opt_copy_original.get()
        candidates = [mf for mf in self._media_files if mf.needs_conversion and not mf.is_duplicate]
        if not candidates and not copy_orig:
            messagebox.showinfo('Nothing to Do', 'No conversion candidates and "Copy originals" is off.')
            return
        _, _, preset_label, _ = QUALITY_PRESETS[preset]
        msg = f"Convert {len(candidates)} file(s)?\n\nPreset: {preset_label}\nOutput: {self._scan_path / 'shrinkified'}\n"
        if copy_orig:
            unconverted = [mf for mf in self._media_files if not mf.needs_conversion and not mf.is_duplicate]
            msg += f"\n+ Copy {len(unconverted)} unconverted file(s) to output folder.\n"
        msg += "\nOriginal files will NOT be deleted."
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
            args=(candidates, dry, hw, preset, copy_orig),
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
            + ('[DRY RUN — no files will be deleted]' if dry else 'THIS CANNOT BE UNDONE.')
        )
        if not confirm:
            return
        self._running = True
        self._btn_duplicates.config(state=tk.DISABLED, text='Deleting…')
        self._log_autoscroll = True
        threading.Thread(target=self._run_delete_dupes, args=(dry,), daemon=True).start()

    # ─────────────────────────────────────────────────────────
    # BACKGROUND THREADS
    # ─────────────────────────────────────────────────────────
    def _run_scan(self, scan_path: Path):
        try:
            preset = self._opt_preset.get()
            self._log_section('Scanning files')
            media_files, scan_errors = scan_directory(
                scan_path,
                progress_callback=lambda c, t, f: self.after(
                    0, lambda p=int(c/t*40) if t else 0, fn=f:
                    self._set_progress(p, f'Scanning: {fn}')),
                error_callback=lambda path, err:
                    self._log_err(f'Scan error — {path.name}: {err}')
            )
            self._log_info(f'{len(media_files)} media files found.')
            if scan_errors:
                self._log_msg(f'  → {len(scan_errors)} files had scan errors (skipped).\n', 'yellow')
            if not media_files:
                self._log_err('No supported media files found.')
                self._done_scan()
                return

            if not self._opt_no_hash.get():
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
                self._log_info('Hash skipped.')

            self._log_section('Analyzing')
            self._set_progress(65, 'Analyzing…')
            summary = analyze_all(media_files, preset)
            self._media_files = media_files
            self._scan_errors = scan_errors
            self._summary = summary

            convert_count = summary.videos_to_convert + summary.images_to_convert
            self._log_info(f'Total: {summary.total_files:,} files, {_fmt_size(summary.total_size_bytes)}')
            self._log_info(f'Conversion candidates: {convert_count}  (est. −{_fmt_size(summary.estimated_savings_bytes)})')
            self._log_info(f'Duplicates: {summary.duplicate_count}  (−{_fmt_size(summary.duplicate_savings_bytes)})')
            self._log_info(f'Total potential savings: −{_fmt_size(summary.total_potential_savings_bytes)}  ({summary.savings_percentage:.1f}%)')
            self.after(0, lambda: self._show_summary(summary))

            self._set_progress(90, 'Generating report…')
            report_path = Path('shrinkify_report.html')
            generate_html_report(media_files, summary, scan_path, report_path)
            self._log_info(f'Report saved → {report_path.resolve()}')
            self.after(0, lambda: self._btn_report.config(state=tk.NORMAL))

            self._set_progress(100, 'Analysis complete ✓')
            self._log_msg('\n✓ Analysis complete.\n', 'accent')
            self.after(0, lambda: self._btn_convert.config(
                state=tk.NORMAL, text='⚙️  Convert Files'))
            self.after(0, lambda: self._btn_duplicates.config(
                state=tk.NORMAL if summary.duplicate_count > 0 else tk.DISABLED,
                text='🗑  Delete Duplicates'))
        except Exception as e:
            self._log_err(f'Unexpected error: {e}')
        finally:
            self._done_scan()

    def _run_convert(self, candidates: list, dry_run: bool, hw_accel: bool,
                     preset: str, copy_orig: bool):
        try:
            shrinkified_dir = self._scan_path / 'shrinkified'
            _, _, preset_label, _ = QUALITY_PRESETS[preset]
            dry_label = ' (DRY RUN)' if dry_run else ''
            self._log_section(
                f'Converting{dry_label} [{preset_label}] — {len(candidates)} files → shrinkified/')

            total_saved = 0
            success_count = 0
            fail_count = 0

            for i, mf in enumerate(candidates, 1):
                pct = int(i / len(candidates) * (80 if copy_orig else 100))
                self.after(0, lambda p=pct, fn=mf.filename:
                    self._set_progress(p, f'Converting ({p}%): {fn}'))
                result = convert_file(mf, shrinkified_dir=shrinkified_dir,
                                      use_hw_accel=hw_accel, dry_run=dry_run, preset=preset)
                if result.success:
                    success_count += 1
                    total_saved += result.size_saved_bytes
                    self._log_ok(
                        f'{mf.filename}  '
                        f'{_fmt_size(result.original_size_bytes)} → {_fmt_size(result.final_size_bytes)}'
                        f'  (−{_fmt_size(result.size_saved_bytes)})')
                elif result.skipped:
                    self._log_skip(f'{mf.filename}: {result.skip_reason}')
                else:
                    fail_count += 1
                    self._log_err(f'{mf.filename}: {result.error_message[:120]}')

            self._log_info(
                f'Conversion done: {success_count} succeeded, {fail_count} failed, '
                f'saved: {_fmt_size(total_saved)}')

            if copy_orig:
                self._log_section(f'Copying unconverted files{dry_label}')
                self._set_progress(85, 'Copying originals…')
                copied, copied_bytes = copy_unconverted(
                    self._media_files, shrinkified_dir, dry_run=dry_run)
                self._log_info(f'{copied} files copied ({_fmt_size(copied_bytes)})')

            self._set_progress(100, 'Conversion complete ✓')
            self._log_msg('\n✓ Conversion complete.\n', 'accent')
        except Exception as e:
            self._log_err(f'Unexpected error during conversion: {e}')
        finally:
            self._done_action(self._btn_convert, '⚙️  Convert Files')

    def _run_delete_dupes(self, dry_run: bool):
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
            self._done_action(self._btn_duplicates, '🗑  Delete Duplicates')

    # ─────────────────────────────────────────────────────────
    def _done_scan(self):
        self._running = False
        self.after(0, lambda: self._btn_scan.config(state=tk.NORMAL, text='🔍  Analyze'))

    def _done_action(self, btn, label):
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
        cards = [
            (f"{summary.total_files:,}", f"{_fmt_size(summary.total_size_bytes)}", 'Total Files', COLORS['blue']),
            (f"{summary.videos_to_convert + summary.images_to_convert:,}", 'conversion candidates', 'Convert', COLORS['accent2']),
            (f"{summary.duplicate_count:,}", f"{_fmt_size(summary.duplicate_size_bytes)}", 'Duplicates', COLORS['red']),
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
    frame = tk.Frame(parent, bg=COLORS['surface2'], cursor='hand2')
    icon_lbl = tk.Label(frame, text=icon, bg=COLORS['surface2'], fg=color,
                        font=UI_FONT, width=3, anchor='center')
    icon_lbl.pack(side=tk.LEFT, padx=(8, 0), pady=8)
    text_lbl = tk.Label(frame, text=label, bg=COLORS['surface2'], fg=color,
                        font=UI_BOLD, anchor='w')
    text_lbl.pack(side=tk.LEFT, padx=(4, 8), pady=8, fill=tk.X, expand=True)

    def on_enter(_):
        if frame.cget('cursor') != 'arrow':
            frame.config(bg=COLORS['surface'])
            icon_lbl.config(bg=COLORS['surface'])
            text_lbl.config(bg=COLORS['surface'])

    def on_leave(_):
        frame.config(bg=COLORS['surface2'])
        icon_lbl.config(bg=COLORS['surface2'])
        text_lbl.config(bg=COLORS['surface2'])

    def on_click(_):
        if frame.cget('cursor') != 'arrow':
            command()

    for w in (frame, icon_lbl, text_lbl):
        w.bind('<Enter>', on_enter)
        w.bind('<Leave>', on_leave)
        w.bind('<Button-1>', on_click)

    def _config(**kwargs):
        if 'state' in kwargs:
            if kwargs['state'] == tk.DISABLED:
                frame.config(cursor='arrow')
                icon_lbl.config(fg=COLORS['text_muted'])
                text_lbl.config(fg=COLORS['text_muted'])
            else:
                frame.config(cursor='hand2')
                icon_lbl.config(fg=color)
                text_lbl.config(fg=color)
        if 'text' in kwargs:
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
