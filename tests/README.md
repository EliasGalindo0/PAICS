# Testes PAICS

## Estrutura

- `unit/` – Testes unitários (auth, models, connection)
- `e2e/` – Testes end-to-end com Playwright (login, dashboards)
- `conftest.py` – Fixtures compartilhadas

## Executar localmente

### Pré-requisitos

- MongoDB rodando (`just docker-mongodb-start` ou local)
- Python 3.12

### Instalação

```bash
pip install -r requirements-dev.txt
playwright install chromium
```

### Rodar testes

```bash
# Apenas unitários
pytest tests/unit -v

# Apenas E2E (inicia Streamlit em background)
pytest tests/e2e -v

# Todos
pytest tests/ -v
```

### Variáveis de ambiente

Os testes usam `paics_db_test` por padrão. Defina:

- `MONGO_URI` – URI do MongoDB (padrão: `mongodb://localhost:27017/`)
- `MONGO_DB_NAME` – Banco de testes (padrão: `paics_db_test`)
- `JWT_SECRET_KEY` – Para tokens (padrão: `test-secret-key-for-ci`)
- `GOOGLE_API_KEY` – Pode ser dummy em testes

## CI/CD

O workflow `.github/workflows/ci.yml` roda em todo push/PR para `main` e `develop`:

1. Inicia MongoDB (service container)
2. Executa testes unitários
3. Executa testes E2E com Playwright

Configure proteção de branch conforme `.github/BRANCH_PROTECTION.md` para exigir aprovação dos testes antes do merge.
