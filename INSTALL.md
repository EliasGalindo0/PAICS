# Guia de Instalação - PAICS

## Método Rápido (com Just) ⚡

Se você tem o [Just](https://github.com/casey/just) instalado (ferramenta de comandos), pode configurar tudo com um único comando:

```bash
just init
```

Isso criará o ambiente virtual, instalará todas as dependências e configurará o projeto automaticamente.

Depois, configure sua API Key:
```bash
# Linux/Mac:
export GOOGLE_API_KEY="sua_chave_aqui"

# Windows (PowerShell):
$env:GOOGLE_API_KEY="sua_chave_aqui"

# Windows (CMD):
set GOOGLE_API_KEY=sua_chave_aqui
```

Para ver todos os comandos disponíveis:
```bash
just --list
```

**Vantagens do Just:**
- ✅ Um único comando para setup completo
- ✅ Comandos padronizados e documentados
- ✅ Verificação automática do ambiente
- ✅ Comandos de desenvolvimento integrados

## Método Manual (Passo a Passo)

### 1. Pré-requisitos

Certifique-se de ter instalado:
- Python 3.8 ou superior
- pip (gerenciador de pacotes Python)
- Git (opcional, para controle de versão)
- Just (opcional, mas recomendado) - [Instalar Just](https://github.com/casey/just)

### 2. Configuração do Ambiente Virtual

```bash
# Criar ambiente virtual
python -m venv venv

# Ativar ambiente virtual
# Windows:
venv\Scripts\activate

# Linux/Mac:
source venv/bin/activate
```

### 3. Instalação das Dependências

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configuração da API Key

#### Opção 1: Arquivo .env (Recomendado)

1. Copie o arquivo `.env.example` para `.env`:
```bash
# Linux/Mac:
cp .env.example .env

# Windows (PowerShell):
Copy-Item .env.example .env

# Windows (CMD):
copy .env.example .env
```

2. Edite o arquivo `.env` e adicione sua chave da API:
```
GOOGLE_API_KEY=sua_chave_real_aqui
```

**Vantagem:** O arquivo `.env` é automaticamente carregado pelo projeto usando `python-dotenv`. Não é necessário configurar variáveis de ambiente do sistema.

#### Opção 2: Variável de Ambiente do Sistema

**Windows (PowerShell):**
```powershell
$env:GOOGLE_API_KEY="sua_chave_api_aqui"
```

**Windows (CMD):**
```cmd
set GOOGLE_API_KEY=sua_chave_api_aqui
```

**Linux/Mac:**
```bash
export GOOGLE_API_KEY="sua_chave_api_aqui"
```

### 5. Obter Chave da API do Google Gemini

1. Acesse: https://makersuite.google.com/app/apikey
2. Faça login com sua conta Google
3. Clique em "Create API Key"
4. Copie a chave gerada
5. Use a chave conforme as opções acima

### 6. Testar a Instalação

```bash
python main.py
```

Se configurado corretamente, o sistema processará o arquivo PDF especificado no código.

### 7. Solução de Problemas

**Erro: "No module named 'fitz'"**
- Execute: `pip install PyMuPDF`

**Erro: "No module named 'google.generativeai'"**
- Execute: `pip install google-generativeai`

**Erro: "No module named 'docx'"**
- Execute: `pip install python-docx`

**Erro de API Key:**
- Verifique se a variável de ambiente está configurada corretamente
- Teste com: `echo $GOOGLE_API_KEY` (Linux/Mac) ou `echo %GOOGLE_API_KEY%` (Windows)

