"""Rotas de usuários (admin)"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from database.connection import get_db
from database.models import User, Requisicao, Laudo, Clinica
from auth.password import hash_password

from api.dependencies import get_current_user, require_admin

router = APIRouter(prefix="/api", tags=["usuarios"])


class UsuarioCreate(BaseModel):
    nome: str
    username: str
    email: str
    senha_temporaria: str
    role: str = "user"
    clinica_id: Optional[str] = None


class UsuarioUpdate(BaseModel):
    nome: Optional[str] = None
    username: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    ativo: Optional[bool] = None
    clinica_id: Optional[str] = None


@router.get("/usuarios")
def listar_usuarios(user: dict = Depends(require_admin)):
    """Lista todos os usuários (admin)."""
    db = get_db()
    user_model = User(db.users)
    users = user_model.get_all()
    return [
        {
            "id": u["id"],
            "nome": u.get("nome", ""),
            "username": u.get("username", ""),
            "email": u.get("email", ""),
            "role": u.get("role", "user"),
            "ativo": u.get("ativo", True),
            "clinica_id": u.get("clinica_id"),
            "primeiro_acesso": u.get("primeiro_acesso", False),
        }
        for u in users
    ]


@router.get("/usuarios/{usuario_id}")
def obter_usuario(usuario_id: str, user: dict = Depends(require_admin)):
    """Detalhes de um usuário."""
    db = get_db()
    user_model = User(db.users)
    req_model = Requisicao(db.requisicoes)
    laudo_model = Laudo(db.laudos)
    clinica_model = Clinica(db.clinicas)

    u = user_model.find_by_id(usuario_id)
    if not u:
        raise HTTPException(404, "Usuário não encontrado")
    reqs = req_model.find_by_user(usuario_id)
    laudos = laudo_model.find_by_user(usuario_id)
    laudos_liberados = [l for l in laudos if l.get("status") == "liberado"]

    clinica_nome = None
    if u.get("clinica_id"):
        c = clinica_model.find_by_id(u["clinica_id"])
        clinica_nome = (c or {}).get("nome") if c else None

    return {
        "id": u["id"],
        "nome": u.get("nome", ""),
        "username": u.get("username", ""),
        "email": u.get("email", ""),
        "role": u.get("role", "user"),
        "ativo": u.get("ativo", True),
        "clinica_id": u.get("clinica_id"),
        "clinica_nome": clinica_nome,
        "primeiro_acesso": u.get("primeiro_acesso", False),
        "senha_temporaria": u.get("senha_temporaria") if u.get("primeiro_acesso") else None,
        "total_requisicoes": len(reqs),
        "total_laudos": len(laudos),
        "laudos_liberados": len(laudos_liberados),
    }


@router.post("/usuarios")
def criar_usuario(body: UsuarioCreate, user: dict = Depends(require_admin)):
    """Cria usuário com senha temporária (admin)."""
    db = get_db()
    user_model = User(db.users)
    if user_model.find_by_username(body.username.strip()):
        raise HTTPException(400, f"Usuário '{body.username}' já existe")
    if user_model.find_by_email(body.email.strip()):
        raise HTTPException(400, f"E-mail '{body.email}' já cadastrado")
    if len(body.senha_temporaria) < 6:
        raise HTTPException(400, "Senha temporária deve ter pelo menos 6 caracteres")

    pw_hash = hash_password(body.senha_temporaria)
    senha_temp = body.senha_temporaria  # Guardar para retornar
    user_id = user_model.create(
        username=body.username.strip(),
        email=body.email.strip(),
        password_hash=pw_hash,
        nome=body.nome.strip(),
        role=body.role,
        clinica_id=body.clinica_id if body.role == "user" else None,
        primeiro_acesso=True,
        senha_temporaria=senha_temp,
    )
    return {
        "success": True,
        "id": user_id,
        "username": body.username,
        "email": body.email,
        "senha_temporaria": senha_temp,
    }


@router.patch("/usuarios/{usuario_id}")
def atualizar_usuario(usuario_id: str, body: UsuarioUpdate, user: dict = Depends(require_admin)):
    """Atualiza usuário (admin)."""
    db = get_db()
    user_model = User(db.users)
    u = user_model.find_by_id(usuario_id)
    if not u:
        raise HTTPException(404, "Usuário não encontrado")
    updates = {}
    if body.nome is not None:
        updates["nome"] = body.nome.strip()
    if body.username is not None:
        other = user_model.find_by_username(body.username.strip())
        if other and other.get("id") != usuario_id:
            raise HTTPException(400, f"Usuário '{body.username}' já existe")
        updates["username"] = body.username.strip()
    if body.email is not None:
        other = user_model.find_by_email(body.email.strip())
        if other and other.get("id") != usuario_id:
            raise HTTPException(400, f"E-mail '{body.email}' já cadastrado")
        updates["email"] = body.email.strip()
    if body.role is not None:
        updates["role"] = body.role
    if body.ativo is not None:
        updates["ativo"] = body.ativo
    if body.clinica_id is not None:
        updates["clinica_id"] = body.clinica_id if body.clinica_id else None
    if not updates:
        return {"success": True}
    user_model.update(usuario_id, updates)
    return {"success": True}


@router.delete("/usuarios/{usuario_id}")
def excluir_usuario(usuario_id: str, user: dict = Depends(require_admin)):
    """Exclui usuário (admin). Não exclui se for o próprio admin."""
    if usuario_id == user["id"]:
        raise HTTPException(400, "Não é possível excluir o próprio usuário")
    db = get_db()
    user_model = User(db.users)
    u = user_model.find_by_id(usuario_id)
    if not u:
        raise HTTPException(404, "Usuário não encontrado")
    if not user_model.delete(usuario_id):
        raise HTTPException(500, "Erro ao excluir usuário")
    return {"success": True}
