"""Testes unitários da estrutura do admin_dashboard."""
import os

import pytest

_ADMIN_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "pages", "admin_dashboard.py")


@pytest.mark.unit
def test_admin_nav_contem_exames():
    """Admin deve ter opção 'Exames' na navegação."""
    with open(_ADMIN_PATH, encoding="utf-8") as f:
        content = f.read()
    assert '"Exames"' in content
    assert 'page == "Exames"' in content


@pytest.mark.unit
def test_admin_nav_contem_novo_exame():
    """Admin deve ter opção para novo exame/requisição na navegação."""
    with open(_ADMIN_PATH, encoding="utf-8") as f:
        content = f.read()
    # Pode ser "Novo Exame" ou "Nova Requisição" dependendo da nomenclatura
    assert '"Novo Exame"' in content or '"Nova Requisição"' in content


@pytest.mark.unit
def test_admin_nav_contem_knowledge_base_aprendizado():
    """Admin deve ter página unificada 'Knowledge Base e Aprendizado'."""
    with open(_ADMIN_PATH, encoding="utf-8") as f:
        content = f.read()
    assert "Knowledge Base e Aprendizado" in content


@pytest.mark.unit
def test_admin_nav_nao_contem_laudos():
    """Página Laudos foi removida; não deve existir como opção."""
    with open(_ADMIN_PATH, encoding="utf-8") as f:
        content = f.read()
    assert 'page == "Laudos"' not in content
    assert '["Laudos"' not in content


@pytest.mark.unit
def test_admin_usa_requisicao_model():
    """Admin deve usar Requisicao (requisição) no backend."""
    with open(_ADMIN_PATH, encoding="utf-8") as f:
        content = f.read()
    assert "from database.models import Requisicao" in content
    assert "requisicao_model" in content
    assert "db.requisicoes" in content
