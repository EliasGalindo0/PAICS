"""Testes unitários de configuração."""
import pytest


@pytest.mark.unit
def test_uploads_dir_definido():
    """UPLOADS_DIR está definido e contém 'uploads'."""
    from config import UPLOADS_DIR

    assert UPLOADS_DIR is not None
    assert isinstance(UPLOADS_DIR, str)
    assert "uploads" in UPLOADS_DIR
