"""
Utilitário para exibir o logo do sistema.
Usa data URL (base64) para evitar st.image() → armazenamento efêmero do Streamlit,
que falha com múltiplas réplicas / load balancer (MediaFileStorageError).
"""
import base64
import os
import streamlit as st
from io import BytesIO

try:
    from config import LOGO_PATH
except ImportError:
    LOGO_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logo", "PAICS.jpeg")


def get_logo_path() -> str:
    """Retorna o caminho do arquivo de logo (usa config para consistência em produção)"""
    return LOGO_PATH


def _logo_to_data_url() -> str | None:
    """Carrega o logo e retorna data URL base64, ou None se falhar."""
    try:
        from PIL import Image
        logo_path = get_logo_path()
        if not os.path.exists(logo_path):
            return None
        img = Image.open(logo_path)
        if img.mode != "RGB":
            img = img.convert("RGB")
        buf = BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        b64 = base64.b64encode(buf.read()).decode()
        return f"data:image/png;base64,{b64}"
    except Exception:
        return None


def display_logo(width: int = 200, use_column_width: bool = False) -> None:
    """
    Exibe o logo do sistema (via data URL para funcionar com múltiplas réplicas).
    """
    data_url = _logo_to_data_url()
    if data_url:
        style = "width:100%;max-width:100%;" if use_column_width else f"width:{width}px;max-width:{width}px;"
        st.markdown(
            f'<img src="{data_url}" style="{style}height:auto;display:block;" alt="PAICS">',
            unsafe_allow_html=True,
        )
    else:
        st.markdown("### 🐾 PAICS")


def display_logo_centered(width: int = 200) -> None:
    """Exibe o logo centralizado (via data URL para funcionar com múltiplas réplicas)."""
    data_url = _logo_to_data_url()
    if data_url:
        st.markdown(
            f'<div style="display:flex;justify-content:center;margin-bottom:1rem;">'
            f'<img src="{data_url}" style="width:{width}px;max-width:{width}px;height:auto;" alt="PAICS">'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown("### 🐾 PAICS")
