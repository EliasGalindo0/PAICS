"""
Utilitários para o painel financeiro
"""
from datetime import datetime, timedelta
from typing import List, Dict
from database.connection import get_db
from database.models import Requisicao, Laudo, Fatura, User


def gerar_fechamento(user_id: str, data_inicio: datetime, data_fim: datetime,
                     valor_por_exame: float = 50.0) -> Dict:
    """
    Gera fechamento financeiro para um usuário no período especificado
    """
    db = get_db()
    requisicao_model = Requisicao(db.requisicoes)
    laudo_model = Laudo(db.laudos)

    # Buscar requisições do usuário no período
    requisicoes = requisicao_model.find_by_user(user_id)

    # Filtrar por período e status liberado
    exames = []
    for req in requisicoes:
        req_date = req.get('created_at')
        if isinstance(req_date, str):
            try:
                req_date = datetime.fromisoformat(req_date.replace('Z', '+00:00'))
            except:
                continue

        if data_inicio <= req_date <= data_fim:
            laudo = laudo_model.find_by_requisicao(req['id'])
            if laudo and laudo.get('status') == 'liberado':
                exames.append({
                    'requisicao_id': req['id'],
                    'paciente': req.get('paciente', 'N/A'),
                    'tipo_exame': req.get('tipo_exame', 'N/A'),
                    'data': req_date,
                    'valor': valor_por_exame
                })

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


def gerar_fechamento_todos_usuarios(data_inicio: datetime, data_fim: datetime,
                                    valor_por_exame: float = 50.0) -> List[Dict]:
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
                usuario['id'],
                data_inicio,
                data_fim,
                valor_por_exame
            )
            if fechamento['quantidade_exames'] > 0:
                fechamentos.append({
                    'usuario': usuario,
                    'fechamento': fechamento
                })

    return fechamentos
