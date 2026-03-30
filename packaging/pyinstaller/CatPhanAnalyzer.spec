# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for CatPhan Analyzer GUI executable.

This builds a standalone executable for the package GUI entrypoint
that opens a GUI folder picker and runs analysis.

Usage:
    pyinstaller packaging/pyinstaller/CatPhanAnalyzer.spec

Output:
    dist/CatPhanAnalyzer.exe - Double-click to run GUI
"""

import os
import sys
from PyInstaller.utils.hooks import collect_submodules

SPEC_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SPEC_DIR, '..', '..'))
SRC_DIR = os.path.join(ROOT_DIR, 'src')
ENTRYPOINT = os.path.join(SRC_DIR, 'catphan_analysis', 'select_and_analyze.py')

sys.path.insert(0, SRC_DIR)

block_cipher = None

a = Analysis(
    [ENTRYPOINT],
    pathex=[SRC_DIR],
    binaries=[],
    datas=[],
    hiddenimports=(
        collect_submodules('catphan_analysis')
        + collect_submodules('alexandria')
        + [
            'scipy.special.cython_special',  # Required by scipy
        ]
    ),
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
    name='CatPhanAnalyzer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window (GUI mode)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add icon='catphan.ico' if you have an icon file
)
