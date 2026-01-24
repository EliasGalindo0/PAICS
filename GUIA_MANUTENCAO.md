# Guia de Manutenção - PAICS

**Sistema de Análise de Imagens Veterinárias com IA**

Este documento descreve a estrutura do projeto, a função dos principais arquivos e diretórios, os fluxos de negócio e orientações para manutenção.

---

## 1. Visão geral do projeto

O **PAICS** é um sistema web (Streamlit) para:

- **Usuários**: enviar requisições de laudos com imagens (JPG, PNG, DICOM), acompanhar status e baixar laudos em PDF quando liberados.
- **Administradores**: criar usuários (com senha temporária), revisar requisições, ver imagens, editar/validar/liberar laudos gerados por IA (Google Gemini), gerenciar financeiro e knowledge base.

**Stack principal**: Python, Streamlit, MongoDB, ChromaDB (vetorial), Google Gemini (IA), fpdf2 (PDF).

---

## 2. Estrutura de diretórios

```
PAICS/
├── auth/                 # Autenticação e sessão
├── ai/                   # IA (Gemini) e carregamento de imagens/DICOM
├── database/             # Conexão e modelos MongoDB
├── vector_db/            # ChromaDB para laudos (aprendizado)
├── knowledge_base/       # KB (PDFs, prompts, orientações)
├── pages/                # Páginas Streamlit (login, dashboards)
├── scripts/              # Scripts CLI (seed admin, create admin)
├── utils/                # Utilitários (ex.: financeiro)
├── uploads/              # Imagens enviadas por usuários (por user_id)
├── .streamlit/           # Config Streamlit
├── streamlit_app.py      # Entrada da aplicação web
├── main.py               # CLI / VetReportGenerator (PDF, Word)
├── run_paics.py          # Launcher com verificação de API key
├── justfile              # Receitas Just (setup, MongoDB, fix-*, etc.)
├── requirements.txt      # Dependências Python
├── docker-compose.yml   # MongoDB em Docker
└── *.md                  # Documentação (README, QUICK_START, ENV_VARIABLES, etc.)
```

---

## 3. Principais arquivos e responsabilidades

### 3.1 Entrada e configuração

| Arquivo | Responsabilidade |
|--------|-------------------|
| **`streamlit_app.py`** | Ponto de entrada da aplicação web. Verifica autenticação, redireciona para `pages/login.py`, `pages/admin_dashboard.py` ou `pages/user_dashboard.py`. |
| **`main.py`** | Ferramenta de linha de comando e classe `VetReportGenerator`: processamento de PDFs/Word, uso de `ai.analyzer` para IA. **Não** é o entry point do Streamlit. |
| **`run_paics.py`** | Launcher alternativo (tkinter, verificação de API key, abertura do navegador). Usado em fluxos de execução específicos. |
| **`config.py`** | Configurações centralizadas (API, diretórios, fontes, OCR) a partir de `.env`. |
| **`.streamlit/config.toml`** | Configuração do Streamlit (tema, servidor, porta). |

### 3.2 Autenticação

| Arquivo | Responsabilidade |
|--------|-------------------|
| **`auth/auth_utils.py`** | Hash/verificação de senha, criação/limpeza de sessão (`st.session_state`), `login_user`, `get_current_user`, `require_auth`. Usado em login e dashboards. |

### 3.3 Banco de dados (MongoDB)

| Arquivo | Responsabilidade |
|--------|-------------------|
| **`database/connection.py`** | Conexão singleton com MongoDB (`get_client`, `get_db`), `init_db` (índices). Usa `MONGO_URI` e `MONGO_DB_NAME` do `.env`. |
| **`database/models.py`** | Modelos: **User**, **Requisicao**, **Laudo**, **Fatura**, **KnowledgeBaseItem**. CRUD e regras de negócio (ex.: status de laudo, `find_by_user`). |

### 3.4 IA e imagens

| Arquivo | Responsabilidade |
|--------|-------------------|
| **`ai/analyzer.py`** | **`VetAIAnalyzer`**: envia imagens ao Gemini e gera texto do laudo. **`load_dicom_image`**: converte DICOM em PIL. **`load_images_for_analysis`**: carrega JPG/PNG/DICOM a partir de caminhos. Usado em user_dashboard, admin_dashboard e main. |

### 3.5 Banco vetorial (ChromaDB)

| Arquivo | Responsabilidade |
|--------|-------------------|
| **`vector_db/vector_store.py`** | **`VectorStore`**: persiste laudos no ChromaDB, `add_laudo`, `search_similar`. Usado ao **validar** laudo no admin (opcional; em caso de erro rpds/chromadb, a validação segue). |

### 3.6 Páginas Streamlit

