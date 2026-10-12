"""
converter.py — Conversion logic.

Images  -> ffmpeg (AVIF, optionally GPU-accelerated) + exiftool for metadata preservation
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
_HW_DEVICE_ARGS: dict[str, list[str]] = {}


def _run_encoder_probe(encoder: str, cmd: list[str]) -> bool:
    """Runs a probe command and records a concise failure reason."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True, encoding='utf-8', errors='replace', timeout=15,
            **no_window()
        )
        if result.returncode == 0:
            _PROBE_FAILURE_REASONS.pop(encoder, None)
            return True
        _PROBE_FAILURE_REASONS[encoder] = (result.stderr or '(no stderr)').strip()[-400:]
        return False
    except subprocess.TimeoutExpired:
        _PROBE_FAILURE_REASONS[encoder] = 'probe timed out after 15 s'
        return False
    except Exception as exc:
        _PROBE_FAILURE_REASONS[encoder] = str(exc)
        return False


def _probe_encoder(encoder: str, device_args: list[str] | None = None) -> bool:
    """
    Tests whether an encoder works by running a short null encode.
    Returns True only if ffmpeg exits cleanly without errors.

    Robustness notes vs. the old single-frame probe:
    - '-vframes 5' instead of 1: some NVENC implementations reject single-frame
      encodes because GOP initialisation never completes, producing a non-zero
      exit code even though the encoder is perfectly functional on real files.
    - '-pix_fmt' selection: QSV requires 'nv12' (yuv420p is rejected by QSV).
      Other encoders use explicit 'yuv420p' to prevent driver format negotiation
      failures.
    - Device args starting with '-init_hw_device' are placed before '-i'
      (global options).
    - stderr is captured and stored in _PROBE_FAILURE_REASONS so callers can
      surface a human-readable explanation when the probe fails.
    """
    pix_fmt = 'nv12' if 'qsv' in encoder else 'yuv420p'
    args = device_args or []
    is_global = bool(args and args[0] in ('-init_hw_device', '-filter_hw_device'))
    global_args = args if is_global else []
    encoder_extra = [] if is_global else args

    base_cmd = [
        FFMPEG, '-loglevel', 'error',
        *global_args,
        '-f', 'lavfi', '-i', 'color=black:s=256x256:r=1:d=1',
        '-vframes', '5',
        '-pix_fmt', pix_fmt,
    ]
    if encoder == 'hevc_videotoolbox':
        base_cmd += ['-color_range', 'tv']
    base_cmd += ['-c:v', encoder, *encoder_extra, '-f', 'null', '-']

    return _run_encoder_probe(encoder, base_cmd)


def _available_encoders() -> str:
    """Returns the stdout+stderr of ffmpeg -encoders, or empty string on error."""
    try:
        result = subprocess.run(
            [FFMPEG, '-encoders'],
            capture_output=True, encoding='utf-8', errors='replace', timeout=10,
            **no_window()
        )
        return result.stdout + result.stderr
    except Exception:
        return ''


def _get_dri_render_devices() -> list[Path]:
    """Returns sorted Linux DRI render nodes (/dev/dri/renderD*), if available."""
    if sys.platform.startswith('linux') and Path('/dev/dri').exists():
        return sorted(Path('/dev/dri').glob('renderD*'))
    return []


def _probe_nvenc_encoder(encoder: str) -> bool:
    """Selects the first NVENC-capable GPU that passes an encode probe."""
    for index in range(16):
        args = ['-gpu', str(index)]
        if _probe_encoder(encoder, args):
            _HW_DEVICE_ARGS[encoder] = args
            return True
    return False


def _probe_qsv_encoder(encoder: str) -> bool:
    """Selects the first working QSV configuration (default or Linux render nodes)."""
    # 1. Try default driver configuration (Windows, or Linux auto-detection)
    if _probe_encoder(encoder):
        return True

    # 2. On Linux, try with explicit DRI render nodes
    for device in _get_dri_render_devices():
        args = ['-init_hw_device', f'qsv=hw,child_device={device}', '-filter_hw_device', 'hw']
        if _probe_encoder(encoder, device_args=args):
            _HW_DEVICE_ARGS[encoder] = args
            return True
        va_args = ['-init_hw_device', f'vaapi=va:{device}', '-init_hw_device', 'qsv=hw@va', '-filter_hw_device', 'hw']
        if _probe_encoder(encoder, device_args=va_args):
            _HW_DEVICE_ARGS[encoder] = va_args
            return True
    return False


