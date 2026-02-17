"""Rotas de clínicas e veterinários"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from database.connection import get_db
from database.models import Clinica, Veterinario, User
from auth.password import hash_password

from api.dependencies import get_current_user, require_admin

router = APIRouter(prefix="/api", tags=["clinicas"])


class ClinicaCreate(BaseModel):
    nome: str
    cnpj: str = ""
    endereco: str = ""
    numero: str = ""
    bairro: str = ""
    cidade: str = ""
    cep: str = ""
    telefone: str = ""
    email: str = ""


class ClinicaUpdate(BaseModel):
    nome: Optional[str] = None
    cnpj: Optional[str] = None
    endereco: Optional[str] = None
    numero: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    cep: Optional[str] = None
    telefone: Optional[str] = None
    email: Optional[str] = None
    ativa: Optional[bool] = None


class ClinicaCompletaCreate(BaseModel):
    """Clínica + conta de acesso (usuário para login)"""
    nome: str
    cnpj: str = ""
    endereco: str = ""
    numero: str = ""
    bairro: str = ""
    cidade: str = ""
    cep: str = ""
    telefone: str = ""
    email: str
    username: str
    senha_temporaria: str


class VeterinarioCreate(BaseModel):
    nome: str
    crmv: str
    email: str = ""


class VeterinarioUpdate(BaseModel):
    nome: Optional[str] = None
    crmv: Optional[str] = None
    email: Optional[str] = None
    ativo: Optional[bool] = None


@router.get("/cep/{cep}")
def buscar_cep(cep: str):
    """Busca endereço por CEP (ViaCEP)."""
    from utils.viacep import buscar_cep as viacep_buscar
    cep_limpo = "".join(c for c in cep if c.isdigit())
    if len(cep_limpo) != 8:
        raise HTTPException(400, "CEP deve ter 8 dígitos")
    data = viacep_buscar(cep_limpo)
    if not data:
        raise HTTPException(404, "CEP não encontrado")
    return data


@router.get("/clinicas")
def listar_clinicas(
    apenas_ativas: bool = True,
    user: dict = Depends(get_current_user),
):
    """Lista clínicas. User vê só a sua se vinculado."""
    db = get_db()
    clinica_model = Clinica(db.clinicas)
    if user["role"] == "admin":
        clinicas = clinica_model.get_all(apenas_ativas=apenas_ativas)
    else:
        cid = user.get("clinica_id")
        if not cid:
            return []
        c = clinica_model.find_by_id(cid)
        clinicas = [c] if c else []
    return [
        {
            "id": c["id"],
            "nome": c.get("nome", ""),
            "cnpj": c.get("cnpj", ""),
            "endereco": c.get("endereco", ""),
            "telefone": c.get("telefone", ""),
            "email": c.get("email", ""),
            "ativa": c.get("ativa", True),
        }
        for c in clinicas
    ]


@router.get("/clinicas/{clinica_id}")
def obter_clinica(
    clinica_id: str,
    user: dict = Depends(get_current_user),
):
    """Retorna detalhes de uma clínica."""
    db = get_db()
    clinica_model = Clinica(db.clinicas)
    if user["role"] != "admin" and user.get("clinica_id") != clinica_id:
        raise HTTPException(403, "Sem permissão")
    c = clinica_model.find_by_id(clinica_id)
    if not c:
        raise HTTPException(404, "Clínica não encontrada")
    return {
        "id": c["id"],
        "nome": c.get("nome", ""),
        "cnpj": c.get("cnpj", ""),
        "endereco": c.get("endereco", ""),
        "numero": c.get("numero", ""),
        "bairro": c.get("bairro", ""),
        "cidade": c.get("cidade", ""),
        "cep": c.get("cep", ""),
        "telefone": c.get("telefone", ""),
        "email": c.get("email", ""),
        "ativa": c.get("ativa", True),
    }


@router.post("/clinicas")
def criar_clinica(
    data: ClinicaCreate,
    user: dict = Depends(require_admin),
):
    """Cria uma nova clínica (somente admin)."""
    db = get_db()
    clinica_model = Clinica(db.clinicas)
    cid = clinica_model.create(
        nome=data.nome.strip(),
        cnpj=data.cnpj or "",
        endereco=data.endereco or "",
        numero=data.numero or "",
        bairro=data.bairro or "",
        cidade=data.cidade or "",
        cep=data.cep or "",
        telefone=data.telefone or "",
        email=data.email or "",
        ativa=True,
    )
    c = clinica_model.find_by_id(cid)
    return {
        "id": c["id"],
        "nome": c.get("nome", ""),
        "cnpj": c.get("cnpj", ""),
        "endereco": c.get("endereco", ""),
        "telefone": c.get("telefone", ""),
        "email": c.get("email", ""),
        "ativa": c.get("ativa", True),
    }


@router.post("/clinicas/completo")
def criar_clinica_completa(
    data: ClinicaCompletaCreate,
    user: dict = Depends(require_admin),
):
    """Cria clínica + usuário de acesso em uma única operação (somente admin)."""
    db = get_db()
    clinica_model = Clinica(db.clinicas)
    user_model = User(db.users)
    if user_model.find_by_username(data.username.strip()):
        raise HTTPException(400, "Este usuário já está em uso.")
    if user_model.find_by_email(data.email.strip()):
        raise HTTPException(400, "Este e-mail já está cadastrado.")
    cid = clinica_model.create(
        nome=data.nome.strip(),
        cnpj=data.cnpj or "",
        endereco=data.endereco or "",
        numero=data.numero or "",
        bairro=data.bairro or "",
        cidade=data.cidade or "",
        cep=data.cep or "",
        telefone=data.telefone or "",
        email=data.email.strip() or "",
        ativa=True,
    )
    user_model.create(
        username=data.username.strip(),
        email=data.email.strip(),
        password_hash=hash_password(data.senha_temporaria),
        role="user",
        nome=data.nome.strip(),
        ativo=True,
        primeiro_acesso=True,
        senha_temporaria=data.senha_temporaria,
        clinica_id=cid,
    )
    c = clinica_model.find_by_id(cid)
    return {
        "clinica": {
            "id": c["id"],
            "nome": c.get("nome", ""),
            "email": c.get("email", ""),
        },
        "username": data.username.strip(),
        "senha_temporaria": data.senha_temporaria,
    }


@router.patch("/clinicas/{clinica_id}")
def atualizar_clinica(
    clinica_id: str,
    data: ClinicaUpdate,
    user: dict = Depends(require_admin),
):
    """Atualiza uma clínica (somente admin)."""
    db = get_db()
    clinica_model = Clinica(db.clinicas)
    c = clinica_model.find_by_id(clinica_id)
    if not c:
        raise HTTPException(404, "Clínica não encontrada")
    updates = {k: v for k, v in data.model_dump(exclude_unset=True).items()}
    if updates:
        if "nome" in updates:
            updates["nome"] = updates["nome"].strip()
        clinica_model.update(clinica_id, updates)
    c = clinica_model.find_by_id(clinica_id)
    return {"id": c["id"], "nome": c.get("nome", ""), "ativa": c.get("ativa", True)}


@router.get("/clinicas/{clinica_id}/veterinarios")
def listar_veterinarios(
    clinica_id: str,
    apenas_ativos: bool = True,
    user: dict = Depends(get_current_user),
):
    """Lista veterinários de uma clínica."""
    db = get_db()
    clinica_model = Clinica(db.clinicas)
    veterinario_model = Veterinario(db.veterinarios)
    if user["role"] != "admin":
        if user.get("clinica_id") != clinica_id:
            raise HTTPException(403, "Sem permissão")
    vets = veterinario_model.find_by_clinica(clinica_id, apenas_ativos=apenas_ativos)
    return [{"id": v["id"], "nome": v.get("nome", ""), "crmv": v.get("crmv", ""), "email": v.get("email", "")} for v in vets]


@router.post("/clinicas/{clinica_id}/veterinarios")
def criar_veterinario(
    clinica_id: str,
    data: VeterinarioCreate,
    user: dict = Depends(require_admin),
):
    """Cria um veterinário na clínica (somente admin)."""
    db = get_db()
    clinica_model = Clinica(db.clinicas)
    veterinario_model = Veterinario(db.veterinarios)
    c = clinica_model.find_by_id(clinica_id)
    if not c:
        raise HTTPException(404, "Clínica não encontrada")
    vid = veterinario_model.create(
        nome=data.nome.strip(),
        crmv=data.crmv.strip(),
        clinica_id=clinica_id,
        email=data.email or "",
        ativo=True,
    )
    v = veterinario_model.find_by_id(vid)
    return {"id": v["id"], "nome": v.get("nome", ""), "crmv": v.get("crmv", ""), "email": v.get("email", "")}


@router.patch("/clinicas/{clinica_id}/veterinarios/{vet_id}")
def atualizar_veterinario(
    clinica_id: str,
    vet_id: str,
    data: VeterinarioUpdate,
    user: dict = Depends(require_admin),
):
    """Atualiza um veterinário (somente admin)."""
    db = get_db()
    veterinario_model = Veterinario(db.veterinarios)
    v = veterinario_model.find_by_id(vet_id)
    if not v or v.get("clinica_id") != clinica_id:
        raise HTTPException(404, "Veterinário não encontrado")
    updates = {k: v for k, v in data.model_dump(exclude_unset=True).items()}
    if updates:
        if "nome" in updates:
            updates["nome"] = updates["nome"].strip()
        if "crmv" in updates:
            updates["crmv"] = updates["crmv"].strip()
        veterinario_model.update(vet_id, updates)
    v = veterinario_model.find_by_id(vet_id)
    return {"id": v["id"], "nome": v.get("nome", ""), "crmv": v.get("crmv", ""), "ativo": v.get("ativo", True)}
