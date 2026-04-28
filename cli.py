"""
cli.py — Shrinkify command-line interface.

Usage:
  python cli.py <directory> [options]

Examples:
  python cli.py "C:\\Photos"
  python cli.py "C:\\Takeout" --convert --copy-originals
  python cli.py "C:\\Videos"  --convert --dry-run
"""

import argparse
import sys
from pathlib import Path

from core.scanner import scan_directory, compute_hashes, find_duplicates
from core.analyzer import analyze_all
from core.converter import convert_file, copy_unconverted, delete_duplicates
from core.reporter import generate_html_report, print_summary, _fmt_size
from version import __version__


def _progress_bar(current: int, total: int, filename: str, width: int = 35) -> None:
    pct = current / total if total > 0 else 0
    filled = int(width * pct)
    bar = '█' * filled + '░' * (width - filled)
    name = filename[:48] + '…' if len(filename) > 50 else filename.ljust(50)
    print(f"\r  [{bar}] {current}/{total}  {name}", end='', flush=True)


def main():
    parser = argparse.ArgumentParser(
        prog='shrinkify',
        description='Analyze media files, suggest conversions, and detect duplicates.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli.py "C:\\Photos"                           → Analyze only + HTML report
  python cli.py "C:\\Takeout" --convert                → Analyze + convert
  python cli.py "C:\\Takeout" --convert --copy-originals → Complete output folder
  python cli.py "C:\\Videos"  --convert --dry-run      → Simulate (nothing changes)
  python cli.py "C:\\Media"   --duplicates             → Delete duplicates

Dry run:
  Shows exactly what would happen without touching any files.
  Always use this first to preview results before committing.
        """
    )
    parser.add_argument('directory',          type=str, help='Directory to scan')
    parser.add_argument('--convert',          action='store_true', help='Convert candidates')
    parser.add_argument('--preset',           type=str, default='balanced',
                        choices=['max', 'balanced', 'conservative'],
                        help='Quality preset (default: balanced)')
    parser.add_argument('--copy-originals',   action='store_true',
                        help='Also copy unconverted files to output folder')
    parser.add_argument('--preserve-structure', action='store_true',
                        help='Preserve subfolder structure inside shrinkified/')
    parser.add_argument('--duplicates',       action='store_true', help='Delete duplicate files')
    parser.add_argument('--dry-run',          action='store_true', help='Simulate — no files modified')
    parser.add_argument('--no-hash',          action='store_true', help='Skip hash computation')
    parser.add_argument('--hw-accel',         action='store_true', help='NVIDIA GPU acceleration (NVENC)')
    parser.add_argument('--report',           type=str, default='shrinkify_report.html')
    parser.add_argument('--no-report',        action='store_true')
    parser.add_argument('--version', action='version', version=f'Shrinkify {__version__}')

    args = parser.parse_args()
    scan_dir = Path(args.directory)
    if not scan_dir.exists() or not scan_dir.is_dir():
        print(f"\n  ERROR: Directory not found → {scan_dir}\n")
        sys.exit(1)

    shrinkified_dir = scan_dir / 'shrinkified'

    print(f"\n  Shrinkify starting...\n  Directory: {scan_dir}\n")

    # 1. Scan
    print("  [1/4] Scanning files...")
    media_files, scan_errors = scan_directory(
        scan_dir, progress_callback=lambda c, t, f: _progress_bar(c, t, f))
    print(f"\n  → {len(media_files)} media files found.")
    if scan_errors:
        print(f"  → {len(scan_errors)} files had scan errors.")
    print()
    if not media_files:
        print("  No supported media files found. Exiting.\n")
        sys.exit(0)

    # 2. Hash
    dup_count = 0
    if not args.no_hash:
        print("  [2/4] Computing hashes...")
        compute_hashes(media_files, progress_callback=lambda c, t, f: _progress_bar(c, t, f))
        dup_count = find_duplicates(media_files)
        print(f"\n  → {dup_count} duplicates found.\n")
    else:
        print("  [2/4] Hash skipped (--no-hash)\n")

    # 3. Analyze
    print("  [3/4] Analyzing files...")
    summary = analyze_all(media_files, args.preset)
    print_summary(summary, scan_dir)

    # 4. Convert
    if args.convert:
        candidates = [mf for mf in media_files if mf.needs_conversion and not mf.is_duplicate]
        dry_label = " (DRY RUN)" if args.dry_run else ""
        if candidates:
            print(f"  [4/4] Converting{dry_label} [{args.preset}] — {len(candidates)} files → {shrinkified_dir}\n")
            total_saved = 0
            success_count = 0
            fail_count = 0
            for i, mf in enumerate(candidates, 1):
                print(f"  [{i}/{len(candidates)}] {mf.filename}")
                result = convert_file(mf, shrinkified_dir=shrinkified_dir,
                                      scan_root=scan_dir,
                                      preserve_structure=args.preserve_structure,
                                      use_hw_accel=args.hw_accel,
                                      dry_run=args.dry_run, preset=args.preset)
                if result.success:
                    success_count += 1
                    total_saved += result.size_saved_bytes
                    print(f"    ✓ {_fmt_size(result.original_size_bytes)} → {_fmt_size(result.final_size_bytes)}  (−{_fmt_size(result.size_saved_bytes)})")
                elif result.skipped:
                    print(f"    ○ Skipped: {result.skip_reason}")
                else:
                    fail_count += 1
                    print(f"    ✗ Error: {result.error_message[:80]}")
            print(f"\n  ── Done: {success_count} succeeded, {fail_count} failed, saved: {_fmt_size(total_saved)}\n")

        if args.copy_originals:
            print(f"  Copying unconverted files{dry_label}...")
            copied, copied_bytes = copy_unconverted(media_files, shrinkified_dir,
                                                       scan_root=scan_dir,
                                                       preserve_structure=args.preserve_structure,
                                                       dry_run=args.dry_run)
            print(f"  → {copied} files copied ({_fmt_size(copied_bytes)})\n")
    else:
        print("  [4/4] Conversion skipped (add --convert to enable)\n")

    # 5. Duplicates
    if args.duplicates and dup_count > 0:
        dry_label = " (DRY RUN)" if args.dry_run else ""
        print(f"  Deleting duplicates{dry_label}...")
        deleted, saved = delete_duplicates(media_files, dry_run=args.dry_run)
        print(f"  → {deleted} deleted, {_fmt_size(saved)} recovered.\n")

    # 6. Report
    if not args.no_report:
        report_path = Path(args.report)
        print(f"  Generating HTML report → {report_path}...")
        generate_html_report(media_files, summary, scan_dir, report_path)
        print(f"  → Report ready: {report_path.resolve()}\n")


if __name__ == '__main__':
    main()