| Arquivo | Responsabilidade |
|--------|-------------------|
| **`pages/login.py`** | Tela de login (email/senha), chama `login_user`, redireciona para admin ou user dashboard. Inicializa DB com `init_db`. |
| **`pages/user_dashboard.py`** | Dashboard do usuário: **Meus Laudos** (lista, filtros, notificação de liberados, download PDF), **Nova Requisição** (formulário, upload, criação de requisição + laudo IA em background), **Minhas Faturas**. Primeira aba padrão: Meus Laudos. |
| **`pages/admin_dashboard.py`** | Dashboard do admin: **Requisições** (listar, Criar/Editar Laudo), **Laudos** (editar, ver imagens, Validar, Liberar), **Usuários** (criar com senha temporária, detalhes, ativar/desativar), **Financeiro**, **Knowledge Base**. Exibe imagens da requisição na tela de edição de laudo. |

### 3.7 Scripts e seed

| Arquivo | Responsabilidade |
|--------|-------------------|
| **`scripts/seed_admin.py`** | Cria usuário admin *dummy* (`admin` / `admin`) para primeiro acesso. Executado por `just start` (ou `just seed-admin`). |
| **`scripts/create_admin.py`** | Criação interativa de admin via CLI (alternativa ao seed). |

### 3.8 Utilitários e conhecimento

| Arquivo | Responsabilidade |
|--------|-------------------|
| **`utils/financeiro.py`** | Lógica de fechamentos, faturas e painel financeiro (usado no admin). |
| **`knowledge_base/kb_manager.py`** | Gestão da base de conhecimento (PDFs, prompts, orientações). |

### 3.9 Infra e automação

| Arquivo | Responsabilidade |
|--------|-------------------|
| **`justfile`** | Receitas Just: `setup`, `init`, `streamlit`, `docker-mongodb-*`, `seed-admin`, `create-admin`, `start`, `fix-grpc`, `fix-numpy`, `fix-rpds`, `fix-bson`, `fix-pillow`, `check-mongodb`, etc. |
| **`docker-compose.yml`** | Sobe MongoDB em container para desenvolvimento/testes. |
| **`requirements.txt`** | Dependências Python (streamlit, pymongo, google-generativeai, fpdf2, pydicom, chromadb, etc.). |

---

## 4. Fluxos principais

### 4.1 Login e rotas

1. Usuário acessa a app → `streamlit_app.py` verifica `st.session_state.authenticated`.
2. Se não autenticado → `st.switch_page("pages/login.py")`.
3. Em `login.py`: formulário (email/senha) → `login_user` → em sucesso, `create_session` e redirecionamento:
   - **admin** → `pages/admin_dashboard.py`
   - **user** → `pages/user_dashboard.py`

### 4.2 Requisição e laudo (usuário)

1. Usuário em **Nova Requisição**: preenche paciente, tutor, clínica, tipo de exame, observações, envia imagens.
2. Submit: grava imagens em `uploads/{user_id}/`, cria **Requisicao** no MongoDB, chama **IA** (se `GOOGLE_API_KEY` ok) para gerar laudo em background, cria **Laudo** com status `pendente`.
3. Usuário não vê mensagens de IA nem prévia do laudo; apenas confirmação de requisição enviada.
4. Em **Meus Laudos**, usuário vê todos os laudos (incl. pendentes); quando **liberado**, pode baixar PDF. Notificação ao abrir a aba se houver laudos recém liberados.

### 4.3 Revisão e liberação (admin)

1. Admin em **Requisições**: vê requisições, clica em **Criar/Editar Laudo** → define `editing_requisicao` e orienta a ir em **Laudos**.
2. Em **Laudos**, se `editing_requisicao` está definido: carrega requisição e laudo, **exibe as imagens** para conferência, mostra editor de texto.
3. Se não existe laudo: pode **Gerar Laudo com IA** ou criar placeholder. Em seguida: **Salvar**, **Validar** (opcionalmente VectorStore), **Liberar** ou **Cancelar**.
4. Ao **Liberar**: status do laudo → `liberado`, requisição → `liberado`; usuário passa a ver o laudo e o botão de download PDF.

---

## 5. Banco de dados

### 5.1 MongoDB

- **Conexão**: `database/connection.py`, variáveis `MONGO_URI` e `MONGO_DB_NAME` (ex.: `paics_db`).
- **Coleções**: `users`, `requisicoes`, `laudos`, `faturas`, etc., conforme `database/models.py`.
- **Índices**: criados em `init_db()` (email, username, user_id, status, created_at, etc.).

### 5.2 ChromaDB (vetorial)

- **Uso**: laudos validados são adicionados ao VectorStore para buscas similares.
- **Persistência**: diretório `vector_db/` (ex.: `chroma.sqlite3`).
- **Import**: feito de forma *lazy* no admin (ao validar) para evitar carregar chromadb/numpy em todos os acessos. Em falhas (ex.: rpds), a validação segue sem vetorial.

---

## 6. Variáveis de ambiente

Principais variáveis (detalhes em **`ENV_VARIABLES.md`**):

