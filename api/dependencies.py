"""Dependências de autenticação da API"""
import time
from typing import Optional
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from auth.jwt_utils import verify_token
from database.connection import get_db
from database.models import User

security = HTTPBearer(auto_error=False)

_USER_TTL_SECONDS = 60.0
_USER_CACHE_MAX = 256
_user_cache: dict[str, tuple[float, dict]] = {}


def _cache_get(token: str) -> Optional[dict]:
    entry = _user_cache.get(token)
    if not entry:
        return None
    expires_at, user = entry
    if expires_at <= time.monotonic():
        _user_cache.pop(token, None)
        return None
    return user


def _cache_put(token: str, user: dict) -> None:
    now_ts = time.monotonic()
    if len(_user_cache) >= _USER_CACHE_MAX:
        stale = [k for k, (exp, _) in _user_cache.items() if exp <= now_ts]
        for k in stale:
            _user_cache.pop(k, None)
        if len(_user_cache) >= _USER_CACHE_MAX:
            oldest = min(_user_cache, key=lambda k: _user_cache[k][0])
            _user_cache.pop(oldest, None)
    _user_cache[token] = (now_ts + _USER_TTL_SECONDS, user)


def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> dict:
    """Valida o token JWT e retorna o usuário atual (com cache curto)."""
    if not credentials:
        raise HTTPException(status_code=401, detail="Token não fornecido")
    token = credentials.credentials
    cached = _cache_get(token)
    if cached is not None:
        return cached
    payload = verify_token(token, "access")
    if not payload:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado")
    db = get_db()
    user = User(db.users).find_by_id(payload.get("user_id", ""))
    if not user or not user.get("ativo", True):
        raise HTTPException(status_code=401, detail="Usuário não encontrado ou inativo")
    _cache_put(token, user)
    return user


def require_admin(user: dict = Depends(get_current_user)) -> dict:
    """Exige que o usuário seja admin."""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Acesso restrito a administradores")
    return user
