"""
Conexão com MongoDB
"""
import os
from urllib.parse import quote_plus

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from dotenv import load_dotenv
import certifi

load_dotenv()


# Host da app no Railway; se a URI apontar para ele, é erro de config (deve apontar para o MongoDB)
_RAILWAY_APP_HOST = "paics.railway.internal"


def _get_mongo_uri() -> str:
    """Monta MONGO_URI a partir de variáveis de ambiente.
    No Railway: se MONGO_URL/MONGO_URI apontarem para paics.railway.internal (host da app),
    ignora e monta a URI a partir de MONGOHOST/MONGOUSER/MONGOPASSWORD (referências ao serviço MongoDB).
    """
    url_from_mongo = os.getenv("MONGO_URL") or ""
    uri_from_app = os.getenv("MONGO_URI") or ""
    # Rejeitar URI que aponta para o host da aplicação (Connection refused)
    def _uri_ok(uri: str) -> bool:
        if not uri or "${{" in uri:
            return False
        if _RAILWAY_APP_HOST in uri:
            return False
        return True
    if _uri_ok(url_from_mongo):
        return url_from_mongo.rstrip("/") + "/"
    if _uri_ok(uri_from_app):
        return uri_from_app.rstrip("/") + "/"
    # Montar a partir de MONGOHOST etc. (cada um como referência ao serviço MongoDB no Railway)
    host = os.getenv("MONGOHOST")
    if host and "${{" not in host and _RAILWAY_APP_HOST not in host:
        user = os.getenv("MONGOUSER", "")
        password = os.getenv("MONGOPASSWORD", "")
        port = os.getenv("MONGOPORT", "27017")
        if user and password:
            auth = f"{quote_plus(user)}:{quote_plus(password)}@"
        else:
            auth = ""
        return f"mongodb://{auth}{host}:{port}/"
    return "mongodb://localhost:27017/"


MONGO_URI = _get_mongo_uri()
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "paics_db")

_client = None
_db = None


def _is_atlas_uri(uri: str) -> bool:
    """True se a URI for do MongoDB Atlas (host mongodb.net)."""
    return "mongodb.net" in (uri or "")


def get_client():
    """Retorna o cliente MongoDB (singleton)"""
    global _client
    if _client is None:
        try:
            kwargs = {"serverSelectionTimeoutMS": 10000}
            if _is_atlas_uri(MONGO_URI):
                kwargs["tls"] = True
                strict = os.getenv("MONGO_TLS_STRICT", "").strip().lower() in ("1", "true", "yes")
                if strict:
                    kwargs["tlsCAFile"] = certifi.where()
                else:
                    # Railway/containers: TLSV1_ALERT_INTERNAL_ERROR com CA/certifi.
                    # SSL sem verificação de certificado usa fluxo que costuma funcionar.
                    kwargs["tlsAllowInvalidCertificates"] = True
                    kwargs["tlsAllowInvalidHostnames"] = True
            _client = MongoClient(MONGO_URI, **kwargs)
            # Testar conexão
            _client.server_info()
        except ConnectionFailure as e:
            raise ConnectionError(
                "Não foi possível conectar ao MongoDB. "
                "Verifique se o MongoDB está rodando e se a URI está correta. "
                f"Detalhe: {e}"
            ) from e
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
    db.requisicoes.create_index("clinica_id")
    db.requisicoes.create_index("veterinario_id")

    # Índices para clínicas e veterinários
    db.clinicas.create_index("ativa")
    db.clinicas.create_index("nome")
    db.veterinarios.create_index("clinica_id")
    db.veterinarios.create_index("ativo")

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

    # Índices para correções de laudo (aprendizado com correções do especialista)
    db.correcoes_laudo.create_index("laudo_id")
    db.correcoes_laudo.create_index("requisicao_id")
    db.correcoes_laudo.create_index("categoria")
    db.correcoes_laudo.create_index("created_at")
    db.correcoes_laudo.create_index([("contexto.especie", 1), ("contexto.raca", 1), ("contexto.regiao_estudo", 1)])

    return db
