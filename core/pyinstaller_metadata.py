"""
gesturedrive.core.pyinstaller_metadata
=======================================
PyInstaller Build Metadata and Specification Generator.

Stores Windows EXE version resource information and generates PyInstaller
build specs referencing central core.version metadata.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

from core.version import (
    APP_NAME,
    BUILD_NUMBER,
    COMPANY,
    COPYRIGHT,
    DEVELOPER,
    LICENSE,
    VERSION,
)


def get_pyinstaller_metadata() -> Dict[str, str]:
    """Return dictionary of Windows executable compilation metadata."""
    return {
        "product_name": APP_NAME,
        "internal_name": "DriveByGesture",
        "original_filename": "DriveByGesture.exe",
        "company_name": COMPANY,
        "file_description": "DriveByGesture Control Center — Real-Time Hand Gesture Driving & Desktop Navigator",
        "copyright": COPYRIGHT,
        "legal_trademarks": COPYRIGHT,
        "file_version": VERSION,
        "product_version": VERSION,
        "build_number": BUILD_NUMBER,
        "license": LICENSE,
        "developer": DEVELOPER,
    }


def generate_version_file_content() -> str:
    """Generate PyInstaller file_version_info.txt content for Windows EXE resource embedding."""
    meta = get_pyinstaller_metadata()
    ver_parts = [int(p) if p.isdigit() else 0 for p in VERSION.split(".")]
    while len(ver_parts) < 4:
        ver_parts.append(0)

    ver_tuple = tuple(ver_parts)

    return f"""# UTF-8
# VSVersionInfo file for PyInstaller build
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={ver_tuple},
    prodvers={ver_tuple},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
        StringTable(
          u'040904B0',
          [
            StringStruct(u'CompanyName', u'{meta["company_name"]}'),
            StringStruct(u'FileDescription', u'{meta["file_description"]}'),
            StringStruct(u'FileVersion', u'{meta["file_version"]}'),
            StringStruct(u'InternalName', u'{meta["internal_name"]}'),
            StringStruct(u'LegalCopyright', u'{meta["copyright"]}'),
            StringStruct(u'OriginalFilename', u'{meta["original_filename"]}'),
            StringStruct(u'ProductName', u'{meta["product_name"]}'),
            StringStruct(u'ProductVersion', u'{meta["product_version"]}')
          ]
        )
      ]
    ),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
"""


def generate_spec_file_content() -> str:
    """Generate PyInstaller .spec file content."""
    return """# -*- mode: python ; coding: utf-8 -*-
# PyInstaller Build Specification for DriveByGesture.exe

block_cipher = None

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('resources', 'resources'),
        ('profiles', 'profiles'),
        ('config', 'config'),
    ],
    hiddenimports=[
        'mediapipe',
        'cv2',
        'PySide6',
        'vgamepad',
        'psutil',
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
    name='DriveByGesture',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='resources/icons/app.ico',
)
"""
