# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import copy_metadata, collect_data_files

block_cipher = None

# Coletar metadata e dados do Streamlit
streamlit_datas = copy_metadata('streamlit')
streamlit_datas += collect_data_files('streamlit')

a = Analysis(
    ['run_paics.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('streamlit_app.py', '.'),
        ('main.py', '.'),
        ('config.py', '.'),
        ('.env.example', '.'),
    ] + streamlit_datas,  # Adicionar dados do Streamlit
    hiddenimports=[
        'streamlit',
        'streamlit.web',
        'streamlit.web.cli',
        'streamlit.web.bootstrap',
        'streamlit.web.server',
        'streamlit.web.server.server',
        'streamlit.runtime',
        'streamlit.runtime.scriptrunner',
        'streamlit.runtime.scriptrunner.magic_funcs',
        'streamlit.runtime.legacy_caching',
        'streamlit.runtime.caching',
        'streamlit.runtime.uploaded_file_manager',
        'streamlit.runtime.state',
        'streamlit.runtime.state.session_state',
        'streamlit.components.v1',
        'google.generativeai',
        'google.ai.generativelanguage',
        'google.api_core',
        'PIL',
        'PIL._imaging',
        'fitz',
        'pytesseract',
        'fpdf',
        'fpdf2',
        'docx',
        'dotenv',
        'altair',
        'blinker',
        'cachetools',
        'click',
        'gitpython',
        'importlib_metadata',
        'jinja2',
        'numpy',
        'packaging',
        'pandas',
        'protobuf',
        'pyarrow',
        'pydeck',
        'requests',
        'rich',
        'toml',
        'tornado',
        'typing_extensions',
        'tzlocal',
        'validators',
        'watchdog',
    ],
    hookspath=['./'],  # Usar hooks do diretório atual
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
    [],
    exclude_binaries=True,
    name='PAICS',
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

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='PAICS',
)