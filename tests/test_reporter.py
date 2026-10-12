"""Tests for duplicate paths in the HTML report."""

import tempfile
import unittest
from pathlib import Path

from core.reporter import _duplicate_table
from core.scanner import MediaFile


class DuplicateReportTests(unittest.TestCase):
    def test_duplicate_table_shows_paths_relative_to_scan_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = root / 'original.mp4'
            duplicate = root / 'nested' / 'duplicate.mp4'
            duplicate.parent.mkdir()
            original.write_bytes(b'original')
            duplicate.write_bytes(b'duplicate')
            media_file = MediaFile(
                path=duplicate,
                size_bytes=duplicate.stat().st_size,
                media_type='video',
                is_duplicate=True,
                duplicate_of=original,
            )

            table = _duplicate_table([media_file], root)

            self.assertIn('nested/duplicate.mp4', table)
            self.assertIn('original.mp4', table)
            self.assertNotIn(str(root), table)


if __name__ == '__main__':
    unittest.main()