def _probe_hwframe_encoder(
    encoder: str,
    device_spec: str,
    device_name: str,
    pixel_format: str,
    encoder_options: list[str],
    device_args: list[str] | None = None,
) -> bool:
    """Tests an encoder that accepts only frames uploaded to a hardware device."""
    cmd = [
        FFMPEG, '-loglevel', 'error',
        *(device_args or ['-init_hw_device', device_spec, '-filter_hw_device', device_name]),
        '-f', 'lavfi', '-i', 'color=black:s=256x256:r=1:d=1',
        '-vf', f'format={pixel_format},hwupload',
        '-vframes', '1',
        '-c:v', encoder, *encoder_options,
        '-f', 'null', '-',
    ]
    return _run_encoder_probe(encoder, cmd)


def _probe_vaapi_encoder(
    encoder: str,
    pixel_format: str = 'nv12',
    encoder_options: list[str] | None = None,
) -> bool:
    """Probes Linux VA-API render nodes (or default va device) for an encoder."""
    options = encoder_options or ['-rc_mode', 'CQP', '-qp', '24']
    device_spec = 'vaapi=va'
    device_name = 'va'

    for device in _get_dri_render_devices():
        args = ['-init_hw_device', f'vaapi=va:{device}', '-filter_hw_device', device_name]
        if _probe_hwframe_encoder(encoder, device_spec, device_name, pixel_format, options, device_args=args):
            _HW_DEVICE_ARGS[encoder] = args
            return True

    args = ['-init_hw_device', device_spec, '-filter_hw_device', device_name]
    if _probe_hwframe_encoder(encoder, device_spec, device_name, pixel_format, options, device_args=args):
        _HW_DEVICE_ARGS[encoder] = args
        return True

    return False


def _probe_vulkan_encoder(
    encoder: str,
    pixel_format: str = 'yuv420p',
    encoder_options: list[str] | None = None,
) -> bool:
    """Probes Vulkan device indices 0..15 for an encoder."""
    options = encoder_options or ['-rc_mode', 'cqp', '-qp', '32']
    device_name = 'vk'

    for index in range(16):
        args = ['-init_hw_device', f'vulkan=vk:{index}', '-filter_hw_device', device_name]
        if _probe_hwframe_encoder(encoder, f'vulkan=vk:{index}', device_name, pixel_format, options, device_args=args):
            _HW_DEVICE_ARGS[encoder] = args
            return True

    return False


def detect_hw_encoder() -> str | None:
    """
    Returns the best available hardware HEVC encoder, or None.
    Priority: macOS VideoToolbox -> NVIDIA NVENC -> Intel QSV -> Linux VA-API -> AMD AMF
    """
    output = _available_encoders()
    if not output:
        return None

    candidates = [
        ('hevc_videotoolbox', sys.platform == 'darwin'),
        ('hevc_nvenc',        True),
        ('hevc_qsv',          True),
        ('hevc_vaapi',        sys.platform.startswith('linux')),
        ('hevc_amf',          True),
    ]
    for encoder, ok in candidates:
        if not ok or encoder not in output:
            continue
        if encoder == 'hevc_nvenc' and _probe_nvenc_encoder(encoder):
            return encoder
        if encoder == 'hevc_qsv' and _probe_qsv_encoder(encoder):
            return encoder
        if encoder == 'hevc_vaapi' and _probe_vaapi_encoder(encoder, 'nv12', ['-rc_mode', 'CQP', '-qp', '24']):
            return encoder
        if encoder not in ('hevc_nvenc', 'hevc_qsv', 'hevc_vaapi') and _probe_encoder(encoder):
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


