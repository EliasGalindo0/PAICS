"""
Fixtures compartilhadas para testes.
"""
import os
import sys
import subprocess
import time
import signal

import pytest

# Garantir que o projeto está no path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# Variáveis de ambiente para testes (MongoDB local/CI)
@pytest.fixture(scope="session")
def env_for_tests():
    """Variáveis de ambiente para rodar testes."""
    return {
        "MONGO_URI": os.getenv("MONGO_URI", "mongodb://localhost:27017/"),
        "MONGO_DB_NAME": os.getenv("MONGO_DB_NAME", "paics_db_test"),
        "JWT_SECRET_KEY": os.getenv("JWT_SECRET_KEY", "test-secret-key-for-ci"),
        "GOOGLE_API_KEY": os.getenv("GOOGLE_API_KEY", "dummy-key-for-tests"),
    }


@pytest.fixture(scope="session")
def set_test_env(env_for_tests):
    """Define variáveis de ambiente antes dos testes."""
    original = {}
    for k, v in env_for_tests.items():
        original[k] = os.environ.get(k)
        os.environ[k] = v
    yield
    for k, v in original.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v


@pytest.fixture
def db(set_test_env):
    """Banco de dados para testes (usa paics_db_test)."""
    from database.connection import get_db, init_db
    init_db()
    return get_db()


@pytest.fixture
def clean_db(db):
    """Limpa coleções de teste antes do teste."""
    for coll_name in ["users", "clinicas", "veterinarios", "requisicoes", "laudos", "sessions", "faturas"]:
        if coll_name in db.list_collection_names():
            db[coll_name].delete_many({})
    yield db


@pytest.fixture
def seed_test_data(clean_db):
    """Insere admin e usuário de teste."""
    from auth.auth_utils import hash_password
    from database.models import User, Clinica, Veterinario

    user_model = User(clean_db.users)
    clinica_model = Clinica(clean_db.clinicas)
    vet_model = Veterinario(clean_db.veterinarios)

    # Admin
    admin_id = user_model.create(
        username="admin",
        email="admin@paics.local",
        password_hash=hash_password("admin"),
        role="admin",
        nome="Admin Teste",
        ativo=True,
        primeiro_acesso=False,
        clinica_id=None,
    )

    # Clínica + veterinário + usuário
    clinica_id = clinica_model.create(
        nome="Clínica Teste",
        cnpj="",
        endereco="",
        telefone="",
        email="contato@teste.local",
        ativa=True,
    )
    vet_model.create(nome="Dr. Vet", crmv="CRMV-1", clinica_id=clinica_id, email="vet@teste.local")
    user_id = user_model.create(
        username="user",
        email="user@paics.local",
        password_hash=hash_password("user"),
        role="user",
        nome="User Teste",
        ativo=True,
        primeiro_acesso=False,
        clinica_id=clinica_id,
    )

    return {"admin_id": admin_id, "user_id": user_id, "clinica_id": clinica_id}


# --- Fixtures para E2E ---
@pytest.fixture(scope="session")
def streamlit_server():
    """Inicia o servidor Streamlit em background para testes E2E."""
    port = 8501
    cmd = [
        sys.executable, "-m", "streamlit", "run",
        "streamlit_app.py",
        "--server.port", str(port),
        "--server.headless", "true",
        "--server.runOnSave", "false",
        "--browser.gatherUsageStats", "false",
    ]
    env = os.environ.copy()
    env["MONGO_URI"] = env.get("MONGO_URI", "mongodb://localhost:27017/")
    env["MONGO_DB_NAME"] = os.getenv("MONGO_DB_NAME", "paics_db_test")
    env["JWT_SECRET_KEY"] = env.get("JWT_SECRET_KEY", "test-secret-key-for-ci")
    env["GOOGLE_API_KEY"] = env.get("GOOGLE_API_KEY", "dummy-key-for-tests")

    proc = subprocess.Popen(
        cmd,
        cwd=PROJECT_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    # Aguardar servidor subir
    for _ in range(60):
        try:
            import urllib.request
            urllib.request.urlopen(f"http://localhost:{port}/", timeout=1)
            break
        except Exception:
            time.sleep(1)
    else:
        proc.terminate()
        raise RuntimeError("Streamlit não iniciou em 60s")
    yield f"http://localhost:{port}"
    proc.terminate()
    proc.wait(timeout=10)


@pytest.fixture
def e2e_page(streamlit_server, seed_test_data):
    """Página Playwright pronta para testes E2E (com seed já aplicado)."""
    pytest.importorskip("playwright")
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(streamlit_server, wait_until="networkidle", timeout=30000)
        yield page
        browser.close()
