"""
Página de Login
"""
import streamlit as st
from auth.auth_utils import login_user, hash_password
from database.connection import get_db, init_db
from database.models import User

st.set_page_config(page_title="Login - PAICS", page_icon="🔐", layout="centered")

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

# Tabs para Login e Criar Conta
tab1, tab2 = st.tabs(["Login", "Criar Conta"])

with tab1:
    st.subheader("Entrar")

    with st.form("login_form"):
        email = st.text_input("Email", placeholder="seu@email.com")
        password = st.text_input("Senha", type="password")
        submit = st.form_submit_button("Entrar", type="primary")

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

with tab2:
    st.subheader("Criar Nova Conta")
    st.info("⚠️ Apenas usuários podem criar contas. Contas de administrador devem ser criadas diretamente no banco de dados.")

    with st.form("register_form"):
        nome = st.text_input("Nome Completo")
        username = st.text_input("Username")
        email = st.text_input("Email", placeholder="seu@email.com")
        password = st.text_input("Senha", type="password")
        password_confirm = st.text_input("Confirmar Senha", type="password")
        submit = st.form_submit_button("Criar Conta", type="primary")

        if submit:
            if not all([nome, username, email, password, password_confirm]):
                st.warning("Por favor, preencha todos os campos")
            elif password != password_confirm:
                st.error("As senhas não coincidem")
            else:
                try:
                    db = get_db()
                    user_model = User(db.users)

                    # Verificar se email ou username já existem
                    if user_model.find_by_email(email):
                        st.error("Este email já está cadastrado")
                    elif user_model.find_by_username(username):
                        st.error("Este username já está em uso")
                    else:
                        # Criar usuário
                        password_hash = hash_password(password)
                        user_id = user_model.create(
                            username=username,
                            email=email,
                            password_hash=password_hash,
                            role="user",
                            nome=nome
                        )
                        st.success("Conta criada com sucesso! Você pode fazer login agora.")
                        st.rerun()
                except Exception as e:
                    st.error(f"Erro ao criar conta: {str(e)}")
