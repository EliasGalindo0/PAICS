"""
Conexão com MongoDB
"""
import os
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from dotenv import load_dotenv

load_dotenv()

# Configurações do MongoDB
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "paics_db")

_client = None
_db = None


def get_client():
    """Retorna o cliente MongoDB (singleton)"""
    global _client
    if _client is None:
        try:
            _client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            # Testar conexão
            _client.server_info()
        except ConnectionFailure:
            raise ConnectionError(
                "Não foi possível conectar ao MongoDB. "
                "Verifique se o MongoDB está rodando e se a URI está correta."
            )
    return _client


def get_db():
    """Retorna a instância do banco de dados"""
    global _db
    if _db is None:
        client = get_client()
        _db = client[MONGO_DB_NAME]
    return _db


def init_db():
    """Inicializa o banco de dados criando índices necessários"""
    db = get_db()

    # Índices para usuários
    db.users.create_index("email", unique=True)
    db.users.create_index("username", unique=True)

    # Índices para laudos
    db.laudos.create_index("requisicao_id")
    db.laudos.create_index("status")
    db.laudos.create_index("created_at")

    # Índices para requisições
    db.requisicoes.create_index("user_id")
    db.requisicoes.create_index("status")
    db.requisicoes.create_index("created_at")

    # Índices para faturas
    db.faturas.create_index("user_id")
    db.faturas.create_index("periodo")
    db.faturas.create_index("status")

    # Índices para knowledge base
    db.knowledge_base.create_index("tipo")
    db.knowledge_base.create_index("tags")

    # Índices para sessões
    db.sessions.create_index("user_id")
    db.sessions.create_index("refresh_token", unique=True)
    db.sessions.create_index("device_id")
    db.sessions.create_index("expires_at")
    db.sessions.create_index([("user_id", 1), ("active", 1)])

    # Índices para learning history
    db.learning_history.create_index("laudo_id")
    db.learning_history.create_index("requisicao_id")
    db.learning_history.create_index("rating")
    db.learning_history.create_index("modelo_usado")
    db.learning_history.create_index("usado_api_externa")
    db.learning_history.create_index("created_at")
    db.learning_history.create_index([("contexto.especie", 1), ("contexto.raca", 1)])
    db.learning_history.create_index([("rating", -1), ("created_at", -1)])

    return db
