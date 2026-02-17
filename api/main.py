"""
PAICS API - FastAPI backend para o frontend Next.js
Expõe autenticação e dados (exames) para consumo pelo React.
"""
import os
import sys
from contextlib import asynccontextmanager

# Garantir que o projeto raiz está no path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

# Importações do projeto PAICS
from database.connection import get_db
from database.models import User
from auth.password import verify_password
from auth.jwt_utils import (
    generate_access_token,
    generate_refresh_token,
    refresh_access_token,
)

from api.dependencies import get_current_user
from api.routers.exames import router as exames_router
from api.routers.requisicoes import router as requisicoes_router
from api.routers.clinicas import router as clinicas_router
from api.routers.usuarios import router as usuarios_router
from api.routers.financeiro import router as financeiro_router
from api.routers.knowledge_base import router as knowledge_base_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicialização e shutdown da API."""
    yield


app = FastAPI(
    title="PAICS API",
    description="API REST para o sistema PAICS - Análise de Imagens Veterinárias",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS: em produção, defina CORS_ORIGINS no .env (ex.: https://paics.seudominio.com,https://vm-ip:3000)
_cors_origins = os.getenv("CORS_ORIGINS", "").strip()
CORS_ORIGINS = [o.strip() for o in _cors_origins.split(",") if o.strip()] or [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "Origin"],
)


# --- Schemas ---
class LoginRequest(BaseModel):
    email_or_username: str
    password: str
    remember_me: bool = False


class LoginResponse(BaseModel):
    success: bool
    message: str
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    user: Optional[dict] = None


class RefreshRequest(BaseModel):
    refresh_token: str


# Incluir routers
app.include_router(exames_router)
app.include_router(requisicoes_router)
app.include_router(clinicas_router)
app.include_router(usuarios_router)
app.include_router(financeiro_router)
app.include_router(knowledge_base_router)


# --- Rotas de autenticação ---
@app.post("/api/auth/login", response_model=LoginResponse)
def login(data: LoginRequest):
    """Login com email/username e senha. Retorna tokens JWT."""
    db = get_db()
    user_model = User(db.users)

    user = user_model.find_by_email(data.email_or_username)
    if not user:
        user = user_model.find_by_username(data.email_or_username)
    if not user:
        return LoginResponse(success=False, message="E-mail/usuário ou senha incorretos")
    if not user.get("ativo", True):
        return LoginResponse(success=False, message="Usuário inativo. Entre em contato com o administrador.")
    if not verify_password(data.password, user["password_hash"]):
        return LoginResponse(success=False, message="E-mail/usuário ou senha incorretos")

    access_token = generate_access_token(user["id"], user["username"], user["role"])
    refresh_token = generate_refresh_token(user["id"])

    # Criar sessão no banco (opcional, para compatibilidade)
    try:
        from database.models import Session
        import secrets
        session_model = Session(db.sessions)
        session_model.create(
            user_id=user["id"],
            refresh_token=refresh_token,
            device_id=secrets.token_urlsafe(16),
            device_info="API/Next.js",
            ip_address="",
        )
    except Exception:
        pass

    user_safe = {
        "id": user["id"],
        "username": user["username"],
        "email": user.get("email", ""),
        "nome": user.get("nome", user.get("username", "")),
        "role": user["role"],
        "primeiro_acesso": user.get("primeiro_acesso", False),
    }
    return LoginResponse(
        success=True,
        message="Login realizado com sucesso",
        access_token=access_token,
        refresh_token=refresh_token,
        user=user_safe,
    )


@app.post("/api/auth/refresh")
def refresh_token_route(data: RefreshRequest):
    """Renova o access token usando o refresh token."""
    new_tokens = refresh_access_token(data.refresh_token)
    if not new_tokens:
        raise HTTPException(status_code=401, detail="Refresh token inválido ou expirado")
    new_access, new_refresh = new_tokens
    return {"access_token": new_access, "refresh_token": new_refresh}


@app.get("/api/auth/me")
def get_me(user: dict = Depends(get_current_user)):
    """Retorna os dados do usuário autenticado."""
    return {
        "id": user["id"],
        "username": user["username"],
        "email": user.get("email", ""),
        "nome": user.get("nome", user.get("username", "")),
        "role": user["role"],
        "primeiro_acesso": user.get("primeiro_acesso", False),
        "clinica_id": user.get("clinica_id"),
    }


class AlterarSenhaRequest(BaseModel):
    senha_atual: str
    nova_senha: str


@app.post("/api/auth/alterar-senha")
def alterar_senha(body: AlterarSenhaRequest, user: dict = Depends(get_current_user)):
    """Altera a senha. Obrigatório no primeiro acesso (senha temporária)."""
    from auth.password import verify_password, hash_password
    db = get_db()
    user_model = User(db.users)
    u = user_model.find_by_id(user["id"])
    if not u:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    if not verify_password(body.senha_atual, u["password_hash"]):
        raise HTTPException(status_code=400, detail="Senha atual incorreta")
    if len(body.nova_senha) < 6:
        raise HTTPException(status_code=400, detail="Nova senha deve ter pelo menos 6 caracteres")
    user_model.update(user["id"], {
        "password_hash": hash_password(body.nova_senha),
        "primeiro_acesso": False,
        "senha_temporaria": None,
    })
    return {"success": True, "message": "Senha alterada com sucesso"}


@app.post("/api/auth/logout")
def logout(user: dict = Depends(get_current_user)):
    """Logout (invalidação de sessão pode ser feita no cliente)."""
    return {"message": "Logout realizado"}


# --- Health check ---
@app.get("/api/health")
def health():
    """Health check para monitoramento."""
    return {"status": "ok", "service": "paics-api"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
