"""Testes unitários dos modelos de dados."""
import pytest


@pytest.mark.unit
def test_user_create_and_find(clean_db):
    """User.create e find_by_* devem funcionar."""
    from auth.auth_utils import hash_password
    from database.models import User

    user_model = User(clean_db.users)
    uid = user_model.create(
        username="joao",
        email="joao@test.local",
        password_hash=hash_password("senha"),
        role="user",
        nome="João Silva",
    )
    assert uid

    u = user_model.find_by_id(uid)
    assert u
    assert u["username"] == "joao"
    assert u["email"] == "joao@test.local"
    assert u["nome"] == "João Silva"
    assert u["role"] == "user"

    u2 = user_model.find_by_username("joao")
    assert u2 and u2["id"] == uid
    u3 = user_model.find_by_email("joao@test.local")
    assert u3 and u3["id"] == uid


@pytest.mark.unit
def test_clinica_create_and_find(clean_db):
    """Clinica.create e find_by_id devem funcionar."""
    from database.models import Clinica

    model = Clinica(clean_db.clinicas)
    cid = model.create(
        nome="Clínica XYZ",
        cnpj="12.345.678/0001-00",
        endereco="Rua A, 1",
        telefone="11999999999",
        email="contato@xyz.local",
    )
    assert cid
    c = model.find_by_id(cid)
    assert c
    assert c["nome"] == "Clínica XYZ"
    assert c["endereco"] == "Rua A, 1"
    assert c["telefone"] == "11999999999"


@pytest.mark.unit
def test_clinica_delete(clean_db):
    """Clinica.delete deve remover a clínica e limpar referências."""
    from auth.auth_utils import hash_password
    from database.models import Clinica, User, Veterinario

    clinica_model = Clinica(clean_db.clinicas)
    user_model = User(clean_db.users)
    vet_model = Veterinario(clean_db.veterinarios)

    cid = clinica_model.create(nome="Clínica Del", email="x@x.local")
    user_model.create(
        username="u1", email="u1@x.local", password_hash=hash_password("x"),
        role="user", clinica_id=cid,
    )
    vet_model.create(nome="V1", crmv="CRMV", clinica_id=cid)

    ok = clinica_model.delete(cid)
    assert ok
    assert clinica_model.find_by_id(cid) is None
    u = user_model.find_by_username("u1")
    assert u and u.get("clinica_id") is None
    vets = list(clean_db.veterinarios.find({"clinica_id": cid}))
    assert len(vets) == 0


@pytest.mark.unit
def test_requisicao_create(clean_db):
    """Requisicao.create deve funcionar."""
    from auth.auth_utils import hash_password
    from database.models import User, Requisicao

    user_model = User(clean_db.users)
    uid = user_model.create(
        username="rq", email="rq@t.local", password_hash=hash_password("x"),
        role="user",
    )
    req_model = Requisicao(clean_db.requisicoes)
    rid = req_model.create(
        user_id=uid,
        imagens=[],
        paciente="REX",
        tutor="MARIA",
        clinica="Clínica X",
        tipo_exame="raio-x",
    )
    assert rid
    r = req_model.find_by_id(rid)
    assert r
    assert r["paciente"] == "REX"
    assert r["tutor"] == "MARIA"
