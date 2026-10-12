"""Tests for opt-in GPU-backed AVIF command selection."""

import unittest
from pathlib import Path
from unittest.mock import patch

from core import converter
from core.converter import _image_cmd
from core.scanner import MediaFile


class ImageHardwareEncodingTests(unittest.TestCase):
    def setUp(self):
        self.media_file = MediaFile(Path('source.jpg'), 100, 'image')
        self.output_path = Path('result.avif')
        converter._HW_DEVICE_ARGS.clear()

    @patch('core.converter.get_hw_image_encoder', return_value='av1_nvenc')
    def test_gpu_mode_uses_available_av1_encoder(self, mock_encoder):
        cmd, is_hardware = _image_cmd(
            self.media_file, self.output_path, quality=75, use_hw_accel=True
        )

        self.assertTrue(is_hardware)
        self.assertIn('av1_nvenc', cmd)
        self.assertNotIn('libaom-av1', cmd)
        mock_encoder.assert_called_once()

    @patch('core.converter.get_hw_image_encoder')
    def test_cpu_mode_does_not_probe_or_use_gpu(self, mock_encoder):
        cmd, is_hardware = _image_cmd(
            self.media_file, self.output_path, quality=75, use_hw_accel=False
        )

        self.assertFalse(is_hardware)
        self.assertIn('libaom-av1', cmd)
        mock_encoder.assert_not_called()

    @patch('core.converter.get_hw_image_encoder', return_value='av1_vaapi')
    def test_vaapi_mode_initializes_and_uploads_to_the_vaapi_device(self, mock_encoder):
        cmd, is_hardware = _image_cmd(
            self.media_file, self.output_path, quality=75, use_hw_accel=True
        )

        self.assertTrue(is_hardware)
        self.assertIn('av1_vaapi', cmd)
        self.assertIn('vaapi=va', cmd)
        self.assertIn('format=nv12,hwupload', cmd)

    @patch('core.converter.get_hw_image_encoder', return_value='av1_vulkan')
    def test_vulkan_mode_initializes_and_uploads_to_the_vulkan_device(self, mock_encoder):
        cmd, is_hardware = _image_cmd(
            self.media_file, self.output_path, quality=75, use_hw_accel=True
        )

        self.assertTrue(is_hardware)
        self.assertIn('av1_vulkan', cmd)
        self.assertIn('vulkan=vk', cmd)
        self.assertIn('format=yuv420p,hwupload', cmd)

    @patch('core.converter._probe_encoder', side_effect=[False, True])
    def test_nvenc_probe_selects_the_first_working_gpu_index(self, mock_probe):
        self.assertTrue(converter._probe_nvenc_encoder('av1_nvenc'))

        self.assertEqual(
            mock_probe.call_args_list[0].args,
            ('av1_nvenc', ['-gpu', '0']),
        )
        self.assertEqual(
            mock_probe.call_args_list[1].args,
            ('av1_nvenc', ['-gpu', '1']),
        )
        self.assertEqual(converter._HW_DEVICE_ARGS['av1_nvenc'], ['-gpu', '1'])

    @patch('core.converter.get_hw_image_encoder', return_value='av1_nvenc')
    def test_image_command_reuses_the_selected_nvenc_gpu(self, mock_encoder):
        converter._HW_DEVICE_ARGS['av1_nvenc'] = ['-gpu', '1']

        cmd, _ = _image_cmd(
            self.media_file, self.output_path, quality=75, use_hw_accel=True
        )

        self.assertIn('-gpu', cmd)
        self.assertEqual(cmd[cmd.index('-gpu') + 1], '1')

    @patch('core.converter._probe_hwframe_encoder', side_effect=[False, True])
    @patch('core.converter.subprocess.run')
    def test_vulkan_detection_selects_the_first_working_device_index(
        self, mock_run, mock_probe
    ):
        mock_run.return_value.stdout = 'av1_vulkan'
        mock_run.return_value.stderr = ''

        self.assertEqual(converter.detect_hw_image_encoder(), 'av1_vulkan')
        self.assertEqual(
            converter._HW_DEVICE_ARGS['av1_vulkan'],
            ['-init_hw_device', 'vulkan=vk:1', '-filter_hw_device', 'vk'],
        )

    @patch('core.converter.EXIFTOOL_AVAILABLE', True)
    @patch('core.converter._copy_metadata_exiftool', return_value=True)
    @patch('core.converter._image_cmd', return_value=(['ffmpeg', '-fake-hw'], 'av1_vaapi'))
    @patch('core.converter.subprocess.run')
    def test_vaapi_conversion_performs_remux_pass(
        self, mock_run, mock_image_cmd, mock_copy_metadata
    ):
        mock_proc = unittest.mock.MagicMock()
        mock_proc.returncode = 0
        mock_run.return_value = mock_proc

        with unittest.mock.patch.object(Path, 'exists', return_value=True), \
             unittest.mock.patch.object(Path, 'replace') as mock_replace, \
             unittest.mock.patch.object(Path, 'stat') as mock_stat:
            mock_stat.return_value.st_size = 50
            res = converter._convert_image_ffmpeg(
                self.media_file, self.output_path, quality=75, use_hw_accel=True
            )

        self.assertTrue(res.success)
        self.assertEqual(mock_run.call_count, 2)
        remux_cmd = mock_run.call_args_list[1].args[0]
        self.assertIn('-c:v', remux_cmd)
        self.assertIn('copy', remux_cmd)
        self.assertIn('-map', remux_cmd)
        self.assertIn('0:v:0', remux_cmd)
        mock_replace.assert_called_once_with(self.output_path)

    @patch('core.converter.EXIFTOOL_AVAILABLE', True)
    @patch('core.converter._copy_metadata_exiftool', return_value=True)
    @patch('core.converter._image_cmd', return_value=(['ffmpeg', '-fake-nvenc'], 'av1_nvenc'))
    @patch('core.converter.subprocess.run')
    def test_nvenc_conversion_is_single_pass_without_remux(
        self, mock_run, mock_image_cmd, mock_copy_metadata
    ):
        mock_proc = unittest.mock.MagicMock()
        mock_proc.returncode = 0
        mock_run.return_value = mock_proc

        with unittest.mock.patch.object(Path, 'exists', return_value=True), \
             unittest.mock.patch.object(Path, 'replace') as mock_replace, \
             unittest.mock.patch.object(Path, 'stat') as mock_stat:
            mock_stat.return_value.st_size = 50
            res = converter._convert_image_ffmpeg(
                self.media_file, self.output_path, quality=75, use_hw_accel=True
            )

        self.assertTrue(res.success)
        self.assertEqual(mock_run.call_count, 1)
        mock_replace.assert_not_called()


if __name__ == '__main__':
    unittest.main()
