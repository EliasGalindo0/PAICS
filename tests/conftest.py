"""Fixtures compartilhados para testes."""
import os
import pytest


@pytest.fixture
def db():
    """Retorna a instância do banco de dados (pode usar MONGO_DB_NAME de .env ou paics_test)."""
    from database.connection import get_db

    return get_db()


@pytest.fixture
def clean_db(db):
    """Banco com coleções limpas para testes isolados. Limpa após o teste."""
    collections_to_clean = [
        "users",
        "clinicas",
        "veterinarios",
        "requisicoes",
        "laudos",
        "sessions",
        "faturas",
    ]
    for coll_name in collections_to_clean:
        if coll_name in db.list_collection_names():
            db[coll_name].delete_many({})
    yield db
    # Limpar novamente após o teste (opcional, garante isolamento)
    for coll_name in collections_to_clean:
        if coll_name in db.list_collection_names():
            db[coll_name].delete_many({})
