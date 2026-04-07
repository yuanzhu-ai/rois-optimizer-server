# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

# 收集动态导入子模块（FastAPI/uvicorn 体系大量使用动态 import）
hiddenimports = []
for pkg in [
    'uvicorn',
    'fastapi',
    'starlette',
    'pydantic',
    'pydantic_settings',
    'slowapi',
    'jwt',
    'src',
]:
    try:
        hiddenimports += collect_submodules(pkg)
    except Exception:
        pass

# 数据文件：保留 config.yaml.example 作为 fallback；git.properties 可能未生成
datas = [
    ('src/config/config.yaml.example', 'src/config'),
]
if os.path.exists('git.properties'):
    datas.append(('git.properties', '.'))

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
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

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='optimize_server',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
