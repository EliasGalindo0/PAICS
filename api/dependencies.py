"""Dependências de autenticação da API"""
from typing import Optional
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from auth.jwt_utils import verify_token
from database.connection import get_db
from database.models import User

security = HTTPBearer(auto_error=False)


def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> dict:
    """Valida o token JWT e retorna o usuário atual."""
    if not credentials:
        raise HTTPException(status_code=401, detail="Token não fornecido")
    token = credentials.credentials
    payload = verify_token(token, "access")
    if not payload:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado")
    db = get_db()
    user = User(db.users).find_by_id(payload.get("user_id", ""))
    if not user or not user.get("ativo", True):
        raise HTTPException(status_code=401, detail="Usuário não encontrado ou inativo")
    return user


def require_admin(user: dict = Depends(get_current_user)) -> dict:
    """Exige que o usuário seja admin."""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Acesso restrito a administradores")
    return user
