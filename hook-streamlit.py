"""
Hook customizado para PyInstaller incluir metadata do Streamlit
"""
from PyInstaller.utils.hooks import copy_metadata, collect_data_files, collect_submodules

# Copiar metadata do streamlit
datas = copy_metadata('streamlit')

# Copiar arquivos de dados do streamlit
datas += collect_data_files('streamlit')

# Incluir todos os submódulos
hiddenimports = collect_submodules('streamlit')

# Adicionar imports específicos que podem estar faltando
hiddenimports += [
    'streamlit.web.cli',
    'streamlit.web.bootstrap',
    'streamlit.runtime',
    'streamlit.runtime.scriptrunner',
    'streamlit.runtime.scriptrunner.magic_funcs',
    'streamlit.runtime.legacy_caching',
    'streamlit.runtime.caching',
    'streamlit.runtime.uploaded_file_manager',
]
