"""Regression tests for safe duplicate detection."""

import tempfile
import unittest
from pathlib import Path

from core.scanner import MediaFile, compute_hashes, find_duplicates


class DuplicateHashingTests(unittest.TestCase):
    def _media_file(self, path: Path) -> MediaFile:
        return MediaFile(path=path, size_bytes=path.stat().st_size, media_type='video')

    def test_files_with_equal_edges_but_different_middle_are_not_duplicates(self):
        """Regression: sampled first/last chunks produced a false duplicate."""
        chunk_size = 4 * 1024 * 1024
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = b'head' * (chunk_size // 4)
            last = b'tail' * (chunk_size // 4)
            (root / 'first.mp4').write_bytes(first + b'A' * chunk_size + last)
            (root / 'second.mp4').write_bytes(first + b'B' * chunk_size + last)

            files = [self._media_file(root / 'first.mp4'), self._media_file(root / 'second.mp4')]
            compute_hashes(files)

            self.assertNotEqual(files[0].file_hash, files[1].file_hash)
            self.assertEqual(find_duplicates(files), 0)
            self.assertEqual([file.is_duplicate for file in files], [False, False])

    def test_unique_files_do_not_receive_a_full_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'first.mp4').write_bytes(b'first unique file')
            (root / 'second.mp4').write_bytes(b'second unique file')
            files = [self._media_file(root / 'first.mp4'), self._media_file(root / 'second.mp4')]

            compute_hashes(files)

            self.assertEqual([file.file_hash for file in files], [None, None])

if __name__ == '__main__':
    unittest.main()
