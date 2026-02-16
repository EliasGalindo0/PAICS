"""
Utilitários para o painel financeiro
"""
from datetime import datetime
from typing import List, Dict
from database.connection import get_db
from database.models import Requisicao, Laudo, Fatura, User, SystemConfig


def _get_finance_config():
    """Obtém configurações financeiras padrão (preço base e acréscimo plantão)."""
    db = get_db()
    cfg_model = SystemConfig(db.system_config)
    valor_base = cfg_model.get_value("financeiro.valor_base_exame", 50.0)
    acrescimo_plantao = cfg_model.get_value("financeiro.acrescimo_plantao", 60.0)
    return valor_base, acrescimo_plantao


def set_acrescimo_plantao(novo_valor: float, changed_by: str | None = None) -> None:
    """Atualiza o valor de acréscimo de plantão no SystemConfig."""
    db = get_db()
    cfg_model = SystemConfig(db.system_config)
    cfg_model.set_value("financeiro.acrescimo_plantao", float(novo_valor), changed_by=changed_by)


def set_valor_base_exame(novo_valor: float, changed_by: str | None = None) -> None:
    """Atualiza o valor base padrão por exame no SystemConfig."""
    db = get_db()
    cfg_model = SystemConfig(db.system_config)
    cfg_model.set_value("financeiro.valor_base_exame", float(novo_valor), changed_by=changed_by)


def gerar_fechamento(
    user_id: str,
    data_inicio: datetime,
    data_fim: datetime,
    valor_por_exame: float | None = None,
    valor_plantao: float | None = None,
) -> Dict:
    """
    Gera fechamento financeiro para um usuário no período especificado
    """
    db = get_db()
    requisicao_model = Requisicao(db.requisicoes)
    laudo_model = Laudo(db.laudos)

    # Definir valores padrão a partir da configuração, permitindo override
    cfg_valor_base, cfg_acrescimo_plantao = _get_finance_config()
    valor_base_exame = float(valor_por_exame if valor_por_exame is not None else cfg_valor_base)
    valor_acrescimo_plantao = float(
        valor_plantao if valor_plantao is not None else cfg_acrescimo_plantao
    )

    # Buscar requisições do usuário no período
    requisicoes = requisicao_model.find_by_user(user_id)

    # Batch: buscar todos os laudos de uma vez
    req_ids = [r["id"] for r in requisicoes]
    laudos_map = laudo_model.find_by_requisicao_ids(req_ids) if req_ids else {}

    # Filtrar por período e status liberado
    exames = []
    from datetime import timezone as _tzmod
    from utils.timezone import utc_to_local

    for req in requisicoes:
        req_date = req.get("created_at")
        if isinstance(req_date, str):
            try:
                req_date = datetime.fromisoformat(req_date.replace("Z", "+00:00"))
            except Exception:
                continue

        if not isinstance(req_date, datetime):
            continue

        # Normalizar: assumir UTC quando não há timezone e converter para local (GMT-3)
        if req_date.tzinfo is None:
            req_date = req_date.replace(tzinfo=_tzmod.utc)
        req_date_local = utc_to_local(req_date)

        if data_inicio <= req_date_local <= data_fim:
            laudo = laudos_map.get(req["id"])
            if laudo and laudo.get("status") == "liberado":
                is_plantao = (req.get("plantao") == "Sim")
                valor_base = valor_base_exame
                acrescimo_plantao = valor_acrescimo_plantao if is_plantao else 0.0
                valor_total_exame = valor_base + acrescimo_plantao

                observacao = ""
                if is_plantao and acrescimo_plantao > 0:
                    observacao = f"Plantão - Acréscimo R$ {acrescimo_plantao:.2f}"

                exames.append(
                    {
                        "requisicao_id": req["id"],
                        "paciente": req.get("paciente", "N/A"),
                        "tipo_exame": req.get("tipo_exame", "N/A"),
                        "data": req_date_local,
                        "valor_base": valor_base,
                        "plantao": is_plantao,
                        "acrescimo_plantao": acrescimo_plantao,
                        "valor": valor_total_exame,
                        "observacao": observacao,
                    }
                )

    # Calcular total
    valor_total = sum(exame['valor'] for exame in exames)

    # Criar período string
    periodo = f"{data_inicio.strftime('%Y-%m-%d')} a {data_fim.strftime('%Y-%m-%d')}"

    return {
        'user_id': user_id,
        'periodo': periodo,
        'exames': exames,
        'valor_total': valor_total,
        'quantidade_exames': len(exames)
    }


def criar_fatura(user_id: str, periodo: str, exames: List[Dict],
                 valor_total: float) -> str:
    """Cria uma nova fatura"""
    db = get_db()
    fatura_model = Fatura(db.faturas)

    fatura_id = fatura_model.create(
        user_id=user_id,
        periodo=periodo,
        exames=exames,
        valor_total=valor_total,
        status="pendente"
    )

    return fatura_id


def gerar_fechamento_todos_usuarios(
    data_inicio: datetime,
    data_fim: datetime,
    valor_por_exame: float | None = None,
    valor_plantao: float | None = None,
) -> List[Dict]:
    """
    Gera fechamento para todos os usuários no período
    """
    db = get_db()
    user_model = User(db.users)

    usuarios = user_model.get_all(role="user")
    fechamentos = []

    for usuario in usuarios:
        if usuario.get('ativo', True):
            fechamento = gerar_fechamento(
                usuario["id"],
                data_inicio,
                data_fim,
                valor_por_exame=valor_por_exame,
                valor_plantao=valor_plantao,
            )
            if fechamento['quantidade_exames'] > 0:
                fechamentos.append({
                    'usuario': usuario,
                    'fechamento': fechamento
                })

    return fechamentos
