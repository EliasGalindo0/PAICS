"""
Utilitários de autenticação
"""
import hashlib
import secrets
from typing import Optional, Dict
import streamlit as st
from database.connection import get_db
from database.models import User, Session
from auth.jwt_utils import (
    generate_access_token, 
    generate_refresh_token, 
    verify_token,
    refresh_access_token,
    is_token_expiring_soon
)


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


def login_user(email_or_username: str, password: str, remember_me: bool = False) -> tuple[bool, str, dict]:
    """
    Tenta fazer login do usuário com suporte a sessão persistente
    
    Args:
        email_or_username: Email ou username do usuário
        password: Senha do usuário
        remember_me: Se True, cria tokens de longa duração (30 dias)
    
    Returns:
        Tupla (sucesso, mensagem, tokens_dict) onde tokens_dict contém access_token e refresh_token
    """
    try:
        db = get_db()
        user_model = User(db.users)
        
        # Tentar buscar por email primeiro
        user = user_model.find_by_email(email_or_username)
        
        # Se não encontrou por email, tentar por username
        if not user:
            user = user_model.find_by_username(email_or_username)

        if not user:
            return False, "Email/usuário ou senha incorretos", {}

        if not user.get('ativo', True):
            return False, "Usuário inativo. Entre em contato com o administrador.", {}

        if not verify_password(password, user['password_hash']):
            return False, "Email/usuário ou senha incorretos", {}

        # Gerar tokens JWT
        access_token = generate_access_token(user['id'], user['username'], user['role'])
        refresh_token = generate_refresh_token(user['id'])
        
        # Criar sessão no banco de dados
        session_model = Session(db.sessions)
        device_id = secrets.token_urlsafe(16)
        device_info = st.session_state.get('device_info', 'Unknown Device')
        ip_address = st.session_state.get('ip_address', '')
        
        session_model.create(
            user_id=user['id'],
            refresh_token=refresh_token,
            device_id=device_id,
            device_info=device_info,
            ip_address=ip_address
        )

        # Criar sessão no Streamlit
        create_session(user['id'], user['username'], user['role'])
        st.session_state['access_token'] = access_token
        st.session_state['refresh_token'] = refresh_token
        st.session_state['remember_me'] = remember_me

        # Verificar se é primeiro acesso (obrigar alteração de senha)
        if user.get('primeiro_acesso', False):
            st.session_state['primeiro_acesso'] = True
            st.session_state['requer_alteracao_senha'] = True

        tokens = {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'remember_me': remember_me
        }

        return True, "Login realizado com sucesso", tokens

    except Exception as e:
        return False, f"Erro ao fazer login: {str(e)}", {}
def restore_session_from_db(user_id: str) -> bool:
    """
    Restaura sessão do banco de dados usando user_id
    Busca sessões ativas e renova tokens se necessário
    """
    try:
        db = get_db()
        session_model = Session(db.sessions)
        user_model = User(db.users)
        
        # Buscar usuário
        user = user_model.find_by_id(user_id)
        if not user or not user.get('ativo'):
            return False
        
        # Buscar sessões ativas do usuário
        sessions = session_model.find_by_user(user_id)
        if not sessions:
            return False
        
        # Tentar usar a sessão mais recente
        active_session = sessions[0]  # Já ordenado por last_used_at desc
        
        # Verificar se a sessão não expirou
        from datetime import datetime
        if active_session.get('expires_at') and active_session['expires_at'] < datetime.utcnow():
            return False
        
        # Tentar renovar tokens usando o refresh_token da sessão
        refresh_token = active_session.get('refresh_token')
        if not refresh_token:
            return False
        
        new_tokens = refresh_access_token(refresh_token)
        if new_tokens:
            new_access, new_refresh = new_tokens
            
            # Atualizar tokens no session_state
            st.session_state['access_token'] = new_access
            st.session_state['refresh_token'] = new_refresh
            
            # Atualizar refresh_token na sessão do banco
            from bson import ObjectId
            session_id = active_session.get('id')  # to_dict converte _id para id
            if session_id:
                session_model.collection.update_one(
                    {"_id": ObjectId(session_id)},
                    {"$set": {"refresh_token": new_refresh, "last_used_at": datetime.utcnow()}}
                )
            
            # Criar sessão no Streamlit
            create_session(user_id, user.get('username', ''), user.get('role', 'user'))
            
            return True
        
        return False
        
    except Exception as e:
        return False


def find_active_session_by_user_id(user_id: str) -> Optional[Dict]:
    """
    Busca sessão ativa no banco de dados para um user_id
    Retorna a sessão mais recente se encontrada
    """
    try:
        db = get_db()
        session_model = Session(db.sessions)
        user_model = User(db.users)
        
        # Verificar se usuário existe e está ativo
        user = user_model.find_by_id(user_id)
        if not user or not user.get('ativo'):
            return None
        
        # Buscar sessões ativas do usuário
        sessions = session_model.find_by_user(user_id)
        if not sessions:
            return None
        
        # Retornar a sessão mais recente
        active_session = sessions[0]  # Já ordenado por last_used_at desc
        
        # Verificar se a sessão não expirou
        from datetime import datetime
        if active_session.get('expires_at') and active_session['expires_at'] < datetime.utcnow():
            return None
        
        return active_session
        
    except Exception as e:
        print(f"Erro ao buscar sessão ativa: {e}")
        return None


