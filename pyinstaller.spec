# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
import os
import sys

from PyInstaller.utils.hooks import collect_data_files, collect_submodules


PROJECT_ROOT = Path.cwd().resolve()
APP_NAME = "TLAMATINI"


def optional_tree(relative_path: str, target_name: str):
    source = PROJECT_ROOT / relative_path
    return [(str(source), target_name)] if source.exists() else []


def pick_icon() -> str | None:
    candidates = []
    if sys.platform.startswith("win"):
        candidates = [PROJECT_ROOT / "assets" / "app_icon.ico"]
    elif sys.platform == "darwin":
        candidates = [PROJECT_ROOT / "assets" / "app_icon.icns"]
    else:
        candidates = [
            PROJECT_ROOT / "assets" / "app_icon.png",
            PROJECT_ROOT / "assets" / "app_icon.ico",
        ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return None


datas = []
datas += optional_tree("assets", "assets")
datas += optional_tree("map_ui", "map_ui")
datas += optional_tree("local_ai/config", "local_ai/config")
datas += optional_tree("local_ai/runtime", "local_ai/runtime")
datas += optional_tree("local_ai/models", "local_ai/models")
datas += optional_tree("public_license_key.pem", ".")
datas += collect_data_files("tkinterdnd2", include_py_files=False)
datas += collect_data_files("PIL", include_py_files=False)

hiddenimports = []
hiddenimports += collect_submodules("core")
hiddenimports += collect_submodules("interfaz")
hiddenimports += collect_submodules("sistema")
hiddenimports += collect_submodules("cryptography")
hiddenimports += ["tkinterdnd2", "PIL._tkinter_finder"]

binaries = []

icon_path = pick_icon()

block_cipher = None

a = Analysis(
    ["main.py"],
    pathex=[str(PROJECT_ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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

if sys.platform == "darwin":
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name=APP_NAME,
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=True,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=icon_path,
    )

    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name=APP_NAME,
    )

    app = BUNDLE(
        coll,
        name=f"{APP_NAME}.app",
        icon=icon_path,
        bundle_identifier="com.tlamatini.desktop",
        info_plist={
            "CFBundleName": APP_NAME,
            "CFBundleDisplayName": APP_NAME,
            "CFBundleIdentifier": "com.tlamatini.desktop",
            "CFBundleShortVersionString": os.environ.get("TLAMATINI_APP_VERSION", "5.2.3"),
            "CFBundleVersion": os.environ.get("TLAMATINI_APP_VERSION", "5.2.3"),
            "NSHighResolutionCapable": True,
        },
    )
else:
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name=APP_NAME,
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
        icon=icon_path,
    )
