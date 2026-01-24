"""
Página de Login
"""
import streamlit as st
from auth.auth_utils import login_user
from database.connection import init_db

st.set_page_config(
    page_title="Login - PAICS", 
    page_icon="🔐", 
    layout="centered",
    menu_items=None
)

# Ocultar menu de navegação de páginas
st.markdown("""
    <style>
    [data-testid="stSidebarNav"] {
        display: none;
    }
    </style>
""", unsafe_allow_html=True)

# Inicializar banco de dados
try:
    init_db()
except Exception as e:
    st.error(f"Erro ao conectar ao banco de dados: {e}")
    st.stop()

# Se já estiver autenticado, redirecionar
if st.session_state.get('authenticated'):
    if st.session_state.get('role') == 'admin':
        st.switch_page("pages/admin_dashboard.py")
    else:
        st.switch_page("pages/user_dashboard.py")

st.title("🔐 Login - PAICS")
st.markdown("Sistema de Análise de Imagens Veterinárias com IA")

st.info("ℹ️ **Acesso Restrito:** Apenas administradores podem criar contas. Entre em contato com o administrador do sistema para obter suas credenciais de acesso.")

st.subheader("Entrar")

with st.form("login_form"):
    email = st.text_input("Email", placeholder="seu@email.com")
    password = st.text_input("Senha", type="password")
    submit = st.form_submit_button("Entrar", type="primary", use_container_width=True)

    if submit:
        if email and password:
            success, message = login_user(email, password)
            if success:
                st.success(message)
                st.rerun()
            else:
                st.error(message)
        else:
            st.warning("Por favor, preencha todos os campos")
