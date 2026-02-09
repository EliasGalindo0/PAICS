"""Testes unitários da conexão MongoDB."""
import pytest


@pytest.mark.unit
def test_connection_get_client(db):
    """get_client deve retornar cliente MongoDB conectado."""
    from database.connection import get_client

    client = get_client()
    assert client is not None
    info = client.server_info()
    assert "version" in info


@pytest.mark.unit
def test_connection_get_db(db):
    """get_db deve retornar banco de dados."""
    from database.connection import get_db, MONGO_DB_NAME

    database = get_db()
    assert database is not None
    assert database.name == MONGO_DB_NAME
