"""Testes E2E - Login e autenticação."""
import pytest


@pytest.mark.e2e
def test_login_page_loads(e2e_page):
    """Página de login deve carregar e exibir formulário."""
    page = e2e_page
    page.wait_for_load_state("networkidle")
    # Aguardar o Streamlit renderizar o formulário (conteúdo vem via WebSocket)
    page.get_by_label("E-mail ou Usuário").wait_for(state="visible", timeout=15000)
    assert page.get_by_role("button", name="Entrar").is_visible()


@pytest.mark.e2e
def test_login_admin_success(e2e_page):
    """Login com admin/admin deve redirecionar para dashboard admin."""
    page = e2e_page
    page.wait_for_load_state("networkidle")

    # Preencher formulário de login (Streamlit usa labels)
    page.get_by_label("E-mail ou Usuário").fill("admin")
    page.get_by_label("Senha").fill("admin")
    page.get_by_role("button", name="Entrar").click()

    # Aguardar redirect e verificar dashboard admin
    page.wait_for_timeout(4000)
    content = page.content()
    assert "Requisições" in content or "Clínicas" in content or "Usuários" in content or "admin" in content.lower()


@pytest.mark.e2e
def test_login_user_success(e2e_page):
    """Login com user/user deve redirecionar para dashboard do usuário."""
    page = e2e_page
    page.wait_for_load_state("networkidle")

    page.get_by_label("E-mail ou Usuário").fill("user")
    page.get_by_label("Senha").fill("user")
    page.get_by_role("button", name="Entrar").click()

    page.wait_for_timeout(4000)
    content = page.content()
    assert "Meus Laudos" in content or "Nova Requisição" in content or "Minhas Faturas" in content


@pytest.mark.e2e
def test_login_invalid_credentials(e2e_page):
    """Login com credenciais inválidas deve mostrar erro."""
    page = e2e_page
    page.wait_for_load_state("networkidle")

    page.get_by_label("E-mail ou Usuário").fill("invalido")
    page.get_by_label("Senha").fill("senhaerrada")
    page.get_by_role("button", name="Entrar").click()

    page.wait_for_timeout(2000)
    content = page.content()
    # Deve permanecer na página de login ou mostrar mensagem de erro
    assert "Login" in content or "login" in content or "incorreto" in content.lower() or "inválid" in content.lower() or "erro" in content.lower()
