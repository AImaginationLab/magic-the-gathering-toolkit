# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files

# Only include the specific hidden imports we actually need
# Don't use collect_submodules for sklearn/scipy - it pulls in everything including tests
hiddenimports = [
    # Core app
    'mtg_core',
    'mtg_core.api',
    'mtg_core.api.server',
    'mtg_core.api.routes',
    # FastAPI/Uvicorn essentials
    'uvicorn.logging',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan.on',
    'uvicorn.lifespan.off',
    # Pydantic
    'pydantic',
    'pydantic_settings',
    # sklearn - only what we actually use
    'sklearn.neighbors',
    'sklearn.metrics.pairwise',
    # Database
    'aiosqlite',
    'duckdb',
]

# Data files needed at runtime
datas = [
    *collect_data_files('symspellpy'),
]

# Exclude unnecessary heavy modules
excludes = [
    # sklearn test suites and unused submodules
    'sklearn.tests',
    'sklearn.cluster.tests',
    'sklearn.datasets.tests',
    'sklearn.ensemble.tests',
    'sklearn.linear_model.tests',
    'sklearn.metrics.tests',
    'sklearn.neighbors.tests',
    'sklearn.tree.tests',
    'sklearn.externals.array_api_compat.torch',
    'sklearn.externals.array_api_compat.cupy',
    'sklearn.externals.array_api_compat.dask',
    # scipy array_api_compat backends we don't use
    'scipy._lib.array_api_compat.torch',
    'scipy._lib.array_api_compat.cupy',
    # Other unused
    'torch',
    'cupy',
    'dask',
    'matplotlib',
    'PIL',
    'cv2',
    'tensorflow',
    'keras',
    # Test frameworks
    'pytest',
    'hypothesis',
    '_pytest',
]

a = Analysis(
    ['pyinstaller_entry.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)

pyz = PYZ(a.pure)

# Use onedir mode (COLLECT) for faster startup instead of single file
# sklearn/scipy are huge and decompressing from single exe takes ~60s
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,  # Don't embed binaries in exe for onedir mode
    name='mtg-api',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# Collect all files into a directory
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='mtg-api',
)
