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

### 4. Criar Usuário Administrador

```bash
python scripts/create_admin.py
```

Siga as instruções para criar o primeiro administrador.

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
3. ✅ Admin criado? → Execute `just create-admin` ou `python scripts/create_admin.py`
4. ✅ Sistema iniciado? → Execute `just start` ou `streamlit run streamlit_app.py`
5. ✅ Acesse → `http://localhost:8501`

## 🐛 Problemas Comuns

### Erro: "Não foi possível conectar ao MongoDB"
- **Se estiver usando Docker:** `just docker-mongodb-start`
- **Se estiver usando instalação local:** `just start-mongodb` ou inicie o serviço manualmente
- Verifique o status: `just check-mongodb`
- Verifique a URI no `.env` (padrão: `mongodb://localhost:27017/`)

### Erro: "API Key não configurada"
- Verifique se o arquivo `.env` existe
- Verifique se `GOOGLE_API_KEY` está preenchida

### Erro ao criar admin
- Certifique-se de que o MongoDB está acessível
- Verifique se o banco foi inicializado

## 📚 Próximos Passos

Após o login, você terá acesso a:

- **Admin**: Dashboard completo com todas as funcionalidades
- **Usuário**: Envio de requisições e visualização de laudos

Consulte o `README_NOVO_SISTEMA.md` para mais detalhes.