def detect_hw_image_encoder() -> str | None:
    """Returns a working hardware AV1 encoder suitable for AVIF output."""
    output = _available_encoders()
    if not output:
        return None

    # AVIF stores AV1.  Keep this separate from HEVC video detection: a GPU
    # may encode HEVC but not AV1 (for example, pre-Ada NVIDIA hardware).
    candidates = [
        ('av1_videotoolbox', sys.platform == 'darwin'),
        ('av1_nvenc',        True),
        ('av1_qsv',          True),
        ('av1_amf',          True),
        ('av1_vaapi',        sys.platform.startswith('linux')),
        ('av1_vulkan',       sys.platform.startswith('linux') or sys.platform == 'win32'),
    ]
    for encoder, ok in candidates:
        if not ok or encoder not in output:
            continue
        if encoder == 'av1_nvenc' and _probe_nvenc_encoder(encoder):
            return encoder
        if encoder == 'av1_qsv' and _probe_qsv_encoder(encoder):
            return encoder
        if encoder == 'av1_vaapi' and _probe_vaapi_encoder(encoder, 'nv12', ['-rc_mode', 'CQP', '-qp', '32']):
            return encoder
        if encoder == 'av1_vulkan' and _probe_vulkan_encoder(encoder, 'yuv420p', ['-rc_mode', 'cqp', '-qp', '32']):
            return encoder
        if encoder not in ('av1_nvenc', 'av1_qsv', 'av1_vaapi', 'av1_vulkan') and _probe_encoder(encoder):
            return encoder
    return None


_HW_IMAGE_ENCODER_CACHE: str | None | bool = False  # False = not yet probed


def get_hw_image_encoder() -> str | None:
    global _HW_IMAGE_ENCODER_CACHE
    if _HW_IMAGE_ENCODER_CACHE is False:
        _HW_IMAGE_ENCODER_CACHE = detect_hw_image_encoder()
    return _HW_IMAGE_ENCODER_CACHE


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


def _selected_device_args(encoder: str) -> list[str]:
    return _HW_DEVICE_ARGS.get(encoder, [])


def _video_cmd(mf: MediaFile, output_path: Path, use_hw_accel: bool, preset: str) -> list[str]:
    crf = _video_crf(preset)
    hw = get_hw_encoder() if use_hw_accel else None
    device_args = _selected_device_args(hw) if hw else []
    is_global = bool(device_args and device_args[0] in ('-init_hw_device', '-filter_hw_device'))
    global_hw_args = device_args if is_global else []
    encoder_hw_args = [] if is_global else device_args

    cmd = [FFMPEG, *global_hw_args, '-i', str(mf.path), '-y']
    if hw == 'hevc_videotoolbox':
        qv = int(20 + (crf - 20) * (55 / 8))
        cmd += ['-c:v', 'hevc_videotoolbox', '-q:v', str(qv), '-tag:v', 'hvc1']
    elif hw == 'hevc_nvenc':
        # '-b:v 0' is required in ffmpeg 6+ to disable the implicit bitrate
        # target; without it, '-rc vbr -cq X' can silently fall back to
        # bitrate-based mode (or error out with newer NVIDIA drivers).
        cmd += ['-c:v', 'hevc_nvenc', '-rc', 'vbr', '-cq', str(crf + 4),
                '-b:v', '0', '-preset', 'p4', *encoder_hw_args]
    elif hw == 'hevc_qsv':
        cmd += ['-pix_fmt', 'nv12', '-c:v', 'hevc_qsv', '-global_quality', str(crf + 2), *encoder_hw_args]
    elif hw == 'hevc_vaapi':
        if not global_hw_args:
            cmd[1:1] = ['-init_hw_device', 'vaapi=va', '-filter_hw_device', 'va']
        cmd += ['-vf', 'format=nv12,hwupload', '-c:v', 'hevc_vaapi',
                '-rc_mode', 'CQP', '-qp', str(crf)]
    elif hw == 'hevc_amf':
        cmd += ['-c:v', 'hevc_amf', '-quality', 'quality', '-rc', 'cqp',
                '-qp_i', str(crf), '-qp_p', str(crf), *encoder_hw_args]
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


