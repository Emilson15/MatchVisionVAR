# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

datas = []
datas += collect_data_files('customtkinter')
datas += collect_data_files('ultralytics')
datas += [('logo.png', '.'), ('logo.ico', '.')]

hiddenimports = [
    'customtkinter',
    'ultralytics',
    'cv2',
    'scipy',
    'scipy.spatial',
    'scipy.special',
    'pandas',
    'openpyxl',
    'PIL',
    'PIL.ImageTk',
    'requests',
    'torch',
    'torchvision'
]
hiddenimports += collect_submodules('ultralytics')

a = Analysis(
    ['app_desktop.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'IPython', 'notebook', 'pytest'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='MatchVision_VAR',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon='logo.ico',
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='MatchVision_VAR',
)
