"""
Utilitários de autenticação
"""
import hashlib
import secrets
import streamlit as st
from database.connection import get_db
from database.models import User


def hash_password(password: str) -> str:
    """Gera hash da senha usando SHA-256 com salt"""
    salt = secrets.token_hex(16)
    password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    return f"{salt}:{password_hash}"


def verify_password(password: str, password_hash: str) -> bool:
    """Verifica se a senha está correta"""
    try:
        salt, stored_hash = password_hash.split(":")
        password_hash_check = hashlib.sha256((password + salt).encode()).hexdigest()
        return password_hash_check == stored_hash
    except ValueError:
        return False


def create_session(user_id: str, username: str, role: str):
    """Cria sessão do usuário no Streamlit"""
    st.session_state['authenticated'] = True
    st.session_state['user_id'] = user_id
    st.session_state['username'] = username
    st.session_state['role'] = role


def clear_session():
    """Limpa a sessão do usuário"""
    if 'authenticated' in st.session_state:
        del st.session_state['authenticated']
    if 'user_id' in st.session_state:
        del st.session_state['user_id']
    if 'username' in st.session_state:
        del st.session_state['username']
    if 'role' in st.session_state:
        del st.session_state['role']


def get_current_user() -> dict:
    """Retorna o usuário atual da sessão"""
    if not st.session_state.get('authenticated'):
        return None

    db = get_db()
    user_model = User(db.users)
    return user_model.find_by_id(st.session_state.get('user_id'))


def require_auth(required_role: str = None):
    """Decorador para verificar autenticação"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            if not st.session_state.get('authenticated'):
                st.error("Você precisa estar autenticado para acessar esta página.")
                st.stop()

            if required_role and st.session_state.get('role') != required_role:
                st.error("Você não tem permissão para acessar esta página.")
                st.stop()

            return func(*args, **kwargs)
        return wrapper
    return decorator


def login_user(email: str, password: str) -> tuple[bool, str]:
    """
    Tenta fazer login do usuário
    Retorna (sucesso, mensagem)
    """
    try:
        db = get_db()
        user_model = User(db.users)
        user = user_model.find_by_email(email)

        if not user:
            return False, "Email ou senha incorretos"

        if not user.get('ativo', True):
            return False, "Usuário inativo. Entre em contato com o administrador."

        if not verify_password(password, user['password_hash']):
            return False, "Email ou senha incorretos"

        # Criar sessão
        create_session(user['id'], user['username'], user['role'])
        return True, "Login realizado com sucesso"

    except Exception as e:
        return False, f"Erro ao fazer login: {str(e)}"
