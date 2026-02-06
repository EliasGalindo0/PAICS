# 📋 Variáveis de Ambiente - PAICS

Este documento lista todas as variáveis de ambiente suportadas pelo projeto PAICS.

## 🔴 Variáveis Obrigatórias

### `GOOGLE_API_KEY`
- **Descrição**: Chave da API do Google Gemini para gerar laudos automaticamente
- **Tipo**: String
- **Onde obter**: https://makersuite.google.com/app/apikey
- **Exemplo**: `GOOGLE_API_KEY=AIzaSyC...`

**⚠️ Sem esta variável, o projeto não conseguirá gerar laudos automaticamente.**

### `MONGO_URI`
- **Descrição**: URI de conexão do MongoDB
- **Tipo**: String
- **Padrão**: `mongodb://localhost:27017/` (MongoDB local ou Docker)
- **MongoDB Atlas (gratuito)**:
  1. Crie uma conta em [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
  2. Crie um cluster **M0 (Free)** e um usuário de banco
  3. Em **Database** → **Connect** → **Drivers** copie a connection string
  4. Substitua `<password>` pela senha do usuário e opcionalmente adicione o nome do banco: `mongodb+srv://usuario:senha@cluster0.xxxxx.mongodb.net/paics_db?retryWrites=true&w=majority`
- **Exemplo (Atlas)**: `MONGO_URI=mongodb+srv://paics:minhasenha@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority`

### `MONGO_DB_NAME`
- **Descrição**: Nome do banco de dados
- **Tipo**: String
- **Padrão**: `paics_db`
- **Exemplo**: `MONGO_DB_NAME=paics_db`

## 🟢 Variáveis Opcionais

### Configuração da IA

#### `GEMINI_MODEL_NAME`
- **Descrição**: Modelo da IA Gemini a ser utilizado
- **Tipo**: String
- **Padrão**: `gemini-1.5-pro-latest`
- **Opções disponíveis**:
  - `gemini-1.5-pro-latest` - Modelo mais avançado (recomendado)
  - `gemini-1.5-flash` - Mais rápido, menos preciso
  - `gemini-2.0-flash-exp` - Versão experimental mais recente
- **Exemplo**: `GEMINI_MODEL_NAME=gemini-1.5-flash`

### Configuração de Diretórios

#### `OUTPUT_DIR`
- **Descrição**: Diretório onde os laudos serão salvos (modo linha de comando)
- **Tipo**: String (caminho)
- **Padrão**: `laudos_com_ia`
- **Exemplo**: `OUTPUT_DIR=/var/paics/laudos`

#### `STREAMLIT_TEMP_DIR`
- **Descrição**: Diretório temporário usado pela interface Streamlit
- **Tipo**: String (caminho)
- **Padrão**: `temp_laudos`
- **Exemplo**: `STREAMLIT_TEMP_DIR=/tmp/paics`

### Configuração de Processamento de PDF

#### `PDF_ZOOM_FACTOR`
- **Descrição**: Fator de zoom para processamento de PDF (melhora qualidade da imagem)
- **Tipo**: Float
- **Padrão**: `2.0`
- **Valores recomendados**: `1.0` a `3.0`
  - Valores maiores = melhor qualidade, mas arquivos maiores e processamento mais lento
  - Valores menores = processamento mais rápido, mas qualidade reduzida
- **Exemplo**: `PDF_ZOOM_FACTOR=2.5`

### Configuração de Documento Word

#### `IMAGE_WIDTH_INCHES`
- **Descrição**: Largura das imagens inseridas no documento Word (em polegadas)
- **Tipo**: Float
- **Padrão**: `5.5`
- **Valores recomendados**: `4.0` a `7.0`
- **Exemplo**: `IMAGE_WIDTH_INCHES=6.0`

#### `DOC_FONT_NAME`
- **Descrição**: Nome da fonte usada no documento Word
- **Tipo**: String
- **Padrão**: `Calibri`
- **Opções**: Qualquer fonte instalada no sistema (Calibri, Arial, Times New Roman, etc.)
- **Exemplo**: `DOC_FONT_NAME=Arial`

#### `DOC_FONT_SIZE`
- **Descrição**: Tamanho da fonte usada no documento Word (em pontos)
- **Tipo**: Integer
- **Padrão**: `11`
- **Valores recomendados**: `10` a `14`
- **Exemplo**: `DOC_FONT_SIZE=12`

## 📝 Exemplo de Arquivo .env Completo

```bash
# ==========================================
# PAICS - Variáveis de Ambiente
# ==========================================

# REQUERIDA
GOOGLE_API_KEY=sua_chave_api_aqui

# MongoDB (em produção use Atlas; local/Docker use o padrão)
MONGO_URI=mongodb://localhost:27017/
MONGO_DB_NAME=paics_db

# Configuração da IA
GEMINI_MODEL_NAME=gemini-1.5-pro-latest

# Diretórios
OUTPUT_DIR=laudos_com_ia
STREAMLIT_TEMP_DIR=temp_laudos

# Processamento de PDF
PDF_ZOOM_FACTOR=2.0

# Documento Word
IMAGE_WIDTH_INCHES=5.5
DOC_FONT_NAME=Calibri
DOC_FONT_SIZE=11
```

## 🚀 Como Configurar

### Método 1: Arquivo .env (Recomendado)

1. Copie o arquivo `.env.example` para `.env`:
```bash
cp .env.example .env
```

2. Edite o arquivo `.env` e configure as variáveis necessárias:
```bash
nano .env  # ou use seu editor favorito
```

### Método 2: Variáveis de Ambiente do Sistema

#### Linux/Mac:
```bash
export GOOGLE_API_KEY="sua_chave_aqui"
export GEMINI_MODEL_NAME="gemini-1.5-pro-latest"
```

#### Windows (PowerShell):
```powershell
$env:GOOGLE_API_KEY="sua_chave_aqui"
$env:GEMINI_MODEL_NAME="gemini-1.5-pro-latest"
```

#### Windows (CMD):
```cmd
set GOOGLE_API_KEY=sua_chave_aqui
set GEMINI_MODEL_NAME=gemini-1.5-pro-latest
```

## ✅ Verificação

Para verificar se as variáveis estão configuradas corretamente:

```bash
# Usando Just
just check-api-key
just test-env

# Ou manualmente
python test_env.py
```

## 📚 Referências

- [Documentação do Google Gemini](https://ai.google.dev/docs)
- [python-dotenv](https://pypi.org/project/python-dotenv/)
- [Streamlit Configuration](https://docs.streamlit.io/library/advanced-features/configuration)

