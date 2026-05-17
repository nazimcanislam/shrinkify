"""
converter.py — Conversion logic.

Images  -> ffmpeg (AVIF) + exiftool for metadata preservation
Videos  -> ffmpeg with auto-detected hardware encoder

Image conversion requires exiftool. If exiftool is not found at startup,
image conversion will fail-fast before running ffmpeg (no wasted CPU time).
"""

import shutil
import subprocess
import sys
from pathlib import Path
from dataclasses import dataclass

from core.utils import FFMPEG, EXIFTOOL, EXIFTOOL_AVAILABLE, no_window
from core.scanner import MediaFile
from core.analyzer import QUALITY_PRESETS, DEFAULT_PRESET


# ---------------------------------------------------------------------------
# Hardware encoder detection
# ---------------------------------------------------------------------------

# Stores the stderr output of the first failing probe for each encoder,
# so the GUI can surface a useful "why did GPU detection fail?" message.
_PROBE_FAILURE_REASONS: dict[str, str] = {}


def _probe_encoder(encoder: str) -> bool:
    """
    Tests whether an encoder works by running a short null encode.
    Returns True only if ffmpeg exits cleanly without errors.

    Robustness notes vs. the old single-frame probe:
    - '-vframes 5' instead of 1: some NVENC implementations reject single-frame
      encodes because GOP initialisation never completes, producing a non-zero
      exit code even though the encoder is perfectly functional on real files.
    - '-pix_fmt yuv420p' is explicit: without it, format negotiation can fail
      on drivers that changed their default surface format (seen with RTX 40xx
      laptop GPUs on driver 530+).
    - stderr is captured and stored in _PROBE_FAILURE_REASONS so callers can
      surface a human-readable explanation when the probe fails.
    """
    base_cmd = [
        FFMPEG, '-loglevel', 'error',
        '-f', 'lavfi', '-i', 'color=black:s=256x256:r=1:d=1',
        '-vframes', '5',
        '-pix_fmt', 'yuv420p',
    ]
    if encoder == 'hevc_videotoolbox':
        base_cmd += ['-color_range', 'tv']
    base_cmd += ['-c:v', encoder, '-f', 'null', '-']

    try:
        result = subprocess.run(
            base_cmd,
            capture_output=True, encoding='utf-8', errors='replace', timeout=15,
            **no_window()
        )
        if result.returncode == 0:
            _PROBE_FAILURE_REASONS.pop(encoder, None)   # clear any stale entry
            return True
        # Store the last 400 chars of stderr so the GUI can report it
        reason = (result.stderr or '(no stderr)').strip()[-400:]
        _PROBE_FAILURE_REASONS[encoder] = reason
        return False
    except subprocess.TimeoutExpired:
        _PROBE_FAILURE_REASONS[encoder] = 'probe timed out after 15 s'
        return False
    except Exception as exc:
        _PROBE_FAILURE_REASONS[encoder] = str(exc)
        return False


