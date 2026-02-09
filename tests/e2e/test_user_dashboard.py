"""Testes E2E - Dashboard do usuário."""
import pytest


@pytest.mark.e2e
def test_user_dashboard_navigation(e2e_page):
    """Após login como user, deve ver Meus Laudos, Nova Requisição, Minhas Faturas."""
    page = e2e_page
    page.wait_for_load_state("networkidle")

    # Login
    page.get_by_label("E-mail ou Usuário").fill("user")
    page.get_by_label("Senha").fill("user")
    page.get_by_role("button", name="Entrar").click()
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(3000)

    content = page.content()
    assert "Meus Laudos" in content
    assert "Nova Requisição" in content
    assert "Minhas Faturas" in content


@pytest.mark.e2e
def test_user_logout(e2e_page):
    """Botão Sair deve realizar logout e redirecionar para login."""
    page = e2e_page
    page.wait_for_load_state("networkidle")

    page.get_by_label("E-mail ou Usuário").fill("user")
    page.get_by_label("Senha").fill("user")
    page.get_by_role("button", name="Entrar").click()
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2000)

    # Clicar em Sair
    page.get_by_role("button", name="Sair").click()
    page.wait_for_timeout(3000)
    content = page.content()
    assert "Entrar" in content or "Login" in content
