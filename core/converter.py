"""
converter.py — Conversion logic.

Images  → pillow-heif  (fixes ffmpeg HEIF muxer unavailability on Windows)
Videos  → ffmpeg libx265
"""

import shutil
import subprocess
import sys
from pathlib import Path
from dataclasses import dataclass
from core.scanner import MediaFile
from core.analyzer import QUALITY_PRESETS, DEFAULT_PRESET


def _no_window() -> dict:
    """Prevents a console window from flashing on Windows (PyInstaller --windowed)."""
    if sys.platform == 'win32':
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = subprocess.SW_HIDE
        return {'startupinfo': si, 'creationflags': subprocess.CREATE_NO_WINDOW}
    return {}


# pillow-heif is an optional dependency; we import lazily and report clearly if missing
_PILLOW_HEIF_AVAILABLE: bool | None = None

def _check_pillow_heif() -> bool:
    global _PILLOW_HEIF_AVAILABLE
    if _PILLOW_HEIF_AVAILABLE is None:
        try:
            import pillow_heif  # noqa: F401
            from PIL import Image  # noqa: F401
            _PILLOW_HEIF_AVAILABLE = True
        except ImportError:
            _PILLOW_HEIF_AVAILABLE = False
    return _PILLOW_HEIF_AVAILABLE


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


def get_output_path(mf: MediaFile, shrinkified_dir: Path) -> Path:
    if mf.media_type == 'video':
        return shrinkified_dir / (mf.path.stem + '.mp4')
    else:
        return shrinkified_dir / (mf.path.stem + '.heic')


def _video_crf(preset: str) -> int:
    return {'max': 28, 'balanced': 24, 'conservative': 20}.get(preset, 24)


def _image_quality(preset: str) -> int:
    """pillow-heif quality (0-100)."""
    return QUALITY_PRESETS.get(preset, QUALITY_PRESETS[DEFAULT_PRESET])[1]


def _video_cmd(mf: MediaFile, output_path: Path, use_hw_accel: bool, preset: str) -> list[str]:
    cmd = ['ffmpeg', '-i', str(mf.path), '-y']
    if use_hw_accel:
        cq = str(_video_crf(preset) + 4)
        cmd += ['-c:v', 'hevc_nvenc', '-rc', 'vbr', '-cq', cq, '-preset', 'p4']
    else:
        cmd += ['-c:v', 'libx265', '-crf', str(_video_crf(preset)), '-preset', 'medium']
    cmd += [
        '-c:a', 'aac', '-b:a', '128k',
        '-map_metadata', '0',
        '-movflags', '+faststart',
        str(output_path)
    ]
    return cmd


def _convert_image_pillow(mf: MediaFile, output_path: Path, quality: int) -> ConversionResult:
    """Convert image to HEIF using pillow-heif."""
    try:
        import pillow_heif
        from PIL import Image

        pillow_heif.register_heif_opener()

        img = Image.open(mf.path)

        # Preserve EXIF if present
        exif = img.info.get('exif', b'')

        save_kwargs: dict = {'format': 'HEIF', 'quality': quality}
        if exif:
            save_kwargs['exif'] = exif

        img.save(output_path, **save_kwargs)

        if not output_path.exists():
            return ConversionResult(
                source_path=mf.path, output_path=output_path,
                success=False, original_size_bytes=mf.size_bytes,
                error_message='Output file was not created'
            )

        final_size = output_path.stat().st_size
        if final_size >= mf.size_bytes:
            output_path.unlink(missing_ok=True)
            return ConversionResult(
                source_path=mf.path, output_path=output_path,
                success=False, original_size_bytes=mf.size_bytes,
                skipped=True, skip_reason='Output was larger than original — original kept'
            )

        return ConversionResult(
            source_path=mf.path, output_path=output_path,
            success=True, original_size_bytes=mf.size_bytes,
            final_size_bytes=final_size
        )

    except Exception as e:
        output_path.unlink(missing_ok=True)
        return ConversionResult(
            source_path=mf.path, output_path=output_path,
            success=False, original_size_bytes=mf.size_bytes,
            error_message=str(e)
        )


