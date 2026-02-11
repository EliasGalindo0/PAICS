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
def test_user_formulario_requisicao_botao_enviar(e2e_page):
    """Formulário Nova Requisição deve ter botão Enviar Requisição em destaque."""
    page = e2e_page
    page.wait_for_load_state("networkidle")

    page.get_by_label("E-mail ou Usuário").fill("user")
    page.get_by_label("Senha").fill("user")
    page.get_by_role("button", name="Entrar").click()
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2000)

    # Acessar Nova Requisição
    page.get_by_text("Nova Requisição").first.click()
    page.wait_for_timeout(2000)

    content = page.content()
    assert "Enviar Requisição" in content


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
