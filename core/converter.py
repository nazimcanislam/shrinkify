"""
converter.py — Conversion logic.

Images  → pillow-heif
Videos  → ffmpeg with auto-detected hardware encoder
"""

import shutil
import subprocess
import sys
from pathlib import Path
from dataclasses import dataclass

# ── Top-level imports for pillow-heif ────────────────────────
# Python caches modules in sys.modules so importing at function level
# works fine performance-wise, but top-level is cleaner and fails fast.
try:
    import pillow_heif as _pillow_heif
    from PIL import Image as _PILImage
    _pillow_heif.register_heif_opener()
    _PILLOW_HEIF_OK = True
except ImportError:
    _PILLOW_HEIF_OK = False

from core.scanner import MediaFile, _find_binary as _find_bin
from core.analyzer import QUALITY_PRESETS, DEFAULT_PRESET

_FFMPEG = _find_bin('ffmpeg')


# ── Subprocess helper ─────────────────────────────────────────

def _no_window() -> dict:
    """Prevents a console window flashing on Windows (PyInstaller --windowed)."""
    if sys.platform == 'win32':
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = subprocess.SW_HIDE
        return {'startupinfo': si, 'creationflags': subprocess.CREATE_NO_WINDOW}
    return {}


# ── Hardware encoder detection ────────────────────────────────

def detect_hw_encoder() -> str | None:
    """
    Returns the best available hardware HEVC encoder for this machine, or None.

    Priority:
      macOS  → hevc_videotoolbox  (Apple Silicon + Intel via VideoToolbox)
      NVIDIA → hevc_nvenc         (Windows / Linux)
      Intel  → hevc_qsv           (Intel Quick Sync, Windows / Linux)
      AMD    → hevc_amf           (AMD, Windows)
      None   → software libx265
    """
    try:
        result = subprocess.run(
            [_FFMPEG, '-encoders'],
            capture_output=True, encoding='utf-8', errors='replace', timeout=10,
            **_no_window()
        )
        output = result.stdout + result.stderr
    except Exception:
        return None

    candidates = [
        ('hevc_videotoolbox', sys.platform == 'darwin'),
        ('hevc_nvenc',        True),
        ('hevc_qsv',          True),
        ('hevc_amf',          True),
    ]
    for encoder, ok in candidates:
        if ok and encoder in output:
            return encoder
    return None


_HW_ENCODER_CACHE: str | None | bool = False  # False = not yet probed


def get_hw_encoder() -> str | None:
    global _HW_ENCODER_CACHE
    if _HW_ENCODER_CACHE is False:
        _HW_ENCODER_CACHE = detect_hw_encoder()
    return _HW_ENCODER_CACHE


# ── Data classes ──────────────────────────────────────────────

@dataclass
class ConversionResult:
    source_path: Path
    output_path: Path
    success: bool
    original_size_bytes: int
    final_size_bytes: int = 0
    error_message: str = ''
    skipped: bool = False
    skip_reason: str = ''

    @property
    def size_saved_bytes(self) -> int:
        return self.original_size_bytes - self.final_size_bytes if self.success else 0

    @property
    def skipped_due_to_size(self) -> bool:
        """True if this file was attempted but output was larger than original."""
        return self.skipped and 'larger' in self.skip_reason


# ── Path helpers ──────────────────────────────────────────────

def get_output_path(
    mf: MediaFile,
    shrinkified_dir: Path,
    scan_root: Path | None = None,
    preserve_structure: bool = False,
) -> Path:
    new_name = (mf.path.stem + '.mp4') if mf.media_type == 'video' else (mf.path.stem + '.heic')
    if preserve_structure and scan_root is not None:
        try:
            rel = mf.path.parent.relative_to(scan_root)
            return shrinkified_dir / rel / new_name
        except ValueError:
            pass
    return shrinkified_dir / new_name


# ── ffmpeg command builders ───────────────────────────────────

def _video_crf(preset: str) -> int:
    return {'max': 28, 'balanced': 24, 'conservative': 20}.get(preset, 24)


def _image_quality(preset: str) -> int:
    return QUALITY_PRESETS.get(preset, QUALITY_PRESETS[DEFAULT_PRESET])[1]


