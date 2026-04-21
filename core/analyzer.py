"""
analyzer.py — Determines conversion candidates and estimates savings.
"""

from dataclasses import dataclass
from core.scanner import MediaFile

OUTDATED_VIDEO_CODECS = {
    'h264', 'avc', 'avc1', 'mpeg4', 'mpeg2video',
    'xvid', 'divx', 'vp8', 'theora', 'wmv2', 'wmv3', 'vc1'
}
MODERN_VIDEO_CODECS = {'hevc', 'h265', 'av1', 'vp9'}
OUTDATED_IMAGE_FORMATS = {'MJPEG', 'PNG', 'BMP', 'TIFF', 'UNKNOWN'}
MODERN_IMAGE_FORMATS = {'HEVC', 'AV1', 'WEBP'}

# Quality presets: (video_crf, image_pillow_quality, label, description)
# image_pillow_quality: pillow-heif quality 0-100
QUALITY_PRESETS = {
    'max':          (28, 60, 'Maximum Shrink',  'Smallest file size. Slight quality reduction, unlikely to be noticeable.'),
    'balanced':     (24, 72, 'Balanced',         'Best trade-off between size and quality. Recommended default.'),
    'conservative': (20, 82, 'Conservative',     'Minimal quality loss. Larger files, safer for archival.'),
}
DEFAULT_PRESET = 'balanced'

# Videos below this bitrate are already efficiently encoded.
LOW_BITRATE_THRESHOLD_KBPS = 3000

MIN_VIDEO_SIZE_MB = 1.0
MIN_IMAGE_SIZE_MB = 0.05


@dataclass
class AnalysisSummary:
    total_files: int = 0
    total_size_bytes: int = 0

    video_count: int = 0
    video_size_bytes: int = 0
    videos_to_convert: int = 0
    videos_already_modern: int = 0

    image_count: int = 0
    image_size_bytes: int = 0
    images_to_convert: int = 0
    images_already_modern: int = 0

    conversion_candidates_size_bytes: int = 0
    estimated_size_after_conversion_bytes: int = 0

    duplicate_count: int = 0
    duplicate_size_bytes: int = 0

    video_codec_distribution: dict = None
    image_format_distribution: dict = None

    def __post_init__(self):
        if self.video_codec_distribution is None:
            self.video_codec_distribution = {}
        if self.image_format_distribution is None:
            self.image_format_distribution = {}

    @property
    def estimated_savings_bytes(self) -> int:
        return self.conversion_candidates_size_bytes - self.estimated_size_after_conversion_bytes

    @property
    def duplicate_savings_bytes(self) -> int:
        return self.duplicate_size_bytes

    @property
    def total_potential_savings_bytes(self) -> int:
        return self.estimated_savings_bytes + self.duplicate_savings_bytes

    @property
    def savings_percentage(self) -> float:
        if self.total_size_bytes == 0:
            return 0.0
        return (self.total_potential_savings_bytes / self.total_size_bytes) * 100


def _video_conversion_ratio(preset: str) -> float:
    return {'max': 0.35, 'balanced': 0.45, 'conservative': 0.60}.get(preset, 0.45)


def _image_conversion_ratio(preset: str) -> float:
    return {'max': 0.45, 'balanced': 0.58, 'conservative': 0.72}.get(preset, 0.58)


def analyze_file(mf: MediaFile, preset: str = DEFAULT_PRESET) -> None:
    if mf.scan_error:
        return
    if mf.media_type == 'video':
        _analyze_video(mf, preset)
    elif mf.media_type == 'image':
        _analyze_image(mf, preset)


def _analyze_video(mf: MediaFile, preset: str) -> None:
    if mf.size_mb < MIN_VIDEO_SIZE_MB:
        return
    codec = (mf.video_codec or '').lower().replace('-', '').replace('.', '')
    if codec in MODERN_VIDEO_CODECS:
        return
    if codec not in OUTDATED_VIDEO_CODECS and codec:
        return
    if mf.bitrate_kbps and mf.bitrate_kbps < LOW_BITRATE_THRESHOLD_KBPS:
        return
    mf.needs_conversion = True
    codec_label = mf.video_codec.upper() if mf.video_codec else 'Unknown'
    mf.conversion_reason = f"{codec_label} → H.265 (HEVC)"
    mf.estimated_output_size_bytes = int(mf.size_bytes * _video_conversion_ratio(preset))


def _analyze_image(mf: MediaFile, preset: str) -> None:
    if mf.size_mb < MIN_IMAGE_SIZE_MB:
        return
    ext = mf.extension
    if ext in {'.heic', '.heif'}:
        return
    fmt = (mf.image_format or '').upper()
    if fmt in MODERN_IMAGE_FORMATS:
        return
    if fmt in OUTDATED_IMAGE_FORMATS or fmt == 'MJPEG':
        mf.needs_conversion = True
        fmt_label = 'JPEG' if fmt == 'MJPEG' else fmt
        mf.conversion_reason = f"{fmt_label} → HEIF"
        mf.estimated_output_size_bytes = int(mf.size_bytes * _image_conversion_ratio(preset))


def analyze_all(media_files: list[MediaFile], preset: str = DEFAULT_PRESET) -> AnalysisSummary:
    summary = AnalysisSummary()
    for mf in media_files:
        analyze_file(mf, preset)
        summary.total_files += 1
        summary.total_size_bytes += mf.size_bytes
        if mf.media_type == 'video':
            summary.video_count += 1
            summary.video_size_bytes += mf.size_bytes
            codec_key = (mf.video_codec or 'unknown').upper()
            summary.video_codec_distribution[codec_key] = \
                summary.video_codec_distribution.get(codec_key, 0) + 1
            if mf.needs_conversion:
                summary.videos_to_convert += 1
                summary.conversion_candidates_size_bytes += mf.size_bytes
                summary.estimated_size_after_conversion_bytes += \
                    (mf.estimated_output_size_bytes or mf.size_bytes)
            else:
                summary.videos_already_modern += 1
        elif mf.media_type == 'image':
            summary.image_count += 1
            summary.image_size_bytes += mf.size_bytes
            fmt_key = mf.image_format or 'UNKNOWN'
            summary.image_format_distribution[fmt_key] = \
                summary.image_format_distribution.get(fmt_key, 0) + 1
            if mf.needs_conversion:
                summary.images_to_convert += 1
                summary.conversion_candidates_size_bytes += mf.size_bytes
                summary.estimated_size_after_conversion_bytes += \
                    (mf.estimated_output_size_bytes or mf.size_bytes)
            else:
                summary.images_already_modern += 1
        if mf.is_duplicate:
            summary.duplicate_count += 1
            summary.duplicate_size_bytes += mf.size_bytes
    return summary
