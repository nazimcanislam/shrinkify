"""
workers.py — Background-thread methods for ShrinkifyApp.

Provided as a mixin so the thread logic stays separate from the widget
setup code in app.py, while still having full access to self (state vars,
log helpers, after(), etc.) through normal inheritance.

All methods here run in daemon threads.  They must never touch Tkinter
widgets directly — all UI updates go through self.after(0, ...) calls.
"""

from pathlib import Path

from core.scanner import scan_directory, scan_file, compute_hashes, find_duplicates
from core.analyzer import analyze_all, QUALITY_PRESETS
from core.converter import (
    convert_file, copy_unconverted, copy_size_skipped,
    delete_duplicates, get_hw_encoder, get_hw_probe_failure_reason,
)
from core.reporter import generate_html_report, _fmt_size


class WorkerMixin:

    # ── Scan ─────────────────────────────────────────────────────────────────

    def _run_scan(self):
        try:
            preset = self._opt_preset.get()
            self._log_section('Scanning')

            if self._single_file:
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
                    self._log_msg(
                        f'  → {len(scan_errors)} files had scan errors.\n',
                        'yellow')

            if not media_files:
                self._log_err('No supported media files found.')
                self._done_scan()
                return

            # Hashing (folder mode only)
            if self._mode == 'folder' and not self._opt_no_hash.get():
                self._log_section('Computing hashes')
                compute_hashes(
                    media_files,
                    progress_callback=lambda c, t, f: self.after(
                        0, lambda p=40 + int(c/t*20) if t else 40, fn=f:
                        self._set_progress(p, f'Hashing: {fn}')))
                dup_count = find_duplicates(media_files)
                if dup_count > 0:
                    self._log_msg(
                        f'  → {dup_count} duplicates found.\n',
                        'yellow', timestamp=True)
                else:
                    self._log_info('No duplicates found.')
            elif self._mode == 'folder':
                self._log_info('Hash skipped.')

            # Analysis
            self._log_section('Analyzing')
            self._set_progress(65, 'Analyzing…')
            summary = analyze_all(media_files, preset)
            self._media_files = media_files
            self._scan_errors = scan_errors
            self._summary     = summary

            convert_count = summary.videos_to_convert + summary.images_to_convert
            self._log_info(
                f'Total: {summary.total_files:,} files, '
                f'{_fmt_size(summary.total_size_bytes)}')
            self._log_info(
                f'Conversion candidates: {convert_count}  '
                f'(est. −{_fmt_size(summary.estimated_savings_bytes)})')
            if self._mode == 'folder':
                self._log_info(
                    f'Duplicates: {summary.duplicate_count}  '
                    f'(−{_fmt_size(summary.duplicate_savings_bytes)})')
            self._log_info(
                f'Total potential savings: '
                f'−{_fmt_size(summary.total_potential_savings_bytes)}'
                f'  ({summary.savings_percentage:.1f}%)')
            self.after(0, lambda: self._show_summary(summary))

            # Report
            self._set_progress(90, 'Generating report…')
            report_path = Path('shrinkify_report.html')
            generate_html_report(media_files, summary, self._scan_path, report_path)
            self._log_info(f'Report saved → {report_path.resolve()}')
            self.after(0, lambda: self._btn_report.config(state='normal'))

            self._set_progress(100, 'Analysis complete ✓')
            self._log_msg('\n✓ Analysis complete.\n', 'accent')
            self.after(0, lambda: self._btn_convert.config(
                state='normal', text='Convert Files'))
            if self._btn_duplicates:
                self.after(0, lambda: self._btn_duplicates.config(
                    state='normal' if summary.duplicate_count > 0 else 'disabled',
                    text='Delete Duplicates'))

        except Exception as e:
            self._log_err(f'Unexpected error: {e}')
        finally:
            self._done_scan()

    # ── Convert ──────────────────────────────────────────────────────────────

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
                    reason = get_hw_probe_failure_reason()
                    if reason:
                        self.after(0, lambda r=reason:
                            self._log_err(f'GPU probe failed — {r}'))
            else:
                enc_info = 'encoder: libx265'

            self._log_section(
                f'Converting{dry_label} '
                f'[{preset_label}, {enc_info}] — {len(candidates)} files')

            total_saved   = 0
            success_count = 0
            fail_count    = 0
            size_skipped: list = []

            for i, mf in enumerate(candidates, 1):
                pct = int(i / len(candidates) * (80 if copy_orig else 100))
                self.after(0, lambda p=pct, fn=mf.filename:
                    self._set_progress(p, f'Converting ({p}%): {fn}'))

                result = convert_file(
                    mf,
                    shrinkified_dir=shrinkified_dir,
                    scan_root=self._scan_path,
                    preserve_structure=preserve,
                    use_hw_accel=hw_accel,
                    dry_run=dry_run,
                    preset=preset)

                if result.success:
                    success_count += 1
                    total_saved   += result.size_saved_bytes
                    self._log_ok(
                        f'{mf.filename}  '
                        f'{_fmt_size(result.original_size_bytes)}'
                        f' → {_fmt_size(result.final_size_bytes)}'
                        f'  (−{_fmt_size(result.size_saved_bytes)})')
                elif result.skipped_due_to_size:
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

                # Files that were never conversion candidates
                copied1, bytes1 = copy_unconverted(
                    self._media_files, shrinkified_dir,
                    scan_root=self._scan_path,
                    preserve_structure=preserve,
                    dry_run=dry_run)
                # Files that were candidates but kept because output was larger
                copied2, bytes2 = copy_size_skipped(
                    size_skipped, shrinkified_dir,
                    scan_root=self._scan_path,
                    preserve_structure=preserve,
                    dry_run=dry_run)

                self._log_info(
                    f'{copied1 + copied2} files copied '
                    f'({_fmt_size(bytes1 + bytes2)})  '
                    f'[{copied1} unconverted + {copied2} kept-as-original]')

            self._set_progress(100, 'Conversion complete ✓')
            self._log_msg('\n✓ Conversion complete.\n', 'accent')

        except Exception as e:
            self._log_err(f'Unexpected error during conversion: {e}')
        finally:
            self._done_action(self._btn_convert, 'Convert Files')

    # ── Delete duplicates ─────────────────────────────────────────────────────

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
            self._done_action(self._btn_duplicates, 'Delete Duplicates')
