"""Testes E2E - Dashboard do administrador."""
import pytest


@pytest.mark.e2e
def test_admin_dashboard_sections(e2e_page):
    """Admin deve ver Requisições, Laudos, Usuários, Clínicas."""
    page = e2e_page
    page.wait_for_load_state("networkidle")

    page.get_by_label("E-mail ou Usuário").fill("admin")
    page.get_by_label("Senha").fill("admin")
    page.get_by_role("button", name="Entrar").click()
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(3000)

    content = page.content()
    assert "Requisições" in content
    assert "Laudos" in content
    assert "Usuários" in content
    assert "Clínicas" in content
