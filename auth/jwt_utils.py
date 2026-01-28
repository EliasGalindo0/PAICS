"""
Utilitários para gerenciamento de tokens JWT
"""
import os
import jwt
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from utils.timezone import now

load_dotenv()

# Chave secreta para assinar tokens (deve estar no .env em produção)
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))
JWT_ALGORITHM = "HS256"

# Duração dos tokens
ACCESS_TOKEN_EXPIRY = timedelta(days=1)  # Token de acesso: 1 dia
REFRESH_TOKEN_EXPIRY = timedelta(days=30)  # Refresh token: 30 dias
REMEMBER_ME_EXPIRY = timedelta(days=30)  # "Lembrar-me": 30 dias


def generate_access_token(user_id: str, username: str, role: str) -> str:
    """Gera um token de acesso JWT"""
    payload = {
        "user_id": user_id,
        "username": username,
        "role": role,
        "type": "access",
        "exp": now() + ACCESS_TOKEN_EXPIRY,
        "iat": now()
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def generate_refresh_token(user_id: str, device_id: Optional[str] = None) -> str:
    """Gera um refresh token JWT"""
    payload = {
        "user_id": user_id,
        "type": "refresh",
        "device_id": device_id or secrets.token_urlsafe(16),
        "exp": now() + REFRESH_TOKEN_EXPIRY,
        "iat": now()
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def verify_token(token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
    """
    Verifica e decodifica um token JWT

    Args:
        token: Token JWT a ser verificado
        token_type: Tipo esperado do token ("access" ou "refresh")

    Returns:
        Payload decodificado se válido, None caso contrário
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])

        # Verificar tipo do token
        if payload.get("type") != token_type:
            return None

        # Verificar se não expirou (jwt.decode já faz isso, mas garantimos)
        exp = payload.get("exp")
        if exp and now() > datetime.fromtimestamp(exp):
            return None

        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
    except Exception:
        return None


def refresh_access_token(refresh_token: str) -> Optional[tuple[str, str]]:
    """
    Gera um novo access token a partir de um refresh token válido

    Returns:
        Tupla (novo_access_token, novo_refresh_token) ou None se inválido
    """
    payload = verify_token(refresh_token, token_type="refresh")
    if not payload:
        return None

    user_id = payload.get("user_id")
    device_id = payload.get("device_id")

    if not user_id:
        return None

    # Buscar informações do usuário para gerar novo access token
    from database.connection import get_db
    from database.models import User

    db = get_db()
    user_model = User(db.users)
    user = user_model.find_by_id(user_id)

    if not user or not user.get('ativo', True):
        return None

    # Gerar novos tokens
    new_access_token = generate_access_token(
        user['id'],
        user.get('username', ''),
        user.get('role', 'user')
    )
    new_refresh_token = generate_refresh_token(user_id, device_id)

    return (new_access_token, new_refresh_token)


def get_token_expiry(token: str) -> Optional[datetime]:
    """Retorna a data de expiração de um token"""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM], options={"verify_exp": False})
        exp = payload.get("exp")
        if exp:
            return datetime.fromtimestamp(exp)
    except Exception:
        pass
    return None


def is_token_expiring_soon(token: str, threshold_hours: int = 2) -> bool:
    """Verifica se o token está próximo de expirar"""
    expiry = get_token_expiry(token)
    if not expiry:
        return True
    
    threshold = now() + timedelta(hours=threshold_hours)
    return expiry <= threshold