def _video_cmd(mf: MediaFile, output_path: Path, use_hw_accel: bool, preset: str) -> list[str]:
    cmd = [_FFMPEG, '-i', str(mf.path), '-y']
    crf = _video_crf(preset)
    if use_hw_accel:
        hw = get_hw_encoder()
        if hw == 'hevc_videotoolbox':
            qv = int(20 + (crf - 20) * (55 / 8))
            cmd += ['-c:v', 'hevc_videotoolbox', '-q:v', str(qv), '-tag:v', 'hvc1']
        elif hw == 'hevc_nvenc':
            cmd += ['-c:v', 'hevc_nvenc', '-rc', 'vbr', '-cq', str(crf + 4), '-preset', 'p4']
        elif hw == 'hevc_qsv':
            cmd += ['-c:v', 'hevc_qsv', '-global_quality', str(crf + 2)]
        elif hw == 'hevc_amf':
            cmd += ['-c:v', 'hevc_amf', '-quality', 'quality', '-rc', 'cqp',
                    '-qp_i', str(crf), '-qp_p', str(crf)]
        else:
            cmd += ['-c:v', 'libx265', '-crf', str(crf), '-preset', 'medium']
    else:
        cmd += ['-c:v', 'libx265', '-crf', str(crf), '-preset', 'medium']
    cmd += ['-c:a', 'aac', '-b:a', '128k', '-map_metadata', '0',
            '-movflags', '+faststart', str(output_path)]
    return cmd


# ── Image conversion ──────────────────────────────────────────

def _convert_image_pillow(mf: MediaFile, output_path: Path, quality: int) -> ConversionResult:
    if not _PILLOW_HEIF_OK:
        return ConversionResult(
            source_path=mf.path, output_path=output_path,
            success=False, original_size_bytes=mf.size_bytes,
            error_message='pillow-heif not installed. Run: pip install pillow-heif pillow'
        )
    try:
        img = _PILImage.open(mf.path)
        exif = img.info.get('exif', b'')
        save_kwargs: dict = {'format': 'HEIF', 'quality': quality}
        if exif:
            save_kwargs['exif'] = exif
        output_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(output_path, **save_kwargs)

        if not output_path.exists():
            return ConversionResult(source_path=mf.path, output_path=output_path,
                                    success=False, original_size_bytes=mf.size_bytes,
                                    error_message='Output file was not created')
        final_size = output_path.stat().st_size
        if final_size >= mf.size_bytes:
            output_path.unlink(missing_ok=True)
            return ConversionResult(source_path=mf.path, output_path=output_path,
                                    success=False, original_size_bytes=mf.size_bytes,
                                    skipped=True,
                                    skip_reason='Output was larger than original — original kept')
        return ConversionResult(source_path=mf.path, output_path=output_path,
                                success=True, original_size_bytes=mf.size_bytes,
                                final_size_bytes=final_size)
    except Exception as e:
        output_path.unlink(missing_ok=True)
        return ConversionResult(source_path=mf.path, output_path=output_path,
                                success=False, original_size_bytes=mf.size_bytes,
                                error_message=str(e))


# ── Main conversion entry point ───────────────────────────────

