"""Testes unitários de autenticação."""
import pytest


@pytest.mark.unit
def test_hash_password():
    """Hash de senha deve ser diferente da senha original e repetível com mesmo salt."""
    from auth.password import hash_password, verify_password

    senha = "x"  # placeholder apenas para teste (não é credencial real)
    h = hash_password(senha)
    assert h != senha
    assert ":" in h
    assert verify_password(senha, h)
    assert not verify_password("y", h)


@pytest.mark.unit
def test_verify_password_invalido():
    """Verificação com hash inválido deve retornar False."""
    from auth.password import verify_password

    assert not verify_password("a", "hash-invalido-sem-doispontos")
    assert not verify_password("a", "")


@pytest.mark.unit
def test_jwt_generate_and_verify():
    """JWT deve gerar e verificar tokens corretamente."""
    from auth.jwt_utils import generate_access_token, verify_token

    token = generate_access_token(user_id="u1", username="usr", role="role")
    assert token
    decoded = verify_token(token)
    assert decoded
    assert decoded.get("user_id") == "u1"
    assert decoded.get("username") == "usr"
    assert decoded.get("role") == "role"