def _image_cmd(
    mf: MediaFile,
    output_path: Path,
    quality: int,
    use_hw_accel: bool,
) -> tuple[list[str], str | None]:
    """Builds an AVIF command and returns the encoder used (or None for CPU)."""
    crf = _image_crf(quality)
    cmd = [FFMPEG, '-loglevel', 'error', '-i', str(mf.path)]
    hw_encoder = get_hw_image_encoder() if use_hw_accel else None
    if hw_encoder == 'av1_videotoolbox':
        cmd += ['-c:v', hw_encoder, '-q:v', str(crf), '-pix_fmt', 'yuv420p']
    elif hw_encoder == 'av1_nvenc':
        cmd += ['-c:v', hw_encoder, '-rc', 'vbr', '-cq', str(crf),
                '-b:v', '0', '-preset', 'p4', '-pix_fmt', 'yuv420p', *_selected_device_args(hw_encoder)]
    elif hw_encoder == 'av1_qsv':
        cmd += ['-c:v', hw_encoder, '-global_quality', str(crf), '-pix_fmt', 'p010le']
    elif hw_encoder == 'av1_amf':
        cmd += ['-c:v', hw_encoder, '-quality', 'quality', '-rc', 'cqp',
                '-qp_i', str(crf), '-qp_p', str(crf), '-pix_fmt', 'yuv420p']
    elif hw_encoder == 'av1_vaapi':
        # VA-API accepts only hardware frames, so initialise a VA device and
        # upload the decoded image before handing it to the encoder.
        cmd[3:3] = _selected_device_args(hw_encoder) or ['-init_hw_device', 'vaapi=va', '-filter_hw_device', 'va']
        cmd += ['-vf', 'format=nv12,hwupload', '-c:v', hw_encoder,
                '-rc_mode', 'CQP', '-qp', str(crf)]
    elif hw_encoder == 'av1_vulkan':
        # Like VA-API, Vulkan encoders accept hardware frames only.
        cmd[3:3] = _selected_device_args(hw_encoder) or ['-init_hw_device', 'vulkan=vk', '-filter_hw_device', 'vk']
        cmd += ['-vf', 'format=yuv420p,hwupload', '-c:v', hw_encoder,
                '-rc_mode', 'cqp', '-qp', str(crf), '-tune', 'hq']
    else:
        # Explicitly select the existing CPU encoder so a failed GPU attempt
        # can reliably retry with the same output format and quality.
        cmd += ['-c:v', 'libaom-av1', '-crf', str(crf), '-still-picture', '1']
    cmd += ['-y', str(output_path)]
    return cmd, hw_encoder


def _convert_image_ffmpeg(
    mf: MediaFile,
    output_path: Path,
    quality: int,
    use_hw_accel: bool = False,
) -> ConversionResult:
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

    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        cmd, used_hw_encoder = _image_cmd(mf, output_path, quality, use_hw_accel)
        result = subprocess.run(
            cmd, capture_output=True, timeout=300,
            encoding='utf-8', errors='replace', **no_window()
        )
        if (result.returncode != 0 or not output_path.exists()) and used_hw_encoder:
            # A probe can pass while a particular image fails due to its pixel
            # format or driver limits.  Preserve conversion reliability by
            # retrying the established CPU path once.
            output_path.unlink(missing_ok=True)
            cmd, used_hw_encoder = _image_cmd(mf, output_path, quality, use_hw_accel=False)
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

        if used_hw_encoder in ('av1_vaapi', 'av1_vulkan') and output_path.exists():
            # VA-API and Vulkan encode to hardware surface frames (vaapi/vulkan),
            # causing FFmpeg's AVIF muxer to emit an invalid pixi box with 0
            # planes ("unsupported plane count [0]"). Encoders with explicit
            # software pixel formats (NVENC, QSV, AMF, VideoToolbox) write
            # compliant pixi boxes directly in one pass. Remuxing via stream
            # copy rebuilds a compliant container for VA-API and Vulkan before
            # ExifTool restores metadata.
            remux_path = output_path.with_name(f"{output_path.stem}.remux{output_path.suffix}")
            remux_cmd = [
                FFMPEG, '-loglevel', 'error',
                '-i', str(output_path),
                '-c:v', 'copy', '-map', '0:v:0',
                '-y', str(remux_path),
            ]
            remux_res = subprocess.run(
                remux_cmd, capture_output=True, timeout=30, **no_window()
            )
            if remux_res.returncode == 0 and remux_path.exists():
                remux_path.replace(output_path)
            else:
                remux_path.unlink(missing_ok=True)

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
        return _convert_image_ffmpeg(mf, output_path, _image_quality(preset), use_hw_accel)

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
