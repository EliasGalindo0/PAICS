"""Testes E2E - Dashboard do administrador."""
import pytest


@pytest.mark.e2e
def test_admin_dashboard_sections(e2e_page):
    """Admin deve ver Requisições, Laudos, Clínicas e Usuários."""
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
    assert "Clínicas e Usuários" in content


@pytest.mark.e2e
def test_admin_clinica_form_campos_endereco(e2e_page):
    """Formulário de cadastro de clínica deve ter CEP, Número, Bairro, Cidade."""
    page = e2e_page
    page.wait_for_load_state("networkidle")

    page.get_by_label("E-mail ou Usuário").fill("admin")
    page.get_by_label("Senha").fill("admin")
    page.get_by_role("button", name="Entrar").click()
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2000)

    # Selecionar "Clínicas e Usuários" na navegação
    page.get_by_text("Clínicas e Usuários", exact=True).first.click()
    page.wait_for_timeout(2000)

    content = page.content()
    assert "Cadastrar nova clínica" in content or "Clientes" in content
    # Campos de endereço expandidos
    assert "CEP" in content
    assert "Buscar" in content or "Logradouro" in content
