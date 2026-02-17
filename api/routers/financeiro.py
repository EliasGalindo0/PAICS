"""Rotas financeiras - fechamentos e faturas"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from database.connection import get_db
from database.models import Fatura, Requisicao, User
from utils.financeiro import gerar_fechamento, criar_fatura, gerar_fechamento_todos_usuarios

from api.dependencies import get_current_user, require_admin

router = APIRouter(prefix="/api", tags=["financeiro"])


def _fmt_dt(x):
    if x is None:
        return None
    if hasattr(x, "strftime"):
        return x.strftime("%d/%m/%Y %H:%M")
    return str(x)[:16]


@router.get("/faturas")
def listar_faturas(
    status: Optional[str] = None,
    user_id: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    """Lista faturas. User vê só as suas; admin pode filtrar por user_id."""
    db = get_db()
    fatura_model = Fatura(db.faturas)
    req_model = Requisicao(db.requisicoes)

    if user["role"] == "admin":
        if user_id:
            faturas = fatura_model.find_by_user(user_id, status=status)
        else:
            faturas = fatura_model.find_all(status=status)
    else:
        faturas = fatura_model.find_by_user(user["id"], status=status)

    result = []
    for f in faturas:
        exames_detalhe = []
        for ex in (f.get("exames") or []):
            req = req_model.find_by_id(ex.get("requisicao_id", ""))
            exames_detalhe.append({
                "requisicao_id": ex.get("requisicao_id"),
                "paciente": req.get("paciente", "N/A") if req else "N/A",
                "valor_base": ex.get("valor_base", ex.get("valor", 0)),
                "acrescimo_plantao": ex.get("acrescimo_plantao", 0),
                "valor": ex.get("valor", 0),
                "plantao": ex.get("plantao", False),
                "observacao": ex.get("observacao", ""),
            })
        result.append({
            "id": f["id"],
            "periodo": f.get("periodo", ""),
            "valor_total": f.get("valor_total", 0),
            "status": f.get("status", "pendente"),
            "quantidade_exames": len(f.get("exames") or []),
            "created_at": _fmt_dt(f.get("created_at")),
            "exames": exames_detalhe,
        })
    return result


class AtualizarStatusFaturaRequest(BaseModel):
    status: str  # "paga" | "cancelada"


@router.patch("/faturas/{fatura_id}")
def atualizar_status_fatura(
    fatura_id: str,
    body: AtualizarStatusFaturaRequest,
    user: dict = Depends(require_admin),
):
    """Atualiza status da fatura (admin): paga ou cancelada."""
    db = get_db()
    fatura_model = Fatura(db.faturas)
    fatura = fatura_model.find_by_id(fatura_id)
    if not fatura:
        raise HTTPException(404, "Fatura não encontrada")
    if body.status not in ("paga", "cancelada"):
        raise HTTPException(400, "Status deve ser 'paga' ou 'cancelada'")
    if not fatura_model.update_status(fatura_id, body.status):
        raise HTTPException(500, "Erro ao atualizar status")
    return {"success": True, "status": body.status}


@router.get("/faturas/{fatura_id}")
def obter_fatura(fatura_id: str, user: dict = Depends(get_current_user)):
    """Detalhes de uma fatura."""
    db = get_db()
    fatura_model = Fatura(db.faturas)
    req_model = Requisicao(db.requisicoes)

    fatura = fatura_model.find_by_id(fatura_id)
    if not fatura:
        raise HTTPException(404, "Fatura não encontrada")
    if user["role"] != "admin" and fatura.get("user_id") != user["id"]:
        raise HTTPException(403, "Sem permissão")

    exames_detalhe = []
    for ex in (fatura.get("exames") or []):
        req = req_model.find_by_id(ex.get("requisicao_id", ""))
        exames_detalhe.append({
            "requisicao_id": ex.get("requisicao_id"),
            "paciente": req.get("paciente", "N/A") if req else "N/A",
            "valor_base": ex.get("valor_base", ex.get("valor", 0)),
            "acrescimo_plantao": ex.get("acrescimo_plantao", 0),
            "valor": ex.get("valor", 0),
            "plantao": ex.get("plantao", False),
            "observacao": ex.get("observacao", ""),
        })

    return {
        "id": fatura["id"],
        "user_id": fatura.get("user_id"),
        "periodo": fatura.get("periodo", ""),
        "valor_total": fatura.get("valor_total", 0),
        "status": fatura.get("status", "pendente"),
        "exames": exames_detalhe,
        "created_at": _fmt_dt(fatura.get("created_at")),
    }


class FechamentoRequest(BaseModel):
    user_id: str
    data_inicio: str
    data_fim: str
    valor_por_exame: Optional[float] = None
    valor_plantao: Optional[float] = None


@router.post("/financeiro/fechamento")
def gerar_fechamento_route(body: FechamentoRequest, user: dict = Depends(require_admin)):
    """Gera fechamento para um usuário no período (admin)."""
    try:
        di = datetime.strptime(body.data_inicio[:10], "%Y-%m-%d")
        df = datetime.strptime(body.data_fim[:10], "%Y-%m-%d")
    except Exception:
        raise HTTPException(400, "Datas inválidas. Use formato YYYY-MM-DD")
    from utils.timezone import combine_date_local, get_date_start, get_date_end
    di = get_date_start(combine_date_local(di.date()))
    df = get_date_end(combine_date_local(df.date()))
    fech = gerar_fechamento(
        body.user_id,
        di,
        df,
        valor_por_exame=body.valor_por_exame,
        valor_plantao=body.valor_plantao,
    )
    return fech


class CriarFaturaRequest(BaseModel):
    user_id: str
    periodo: str
    exames: list
    valor_total: float


@router.post("/financeiro/faturas")
def criar_fatura_route(body: CriarFaturaRequest, user: dict = Depends(require_admin)):
    """Cria fatura a partir de fechamento (admin)."""
    fatura_id = criar_fatura(body.user_id, body.periodo, body.exames, body.valor_total)
    return {"success": True, "id": fatura_id}


@router.get("/financeiro/fechamento-todos")
def fechamento_todos(
    data_inicio: str = None,
    data_fim: str = None,
    valor_por_exame: Optional[float] = None,
    valor_plantao: Optional[float] = None,
    user: dict = Depends(require_admin),
):
    """Gera fechamento para todos os usuários no período (admin)."""
    if not data_inicio or not data_fim:
        raise HTTPException(400, "data_inicio e data_fim são obrigatórios")
    try:
        di = datetime.strptime(data_inicio[:10], "%Y-%m-%d")
        df = datetime.strptime(data_fim[:10], "%Y-%m-%d")
    except Exception:
        raise HTTPException(400, "Datas inválidas")
    from utils.timezone import combine_date_local, get_date_start, get_date_end
    di = get_date_start(combine_date_local(di.date()))
    df = get_date_end(combine_date_local(df.date()))
    fechamentos = gerar_fechamento_todos_usuarios(
        di, df,
        valor_por_exame=valor_por_exame,
        valor_plantao=valor_plantao,
    )
    return fechamentos