def convert_file(
    mf: MediaFile,
    shrinkified_dir: Path,
    scan_root: Path | None = None,
    preserve_structure: bool = False,
    use_hw_accel: bool = False,
    dry_run: bool = False,
    preset: str = DEFAULT_PRESET,
) -> ConversionResult:
    if not mf.needs_conversion:
        return ConversionResult(source_path=mf.path, output_path=mf.path,
                                success=False, original_size_bytes=mf.size_bytes,
                                skipped=True, skip_reason='No conversion needed')

    output_path = get_output_path(mf, shrinkified_dir, scan_root, preserve_structure)

    if dry_run:
        return ConversionResult(source_path=mf.path, output_path=output_path,
                                success=True, original_size_bytes=mf.size_bytes,
                                final_size_bytes=mf.estimated_output_size_bytes or mf.size_bytes,
                                skipped=True, skip_reason='Dry run')

    output_path.parent.mkdir(parents=True, exist_ok=True)

    if mf.media_type == 'image':
        return _convert_image_pillow(mf, output_path, _image_quality(preset))

    cmd = _video_cmd(mf, output_path, use_hw_accel, preset)
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=3600,
                                encoding='utf-8', errors='replace', **_no_window())
        if result.returncode == 0 and output_path.exists():
            final_size = output_path.stat().st_size
            if final_size >= mf.size_bytes:
                output_path.unlink(missing_ok=True)
                return ConversionResult(source_path=mf.path, output_path=output_path,
                                        success=False, original_size_bytes=mf.size_bytes,
                                        skipped=True,
                                        skip_reason='Output was larger than original — original kept')
            return ConversionResult(source_path=mf.path, output_path=output_path,
                                    success=True, original_size_bytes=mf.size_bytes,
                                    final_size_bytes=final_size)
        else:
            err = (result.stderr or '')[-600:]
            return ConversionResult(source_path=mf.path, output_path=output_path,
                                    success=False, original_size_bytes=mf.size_bytes,
                                    error_message=err or 'Unknown ffmpeg error')
    except subprocess.TimeoutExpired:
        output_path.unlink(missing_ok=True)
        return ConversionResult(source_path=mf.path, output_path=output_path,
                                success=False, original_size_bytes=mf.size_bytes,
                                error_message='Timed out after 1 hour')
    except Exception as e:
        return ConversionResult(source_path=mf.path, output_path=output_path,
                                success=False, original_size_bytes=mf.size_bytes,
                                error_message=str(e))


# ── Copy helpers ──────────────────────────────────────────────

def _copy_file(src: Path, dest: Path) -> bool:
    """Copies src to dest, creating parent dirs. Returns True on success."""
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        return True
    except OSError:
        return False


def _dest_for(mf: MediaFile, shrinkified_dir: Path,
              scan_root: Path | None, preserve_structure: bool) -> Path:
    """Original filename kept (no extension change) for copies."""
    if preserve_structure and scan_root is not None:
        try:
            rel = mf.path.parent.relative_to(scan_root)
            return shrinkified_dir / rel / mf.path.name
        except ValueError:
            pass
    return shrinkified_dir / mf.path.name


def copy_unconverted(
    media_files: list[MediaFile],
    shrinkified_dir: Path,
    scan_root: Path | None = None,
    preserve_structure: bool = False,
    dry_run: bool = False,
) -> tuple[int, int]:
    """
    Copies files that were NOT flagged for conversion (needs_conversion=False,
    not duplicate) into shrinkified_dir unchanged.
    Returns (copied_count, total_bytes_copied).
    """
    targets = [mf for mf in media_files if not mf.needs_conversion and not mf.is_duplicate]
    copied_count = 0
    total_bytes = 0
    for mf in targets:
        dest = _dest_for(mf, shrinkified_dir, scan_root, preserve_structure)
        if dry_run or _copy_file(mf.path, dest):
            copied_count += 1
            total_bytes += mf.size_bytes
    return copied_count, total_bytes


def copy_size_skipped(
    skipped_files: list[MediaFile],
    shrinkified_dir: Path,
    scan_root: Path | None = None,
    preserve_structure: bool = False,
    dry_run: bool = False,
) -> tuple[int, int]:
    """
    Copies files whose conversion was attempted but skipped because the output
    was larger than the original. These still have needs_conversion=True so
    copy_unconverted misses them — this function fills that gap.
    Returns (copied_count, total_bytes_copied).
    """
    copied_count = 0
    total_bytes = 0
    for mf in skipped_files:
        dest = _dest_for(mf, shrinkified_dir, scan_root, preserve_structure)
        if dry_run or _copy_file(mf.path, dest):
            copied_count += 1
            total_bytes += mf.size_bytes
    return copied_count, total_bytes


def delete_duplicates(media_files: list[MediaFile], dry_run: bool = False) -> tuple[int, int]:
    deleted_count = 0
    saved_bytes = 0
    for mf in media_files:
        if not mf.is_duplicate:
            continue
        if not dry_run:
            try:
                mf.path.unlink()
                deleted_count += 1
                saved_bytes += mf.size_bytes
            except OSError:
                pass
        else:
            deleted_count += 1
            saved_bytes += mf.size_bytes
    return deleted_count, saved_bytes
