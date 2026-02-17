"""Testes unitários da estrutura do admin dashboard (Next.js)."""
import os

import pytest

# Layout do dashboard com navegação admin
_DASHBOARD_LAYOUT = os.path.join(
    os.path.dirname(__file__), "..", "..", "web", "app", "components", "DashboardLayout.tsx"
)


@pytest.mark.unit
def test_admin_nav_contem_exames():
    """Admin deve ter opção 'Exames' na navegação."""
    with open(_DASHBOARD_LAYOUT, encoding="utf-8") as f:
        content = f.read()
    assert '"Exames"' in content
    assert "/admin/exames" in content


@pytest.mark.unit
def test_admin_nav_contem_nova_requisicao():
    """Admin deve ter opção para nova requisição na navegação."""
    with open(_DASHBOARD_LAYOUT, encoding="utf-8") as f:
        content = f.read()
    assert '"Nova Requisição"' in content
    assert "/admin/requisicoes/nova" in content


@pytest.mark.unit
def test_admin_nav_contem_knowledge_base():
    """Admin deve ter página 'Knowledge Base' na navegação."""
    with open(_DASHBOARD_LAYOUT, encoding="utf-8") as f:
        content = f.read()
    assert "Knowledge Base" in content
    assert "/admin/knowledge-base" in content


@pytest.mark.unit
def test_admin_nav_nao_contem_laudos():
    """Página Laudos foi removida; não deve existir como opção."""
    with open(_DASHBOARD_LAYOUT, encoding="utf-8") as f:
        content = f.read()
    assert ' "Laudos"' not in content
    assert '"/admin/laudos"' not in content


@pytest.mark.unit
def test_backend_usa_requisicao_model():
    """API deve usar Requisicao (requisição) no backend."""
    exames_router = os.path.join(
        os.path.dirname(__file__), "..", "..", "api", "routers", "exames.py"
    )
    with open(exames_router, encoding="utf-8") as f:
        content = f.read()
    assert "from database.models import Requisicao" in content
    assert "req_model" in content or "Requisicao" in content
