"""Testes unitários da integração ViaCEP."""
from unittest.mock import patch, MagicMock

import pytest

from utils.viacep import buscar_cep


@pytest.mark.unit
def test_buscar_cep_valido():
    """buscar_cep com CEP válido retorna dict com logradouro, bairro, cidade."""
    resp = MagicMock()
    resp.json.return_value = {
        "cep": "01310-100",
        "logradouro": "Avenida Paulista",
        "bairro": "Bela Vista",
        "localidade": "São Paulo",
        "uf": "SP",
    }
    resp.raise_for_status = MagicMock()

    with patch("requests.get", return_value=resp):
        result = buscar_cep("01310100")

    assert result is not None
    assert result["cep"] == "01310-100"
    assert result["logradouro"] == "Avenida Paulista"
    assert result["bairro"] == "Bela Vista"
    assert result["cidade"] == "São Paulo"
    assert result["uf"] == "SP"


@pytest.mark.unit
def test_buscar_cep_formatado():
    """buscar_cep aceita CEP com formatação (00000-000)."""
    resp = MagicMock()
    resp.json.return_value = {
        "cep": "01310-100",
        "logradouro": "Avenida Paulista",
        "bairro": "Bela Vista",
        "localidade": "São Paulo",
        "uf": "SP",
    }
    resp.raise_for_status = MagicMock()

    with patch("requests.get", return_value=resp):
        result = buscar_cep("01310-100")

    assert result is not None
    assert result["logradouro"] == "Avenida Paulista"


@pytest.mark.unit
def test_buscar_cep_invalido_retorna_none():
    """buscar_cep com CEP inexistente retorna None (API retorna erro)."""
    resp = MagicMock()
    resp.json.return_value = {"erro": True}
    resp.raise_for_status = MagicMock()

    with patch("requests.get", return_value=resp):
        result = buscar_cep("00000000")

    assert result is None


@pytest.mark.unit
def test_buscar_cep_campo_vazio_retorna_none():
    """buscar_cep com string vazia retorna None."""
    result = buscar_cep("")
    assert result is None


@pytest.mark.unit
def test_buscar_cep_poucos_digitos_retorna_none():
    """buscar_cep com menos de 8 dígitos retorna None."""
    result = buscar_cep("12345")
    assert result is None


@pytest.mark.unit
def test_buscar_cep_muitos_digitos_retorna_none():
    """buscar_cep com mais de 8 dígitos retorna None."""
    result = buscar_cep("123456789")
    assert result is None


@pytest.mark.unit
def test_buscar_cep_excecao_rede_retorna_none():
    """buscar_cep com falha de rede/timeout retorna None."""
    with patch("requests.get", side_effect=Exception("Network error")):
        result = buscar_cep("01310100")

    assert result is None


@pytest.mark.unit
def test_buscar_cep_none_input_retorna_none():
    """buscar_cep com input None retorna None."""
    result = buscar_cep(None)
    assert result is None
