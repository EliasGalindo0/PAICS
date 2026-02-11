"""Testes unitários dos modelos de dados."""
import pytest


@pytest.mark.unit
def test_requisicao_create(clean_db):
    """Requisicao.create deve criar documento e retornar ID."""
    from database.models import User, Requisicao

    # Criar usuário para vincular
    user_id = User(clean_db.users).create(
        username="test_user",
        email="test@test.com",
        password_hash="hash",
        role="user",
        nome="Test User",
    )
    req_model = Requisicao(clean_db.requisicoes)

    req_id = req_model.create(
        user_id=user_id,
        imagens=["/tmp/img1.jpg"],
        paciente="REX",
        tutor="MARIA",
        clinica="Clinica Teste",
        tipo_exame="raio-x",
    )

    assert req_id is not None
    assert len(req_id) == 24  # ObjectId hex length

    found = req_model.find_by_id(req_id)
    assert found is not None
    assert found.get("paciente") == "REX"
    assert found.get("tutor") == "MARIA"
    assert found.get("tipo_exame") == "raio-x"
    assert found.get("status") == "pendente"


@pytest.mark.unit
def test_requisicao_find_by_user(clean_db):
    """Requisicao.find_by_user deve retornar requisições do usuário."""
    from database.models import User, Requisicao

    user_id = User(clean_db.users).create(
        username="user1", email="u1@t.com", password_hash="h", role="user"
    )
    req_model = Requisicao(clean_db.requisicoes)

    req_model.create(user_id=user_id, imagens=[], paciente="A")
    req_model.create(user_id=user_id, imagens=[], paciente="B")

    reqs = req_model.find_by_user(user_id)
    assert len(reqs) == 2
    pacientes = {r.get("paciente") for r in reqs}
    assert pacientes == {"A", "B"}


@pytest.mark.unit
def test_requisicao_update_status(clean_db):
    """Requisicao.update_status deve atualizar o status."""
    from database.models import User, Requisicao

    user_id = User(clean_db.users).create(
        username="u", email="u@t.com", password_hash="h", role="user"
    )
    req_model = Requisicao(clean_db.requisicoes)
    req_id = req_model.create(user_id=user_id, imagens=[], paciente="P")

    ok = req_model.update_status(req_id, "liberado")
    assert ok is True

    found = req_model.find_by_id(req_id)
    assert found.get("status") == "liberado"


@pytest.mark.unit
def test_laudo_find_by_requisicao(clean_db):
    """Laudo.find_by_requisicao deve retornar laudo vinculado à requisição."""
    from database.models import User, Requisicao, Laudo

    user_id = User(clean_db.users).create(
        username="u", email="u@t.com", password_hash="h", role="user"
    )
    req_model = Requisicao(clean_db.requisicoes)
    laudo_model = Laudo(clean_db.laudos)

    req_id = req_model.create(user_id=user_id, imagens=[], paciente="X")
    laudo_id = laudo_model.create(
        requisicao_id=req_id, texto="Laudo teste", texto_original="Laudo teste"
    )

    found = laudo_model.find_by_requisicao(req_id)
    assert found is not None
    assert found.get("id") == laudo_id
    assert found.get("requisicao_id") == req_id
    assert found.get("texto") == "Laudo teste"
