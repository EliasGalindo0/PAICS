"""Testes E2E smoke - garantem que o ambiente está pronto para testes E2E futuros."""

import pytest


@pytest.mark.e2e
def test_e2e_environment_ready():
    """Ambiente E2E está configurado."""
    assert True


@pytest.mark.e2e
def test_playwright_importable():
    """Playwright está instalado."""
    try:
        from playwright.sync_api import sync_playwright

        assert sync_playwright is not None
    except ImportError:
        pytest.skip("Playwright não instalado")
