# -*- mode: python ; coding: utf-8 -*-
# Build a single-file executable:  pyinstaller --noconfirm packaging/open-transfer.spec
# (or `make binary`). The result is dist/open-transfer[.exe].
from PyInstaller.utils.hooks import collect_data_files

a = Analysis(
    ["entry.py"],
    pathex=["../src"],
    datas=collect_data_files("open_transfer"),
    hiddenimports=["cheroot.ssl.builtin"],
    excludes=["tkinter", "pytest", "playwright"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="open-transfer",
    debug=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    # Keep the console: it shows the address, QR code and PIN, and closing it stops sharing.
    console=True,
    icon=["app_icon.ico"],
)
