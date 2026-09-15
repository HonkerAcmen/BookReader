"""
py2app 构建脚本 - 将 library_browser.py 编译为 macOS .app 应用
用法: python3 setup.py py2app
"""

from setuptools import setup
APP = ['library_browser.py']
DATA_FILES = []

OPTIONS = {
    'argv_emulation': False,
    'iconfile': None,
    'plist': {
        'CFBundleName': '图书库浏览器',
        'CFBundleDisplayName': '图书库浏览器',
        'CFBundleIdentifier': 'com.library.browser',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '10.14',
        'NSHumanReadableCopyright': '© 2026 图书集成库',
    },
    'packages': [],
    'includes': [
        'PyQt6',
        'PyQt6.QtCore',
        'PyQt6.QtWidgets',
        'PyQt6.QtGui',
        'fitz',
        'PIL',
        'PIL.Image',
        'PIL.ImageDraw',
        'PIL.ImageFont',
    ],
    'excludes': [
        'matplotlib',
        'numpy',
        'scipy',
        'pandas',
        'tkinter',
        'unittest',
        'pydoc',
        'doctest',
        'difflib',
        'inspect',
        'xml',
        'email',
        'http',
        'urllib',
        'ftplib',
        'smtplib',
    ],
}

setup(
    app=APP,
    name='图书库浏览器',
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
