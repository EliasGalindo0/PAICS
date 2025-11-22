# PAICS - Justfile para gerenciamento do projeto
# Para usar este arquivo, instale o Just: https://github.com/casey/just

# Variáveis
python := "python"
pip := "pip"
venv_dir := "venv"
python_venv := "{{venv_dir}}/bin/python"  # Linux/Mac
python_venv_win := "{{venv_dir}}/Scripts/python.exe"  # Windows
pip_venv := "{{venv_dir}}/bin/pip"  # Linux/Mac
pip_venv_win := "{{venv_dir}}/Scripts/pip.exe"  # Windows

# Detecta o sistema operacional
os := if os() == "windows" { "windows" } else { "unix" }

# Comando padrão (exibe ajuda)
default:
    @just --list

# --- Setup e Instalação ---

# Cria o ambiente virtual Python
setup:
    #!/usr/bin/env bash
    echo "🔧 Criando ambiente virtual..."
    
    # Tentar diferentes comandos Python (prioridade: py > python3 > python)
    PYTHON_CMD=""
    if command -v py &> /dev/null && py --version &> /dev/null; then
        PYTHON_CMD="py"
    elif command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v {{python}} &> /dev/null && {{python}} --version &> /dev/null 2>&1; then
        PYTHON_CMD="{{python}}"
    else
        echo "❌ Erro: Python não encontrado!"
        echo ""
        echo "Por favor, instale o Python:"
        echo "  - Windows: https://www.python.org/downloads/"
        echo "  - Linux: sudo apt install python3 python3-venv (Ubuntu/Debian)"
        echo "  - Mac: brew install python3"
        echo ""
        exit 1
    fi
    
    echo "Usando: $PYTHON_CMD"
    
    # Remover venv existente se estiver vazio ou corrompido
    if [ -d "{{venv_dir}}" ] && [ ! -d "{{venv_dir}}/Scripts" ] && [ ! -d "{{venv_dir}}/bin" ]; then
        echo "⚠️  Removendo ambiente virtual vazio/corrompido..."
        rm -rf {{venv_dir}}
    fi
    
    $PYTHON_CMD -m venv {{venv_dir}}
    
    if [ $? -eq 0 ]; then
        echo "✅ Ambiente virtual criado em {{venv_dir}}/"
        echo ""
        echo "Para ativar o ambiente virtual:"
        echo "  Windows: {{venv_dir}}\\Scripts\\activate"
        echo "  Linux/Mac: source {{venv_dir}}/bin/activate"
    else
        echo "❌ Erro ao criar ambiente virtual!"
        exit 1
    fi

# Instala todas as dependências do projeto
install:
    #!/usr/bin/env bash
    echo "📦 Instalando dependências..."
    {{pip}} install --upgrade pip
    {{pip}} install -r requirements.txt
    echo "✅ Dependências instaladas!"

# Instala dependências no ambiente virtual (Linux/Mac)
install-venv:
    #!/usr/bin/env bash
    if [ ! -d "{{venv_dir}}" ]; then
        echo "❌ Ambiente virtual não encontrado. Execute 'just setup' primeiro."
        exit 1
    fi
    echo "📦 Instalando dependências no ambiente virtual..."
    {{python_venv}} -m pip install --upgrade pip
    {{python_venv}} -m pip install -r requirements.txt
    echo "✅ Dependências instaladas!"

# Instala dependências no ambiente virtual (Windows)
install-venv-win:
    #!/usr/bin/env bash
    if [ ! -d "{{venv_dir}}" ]; then
        echo "❌ Ambiente virtual não encontrado. Execute 'just setup' primeiro."
        exit 1
    fi
    if [ ! -f "{{venv_dir}}/Scripts/python.exe" ] && [ ! -f "{{venv_dir}}/Scripts/activate" ]; then
        echo "❌ Ambiente virtual não está completo. Execute 'just setup' novamente."
        exit 1
    fi
    echo "📦 Instalando dependências no ambiente virtual..."
    {{python_venv_win}} -m pip install --upgrade pip
    {{python_venv_win}} -m pip install -r requirements.txt
    echo "✅ Dependências instaladas!"