def detect_hw_encoder() -> str | None:
    """
    Returns the best available hardware HEVC encoder, or None.
    Priority: macOS VideoToolbox -> NVIDIA NVENC -> Intel QSV -> AMD AMF
    """
    try:
        result = subprocess.run(
            [FFMPEG, '-encoders'],
            capture_output=True, encoding='utf-8', errors='replace', timeout=10,
            **no_window()
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
        if ok and encoder in output and _probe_encoder(encoder):
            return encoder
    return None


_HW_ENCODER_CACHE: str | None | bool = False  # False = not yet probed


def get_hw_encoder() -> str | None:
    global _HW_ENCODER_CACHE
    if _HW_ENCODER_CACHE is False:
        _HW_ENCODER_CACHE = detect_hw_encoder()
    return _HW_ENCODER_CACHE


def get_hw_probe_failure_reason() -> str:
    """
    Returns a human-readable explanation of why GPU encoder detection failed,
    intended for display in the GUI log.  Empty string if detection succeeded.
    """
    if not _PROBE_FAILURE_REASONS:
        return ''
    lines = []
    for enc, reason in _PROBE_FAILURE_REASONS.items():
        lines.append(f'{enc}: {reason}')
    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

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
        return self.skipped and 'larger' in self.skip_reason


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def get_output_path(
    mf: MediaFile,
    shrinkified_dir: Path,
    scan_root: Path | None = None,
    preserve_structure: bool = False,
) -> Path:
    new_name = (mf.path.stem + '.mp4') if mf.media_type == 'video' else (mf.path.stem + '.avif')
    if preserve_structure and scan_root is not None:
        try:
            rel = mf.path.parent.relative_to(scan_root)
            return shrinkified_dir / rel / new_name
        except ValueError:
            pass
    return shrinkified_dir / new_name


# ---------------------------------------------------------------------------
# ffmpeg command builders
# ---------------------------------------------------------------------------

def _video_crf(preset: str) -> int:
    return {'max': 28, 'balanced': 24, 'conservative': 20}.get(preset, 24)


def _image_quality(preset: str) -> int:
    return QUALITY_PRESETS.get(preset, QUALITY_PRESETS[DEFAULT_PRESET])[1]


def _image_crf(quality: int) -> int:
    """Maps Shrinkify quality (0-100) to AVIF CRF (0-63). Lower = better quality."""
    return round(63 - (quality / 100) * 63)


def _video_cmd(mf: MediaFile, output_path: Path, use_hw_accel: bool, preset: str) -> list[str]:
    cmd = [FFMPEG, '-i', str(mf.path), '-y']
    crf = _video_crf(preset)
    if use_hw_accel:
        hw = get_hw_encoder()
        if hw == 'hevc_videotoolbox':
            qv = int(20 + (crf - 20) * (55 / 8))
            cmd += ['-c:v', 'hevc_videotoolbox', '-q:v', str(qv), '-tag:v', 'hvc1']
        elif hw == 'hevc_nvenc':
            # '-b:v 0' is required in ffmpeg 6+ to disable the implicit bitrate
            # target; without it, '-rc vbr -cq X' can silently fall back to
            # bitrate-based mode (or error out with newer NVIDIA drivers).
            cmd += ['-c:v', 'hevc_nvenc', '-rc', 'vbr', '-cq', str(crf + 4),
                    '-b:v', '0', '-preset', 'p4']
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


# ---------------------------------------------------------------------------
# Image conversion — ffmpeg (AVIF) + exiftool (metadata)
# ---------------------------------------------------------------------------

def _copy_metadata_exiftool(source: Path, dest: Path) -> bool:
    """
    Copies all EXIF/IPTC/XMP tags from source to dest using exiftool.
    Also syncs FileCreateDate and FileModifyDate to DateTimeOriginal so the
    filesystem timestamp matches the original capture date.
    Returns True on success.
    """
    cmd = [
        EXIFTOOL,
        '-TagsFromFile', str(source),
        '-All:All',
        '-FileCreateDate<DateTimeOriginal',
        '-FileModifyDate<DateTimeOriginal',
        '-overwrite_original',
        str(dest),
    ]
    try:
        result = subprocess.run(
            cmd, capture_output=True, timeout=30,
            encoding='utf-8', errors='replace', **no_window()
        )
        return result.returncode == 0
    except Exception:
        return False


def _convert_image_ffmpeg(mf: MediaFile, output_path: Path, quality: int) -> ConversionResult:
    """
    Two-step image conversion pipeline:
      1. ffmpeg  — compresses to AVIF
      2. exiftool — restores all metadata from the source file

    Fails fast (before running ffmpeg) if exiftool is not available,
    so no CPU time is wasted on a conversion that would lose metadata.
    """
    # Fast-fail: exiftool required for metadata preservation
    if not EXIFTOOL_AVAILABLE:
        return ConversionResult(
            source_path=mf.path, output_path=output_path,
            success=False, original_size_bytes=mf.size_bytes,
            error_message=(
                'exiftool not found — image conversion aborted to prevent metadata loss. '
                'Place exiftool.exe next to gui.py, or run: winget install OliverBetz.ExifTool'
            ),
        )

    crf = _image_crf(quality)
    cmd = [
        FFMPEG, '-loglevel', 'error',
        '-i', str(mf.path),
        '-crf', str(crf),
        '-y',
        str(output_path),
    ]
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        result = subprocess.run(
            cmd, capture_output=True, timeout=300,
            encoding='utf-8', errors='replace', **no_window()
        )
        if result.returncode != 0 or not output_path.exists():
            err = (result.stderr or '')[-600:]
            return ConversionResult(
                source_path=mf.path, output_path=output_path,
                success=False, original_size_bytes=mf.size_bytes,
                error_message=err or 'Unknown ffmpeg error',
            )

        # Restore all metadata (GPS, dates, camera info, orientation, ...)
        metadata_ok = _copy_metadata_exiftool(mf.path, output_path)

        final_size = output_path.stat().st_size
        if final_size >= mf.size_bytes:
            output_path.unlink(missing_ok=True)
            return ConversionResult(
                source_path=mf.path, output_path=output_path,
                success=False, original_size_bytes=mf.size_bytes,
                skipped=True,
                skip_reason='Output was larger than original — original kept',
            )

        warning = '' if metadata_ok else 'exiftool ran but failed to copy metadata.'
        return ConversionResult(
            source_path=mf.path, output_path=output_path,
            success=True, original_size_bytes=mf.size_bytes,
            final_size_bytes=final_size,
            error_message=warning,
        )

    except subprocess.TimeoutExpired:
        output_path.unlink(missing_ok=True)
        return ConversionResult(
            source_path=mf.path, output_path=output_path,
            success=False, original_size_bytes=mf.size_bytes,
            error_message='Timed out after 5 minutes',
        )
    except Exception as e:
        output_path.unlink(missing_ok=True)
        return ConversionResult(
            source_path=mf.path, output_path=output_path,
            success=False, original_size_bytes=mf.size_bytes,
            error_message=str(e),
        )


# ---------------------------------------------------------------------------
# Main conversion entry point
# ---------------------------------------------------------------------------

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
        return ConversionResult(
            source_path=mf.path, output_path=mf.path,
            success=False, original_size_bytes=mf.size_bytes,
            skipped=True, skip_reason='No conversion needed',
        )

    output_path = get_output_path(mf, shrinkified_dir, scan_root, preserve_structure)

    if dry_run:
        return ConversionResult(
            source_path=mf.path, output_path=output_path,
            success=True, original_size_bytes=mf.size_bytes,
            final_size_bytes=mf.estimated_output_size_bytes or mf.size_bytes,
            skipped=True, skip_reason='Dry run',
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    if mf.media_type == 'image':
        return _convert_image_ffmpeg(mf, output_path, _image_quality(preset))

    # --- Video ---
    cmd = _video_cmd(mf, output_path, use_hw_accel, preset)
    try:
        result = subprocess.run(
            cmd, capture_output=True, timeout=3600,
            encoding='utf-8', errors='replace', **no_window()
        )
        if result.returncode == 0 and output_path.exists():
            final_size = output_path.stat().st_size
            if final_size >= mf.size_bytes:
                output_path.unlink(missing_ok=True)
                return ConversionResult(
                    source_path=mf.path, output_path=output_path,
                    success=False, original_size_bytes=mf.size_bytes,
                    skipped=True,
                    skip_reason='Output was larger than original — original kept',
                )
            return ConversionResult(
                source_path=mf.path, output_path=output_path,
                success=True, original_size_bytes=mf.size_bytes,
                final_size_bytes=final_size,
            )
        err = (result.stderr or '')[-600:]
        return ConversionResult(
            source_path=mf.path, output_path=output_path,
            success=False, original_size_bytes=mf.size_bytes,
            error_message=err or 'Unknown ffmpeg error',
        )
    except subprocess.TimeoutExpired:
        output_path.unlink(missing_ok=True)
        return ConversionResult(
            source_path=mf.path, output_path=output_path,
            success=False, original_size_bytes=mf.size_bytes,
            error_message='Timed out after 1 hour',
        )
    except Exception as e:
        return ConversionResult(
            source_path=mf.path, output_path=output_path,
            success=False, original_size_bytes=mf.size_bytes,
            error_message=str(e),
        )


# ---------------------------------------------------------------------------
# Copy helpers
# ---------------------------------------------------------------------------

def _copy_file(src: Path, dest: Path) -> bool:
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        return True
    except OSError:
        return False


def _dest_for(
    mf: MediaFile,
    shrinkified_dir: Path,
    scan_root: Path | None,
    preserve_structure: bool,
) -> Path:
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
    targets = [mf for mf in media_files if not mf.needs_conversion and not mf.is_duplicate]
    copied_count, total_bytes = 0, 0
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
    copied_count, total_bytes = 0, 0
    for mf in skipped_files:
        dest = _dest_for(mf, shrinkified_dir, scan_root, preserve_structure)
        if dry_run or _copy_file(mf.path, dest):
            copied_count += 1
            total_bytes += mf.size_bytes
    return copied_count, total_bytes


def delete_duplicates(
    media_files: list[MediaFile],
    dry_run: bool = False,
) -> tuple[int, int]:
    deleted_count, saved_bytes = 0, 0
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
