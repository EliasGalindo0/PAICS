"""
Rotas para criar requisições (exames) - com upload de imagens
"""
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from database.connection import get_db
from database.models import Requisicao, Clinica, Veterinario
from database.image_storage import save_image
from utils.timezone import now, combine_date_local

from api.dependencies import get_current_user

router = APIRouter(prefix="/api/requisicoes", tags=["requisicoes"])


def _upper(s):
    return (s or "").strip().upper() if isinstance(s, str) else s


@router.post("")
async def criar_requisicao(
    paciente: str = Form(...),
    tutor: str = Form(...),
    clinica: Optional[str] = Form(""),
    tipo_exame: str = Form("raio-x"),
    especie: Optional[str] = Form(""),
    idade: Optional[str] = Form(""),
    raca: Optional[str] = Form(""),
    sexo: str = Form("Macho"),
    medico_veterinario_solicitante: Optional[str] = Form(""),
    regiao_estudo: Optional[str] = Form(""),
    suspeita_clinica: Optional[str] = Form(""),
    plantao: str = Form("Não"),
    historico_clinico: Optional[str] = Form(""),
    data_exame: Optional[str] = Form(None),
    clinica_id: Optional[str] = Form(None),
    veterinario_id: Optional[str] = Form(None),
    imagens: List[UploadFile] = File(...),
    user: dict = Depends(get_current_user),
):
    """Cria nova requisição com imagens (multipart)."""
    if not paciente.strip() or not tutor.strip():
        raise HTTPException(400, "Paciente e tutor são obrigatórios")
    if not imagens:
        raise HTTPException(400, "Selecione ao menos uma imagem")

    db = get_db()
    req_model = Requisicao(db.requisicoes)
    clinica_model = Clinica(db.clinicas)
    veterinario_model = Veterinario(db.veterinarios)

    clinica_nome = clinica or ""
    medico_vet = medico_veterinario_solicitante or ""
    if clinica_id:
        c = clinica_model.find_by_id(clinica_id)
        if c:
            clinica_nome = c.get("nome", clinica_nome)
    if veterinario_id:
        v = veterinario_model.find_by_id(veterinario_id)
        if v:
            medico_vet = v.get("nome", medico_vet)

    # User com clínica: preencher automaticamente se não informado
    user_clinica_id = user.get("clinica_id")
    if user_clinica_id and not clinica_id:
        clinica_id = user_clinica_id
        c = clinica_model.find_by_id(clinica_id)
        clinica_nome = (c or {}).get("nome", clinica_nome)
        vets = veterinario_model.find_by_clinica(clinica_id, apenas_ativos=True)
        if vets and not veterinario_id:
            veterinario_id = vets[0].get("id")
            medico_vet = vets[0].get("nome", medico_vet)

    imagens_refs = []
    for f in imagens:
        if f.filename and f.size and f.size > 0:
            try:
                data = await f.read()
                ref = save_image(data, f.filename or "imagem", metadata={"user_id": user["id"]})
                imagens_refs.append(ref)
            except Exception as e:
                raise HTTPException(500, f"Erro ao salvar imagem {f.filename}: {str(e)}")

    if not imagens_refs:
        raise HTTPException(400, "Nenhuma imagem válida foi processada")

    data_exame_dt = now()
    if data_exame:
        try:
            from datetime import date
            parts = data_exame[:10].split("-")
            if len(parts) == 3:
                data_exame_dt = combine_date_local(
                    date(int(parts[0]), int(parts[1]), int(parts[2]))
                )
        except Exception:
            pass

    req_id = req_model.create(
        user_id=user["id"],
        imagens=imagens_refs,
        paciente=_upper(paciente),
        tutor=_upper(tutor),
        clinica=clinica_nome,
        tipo_exame=tipo_exame,
        observacoes=_upper(historico_clinico or ""),
        especie=especie or "",
        idade=idade or "",
        raca=_upper(raca or ""),
        sexo=sexo,
        medico_veterinario_solicitante=medico_vet,
        regiao_estudo=_upper(regiao_estudo or ""),
        suspeita_clinica=_upper(suspeita_clinica or ""),
        plantao=plantao,
        historico_clinico=_upper(historico_clinico or ""),
        data_exame=data_exame_dt,
        status="pendente",
        clinica_id=clinica_id,
        veterinario_id=veterinario_id,
    )
    return {"success": True, "id": req_id}