# Setup completo: cria venv e instala dependências
init:
    #!/usr/bin/env bash
    # Verificar se Python está disponível
    if ! command -v {{python}} &> /dev/null && ! command -v python3 &> /dev/null && ! command -v py &> /dev/null; then
        echo "❌ Erro: Python não encontrado!"
        echo ""
        echo "Por favor, instale o Python ou adicione-o ao PATH."
        echo "Tente:"
        echo "  - Instalar Python de https://www.python.org/downloads/"
        echo "  - Ou usar: py -m venv venv (Windows com Python Launcher)"
        echo ""
        exit 1
    fi
    
    just setup
    
    # Aguardar um pouco para garantir que o venv foi criado
    sleep 1
    
    # Detectar SO e instalar dependências apropriadamente
    # Verificar se existe Scripts (Windows) ou bin (Unix) no venv
    if [ -d "{{venv_dir}}/Scripts" ] || [ -f "{{venv_dir}}/Scripts/activate" ]; then
        echo "📦 Detectado ambiente Windows, instalando dependências..."
        just install-venv-win
    elif [ -d "{{venv_dir}}/bin" ] || [ -f "{{venv_dir}}/bin/activate" ]; then
        echo "📦 Detectado ambiente Unix/Linux, instalando dependências..."
        just install-venv
    else
        echo "❌ Erro: Ambiente virtual não foi criado corretamente!"
        echo ""
        echo "O diretório {{venv_dir}} existe mas está vazio ou incompleto."
        echo "Possíveis causas:"
        echo "  1. Python não está instalado corretamente"
        echo "  2. Python não está no PATH"
        echo "  3. Erro ao criar o ambiente virtual"
        echo ""
        echo "Tente criar manualmente:"
        echo "  Windows: py -m venv venv"
        echo "  Linux/Mac: python3 -m venv venv"
        echo ""
        echo "Depois execute:"
        echo "  Windows: just install-venv-win"
        echo "  Linux/Mac: just install-venv"
        exit 1
    fi
    echo ""
    echo "🎉 Ambiente configurado com sucesso!"
    echo ""
    echo "⚠️  Não esqueça de configurar a GOOGLE_API_KEY:"
    echo "   export GOOGLE_API_KEY='sua_chave_aqui'"
    echo "   Ou no Windows: set GOOGLE_API_KEY=sua_chave_aqui"

# Atualiza todas as dependências para as versões mais recentes
update:
    #!/usr/bin/env bash
    echo "🔄 Atualizando dependências..."
    {{pip}} install --upgrade -r requirements.txt
    echo "✅ Dependências atualizadas!"

# --- Execução ---

# Executa o script principal (main.py)
run pdf="exame_raio_x.pdf":
    #!/usr/bin/env bash
    echo "🚀 Executando PAICS..."
    {{python}} main.py
    # Nota: O main.py usa o arquivo padrão, mas você pode editar o arquivo antes

# Executa o script interativo (run.py)
run-interactive:
    #!/usr/bin/env bash
    echo "🚀 Executando PAICS (modo interativo)..."
    {{python}} run.py

# Executa o script principal usando o ambiente virtual
run-venv pdf="exame_raio_x.pdf":
    #!/usr/bin/env bash
    if [ ! -d "{{venv_dir}}" ]; then
        echo "❌ Ambiente virtual não encontrado. Execute 'just setup' primeiro."
        exit 1
    fi
    echo "🚀 Executando PAICS no ambiente virtual..."
    {{python_venv}} main.py

# Executa o script interativo usando o ambiente virtual
run-interactive-venv:
    #!/usr/bin/env bash
    if [ ! -d "{{venv_dir}}" ]; then
        echo "❌ Ambiente virtual não encontrado. Execute 'just setup' primeiro."
        exit 1
    fi
    echo "🚀 Executando PAICS (modo interativo) no ambiente virtual..."
    {{python_venv}} run.py