| Variável | Uso |
|----------|-----|
| **`GOOGLE_API_KEY`** | API Gemini; obrigatória para geração de laudos por IA. |
| **`GEMINI_MODEL_NAME`** | Modelo Gemini (ex.: `gemini-2.5-flash`). |
| **`MONGO_URI`** | URI do MongoDB (ex.: `mongodb://localhost:27017/`). |
| **`MONGO_DB_NAME`** | Nome do banco (ex.: `paics_db`). |

Arquivo **`.env`** na raiz (copiar de **`.env.example`** e ajustar).

---

## 7. Comandos Just úteis

| Comando | Descrição |
|--------|-----------|
| **`just start`** | Setup completo: venv, deps, Docker MongoDB, seed-admin, Streamlit. |
| **`just seed-admin`** | Cria admin dummy (`admin` / `admin`). |
| **`just streamlit`** | Sobe a aplicação Streamlit. |
| **`just docker-mongodb-start`** | Sobe MongoDB via Docker. |
| **`just docker-mongodb-stop`** | Para o container MongoDB. |
| **`just check-mongodb`** | Verifica se o MongoDB está acessível. |
| **`just fix-grpc`** | Reinstala grpcio/google-generativeai (erro `cygrpc`). |
| **`just fix-numpy`** | Reinstala numpy (erro `_multiarray_umath`). |
| **`just fix-rpds`** | Reinstala rpds-py e chromadb (erro `rpds.rpds`). |
| **`just fix-bson`** | Remove bson conflitante e reinstala pymongo. |
| **`just fix-pillow`** | Reinstala Pillow (erro `_imaging`). |

Mais comandos: `just --list`.

---

## 8. Manutenção e troubleshooting

### 8.1 Onde alterar funcionalidades

- **Fluxo de login / sessão**: `auth/auth_utils.py`, `pages/login.py`.
- **Regras de usuário e requisição**: `database/models.py` (User, Requisicao, Laudo).
- **Geração de laudo por IA**: `ai/analyzer.py` (prompt, modelo, pós-processamento).
- **Interface usuário**: `pages/user_dashboard.py` (requisição, laudos, PDF, notificações).
- **Interface admin**: `pages/admin_dashboard.py` (requisições, laudos, imagens, usuários, financeiro, KB).
- **Geração de PDF**: `user_dashboard` (fpdf2) e, se aplicável, `main.VetReportGenerator`.

### 8.2 Erros comuns

- **MongoDB não conecta**: usar `just docker-mongodb-start` ou MongoDB local; conferir `MONGO_URI` e `just check-mongodb`. Ver **`QUICK_START.md`**.
- **`ModuleNotFoundError: rpds.rpds` / chromadb**: `just fix-rpds` ou instalar `rpds-py` e atualizar chromadb. VectorStore é opcional na validação.
- **`numpy._core._multiarray_umath`**: `just fix-numpy` ou usar Python 3.11/3.12. Ver **`QUICK_START.md`**.
- **`cannot import '_imaging'` (PIL)**: `just fix-pillow` ou reinstalar Pillow.
- **DICOM**: carregamento em `ai/analyzer.py` (`load_dicom_image`, `load_images_for_analysis`). Erros de VOI LUT têm fallback para normalização simples.

### 8.3 Uploads e armazenamento

- Imagens das requisições: **`uploads/{user_id}/`** (caminhos absolutos em ambiente de desenvolvimento).
- Laudos em PDF gerados sob demanda no user dashboard; não há pasta global de laudos exportados.

---

## 9. Documentação relacionada

| Documento | Conteúdo |
|-----------|----------|
| **`README.md`** | Visão geral, instalação e uso do projeto. |
| **`README_NOVO_SISTEMA.md`** | Descrição do sistema com auth, dashboards, MongoDB, ChromaDB, KB, financeiro. |
| **`QUICK_START.md`** | Passo a passo rápido, Docker MongoDB, seed-admin, troubleshooting (grpc, numpy, rpds, etc.). |
| **`ENV_VARIABLES.md`** | Lista e descrição das variáveis de ambiente. |
| **`GUIA_MANUTENCAO.md`** | Este guia (estrutura, arquivos, fluxos, manutenção). |

---

## 10. Resumo rápido por camada

| Camada | Onde está | Responsabilidade |
|--------|-----------|-------------------|
| **Entrada web** | `streamlit_app.py` | Roteamento inicial por autenticação. |
| **Telas** | `pages/*.py` | Login, dashboards usuário e admin. |
| **Auth** | `auth/auth_utils.py` | Login, sessão, hash de senha. |
| **Dados** | `database/*.py` | MongoDB, modelos (User, Requisicao, Laudo, Fatura). |
| **IA** | `ai/analyzer.py` | Gemini, DICOM, geração de laudo. |
| **Vetorial** | `vector_db/vector_store.py` | ChromaDB, laudos validados. |
| **CLI / relatórios** | `main.py`, `run_paics.py` | Geração de laudos via CLI e launcher. |
| **Automação** | `justfile` | Setup, MongoDB, Streamlit, correções (fix-*). |

Este guia deve ser atualizado quando forem adicionados novos módulos, fluxos ou comandos relevantes para manutenção.
