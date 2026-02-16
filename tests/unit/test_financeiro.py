"""Testes unitários do módulo financeiro."""
from datetime import datetime, timezone, timedelta

import pytest
from bson import ObjectId


@pytest.mark.unit
def test_gerar_fechamento_com_batch_laudos(clean_db):
    """gerar_fechamento deve usar find_by_requisicao_ids (batch) e retornar exames liberados."""
    from database.models import User, Requisicao, Laudo
    from utils.financeiro import gerar_fechamento

    user_id = User(clean_db.users).create(
        username="vet", email="vet@clinica.com", password_hash="h", role="user", nome="Vet Test"
    )
    req_model = Requisicao(clean_db.requisicoes)
    laudo_model = Laudo(clean_db.laudos)

    # Criar requisições no período (hoje)
    now_utc = datetime.now(timezone.utc)
    req_id1 = req_model.create(user_id=user_id, imagens=[], paciente="REX", tutor="Maria")
    req_id2 = req_model.create(user_id=user_id, imagens=[], paciente="Luna", tutor="João")

    # Garantir created_at no período
    for req_id in [req_id1, req_id2]:
        clean_db.requisicoes.update_one(
            {"_id": ObjectId(req_id)},
            {"$set": {"created_at": now_utc}}
        )

    # Laudo liberado só para req_id1
    laudo_model.create(
        requisicao_id=req_id1, texto="Laudo REX", texto_original="Laudo REX", status="liberado"
    )
    laudo_model.create(
        requisicao_id=req_id2, texto="Laudo Luna", texto_original="Laudo Luna", status="pendente"
    )

    data_ini = now_utc - timedelta(days=1)
    data_fim = now_utc + timedelta(days=1)

    result = gerar_fechamento(user_id, data_ini, data_fim)

    assert result["user_id"] == user_id
    assert "periodo" in result
    assert "exames" in result
    assert "valor_total" in result
    # Apenas o exame com laudo liberado deve entrar
    assert result["quantidade_exames"] == 1
    assert result["exames"][0]["paciente"] == "REX"
    assert result["exames"][0]["requisicao_id"] == req_id1


@pytest.mark.unit
def test_gerar_fechamento_lista_vazia_quando_sem_laudos_liberados(clean_db):
    """gerar_fechamento retorna quantidade_exames=0 quando não há laudos liberados no período."""
    from database.models import User, Requisicao, Laudo
    from utils.financeiro import gerar_fechamento

    user_id = User(clean_db.users).create(
        username="u", email="u@t.com", password_hash="h", role="user"
    )
    req_model = Requisicao(clean_db.requisicoes)
    laudo_model = Laudo(clean_db.laudos)

    req_id = req_model.create(user_id=user_id, imagens=[], paciente="X")
    laudo_model.create(requisicao_id=req_id, texto="Pendente", texto_original="Pendente", status="pendente")

    now_utc = datetime.now(timezone.utc)
    clean_db.requisicoes.update_one(
        {"_id": ObjectId(req_id)},
        {"$set": {"created_at": now_utc}}
    )

    data_ini = now_utc - timedelta(days=1)
    data_fim = now_utc + timedelta(days=1)

    result = gerar_fechamento(user_id, data_ini, data_fim)

    assert result["quantidade_exames"] == 0
    assert result["exames"] == []
    assert result["valor_total"] == 0.0