# --- Desenvolvimento ---

# Verifica se as dependências estão instaladas
check-deps:
    #!/usr/bin/env bash
    # Detectar comando Python (prioridade: py > python3 > python)
    PYTHON_CMD=""
    if command -v py &> /dev/null && py --version &> /dev/null; then
        PYTHON_CMD="py"
    elif command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v {{python}} &> /dev/null && {{python}} --version &> /dev/null 2>&1; then
        PYTHON_CMD="{{python}}"
    else
        echo "❌ Erro: Python não encontrado!"
        exit 1
    fi
    
    echo "🔍 Verificando dependências..."
    $PYTHON_CMD -c "import fitz; print('✅ PyMuPDF instalado')" || echo "❌ PyMuPDF não instalado"
    $PYTHON_CMD -c "import google.generativeai; print('✅ google-generativeai instalado')" || echo "❌ google-generativeai não instalado"
    $PYTHON_CMD -c "import docx; print('✅ python-docx instalado')" || echo "❌ python-docx não instalado"
    $PYTHON_CMD -c "from PIL import Image; print('✅ Pillow instalado')" || echo "❌ Pillow não instalado"

# Verifica se a API Key está configurada (arquivo .env ou variável de ambiente)
check-api-key:
    #!/usr/bin/env bash
    echo "🔍 Verificando GOOGLE_API_KEY..."
    
    # Testar carregamento do .env
    api_key_from_env=""
    if [ -f ".env" ]; then
        echo "📄 Arquivo .env encontrado"
        # Carregar do .env usando Python
        api_key_from_env=$({{python}} -c "from dotenv import load_dotenv; import os; load_dotenv(); print(os.getenv('GOOGLE_API_KEY', ''))" 2>/dev/null)
    else
        echo "⚠️  Arquivo .env não encontrado"
        echo "   Criando .env.example se não existir..."
        if [ ! -f ".env.example" ]; then
            echo "GOOGLE_API_KEY=sua_chave_api_aqui" > .env.example
        fi
    fi
    
    # Verificar variável de ambiente do sistema
    api_key_from_system="$GOOGLE_API_KEY"
    
    # Usar a primeira que estiver configurada
    if [ -n "$api_key_from_env" ] && [ "$api_key_from_env" != "sua_chave_api_aqui" ] && [ -n "$api_key_from_env" ]; then
        api_key="$api_key_from_env"
        source="arquivo .env"
    elif [ -n "$api_key_from_system" ]; then
        api_key="$api_key_from_system"
        source="variável de ambiente do sistema"
    else
        echo "❌ GOOGLE_API_KEY não configurada"
        echo ""
        echo "Configure usando uma das opções:"
        echo "  1. Arquivo .env (recomendado):"
        echo "     cp .env.example .env"
        echo "     # Edite .env e adicione sua chave"
        echo ""
        echo "  2. Variável de ambiente:"
        echo "     export GOOGLE_API_KEY='sua_chave_aqui'  # Linux/Mac"
        echo "     set GOOGLE_API_KEY=sua_chave_aqui       # Windows CMD"
        echo "     \$env:GOOGLE_API_KEY='sua_chave_aqui'    # Windows PowerShell"
        exit 1
    fi
    
    # Verificar se é a chave padrão
    if [ "$api_key" = "sua_chave_api_aqui" ] || [ "$api_key" = "SUA_API_KEY_AQUI" ]; then
        echo "⚠️  GOOGLE_API_KEY encontrada, mas com valor padrão!"
        echo "   Edite o arquivo .env ou configure a variável de ambiente com sua chave real."
        exit 1
    fi
    
    echo "✅ GOOGLE_API_KEY configurada (fonte: $source)"
    # Mostra apenas os primeiros e últimos caracteres da chave por segurança
    if [ ${#api_key} -gt 8 ]; then
        masked="${api_key:0:4}...${api_key: -4}"
    else
        masked="****"
    fi
    echo "   Chave (mascarada): $masked"

# Verifica a configuração completa do ambiente
check:
    @just check-deps
    @echo ""
    @just check-api-key

# Formata o código Python (requer black)
format:
    #!/usr/bin/env bash
    if ! command -v black &> /dev/null; then
        echo "⚠️  Black não está instalado. Instalando..."
        {{pip}} install black
    fi
    echo "🎨 Formatando código Python..."
    black *.py
    echo "✅ Código formatado!"

# Executa linter no código (requer flake8 ou pylint)
lint:
    #!/usr/bin/env bash
    if ! command -v flake8 &> /dev/null; then
        echo "⚠️  flake8 não está instalado. Instalando..."
        {{pip}} install flake8
    fi
    echo "🔍 Executando linter..."
    flake8 *.py --max-line-length=100 --ignore=E501,W503 || true
    echo "✅ Verificação concluída!"

# --- Limpeza ---

# Remove arquivos Python temporários (__pycache__, .pyc)
clean:
    #!/usr/bin/env bash
    echo "🧹 Limpando arquivos temporários..."
    find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    find . -type f -name "*.pyo" -delete 2>/dev/null || true
    find . -type f -name "*.pyd" -delete 2>/dev/null || true
    find . -type d -name "*.egg-info" -exec rm -r {} + 2>/dev/null || true
    echo "✅ Limpeza concluída!"

# Remove o ambiente virtual
clean-venv:
    #!/usr/bin/env bash
    if [ -d "{{venv_dir}}" ]; then
        echo "🗑️  Removendo ambiente virtual..."
        rm -rf {{venv_dir}}
        echo "✅ Ambiente virtual removido!"
    else
        echo "⚠️  Ambiente virtual não encontrado."
    fi

# Limpeza completa: remove venv e arquivos temporários
clean-all:
    @just clean
    @just clean-venv
    echo "🧹 Limpeza completa concluída!"

# --- Documentação e Informação ---

# Mostra informações sobre o projeto
info:
    @echo "📋 Informações do Projeto PAICS"
    @echo ""
    @echo "Python:"
    @{{python}} --version
    @echo ""
    @echo "Pip:"
    @{{pip}} --version
    @echo ""
    @echo "Estrutura do projeto:"
    @ls -la | grep -E "^(-|d)" | head -10 || dir
    @echo ""
    @echo "Arquivos Python:"
    @ls *.py 2>/dev/null || dir *.py

# Gera lista de dependências atualizadas
freeze:
    #!/usr/bin/env bash
    echo "📌 Gerando requirements.txt com versões fixas..."
    {{pip}} freeze > requirements.freeze.txt
    echo "✅ Arquivo requirements.freeze.txt criado!"
    echo "⚠️  Este arquivo pode incluir dependências transitivas."

# --- Testes e Validação ---

# Valida se o código Python está sintaticamente correto
validate:
    #!/usr/bin/env bash
    # Detectar comando Python (prioridade: py > python3 > python)
    PYTHON_CMD=""
    if command -v py &> /dev/null && py --version &> /dev/null; then
        PYTHON_CMD="py"
    elif command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v {{python}} &> /dev/null && {{python}} --version &> /dev/null 2>&1; then
        PYTHON_CMD="{{python}}"
    else
        echo "❌ Erro: Python não encontrado!"
        exit 1
    fi
    
    echo "✅ Validando sintaxe Python..."
    $PYTHON_CMD -m py_compile main.py && echo "✅ main.py: OK"
    $PYTHON_CMD -m py_compile run.py && echo "✅ run.py: OK"
    echo "✅ Validação concluída!"

# Executa um teste rápido importando os módulos
test-import:
    #!/usr/bin/env bash
    # Detectar comando Python (prioridade: py > python3 > python)
    PYTHON_CMD=""
    if command -v py &> /dev/null && py --version &> /dev/null; then
        PYTHON_CMD="py"
    elif command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v {{python}} &> /dev/null && {{python}} --version &> /dev/null 2>&1; then
        PYTHON_CMD="{{python}}"
    else
        echo "❌ Erro: Python não encontrado!"
        exit 1
    fi
    
    echo "🧪 Testando importação de módulos..."
    $PYTHON_CMD -c "from main import VetReportGenerator, VetAIAnalyzer; print('✅ Módulos importados com sucesso!')" || echo "❌ Erro ao importar módulos"

# Testa se o arquivo .env está sendo carregado corretamente
test-env:
    #!/usr/bin/env bash
    echo "🧪 Testando carregamento do arquivo .env..."
    
    # Detectar comando Python (prioridade: py > python3 > python)
    PYTHON_CMD=""
    if command -v py &> /dev/null && py --version &> /dev/null; then
        PYTHON_CMD="py"
    elif command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v {{python}} &> /dev/null && {{python}} --version &> /dev/null 2>&1; then
        PYTHON_CMD="{{python}}"
    else
        echo "❌ Erro: Python não encontrado!"
        echo "Instale o Python ou configure-o no PATH."
        exit 1
    fi
    
    if [ -f "test_env.py" ]; then
        $PYTHON_CMD test_env.py
    else
        echo "❌ Arquivo test_env.py não encontrado"
        echo "Testando manualmente..."
        $PYTHON_CMD -c "from dotenv import load_dotenv; import os; load_dotenv(); key = os.getenv('GOOGLE_API_KEY', 'NÃO_ENCONTRADA'); print('✅ .env carregado!' if key != 'NÃO_ENCONTRADA' else '❌ GOOGLE_API_KEY não encontrada no .env')"
    fi

# --- Utilitários ---

# Lista arquivos PDF na pasta atual
list-pdfs:
    #!/usr/bin/env bash
    echo "📄 Arquivos PDF encontrados:"
    find . -maxdepth 1 -name "*.pdf" -type f 2>/dev/null || echo "Nenhum arquivo PDF encontrado."

# Mostra o tamanho do diretório de saída
show-output-size:
    #!/usr/bin/env bash
    if [ -d "laudos_com_ia" ]; then
        echo "📊 Tamanho do diretório de saída:"
        du -sh laudos_com_ia 2>/dev/null || echo "Diretório existe mas não foi possível calcular o tamanho."
    else
        echo "⚠️  Diretório 'laudos_com_ia' não existe ainda."
    fi

# --- Streamlit ---

# Executa a aplicação Streamlit
streamlit:
    #!/usr/bin/env bash
    echo "🚀 Iniciando aplicação Streamlit..."
    echo "A aplicação estará disponível em: http://localhost:8501"
    streamlit run streamlit_app.py

# Executa a aplicação Streamlit usando o ambiente virtual
streamlit-venv:
    #!/usr/bin/env bash
    if [ ! -d "{{venv_dir}}" ]; then
        echo "❌ Ambiente virtual não encontrado. Execute 'just setup' primeiro."
        exit 1
    fi
    echo "🚀 Iniciando aplicação Streamlit no ambiente virtual..."
    echo "A aplicação estará disponível em: http://localhost:8501"
    {{python_venv}} -m streamlit run streamlit_app.py

# Executa a aplicação Streamlit em modo desenvolvimento (auto-reload)
streamlit-dev:
    #!/usr/bin/env bash
    echo "🚀 Iniciando aplicação Streamlit em modo desenvolvimento..."
    echo "A aplicação estará disponível em: http://localhost:8501"
    streamlit run streamlit_app.py --server.runOnSave true

# Executa a aplicação Streamlit em uma porta específica
streamlit-port port="8501":
    #!/usr/bin/env bash
    echo "🚀 Iniciando aplicação Streamlit na porta {{port}}..."
    echo "A aplicação estará disponível em: http://localhost:{{port}}"
    streamlit run streamlit_app.py --server.port {{port}}

