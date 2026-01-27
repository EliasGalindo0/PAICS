"""
Utilitário para exibir o logo do sistema
"""
import os
import streamlit as st
from PIL import Image


def get_logo_path() -> str:
    """Retorna o caminho do arquivo de logo"""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    logo_path = os.path.join(project_root, "logo", "PAICS.jpeg")
    return logo_path


def display_logo(width: int = 200, use_column_width: bool = False) -> None:
    """
    Exibe o logo do sistema

    Args:
        width: Largura do logo em pixels (se use_column_width=False)
        use_column_width: Se True, usa a largura da coluna
    """
    logo_path = get_logo_path()

    if os.path.exists(logo_path):
        try:
            logo_image = Image.open(logo_path)
            if use_column_width:
                st.image(logo_image, use_container_width=True)
            else:
                st.image(logo_image, width=width)
        except Exception as e:
            st.warning(f"Erro ao carregar logo: {str(e)}")
    else:
        # Fallback: exibir apenas o nome se o logo não existir
        st.markdown("### 🐾 PAICS")


def display_logo_centered(width: int = 200) -> None:
    """Exibe o logo centralizado"""
    logo_path = get_logo_path()

    if os.path.exists(logo_path):
        try:
            logo_image = Image.open(logo_path)
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.image(logo_image, width=width)
        except Exception as e:
            st.warning(f"Erro ao carregar logo: {str(e)}")
    else:
        # Fallback
        st.markdown("### 🐾 PAICS")
