# PAICS - Sistema de Análise de Imagens Veterinárias

Sistema completo de gestão de laudos veterinários com autenticação, dashboards, IA (Google Gemini), MongoDB e ChromaDB.

## Visão Geral

- **Usuários**: Enviar requisições com imagens (JPG, PNG, DICOM), acompanhar status e baixar laudos em PDF quando liberados.
- **Administradores**: Criar usuários e clínicas, revisar requisições, gerar/editar/validar/liberar laudos com IA, gerenciar financeiro e Knowledge Base.

**Stack**: Python, Streamlit, MongoDB, ChromaDB, Google Gemini, fpdf2.

---

## Requisitos

- Python 3.11 ou 3.12
- MongoDB (Docker ou local)
- Chave da API Google Gemini
- Just (opcional, recomendado) – [Instalar Just](https://github.com/casey/just)

---

## Instalação Rápida

### 1. Clone e ambiente

```bash
cd PAICS
just init
```

### 2. Variáveis de ambiente

Copie `.env.example` para `.env` e configure:

```bash
cp .env.example .env   # Linux/Mac
copy .env.example .env # Windows
```

Edite `.env`:
```
GOOGLE_API_KEY=sua_chave_aqui
MONGO_URI=mongodb://localhost:27017/
MONGO_DB_NAME=paics_db
```

### 3. MongoDB

**Opção Docker (recomendado):**
```bash
just docker-mongodb-start
just docker-mongodb-status
```

**Opção local:** Instale MongoDB e inicie o serviço, ou use `just start-mongodb`.

### 4. Seed inicial

```bash
just seed-admin
```

Credenciais do admin dummy: **admin** / **admin**.

⚠️ Faça login, crie seu próprio admin na página Usuários e exclua o dummy.

### 5. Iniciar

```bash
just streamlit
# ou: streamlit run streamlit_app.py
```

Acesse `http://localhost:8501`.

---

## Variáveis de Ambiente

| Variável | Descrição |
|----------|-----------|
| `GOOGLE_API_KEY` | Chave da API Gemini (obrigatória para laudos) |
| `MONGO_URI` | Connection string do MongoDB (ex.: `mongodb://localhost:27017/`) |
| `MONGO_DB_NAME` | Nome do banco (padrão: `paics_db`) |
| `JWT_SECRET_KEY` | Chave para tokens (opcional; gerada se ausente) |
| `GEMINI_MODEL_NAME` | Modelo Gemini (ex.: `gemini-2.5-pro`) |

---

## MongoDB Atlas no Railway

Se usar **MongoDB Atlas** (em vez do MongoDB do Railway):

1. **Network Access** no Atlas: **Add IP Address** → **Allow Access from Anywhere** (`0.0.0.0/0`) para permitir conexões do Railway.
2. **Connection string**:
   - **Cluster padrão**: `mongodb+srv://user:password@cluster.xxx.mongodb.net/?retryWrites=true&w=majority`
   - **Atlas SQL** (Data Federation): `mongodb://user:password@atlas-sql-xxx.a.query.mongodb.net/paics_db?ssl=true&authSource=admin`
3. **TLSV1_ALERT_INTERNAL_ERROR**: se o handshake SSL falhar, defina no Railway: **MONGO_TLS_RELAXED** = `1`.

---

## Deploy no Railway

1. Adicione o serviço MongoDB no Railway.
2. No serviço da aplicação PAICS, em **Variables**:
   - **MONGO_URI** = Referência → serviço MongoDB → **MONGO_URL**
3. Use `MONGO_URL` privado (não `MONGO_PUBLIC_URL`) para evitar egress fees.
4. **Uploads persistentes** (imagens das requisições) — **obrigatório** para ver imagens em produção:
   - Em **Volumes**, crie um volume e monte em `/data` (caminho exato).
   - Em **Variables**, adicione: **UPLOADS_DIR** = `/data/uploads`
   - Sem o Volume em `/data`, as imagens somem a cada redeploy e o logo pode falhar.
5. Faça redeploy.

---

## Uso

### Login

- **Admin**: credenciais criadas pelo seed ou `create-admin`.
- **Usuário**: credenciais criadas pelo admin (não há “Criar Conta” para usuário).

### Dashboard Admin

- **Requisições**: Listar, filtrar, criar/editar laudos.
- **Laudos**: Editar, validar, liberar; visualizar imagens.
- **Usuários**: Criar, ativar/desativar, excluir; vincular a clínicas.
- **Clínicas**: Cadastrar clínicas (nome, CNPJ, endereço, telefone, e-mail), veterinários; ativar/desativar ou excluir.
- **Financeiro**: Gerar fechamentos e faturas.
- **Knowledge Base**: PDFs, prompts, orientações.

### Dashboard Usuário

- **Meus Laudos**: Listar requisições/laudos, filtrar, baixar PDF quando liberado.
- **Nova Requisição**: Formulário (paciente, tutor, espécie, tipo de exame, etc.), upload de imagens, envio.
- **Minhas Faturas**: Consultar faturas.

### Guia para Clientes (administrador pode compartilhar)

1. Login com credenciais fornecidas.
2. Primeiro acesso: alterar senha temporária.
3. **Nova Requisição**: Preencher dados, anexar imagens, enviar.
4. **Meus Laudos**: Acompanhar e baixar PDF quando liberado.
5. **Minhas Faturas**: Consultar faturas.
6. Em caso de erro: reportar ao administrador com mensagem e contexto.

---

## Testes

```bash
pip install -r requirements-dev.txt
playwright install chromium
just test-unit   # apenas unitários
just test-e2e    # E2E (requer MongoDB)
just test        # todos
```

Os testes usam `paics_db_test`. O CI (`.github/workflows/ci.yml`) roda em push/PR para `main` e `develop`. Para exigir aprovação antes do merge: em **Settings → Branches**, crie regra para `main` com **Require status checks** e adicione o job `test`.

---

## Comandos Just

| Comando | Descrição |
|---------|-----------|
| `just init` | Setup completo (venv, deps) |
| `just streamlit` | Inicia a aplicação web |
| `just seed-admin` | Cria admin e clínica dummy |
| `just docker-mongodb-start` | Sobe MongoDB em Docker |
| `just docker-mongodb-stop` | Para MongoDB |
| `just check-mongodb` | Verifica conexão MongoDB |
| `just test` | Executa todos os testes |
| `just test-unit` | Testes unitários |
| `just test-e2e` | Testes E2E |
| `just fix-grpc` | Corrige erro cygrpc |
| `just fix-numpy` | Corrige erro numpy |
| `just fix-rpds` | Corrige ChromaDB/rpds |
| `just fix-bson` | Reinstala pymongo |

Mais: `just --list`.

---

## Estrutura do Projeto

```
PAICS/
├── streamlit_app.py      # Entrada web
├── pages/
│   ├── login.py
│   ├── admin_dashboard.py
│   └── user_dashboard.py
├── auth/                 # Autenticação, JWT
├── database/             # MongoDB, modelos
├── vector_db/            # ChromaDB (laudos validados)
├── ai/                   # Gemini, DICOM
├── knowledge_base/       # PDFs, prompts, orientações
├── utils/                # Financeiro, PDF, etc.
├── scripts/              # seed_admin, create_admin, reset_db
├── tests/                # Unit + E2E
├── docker-compose.yml    # MongoDB
├── Dockerfile            # Deploy
└── justfile
```

---

## Banco de Dados

- **MongoDB**: `users`, `clinicas`, `veterinarios`, `requisicoes`, `laudos`, `faturas`, `sessions`, `knowledge_base`.
- **ChromaDB**: Laudos validados (vetorial); persistido em `vector_db/`.

---

## Sistema de Aprendizado

Laudos validados são indexados no ChromaDB. O sistema pode buscar casos similares (espécie, raça, região, suspeita) para suportar geração futura. Variáveis opcionais: `USE_LOCAL_MODEL`, `LOCAL_MODEL_TYPE`, `OLLAMA_BASE_URL`, etc.

---

## Troubleshooting

| Erro | Solução |
|------|---------|
| MongoDB não conecta | `just docker-mongodb-start` ou `just start-mongodb`; conferir `MONGO_URI` |
| API Key não configurada | Preencher `GOOGLE_API_KEY` no `.env` |
| `cygrpc` / grpc | `just fix-grpc` |
| `numpy._core._multiarray_umath` | `just fix-numpy` ou usar Python 3.11/3.12 |
| `rpds.rpds` / ChromaDB | `just fix-rpds` |
| Não excluir dummy | Criar outro admin, fazer logout, excluir o dummy com o novo admin |

---

## Aviso

Os laudos são **sugestões** e devem ser **revisados por Médico Veterinário** antes do uso. A IA é ferramenta de apoio, não substitui o julgamento clínico.

---

## Licença

Projeto para uso interno.