@router.post("/rascunho")
async def salvar_rascunho(
    paciente: str = Form(""),
    tutor: str = Form(""),
    clinica: Optional[str] = Form(""),
    tipo_exame: str = Form("raio-x"),
    especie: Optional[str] = Form(""),
    idade: Optional[str] = Form(""),
    raca: Optional[str] = Form(""),
    sexo: str = Form("Macho"),
    medico_veterinario_solicitante: Optional[str] = Form(""),
    regiao_estudo: Optional[str] = Form(""),
    suspeita_clinica: Optional[str] = Form(""),
    plantao: str = Form("Não"),
    historico_clinico: Optional[str] = Form(""),
    data_exame: Optional[str] = Form(None),
    clinica_id: Optional[str] = Form(None),
    veterinario_id: Optional[str] = Form(None),
    rascunho_id: Optional[str] = Form(None),
    user: dict = Depends(get_current_user),
):
    """Salva ou atualiza rascunho (sem imagens obrigatórias)."""
    if not paciente.strip() or not tutor.strip():
        raise HTTPException(400, "Paciente e tutor são obrigatórios para salvar rascunho")

    db = get_db()
    veterinario_model = Veterinario(db.veterinarios)
    req_model = Requisicao(db.requisicoes)
    clinica_model = Clinica(db.clinicas)
    clinica_nome = clinica or ""
    if clinica_id:
        c = clinica_model.find_by_id(clinica_id)
        if c:
            clinica_nome = c.get("nome", clinica_nome)
    medico_vet = medico_veterinario_solicitante or ""
    if veterinario_id:
        v = veterinario_model.find_by_id(veterinario_id)
        if v:
            medico_vet = v.get("nome", medico_vet)

    user_clinica_id = user.get("clinica_id")
    if user_clinica_id and not clinica_id:
        clinica_id = user_clinica_id

    data_exame_dt = now()
    if data_exame:
        try:
            from datetime import date
            parts = data_exame[:10].split("-")
            if len(parts) == 3:
                data_exame_dt = combine_date_local(
                    date(int(parts[0]), int(parts[1]), int(parts[2]))
                )
        except Exception:
            pass

    payload = {
        "paciente": _upper(paciente),
        "tutor": _upper(tutor),
        "clinica": clinica_nome,
        "tipo_exame": tipo_exame,
        "especie": especie or "",
        "idade": idade or "",
        "raca": _upper(raca or ""),
        "sexo": sexo,
        "medico_veterinario_solicitante": medico_vet,
        "regiao_estudo": _upper(regiao_estudo or ""),
        "suspeita_clinica": _upper(suspeita_clinica or ""),
        "plantao": plantao,
        "historico_clinico": _upper(historico_clinico or ""),
        "observacoes": _upper(historico_clinico or ""),
        "data_exame": data_exame_dt,
        "clinica_id": clinica_id,
        "veterinario_id": veterinario_id,
    }

    if rascunho_id:
        existing = req_model.find_by_id(rascunho_id)
        if existing and existing.get("user_id") == user["id"] and existing.get("status") == "rascunho":
            req_model.update(rascunho_id, {**payload, "imagens": existing.get("imagens") or []})
            return {"success": True, "id": rascunho_id}

    req_id = req_model.create(
        user_id=user["id"],
        imagens=[],
        status="rascunho",
        paciente=payload["paciente"],
        tutor=payload["tutor"],
        clinica=payload["clinica"],
        tipo_exame=payload["tipo_exame"],
        observacoes=payload["observacoes"],
        especie=payload["especie"],
        idade=payload["idade"],
        raca=payload["raca"],
        sexo=payload["sexo"],
        medico_veterinario_solicitante=payload["medico_veterinario_solicitante"],
        regiao_estudo=payload["regiao_estudo"],
        suspeita_clinica=payload["suspeita_clinica"],
        plantao=payload["plantao"],
        historico_clinico=payload["historico_clinico"],
        data_exame=payload["data_exame"],
        clinica_id=payload.get("clinica_id"),
        veterinario_id=payload.get("veterinario_id"),
    )
    return {"success": True, "id": req_id}


@router.get("/rascunhos")
async def listar_rascunhos(user: dict = Depends(get_current_user)):
    """Lista rascunhos do usuário (requisições com status rascunho)."""
    db = get_db()
    req_model = Requisicao(db.requisicoes)
    rascunhos = req_model.find_by_user(user["id"], status="rascunho")
    return rascunhos
