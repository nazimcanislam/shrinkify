"""
scanner.py — Scans media files using ffprobe.
"""

import subprocess
import json
import os
import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

SUPPORTED_VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm', '.m4v', '.3gp', '.ts'}
SUPPORTED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.heic', '.heif', '.tiff', '.tif', '.bmp', '.webp'}


@dataclass
class MediaFile:
    path: Path
    size_bytes: int
    media_type: str          # 'video' | 'image'

    # Video fields
    video_codec: Optional[str] = None
    audio_codec: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None
    duration_seconds: Optional[float] = None
    bitrate_kbps: Optional[int] = None

    # Image fields
    image_format: Optional[str] = None

    # Analysis results (set by analyzer)
    needs_conversion: bool = False
    conversion_reason: Optional[str] = None
    estimated_output_size_bytes: Optional[int] = None

    # Duplicate detection
    file_hash: Optional[str] = None
    is_duplicate: bool = False
    duplicate_of: Optional[Path] = None

    # Error tracking
    scan_error: Optional[str] = None

    @property
    def size_mb(self) -> float:
        return self.size_bytes / (1024 * 1024)

    @property
    def extension(self) -> str:
        return self.path.suffix.lower()

    @property
    def filename(self) -> str:
        return self.path.name


def _no_window() -> dict:
    """
    Returns subprocess kwargs that prevent a console window from flashing
    on Windows when running from a GUI / PyInstaller --windowed build.
    On other platforms returns an empty dict (no-op).
    """
    import sys
    if sys.platform == 'win32':
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = subprocess.SW_HIDE
        return {'startupinfo': si, 'creationflags': subprocess.CREATE_NO_WINDOW}
    return {}


def _run_ffprobe(file_path: Path) -> Optional[dict]:
    """Runs ffprobe and returns parsed JSON. Returns None on any failure."""
    cmd = [
        'ffprobe', '-v', 'quiet',
        '-print_format', 'json',
        '-show_format', '-show_streams',
        str(file_path)
    ]
    try:
        result = subprocess.run(
            cmd, capture_output=True, timeout=30,
            encoding='utf-8', errors='replace',
            **_no_window()
        )
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout)
        return None
    except subprocess.TimeoutExpired:
        logger.warning(f"ffprobe timed out: {file_path.name}")
        return None
    except json.JSONDecodeError as e:
        logger.warning(f"ffprobe JSON parse error for {file_path.name}: {e}")
        return None
    except FileNotFoundError:
        logger.error("ffprobe not found. Make sure ffmpeg is installed and in PATH.")
        return None
    except Exception as e:
        logger.warning(f"ffprobe unexpected error for {file_path.name}: {e}")
        return None


def _parse_video(file_path: Path, size_bytes: int, probe: dict) -> MediaFile:
    media = MediaFile(path=file_path, size_bytes=size_bytes, media_type='video')
    fmt = probe.get('format', {})
    try:
        duration = float(fmt.get('duration', 0))
        media.duration_seconds = duration if duration > 0 else None
    except (ValueError, TypeError):
        pass
    try:
        bitrate = int(fmt.get('bit_rate', 0)) // 1000
        media.bitrate_kbps = bitrate if bitrate > 0 else None
    except (ValueError, TypeError):
        pass
    for stream in probe.get('streams', []):
        codec_type = stream.get('codec_type', '')
        codec_name = (stream.get('codec_name') or '').lower()
        if codec_type == 'video' and media.video_codec is None:
            media.video_codec = codec_name
            media.width = stream.get('width')
            media.height = stream.get('height')
            fps_str = stream.get('r_frame_rate', '0/1')
            try:
                num, den = fps_str.split('/')
                media.fps = round(float(num) / float(den), 3) if float(den) > 0 else None
            except (ValueError, ZeroDivisionError):
                media.fps = None
        elif codec_type == 'audio' and media.audio_codec is None:
            media.audio_codec = codec_name
    return media


def _parse_image(file_path: Path, size_bytes: int, probe: dict) -> MediaFile:
    media = MediaFile(path=file_path, size_bytes=size_bytes, media_type='image')
    for stream in probe.get('streams', []):
        codec_name = (stream.get('codec_name') or '').upper()
        if codec_name:
            media.image_format = codec_name
            media.width = stream.get('width')
            media.height = stream.get('height')
            break
    if not media.image_format:
        ext_map = {
            '.jpg': 'MJPEG', '.jpeg': 'MJPEG', '.png': 'PNG',
            '.heic': 'HEVC', '.heif': 'HEVC', '.webp': 'WEBP',
            '.tiff': 'TIFF', '.tif': 'TIFF', '.bmp': 'BMP'
        }
        media.image_format = ext_map.get(file_path.suffix.lower(), 'UNKNOWN')
    return media


