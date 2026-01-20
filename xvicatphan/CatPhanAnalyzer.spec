# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for CatPhan Analyzer GUI executable.

This builds a standalone executable for select_and_analyze.py
that opens a GUI folder picker and runs analysis.

Usage:
    pyinstaller CatPhanAnalyzer.spec

Output:
    dist/CatPhanAnalyzer.exe - Double-click to run GUI
"""

block_cipher = None

a = Analysis(
    ['select_and_analyze.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'catphan_analysis',
        'catphan_analysis.analyzer',
        'catphan_analysis.modules.ctp404',
        'catphan_analysis.modules.ctp486',
        'catphan_analysis.modules.ctp528',
        'catphan_analysis.utils.geometry',
        'catphan_analysis.utils.image_processing',
        'scipy.special.cython_special',  # Required by scipy
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
