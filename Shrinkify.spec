# Shrinkify.spec
# PyInstaller build spec — use this instead of the raw CLI command for reliable builds.
#
# Build command (run from the shrinkify/ directory):
#   pyinstaller Shrinkify.spec
#
# Output: dist/Shrinkify.exe  (Windows)
#         dist/Shrinkify      (Linux/macOS)

import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_dynamic_libs, collect_data_files

block_cipher = None

# Collect pillow-heif native libraries (libheif, libde265, etc.)
# These are C extensions that PyInstaller doesn't always find automatically.
pillow_heif_binaries = collect_dynamic_libs('pillow_heif')
pillow_heif_datas    = collect_data_files('pillow_heif')

a = Analysis(
    ['gui.py'],
    pathex=['.'],
    binaries=pillow_heif_binaries,
    datas=[
        ('assets/icon.png', '.'),       # App icon — copied next to the exe
        ('assets/icon.ico', '.'),
        *pillow_heif_datas,
    ],
    hiddenimports=[
        # pillow-heif registers itself as a PIL plugin at runtime;
        # PyInstaller misses it without an explicit hint.
        'pillow_heif',
        'pillow_heif._libheif',
        'PIL',
        'PIL.Image',
        'PIL.ImageFile',
        'PIL.JpegImagePlugin',
        'PIL.PngImagePlugin',
        'PIL.BmpImagePlugin',
        'PIL.TiffImagePlugin',
        'PIL.WebPImagePlugin',
        # tkinter sub-modules sometimes missed on Linux
        'tkinter',
        'tkinter.ttk',
        'tkinter.filedialog',
        'tkinter.messagebox',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Shrinkify',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    # ── Windows-specific ──────────────────────────────────────
    # console=False  →  no black terminal window behind the GUI
    console=False,
    icon='assets/icon.ico' if sys.platform == 'win32' else 'assets/icon.png',
    # Embed a Windows manifest that declares DPI awareness so text isn't blurry
    uac_admin=False,
)