def convert_file(
    mf: MediaFile,
    shrinkified_dir: Path,
    use_hw_accel: bool = False,
    dry_run: bool = False,
    preset: str = DEFAULT_PRESET,
) -> ConversionResult:
    if not mf.needs_conversion:
        return ConversionResult(
            source_path=mf.path, output_path=mf.path,
            success=False, original_size_bytes=mf.size_bytes,
            skipped=True, skip_reason='No conversion needed'
        )

    output_path = get_output_path(mf, shrinkified_dir)

    if dry_run:
        return ConversionResult(
            source_path=mf.path, output_path=output_path,
            success=True, original_size_bytes=mf.size_bytes,
            final_size_bytes=mf.estimated_output_size_bytes or mf.size_bytes,
            skipped=True, skip_reason='Dry run'
        )

    shrinkified_dir.mkdir(parents=True, exist_ok=True)

    # ── Images → pillow-heif ──────────────────────────────────
    if mf.media_type == 'image':
        if not _check_pillow_heif():
            return ConversionResult(
                source_path=mf.path, output_path=output_path,
                success=False, original_size_bytes=mf.size_bytes,
                error_message=(
                    'pillow-heif not installed. '
                    'Run: pip install pillow-heif pillow'
                )
            )
        return _convert_image_pillow(mf, output_path, _image_quality(preset))

    # ── Videos → ffmpeg ──────────────────────────────────────
    cmd = _video_cmd(mf, output_path, use_hw_accel, preset)
    try:
        result = subprocess.run(
            cmd, capture_output=True, timeout=3600,
            encoding='utf-8', errors='replace',
            **_no_window()
        )
        if result.returncode == 0 and output_path.exists():
            final_size = output_path.stat().st_size
            if final_size >= mf.size_bytes:
                output_path.unlink(missing_ok=True)
                return ConversionResult(
                    source_path=mf.path, output_path=output_path,
                    success=False, original_size_bytes=mf.size_bytes,
                    skipped=True, skip_reason='Output was larger than original — original kept'
                )
            return ConversionResult(
                source_path=mf.path, output_path=output_path,
                success=True, original_size_bytes=mf.size_bytes,
                final_size_bytes=final_size
            )
        else:
            err = (result.stderr or '')[-600:]
            return ConversionResult(
                source_path=mf.path, output_path=output_path,
                success=False, original_size_bytes=mf.size_bytes,
                error_message=err or 'Unknown ffmpeg error'
            )
    except subprocess.TimeoutExpired:
        output_path.unlink(missing_ok=True)
        return ConversionResult(
            source_path=mf.path, output_path=output_path,
            success=False, original_size_bytes=mf.size_bytes,
            error_message='Timed out after 1 hour'
        )
    except Exception as e:
        return ConversionResult(
            source_path=mf.path, output_path=output_path,
            success=False, original_size_bytes=mf.size_bytes,
            error_message=str(e)
        )


def copy_unconverted(
    media_files: list[MediaFile],
    shrinkified_dir: Path,
    dry_run: bool = False,
) -> tuple[int, int]:
    """
    Copies files that were NOT converted (needs_conversion=False, not duplicate)
    into shrinkified_dir unchanged.
    Returns (copied_count, total_bytes_copied).
    """
    unconverted = [
        mf for mf in media_files
        if not mf.needs_conversion and not mf.is_duplicate
    ]
    copied_count = 0
    total_bytes = 0

    if not dry_run:
        shrinkified_dir.mkdir(parents=True, exist_ok=True)

    for mf in unconverted:
        dest = shrinkified_dir / mf.path.name
        if not dry_run:
            try:
                shutil.copy2(mf.path, dest)   # copy2 preserves metadata/timestamps
                copied_count += 1
                total_bytes += mf.size_bytes
            except OSError:
                pass
        else:
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
