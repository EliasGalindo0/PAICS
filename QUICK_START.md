# 🚀 Guia Rápido de Início - PAICS

## Passo a Passo para Começar

### 1. Instalar Dependências

```bash
pip install -r requirements.txt
```

### 2. Configurar Variáveis de Ambiente

Copie o arquivo `.env.example` para `.env`:

```bash
# Windows
copy .env.example .env

# Linux/Mac
cp .env.example .env
```

Edite o arquivo `.env` e adicione sua chave da API do Google Gemini:

```
GOOGLE_API_KEY=sua_chave_real_aqui
```

### 3. Iniciar MongoDB

#### 🐳 Opção 1: Docker (RECOMENDADO - Mais Simples)

**Pré-requisito:** Instale o [Docker Desktop](https://www.docker.com/products/docker-desktop)

```bash
# Iniciar MongoDB em container Docker
just docker-mongodb-start

# Verificar status
just docker-mongodb-status

# Parar MongoDB
just docker-mongodb-stop

# Ver logs
just docker-mongodb-logs
```

**Vantagens:**
- ✅ Não precisa instalar MongoDB localmente
- ✅ Funciona em qualquer sistema operacional
- ✅ Fácil de remover e reinstalar
- ✅ Isolado do sistema

#### 💻 Opção 2: Instalação Local

**Windows:**
- MongoDB geralmente inicia automaticamente como serviço
- Ou execute manualmente: `"C:\Program Files\MongoDB\Server\7.0\bin\mongod.exe"`
- Ou use: `just start-mongodb`

**Linux:**
```bash
sudo systemctl start mongod
```

**Mac:**
```bash
brew services start mongodb-community
```

**Verificar se está rodando:**
```bash
just check-mongodb
# ou
mongosh
```

### 4. Criar Administrador Dummy Inicial

O sistema cria automaticamente um administrador dummy para primeiro acesso:

```bash
# Criar administrador dummy (executado automaticamente pelo 'just start')
just seed-admin
```

**Credenciais do administrador dummy:**
- **Username:** `admin`
- **Senha:** `admin`

**⚠️ IMPORTANTE:**
1. Faça login com essas credenciais
2. Acesse a página "Usuários" no dashboard
3. Crie seu próprio usuário administrador
4. Exclua o usuário dummy após criar seu admin

**Alternativa (método manual):**
```bash
# Criar administrador manualmente (não recomendado)
just create-admin
```

### 5. Iniciar o Sistema

```bash
streamlit run streamlit_app.py
```

O sistema abrirá automaticamente no navegador em `http://localhost:8501`

### 6. Fazer Login

- Use as credenciais do administrador criado no passo 4
- Ou crie uma conta de usuário através da interface

## ✅ Verificação Rápida

1. ✅ MongoDB rodando? → `just check-mongodb` ou `mongosh` deve conectar
2. ✅ `.env` configurado? → Verifique se `GOOGLE_API_KEY` está preenchida
3. ✅ Admin dummy criado? → Execute `just seed-admin` (ou use `just start` que faz automaticamente)
4. ✅ Sistema iniciado? → Execute `just start` ou `streamlit run streamlit_app.py`
5. ✅ Acesse → `http://localhost:8501`
6. ✅ Login inicial → Username: `admin`, Senha: `admin`

## 🐛 Problemas Comuns

### Erro: "Não foi possível conectar ao MongoDB"
- **Se estiver usando Docker:** `just docker-mongodb-start`
- **Se estiver usando instalação local:** `just start-mongodb` ou inicie o serviço manualmente
- Verifique o status: `just check-mongodb`
- Verifique a URI no `.env` (padrão: `mongodb://localhost:27017/`)

### Erro: "API Key não configurada"
- Verifique se o arquivo `.env` existe
- Verifique se `GOOGLE_API_KEY` está preenchida

### Erro ao criar admin dummy
- Certifique-se de que o MongoDB está acessível
- Execute: `just seed-admin`
- Verifique se o banco foi inicializado

### Não consigo excluir o usuário dummy
- Certifique-se de ter criado seu próprio usuário administrador primeiro
- Você não pode excluir seu próprio usuário (faça logout e entre com outro admin)

### Erro: `cannot import name 'cygrpc' from 'grpc._cython'`
- Ocorre ao usar `google-generativeai` (Gemini) por instalação corrompida ou incompatível do grpc.
- **Solução:** Execute `just fix-grpc` no terminal (com o venv ativado).
- Ou manualmente:
  ```bash
  pip uninstall -y grpcio grpcio-tools google-generativeai
  pip cache purge
  pip install --upgrade --force-reinstall --no-cache-dir "google-generativeai>=0.3.0"
  ```

### Erro: `No module named 'numpy._core._multiarray_umath'` (ao processar DICOM)
- NumPy com Python 3.13 no Windows às vezes falha nas extensões C.
- **Solução 1:** Execute `just fix-numpy` (reinstala o NumPy).
- **Solução 2:** Se persistir, use **Python 3.11 ou 3.12** no ambiente virtual (3.13 ainda gera incompatibilidades com vários pacotes científicos).

### Erro: `No module named 'rpds.rpds'` (ao validar laudo / chromadb)
- ChromaDB (banco vetorial) depende de `rpds`; o pacote correto é `rpds-py`.
- **Solução:** Execute `just fix-rpds`. Ou manualmente: `pip install rpds-py` e `pip install --upgrade chromadb`.
- O laudo continua sendo **validado** mesmo se o banco vetorial falhar; apenas o “aprendizado” é afetado.

## 📚 Próximos Passos

Após o login, você terá acesso a:

- **Admin**: Dashboard completo com todas as funcionalidades
- **Usuário**: Envio de requisições e visualização de laudos

Consulte o `README_NOVO_SISTEMA.md` para mais detalhes.