def scan_file(file_path: Path) -> Optional[MediaFile]:
    """
    Analyzes a single file. Returns None if unsupported or empty.
    Never raises — errors are captured in MediaFile.scan_error.
    """
    try:
        if not file_path.is_file():
            return None
        ext = file_path.suffix.lower()
        is_video = ext in SUPPORTED_VIDEO_EXTENSIONS
        is_image = ext in SUPPORTED_IMAGE_EXTENSIONS
        if not (is_video or is_image):
            return None
        try:
            size_bytes = file_path.stat().st_size
        except OSError as e:
            logger.warning(f"Cannot stat {file_path.name}: {e}")
            return None
        if size_bytes == 0:
            return None

        media_type = 'video' if is_video else 'image'
        probe = _run_ffprobe(file_path)
        if probe is None:
            mf = MediaFile(path=file_path, size_bytes=size_bytes, media_type=media_type)
            mf.scan_error = 'ffprobe failed (unsupported format or corrupt file)'
            return mf
        return _parse_video(file_path, size_bytes, probe) if is_video else _parse_image(file_path, size_bytes, probe)

    except Exception as e:
        logger.warning(f"Unexpected error scanning {file_path}: {e}")
        try:
            ext = file_path.suffix.lower()
            media_type = 'video' if ext in SUPPORTED_VIDEO_EXTENSIONS else 'image'
            size_bytes = file_path.stat().st_size if file_path.exists() else 0
            mf = MediaFile(path=file_path, size_bytes=size_bytes, media_type=media_type)
            mf.scan_error = str(e)
            return mf
        except Exception:
            return None


def scan_directory(
    directory: Path,
    progress_callback=None,
    error_callback=None
) -> tuple[list[MediaFile], list[tuple[Path, str]]]:
    """
    Recursively scans a directory.
    Returns: (media_files, errors) where errors = [(path, message), ...]
    """
    all_files: list[Path] = []
    for root, _, files in os.walk(directory):
        for fname in files:
            fpath = Path(root) / fname
            ext = fpath.suffix.lower()
            if ext in SUPPORTED_VIDEO_EXTENSIONS or ext in SUPPORTED_IMAGE_EXTENSIONS:
                all_files.append(fpath)

    total = len(all_files)
    results: list[MediaFile] = []
    errors: list[tuple[Path, str]] = []

    for i, fpath in enumerate(all_files):
        if progress_callback:
            progress_callback(i + 1, total, fpath.name)
        media = scan_file(fpath)
        if media:
            results.append(media)
            if media.scan_error:
                errors.append((fpath, media.scan_error))
                if error_callback:
                    error_callback(fpath, media.scan_error)

    return results, errors


def compute_hashes(media_files: list[MediaFile], progress_callback=None) -> None:
    """Computes file hashes in-place. Uses first+last 4 MB chunks for speed."""
    CHUNK_SIZE = 4 * 1024 * 1024
    for i, mf in enumerate(media_files):
        if progress_callback:
            progress_callback(i + 1, len(media_files), mf.filename)
        try:
            h = hashlib.md5()
            with open(mf.path, 'rb') as f:
                h.update(f.read(CHUNK_SIZE))
                if mf.size_bytes > CHUNK_SIZE * 2:
                    f.seek(-CHUNK_SIZE, 2)
                    h.update(f.read(CHUNK_SIZE))
                h.update(str(mf.size_bytes).encode())
            mf.file_hash = h.hexdigest()
        except (IOError, OSError) as e:
            logger.warning(f"Hash failed for {mf.filename}: {e}")
            mf.file_hash = None


def find_duplicates(media_files: list[MediaFile]) -> int:
    """Marks duplicates by hash. Returns count of duplicates found."""
    hash_map: dict[str, MediaFile] = {}
    duplicate_count = 0
    for mf in media_files:
        if not mf.file_hash:
            continue
        if mf.file_hash in hash_map:
            mf.is_duplicate = True
            mf.duplicate_of = hash_map[mf.file_hash].path
            duplicate_count += 1
        else:
            hash_map[mf.file_hash] = mf
    return duplicate_count
