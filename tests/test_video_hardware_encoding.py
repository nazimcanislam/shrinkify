"""Tests for hardware-accelerated HEVC video encoding and detection."""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from core import converter
from core.converter import (
    _video_cmd, _probe_encoder, _probe_qsv_encoder, detect_hw_encoder,
    _probe_vaapi_encoder, _probe_vulkan_encoder, _get_dri_render_devices,
)
from core.scanner import MediaFile


class VideoHardwareEncodingTests(unittest.TestCase):
    def setUp(self):
        self.media_file = MediaFile(Path('source.mp4'), 1000, 'video')
        self.output_path = Path('result.mp4')
        converter._HW_DEVICE_ARGS.clear()
        converter._HW_ENCODER_CACHE = False

    @patch('core.converter._run_encoder_probe', return_value=True)
    def test_probe_encoder_uses_nv12_for_qsv(self, mock_probe):
        self.assertTrue(_probe_encoder('hevc_qsv'))
        cmd = mock_probe.call_args[0][1]
        self.assertIn('-pix_fmt', cmd)
        self.assertEqual(cmd[cmd.index('-pix_fmt') + 1], 'nv12')

    @patch('core.converter._run_encoder_probe', return_value=True)
    def test_probe_encoder_uses_yuv420p_for_nvenc(self, mock_probe):
        self.assertTrue(_probe_encoder('hevc_nvenc'))
        cmd = mock_probe.call_args[0][1]
        self.assertIn('-pix_fmt', cmd)
        self.assertEqual(cmd[cmd.index('-pix_fmt') + 1], 'yuv420p')

    @patch('core.converter._probe_encoder', return_value=True)
    def test_probe_qsv_encoder_succeeds_with_default_driver(self, mock_probe):
        self.assertTrue(_probe_qsv_encoder('hevc_qsv'))
        mock_probe.assert_called_once_with('hevc_qsv')

    @patch('core.converter._probe_encoder', side_effect=[False, True])
    @patch('core.converter.sys.platform', 'linux')
    @patch('pathlib.Path.exists', return_value=True)
    @patch('pathlib.Path.glob', return_value=[Path('/dev/dri/renderD128')])
    def test_probe_qsv_encoder_tries_linux_render_nodes_on_fallback(
        self, mock_glob, mock_exists, mock_probe
    ):
        self.assertTrue(_probe_qsv_encoder('hevc_qsv'))
        self.assertEqual(
            converter._HW_DEVICE_ARGS['hevc_qsv'],
            ['-init_hw_device', 'qsv=hw,child_device=/dev/dri/renderD128', '-filter_hw_device', 'hw']
        )

    @patch('core.converter.subprocess.run')
    @patch('core.converter._probe_nvenc_encoder', return_value=False)
    @patch('core.converter._probe_qsv_encoder', return_value=True)
    def test_detect_hw_encoder_selects_qsv(self, mock_qsv, mock_nvenc, mock_run):
        mock_run.return_value.stdout = 'hevc_qsv hevc_nvenc'
        mock_run.return_value.stderr = ''
        self.assertEqual(detect_hw_encoder(), 'hevc_qsv')

    @patch('core.converter.subprocess.run')
    @patch('core.converter._probe_nvenc_encoder', return_value=False)
    @patch('core.converter._probe_qsv_encoder', return_value=False)
    @patch('core.converter._probe_hwframe_encoder', return_value=True)
    @patch('core.converter.sys.platform', 'linux')
    def test_detect_hw_encoder_selects_vaapi_on_linux(
        self, mock_hwframe, mock_qsv, mock_nvenc, mock_run
    ):
        mock_run.return_value.stdout = 'hevc_vaapi'
        mock_run.return_value.stderr = ''
        self.assertEqual(detect_hw_encoder(), 'hevc_vaapi')
        self.assertIn('hevc_vaapi', converter._HW_DEVICE_ARGS)

    @patch('core.converter._probe_hwframe_encoder', return_value=True)
    @patch('core.converter._get_dri_render_devices', return_value=[Path('/dev/dri/renderD128')])
    def test_probe_vaapi_encoder_uses_dri_device(self, mock_devices, mock_hwframe):
        self.assertTrue(_probe_vaapi_encoder('hevc_vaapi'))
        self.assertEqual(
            converter._HW_DEVICE_ARGS['hevc_vaapi'],
            ['-init_hw_device', 'vaapi=va:/dev/dri/renderD128', '-filter_hw_device', 'va'],
        )

    @patch('core.converter._probe_hwframe_encoder', side_effect=[False, True])
    def test_probe_vulkan_encoder_tries_indices(self, mock_hwframe):
        self.assertTrue(_probe_vulkan_encoder('hevc_vulkan'))
        self.assertEqual(
            converter._HW_DEVICE_ARGS['hevc_vulkan'],
            ['-init_hw_device', 'vulkan=vk:1', '-filter_hw_device', 'vk'],
        )

    @patch('core.converter.get_hw_encoder', return_value='hevc_qsv')
    def test_video_cmd_qsv_includes_nv12_and_global_quality(self, mock_encoder):
        converter._HW_DEVICE_ARGS['hevc_qsv'] = [
            '-init_hw_device', 'qsv=hw,child_device=/dev/dri/renderD128', '-filter_hw_device', 'hw'
        ]
        cmd = _video_cmd(self.media_file, self.output_path, use_hw_accel=True, preset='balanced')

        self.assertIn('hevc_qsv', cmd)
        self.assertIn('-pix_fmt', cmd)
        self.assertEqual(cmd[cmd.index('-pix_fmt') + 1], 'nv12')
        self.assertIn('-global_quality', cmd)
        # Global device arguments must be before -i
        init_idx = cmd.index('-init_hw_device')
        i_idx = cmd.index('-i')
        self.assertLess(init_idx, i_idx)

    @patch('core.converter.get_hw_encoder', return_value='hevc_vaapi')
    def test_video_cmd_vaapi_configures_hwupload_and_device(self, mock_encoder):
        converter._HW_DEVICE_ARGS['hevc_vaapi'] = [
            '-init_hw_device', 'vaapi=va:/dev/dri/renderD128', '-filter_hw_device', 'va'
        ]
        cmd = _video_cmd(self.media_file, self.output_path, use_hw_accel=True, preset='balanced')

        self.assertIn('hevc_vaapi', cmd)
        self.assertIn('format=nv12,hwupload', cmd[cmd.index('-vf') + 1])
        self.assertIn('-rc_mode', cmd)
        self.assertEqual(cmd[cmd.index('-rc_mode') + 1], 'CQP')
        # Global device arguments must be before -i
        init_idx = cmd.index('-init_hw_device')
        i_idx = cmd.index('-i')
        self.assertLess(init_idx, i_idx)

    @patch('core.converter.get_hw_encoder', return_value='hevc_nvenc')
    def test_video_cmd_nvenc_uses_p4_preset_and_gpu(self, mock_encoder):
        converter._HW_DEVICE_ARGS['hevc_nvenc'] = ['-gpu', '0']
        cmd = _video_cmd(self.media_file, self.output_path, use_hw_accel=True, preset='conservative')

        self.assertIn('hevc_nvenc', cmd)
        self.assertIn('-preset', cmd)
        self.assertEqual(cmd[cmd.index('-preset') + 1], 'p4')
        self.assertIn('-gpu', cmd)
        self.assertEqual(cmd[cmd.index('-gpu') + 1], '0')

    @patch('core.converter.get_hw_encoder', return_value=None)
    def test_video_cmd_falls_back_to_libx265_when_no_hw_found(self, mock_encoder):
        cmd = _video_cmd(self.media_file, self.output_path, use_hw_accel=True, preset='conservative')

        self.assertIn('libx265', cmd)
        self.assertIn('-crf', cmd)
        self.assertEqual(cmd[cmd.index('-crf') + 1], '20')

    def test_video_cmd_uses_libx265_when_hw_accel_disabled(self):
        cmd = _video_cmd(self.media_file, self.output_path, use_hw_accel=False, preset='conservative')

        self.assertIn('libx265', cmd)
        self.assertIn('-crf', cmd)
        self.assertEqual(cmd[cmd.index('-crf') + 1], '20')


if __name__ == '__main__':
    unittest.main()
