# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['library_browser.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'pymupdf',
        'fitz',
        'PIL',
        'PIL.Image',
        'PIL.ImageDraw',
        'PIL.ImageFont',
        'PyQt6',
        'PyQt6.QtCore',
        'PyQt6.QtWidgets',
        'PyQt6.QtGui',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'scipy',
        'pandas',
        'unittest',
        'pydoc',
        'doctest',
    ],
    noarchive=False,
    optimize=2,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='图书库浏览器',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='图书库浏览器',
)
app = BUNDLE(
    coll,
    name='图书库浏览器.app',
    icon=None,
    bundle_identifier='com.library.browser',
    info_plist={
        'CFBundleName': '图书库浏览器',
        'CFBundleDisplayName': '图书库浏览器',
        'CFBundleVersion': '1.1.0',
        'CFBundleShortVersionString': '1.1.0',
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '10.14',
        'NSHumanReadableCopyright': '© 2026 图书集成库',
    },
)