def try_restore_session_from_db() -> bool:
    """
    Tenta restaurar sessão do banco de dados sem depender do JavaScript
    Busca sessões ativas recentes e tenta restaurar a mais recente
    Esta é uma abordagem alternativa quando o JavaScript não funciona
    """
    try:
        db = get_db()
        session_model = Session(db.sessions)
        user_model = User(db.users)
        
        # Buscar todas as sessões ativas recentes (últimas 24 horas)
        from datetime import datetime, timedelta
        recent_cutoff = datetime.utcnow() - timedelta(hours=24)
        
        # Buscar sessões ativas que foram usadas recentemente
        sessions = list(session_model.collection.find({
            "active": True,
            "last_used_at": {"$gte": recent_cutoff},
            "expires_at": {"$gt": datetime.utcnow()}
        }).sort("last_used_at", -1).limit(10))
        
        if not sessions:
            return False
        
        # Tentar restaurar a sessão mais recente
        for session_doc in sessions:
            session = session_model.to_dict(session_doc)
            user_id = session.get('user_id')
            
            if not user_id:
                continue
            
            # Verificar se o usuário existe e está ativo
            user = user_model.find_by_id(user_id)
            if not user or not user.get('ativo'):
                continue
            
            # Tentar restaurar usando a função existente
            if restore_session_from_db(user_id):
                return True
        
        return False
        
    except Exception:
        return False


def verify_and_refresh_session() -> bool:
    """
    Verifica e renova tokens automaticamente se necessário
    Retorna True se a sessão é válida, False caso contrário
    """
    try:
        access_token = st.session_state.get('access_token')
        refresh_token = st.session_state.get('refresh_token')
        
        # Se não há tokens, tentar carregar do localStorage via JavaScript
        if not access_token or not refresh_token:
            return False
        
        # Verificar access token
        payload = verify_token(access_token, token_type="access")
        
        if payload:
            # Token válido, atualizar sessão
            user_id = payload.get('user_id')
            username = payload.get('username')
            role = payload.get('role')
            
            if user_id and username and role:
                create_session(user_id, username, role)
                
                # Verificar se está próximo de expirar e renovar se necessário
                if is_token_expiring_soon(access_token, threshold_hours=2):
                    new_tokens = refresh_access_token(refresh_token)
                    if new_tokens:
                        new_access, new_refresh = new_tokens
                        st.session_state['access_token'] = new_access
                        st.session_state['refresh_token'] = new_refresh
                        # Atualizar sessão no banco
                        db = get_db()
                        session_model = Session(db.sessions)
                        session = session_model.find_by_refresh_token(refresh_token)
                        if session:
                            session_model.update_last_used(session['id'])
                            # Atualizar refresh token na sessão
                            session_model.collection.update_one(
                                {"_id": session['_id']},
                                {"$set": {"refresh_token": new_refresh}}
                            )
                
                return True
        
        # Access token inválido, tentar renovar com refresh token
        if refresh_token:
            new_tokens = refresh_access_token(refresh_token)
            if new_tokens:
                new_access, new_refresh = new_tokens
                st.session_state['access_token'] = new_access
                st.session_state['refresh_token'] = new_refresh
                
                # Verificar novo access token
                payload = verify_token(new_access, token_type="access")
                if payload:
                    user_id = payload.get('user_id')
                    username = payload.get('username')
                    role = payload.get('role')
                    
                    if user_id and username and role:
                        create_session(user_id, username, role)
                        return True
        
        # Tokens inválidos
        clear_session()
        return False
        
    except Exception as e:
        clear_session()
        return False


def logout_user(logout_all_devices: bool = False) -> bool:
    """
    Faz logout do usuário
    
    Args:
        logout_all_devices: Se True, faz logout de todos os dispositivos (não usado mais, mas mantido para compatibilidade)
    """
    try:
        user_id = st.session_state.get('user_id')
        refresh_token = st.session_state.get('refresh_token')
        
        if user_id and refresh_token:
            db = get_db()
            session_model = Session(db.sessions)
            
            # Desativar apenas a sessão atual
            session = session_model.find_by_refresh_token(refresh_token)
            if session:
                session_model.deactivate(session['id'])
        
        # Limpar todos os dados do session_state
        clear_session()
        
        # Limpar também os tokens se ainda estiverem no session_state
        if 'access_token' in st.session_state:
            del st.session_state['access_token']
        if 'refresh_token' in st.session_state:
            del st.session_state['refresh_token']
        if 'remember_me' in st.session_state:
            del st.session_state['remember_me']
        
        return True
    except Exception:
        clear_session()
        return False
