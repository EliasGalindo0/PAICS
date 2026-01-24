# PAICS - Justfile para gerenciamento do projeto
# Para usar este arquivo, instale o Just: https://github.com/casey/just

# Variáveis
python := "python"
pip := "pip"
venv_dir := "venv"
# NOTE: use Just path-join so values expand correctly (Just does not re-interpolate {{ }} inside variables)
python_venv := venv_dir / "bin/python"  # Linux/Mac
python_venv_win := venv_dir / "Scripts/python.exe"  # Windows
pip_venv := venv_dir / "bin/pip"  # Linux/Mac
pip_venv_win := venv_dir / "Scripts/pip.exe"  # Windows

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
    if [ -d "{{venv_dir}}" ]; then
        # Verificar se streamlit está instalado
        if [ "{{os}}" = "windows" ]; then
            if ! "{{python_venv_win}}" -m streamlit --version &> /dev/null; then
                echo "❌ Streamlit não está instalado no ambiente virtual."
                echo "📦 Instalando dependências..."
                "{{python_venv_win}}" -m pip install --upgrade pip
                "{{python_venv_win}}" -m pip install -r requirements.txt
                echo "✅ Dependências instaladas!"
            fi
            "{{python_venv_win}}" -m streamlit run streamlit_app.py
        else
            if ! "{{python_venv}}" -m streamlit --version &> /dev/null; then
                echo "❌ Streamlit não está instalado no ambiente virtual."
                echo "📦 Instalando dependências..."
                "{{python_venv}}" -m pip install --upgrade pip
                "{{python_venv}}" -m pip install -r requirements.txt
                echo "✅ Dependências instaladas!"
            fi
            "{{python_venv}}" -m streamlit run streamlit_app.py
        fi
    else
        echo "⚠️  Ambiente virtual não encontrado. Usando Python do sistema..."
        {{python}} -m streamlit run streamlit_app.py
    fi

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
    if [ -d "{{venv_dir}}" ]; then
        if [ "{{os}}" = "windows" ]; then
            if ! "{{python_venv_win}}" -m streamlit --version &> /dev/null; then
                echo "❌ Streamlit não está instalado no ambiente virtual."
                echo "📦 Instalando dependências..."
                "{{python_venv_win}}" -m pip install --upgrade pip
                "{{python_venv_win}}" -m pip install -r requirements.txt
                echo "✅ Dependências instaladas!"
            fi
            "{{python_venv_win}}" -m streamlit run streamlit_app.py --server.runOnSave true
        else
            if ! "{{python_venv}}" -m streamlit --version &> /dev/null; then
                echo "❌ Streamlit não está instalado no ambiente virtual."
                echo "📦 Instalando dependências..."
                "{{python_venv}}" -m pip install --upgrade pip
                "{{python_venv}}" -m pip install -r requirements.txt
                echo "✅ Dependências instaladas!"
            fi
            "{{python_venv}}" -m streamlit run streamlit_app.py --server.runOnSave true
        fi
    else
        echo "⚠️  Ambiente virtual não encontrado. Usando Python do sistema..."
        {{python}} -m streamlit run streamlit_app.py --server.runOnSave true
    fi

# Executa a aplicação Streamlit em uma porta específica
streamlit-port port="8501":
    #!/usr/bin/env bash
    echo "🚀 Iniciando aplicação Streamlit na porta {{port}}..."
    echo "A aplicação estará disponível em: http://localhost:{{port}}"
    if [ -d "{{venv_dir}}" ]; then
        if [ "{{os}}" = "windows" ]; then
            if ! "{{python_venv_win}}" -m streamlit --version &> /dev/null; then
                echo "❌ Streamlit não está instalado no ambiente virtual."
                echo "📦 Instalando dependências..."
                "{{python_venv_win}}" -m pip install --upgrade pip
                "{{python_venv_win}}" -m pip install -r requirements.txt
                echo "✅ Dependências instaladas!"
            fi
            "{{python_venv_win}}" -m streamlit run streamlit_app.py --server.port {{port}}
        else
            if ! "{{python_venv}}" -m streamlit --version &> /dev/null; then
                echo "❌ Streamlit não está instalado no ambiente virtual."
                echo "📦 Instalando dependências..."
                "{{python_venv}}" -m pip install --upgrade pip
                "{{python_venv}}" -m pip install -r requirements.txt
                echo "✅ Dependências instaladas!"
            fi
            "{{python_venv}}" -m streamlit run streamlit_app.py --server.port {{port}}
        fi
    else
        echo "⚠️  Ambiente virtual não encontrado. Usando Python do sistema..."
        {{python}} -m streamlit run streamlit_app.py --server.port {{port}}
    fi

streamlit-kill port="8501":
    #!/usr/bin/env bash
    set -euo pipefail
    echo "🛑 Encerrando Streamlit na porta {{port}}..."

    if [ "{{os}}" = "windows" ]; then
        # Pega PID(s) LISTENING na porta e força encerramento
        pids=$(netstat -ano 2>/dev/null | findstr "LISTENING" | findstr ":{{port}}" | awk '{print $NF}' | tr -d '\r' | sort -u)
        if [ -z "${pids:-}" ]; then
            echo "ℹ️  Nenhum processo LISTENING encontrado na porta {{port}}."
            exit 0
        fi
        echo "Encontrado(s) PID(s): $pids"
        for pid in $pids; do
            taskkill /PID "$pid" /F >/dev/null 2>&1 || true
        done
        echo "✅ Encerrado."
    else
        if command -v lsof >/dev/null 2>&1; then
            pids=$(lsof -ti ":{{port}}" 2>/dev/null | sort -u | tr '\n' ' ')
            if [ -z "${pids:-}" ]; then
                echo "ℹ️  Nenhum processo usando a porta {{port}}."
                exit 0
            fi
            echo "Encontrado(s) PID(s): $pids"
            kill -9 $pids 2>/dev/null || true
            echo "✅ Encerrado."
        else
            echo "❌ 'lsof' não encontrado. Instale lsof ou encerre manualmente o processo."
            exit 1
        fi
    fi

# --- Docker e MongoDB ---

# Verifica se Docker está instalado e rodando
check-docker:
    #!/usr/bin/env bash
    echo "🔍 Verificando Docker..."
    if ! command -v docker &> /dev/null; then
        echo "❌ Docker não está instalado"
        echo ""
        echo "Instale o Docker:"
        echo "  Windows/Mac: https://www.docker.com/products/docker-desktop"
        echo "  Linux: https://docs.docker.com/engine/install/"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        echo "❌ Docker não está rodando"
        echo ""
        echo "Inicie o Docker Desktop ou o serviço Docker"
        exit 1
    fi
    
    echo "✅ Docker está instalado e rodando"
    docker --version

# Inicia MongoDB em container Docker
docker-mongodb-start:
    #!/usr/bin/env bash
    echo "🐳 Iniciando MongoDB em container Docker..."
    
    if ! just check-docker 2>/dev/null; then
        echo "❌ Docker não está disponível"
        exit 1
    fi
    
    if [ ! -f "docker-compose.yml" ]; then
        echo "❌ Arquivo docker-compose.yml não encontrado"
        exit 1
    fi
    
    # Verificar se o container já está rodando
    if docker ps --filter "name=paics-mongodb" --filter "status=running" --quiet | grep -q .; then
        echo "✅ Container MongoDB já está rodando"
        just docker-mongodb-status
        exit 0
    fi
    
    # Iniciar container
    docker-compose up -d mongodb
    
    echo "⏳ Aguardando MongoDB inicializar..."
    sleep 5
    
    # Verificar se está saudável
    max_attempts=30
    attempt=0
    while [ $attempt -lt $max_attempts ]; do
        if docker exec paics-mongodb mongosh --eval "db.runCommand('ping')" --quiet &>/dev/null; then
            echo "✅ MongoDB está rodando e acessível!"
            just docker-mongodb-status
            exit 0
        fi
        attempt=$((attempt + 1))
        echo "   Tentativa $attempt/$max_attempts..."
        sleep 2
    done
    
    echo "⚠️  MongoDB iniciado, mas ainda não está totalmente pronto"
    echo "   Aguarde alguns segundos e verifique: just docker-mongodb-status"
    just docker-mongodb-status

# Para MongoDB em container Docker
docker-mongodb-stop:
    #!/usr/bin/env bash
    echo "🛑 Parando MongoDB em container Docker..."
    
    if [ ! -f "docker-compose.yml" ]; then
        echo "❌ Arquivo docker-compose.yml não encontrado"
        exit 1
    fi
    
    docker-compose stop mongodb
    echo "✅ Container MongoDB parado"

# Remove MongoDB em container Docker (e volumes)
docker-mongodb-remove:
    #!/usr/bin/env bash
    echo "🗑️  Removendo container MongoDB e volumes..."
    
    if [ ! -f "docker-compose.yml" ]; then
        echo "❌ Arquivo docker-compose.yml não encontrado"
        exit 1
    fi
    
    echo "⚠️  Isso irá remover todos os dados do MongoDB!"
    read -p "Tem certeza? (s/N): " confirm
    if [ "$confirm" != "s" ] && [ "$confirm" != "S" ]; then
        echo "Operação cancelada"
        exit 0
    fi
    
    docker-compose down -v
    echo "✅ Container e volumes removidos"

# Mostra status do MongoDB em Docker
docker-mongodb-status:
    #!/usr/bin/env bash
    echo "📊 Status do MongoDB em Docker:"
    echo ""
    
    if docker ps --filter "name=paics-mongodb" --filter "status=running" --quiet | grep -q .; then
        echo ""
        docker ps --filter "name=paics-mongodb"
        echo ""
        
        # Tentar conectar
        PROJECT_ROOT=$(pwd)
        if [ -f "{{venv_dir}}/Scripts/python.exe" ]; then
            PYTHON_CMD="{{python_venv_win}}"
        elif [ -f "{{venv_dir}}/bin/python" ]; then
            PYTHON_CMD="{{python_venv}}"
        else
            PYTHON_CMD=""
            if command -v py &> /dev/null && py --version &> /dev/null; then
                PYTHON_CMD="py"
            elif command -v python3 &> /dev/null; then
                PYTHON_CMD="python3"
            elif command -v {{python}} &> /dev/null && {{python}} --version &> /dev/null 2>&1; then
                PYTHON_CMD="{{python}}"
            fi
        fi
        
        if [ -n "$PYTHON_CMD" ]; then
            if PYTHONPATH="$PROJECT_ROOT" $PYTHON_CMD -c "from pymongo import MongoClient; import os; from dotenv import load_dotenv; load_dotenv(); client = MongoClient(os.getenv('MONGO_URI', 'mongodb://localhost:27017/'), serverSelectionTimeoutMS=2000); client.server_info(); print('OK')" 2>/dev/null; then
                echo "✅ MongoDB está acessível via Python"
            else
                echo "⚠️  Container rodando, mas ainda não está totalmente acessível"
            fi
        fi
    else
        echo "❌ Container MongoDB não está rodando"
        echo ""
        echo "Para iniciar: just docker-mongodb-start"
    fi

# Mostra logs do MongoDB em Docker
docker-mongodb-logs:
    #!/usr/bin/env bash
    echo "📋 Logs do MongoDB:"
    echo ""
    docker-compose logs -f mongodb

# --- Execução Completa do Projeto ---

# Remove completamente o pacote bson conflitante
fix-bson:
    #!/usr/bin/env bash
    echo "🔧 Removendo pacote bson conflitante..."
    if [ -f "{{venv_dir}}/Scripts/python.exe" ]; then
        {{python_venv_win}} -m pip uninstall -y bson 2>/dev/null || true
        rm -rf "{{venv_dir}}/Lib/site-packages/bson" 2>/dev/null || true
        rm -rf "{{venv_dir}}/Lib/site-packages/bson-*.dist-info" 2>/dev/null || true
        {{python_venv_win}} -m pip install --force-reinstall pymongo>=4.6.0
        echo "✅ bson removido e pymongo reinstalado"
    elif [ -f "{{venv_dir}}/bin/python" ]; then
        {{python_venv}} -m pip uninstall -y bson 2>/dev/null || true
        rm -rf "{{venv_dir}}/lib/python*/site-packages/bson" 2>/dev/null || true
        rm -rf "{{venv_dir}}/lib/python*/site-packages/bson-*.dist-info" 2>/dev/null || true
        {{python_venv}} -m pip install --force-reinstall pymongo>=4.6.0
        echo "✅ bson removido e pymongo reinstalado"
    else
        echo "⚠️  Ambiente virtual não encontrado"
    fi

# Verifica se o MongoDB está rodando
check-mongodb:
    #!/usr/bin/env bash
    echo "🔍 Verificando MongoDB..."
    
    # Primeiro verificar Docker
    if command -v docker &> /dev/null && docker info &> /dev/null 2>&1; then
        if docker ps --filter "name=paics-mongodb" --filter "status=running" --quiet | grep -q .; then
            echo "🐳 MongoDB rodando em Docker"
            just docker-mongodb-status
            exit 0
        fi
    fi
    
    # Se não estiver em Docker, verificar conexão local
    PROJECT_ROOT=$(pwd)
    
    if [ -f "{{venv_dir}}/Scripts/python.exe" ]; then
        PYTHON_CMD="{{python_venv_win}}"
    elif [ -f "{{venv_dir}}/bin/python" ]; then
        PYTHON_CMD="{{python_venv}}"
    else
        PYTHON_CMD=""
        if command -v py &> /dev/null && py --version &> /dev/null; then
            PYTHON_CMD="py"
        elif command -v python3 &> /dev/null; then
            PYTHON_CMD="python3"
        elif command -v {{python}} &> /dev/null && {{python}} --version &> /dev/null 2>&1; then
            PYTHON_CMD="{{python}}"
        fi
    fi
    
    if [ -z "$PYTHON_CMD" ]; then
        echo "❌ Python não encontrado"
        exit 1
    fi
    
    if PYTHONPATH="$PROJECT_ROOT" $PYTHON_CMD -c "from pymongo import MongoClient; import os; from dotenv import load_dotenv; load_dotenv(); client = MongoClient(os.getenv('MONGO_URI', 'mongodb://localhost:27017/'), serverSelectionTimeoutMS=3000); client.server_info(); print('OK')" 2>/dev/null; then
        echo "✅ MongoDB está rodando e acessível"
        exit 0
    else
        echo "❌ MongoDB não está acessível"
        echo ""
        if [ "{{os}}" = "windows" ]; then
            echo "Para iniciar o MongoDB no Windows:"
            echo ""
            echo "  Opção 1 - Usar receita automática:"
            echo "    just start-mongodb"
            echo ""
            echo "  Opção 2 - Iniciar serviço manualmente:"
            echo "    - Pressione Win+R, digite 'services.msc' e pressione Enter"
            echo "    - Procure por 'MongoDB' ou 'MongoDB Server'"
            echo "    - Clique com botão direito e selecione 'Iniciar'"
            echo ""
            echo "  Opção 3 - Via linha de comando (como Administrador):"
            echo "    net start MongoDB"
        else
            echo "Para iniciar o MongoDB:"
            echo "  Linux: sudo systemctl start mongod"
            echo "  Mac: brew services start mongodb-community"
        fi
        echo ""
        echo "  Depois, verifique novamente: just check-mongodb"
        exit 1
    fi

# Tenta iniciar o MongoDB (tenta Docker primeiro, depois métodos locais)
start-mongodb:
    #!/usr/bin/env bash
    echo "🚀 Tentando iniciar MongoDB..."
    
    # Primeiro, tentar Docker (recomendado)
    if command -v docker &> /dev/null && docker info &> /dev/null 2>&1; then
        if [ -f "docker-compose.yml" ]; then
            echo "🐳 Docker detectado. Tentando iniciar MongoDB via Docker..."
            if just docker-mongodb-start 2>/dev/null; then
                echo ""
                echo "✅ MongoDB iniciado via Docker!"
                exit 0
            fi
        fi
    fi
    
    # Se Docker não funcionou, tentar métodos locais
    if [ "{{os}}" != "windows" ]; then
        echo "Tentando métodos locais..."
        echo "  Linux: sudo systemctl start mongod"
        echo "  Mac: brew services start mongodb-community"
        echo ""
        echo "💡 Dica: Use Docker para uma solução mais simples:"
        echo "  1. Instale Docker Desktop"
        echo "  2. Execute: just docker-mongodb-start"
        exit 1
    fi
    
    # Verificar se já está rodando (sem causar exit se não estiver)
    PROJECT_ROOT=$(pwd)
    if [ -f "{{venv_dir}}/Scripts/python.exe" ]; then
        PYTHON_CMD="{{python_venv_win}}"
    elif [ -f "{{venv_dir}}/bin/python" ]; then
        PYTHON_CMD="{{python_venv}}"
    else
        PYTHON_CMD=""
        if command -v py &> /dev/null && py --version &> /dev/null; then
            PYTHON_CMD="py"
        elif command -v python3 &> /dev/null; then
            PYTHON_CMD="python3"
        elif command -v {{python}} &> /dev/null && {{python}} --version &> /dev/null 2>&1; then
            PYTHON_CMD="{{python}}"
        fi
    fi
    
    if [ -n "$PYTHON_CMD" ]; then
        if PYTHONPATH="$PROJECT_ROOT" $PYTHON_CMD -c "from pymongo import MongoClient; import os; from dotenv import load_dotenv; load_dotenv(); client = MongoClient(os.getenv('MONGO_URI', 'mongodb://localhost:27017/'), serverSelectionTimeoutMS=2000); client.server_info(); print('OK')" 2>/dev/null; then
            echo "✅ MongoDB já está rodando!"
            exit 0
        fi
    fi
    
    # Tentar iniciar como serviço (várias variações de nome)
    echo "Tentando iniciar serviço MongoDB..."
    SERVICE_STARTED=false
    
    # Lista de possíveis nomes de serviço
    SERVICE_NAMES=("MongoDB")
    
    for service in "${SERVICE_NAMES[@]}"; do
        # Verificar status do serviço
        service_status=$(sc query "$service" 2>/dev/null | grep "STATE" || echo "")
        
        if echo "$service_status" | grep -q "RUNNING"; then
            echo "✅ Serviço '$service' já está rodando"
            SERVICE_STARTED=true
            sleep 2
            break
        elif echo "$service_status" | grep -q "STOPPED"; then
            echo "Serviço '$service' encontrado e parado. Tentando iniciar..."
            if net start "$service" 2>/dev/null; then
                echo "✅ Serviço '$service' iniciado com sucesso"
                SERVICE_STARTED=true
                sleep 3
                break
            else
                echo "⚠️  Não foi possível iniciar o serviço '$service' (pode precisar de privilégios de administrador)"
            fi
        fi
    done
    
    # Tentar também com variações do nome
    if [ "$SERVICE_STARTED" = false ]; then
        # Tentar buscar serviços que contenham "Mongo" no nome
        mongo_services=$(sc query type= service state= all 2>/dev/null | grep -i "mongo" || echo "")
        if [ -n "$mongo_services" ]; then
            echo "Serviços MongoDB encontrados no sistema:"
            echo "$mongo_services"
            echo ""
            echo "Tente iniciar manualmente usando o nome exato do serviço:"
            echo "  net start [nome_do_serviço]"
        fi
    fi
    
    if [ "$SERVICE_STARTED" = true ]; then
        echo ""
        echo "Verificando conexão..."
        sleep 2
        if [ -n "$PYTHON_CMD" ]; then
            if PYTHONPATH="$PROJECT_ROOT" $PYTHON_CMD -c "from pymongo import MongoClient; import os; from dotenv import load_dotenv; load_dotenv(); client = MongoClient(os.getenv('MONGO_URI', 'mongodb://localhost:27017/'), serverSelectionTimeoutMS=3000); client.server_info(); print('OK')" 2>/dev/null; then
                echo "✅ MongoDB está acessível!"
                exit 0
            else
                echo "⚠️  Serviço iniciado, mas ainda não está acessível. Aguarde alguns segundos e tente: just check-mongodb"
                exit 0
            fi
        fi
        exit 0
    fi
    
    # Tentar encontrar mongod.exe no PATH
    echo "Buscando mongod.exe no PATH..."
    MONGOD_IN_PATH=""
    if command -v mongod &> /dev/null; then
        MONGOD_IN_PATH=$(command -v mongod)
    elif command -v mongod.exe &> /dev/null; then
        MONGOD_IN_PATH=$(command -v mongod.exe)
    fi
    
    if [ -n "$MONGOD_IN_PATH" ]; then
        echo "✅ Encontrado no PATH: $MONGOD_IN_PATH"
        echo "Iniciando MongoDB em background..."
        # Criar diretório de dados se não existir
        mkdir -p "/c/data/db" 2>/dev/null || mkdir -p "C:/data/db" 2>/dev/null || true
        "$MONGOD_IN_PATH" --dbpath "C:/data/db" 2>/dev/null &
        sleep 3
        echo ""
        echo "Verificando conexão..."
        if [ -n "$PYTHON_CMD" ]; then
            if PYTHONPATH="$PROJECT_ROOT" $PYTHON_CMD -c "from pymongo import MongoClient; import os; from dotenv import load_dotenv; load_dotenv(); client = MongoClient(os.getenv('MONGO_URI', 'mongodb://localhost:27017/'), serverSelectionTimeoutMS=3000); client.server_info(); print('OK')" 2>/dev/null; then
                echo "✅ MongoDB está acessível!"
                exit 0
            else
                echo "⚠️  MongoDB iniciado, mas ainda não está acessível. Aguarde alguns segundos e tente: just check-mongodb"
                exit 0
            fi
        fi
        exit 0
    fi
    
    # Tentar encontrar em caminhos comuns usando find
    echo "Buscando mongod.exe em caminhos comuns..."
    MONGOD_FOUND=""
    
    # Buscar usando find em diretórios comuns
    SEARCH_DIRS=(
        "/c/Program Files/MongoDB"
        "/c/Program Files (x86)/MongoDB"
        "C:/Program Files/MongoDB"
        "C:/Program Files (x86)/MongoDB"
        "/c/mongodb"
        "C:/mongodb"
    )
    
    for dir in "${SEARCH_DIRS[@]}"; do
        if [ -d "$dir" ]; then
            # Buscar mongod.exe recursivamente
            found=$(find "$dir" -name "mongod.exe" -type f 2>/dev/null | head -1)
            if [ -n "$found" ] && [ -f "$found" ]; then
                MONGOD_FOUND="$found"
                break
            fi
        fi
    done
    
    # Se não encontrou com find, tentar caminhos específicos
    if [ -z "$MONGOD_FOUND" ]; then
        SPECIFIC_PATHS=(
            "/c/Program Files/MongoDB/Server/7.0/bin/mongod.exe"
            "/c/Program Files/MongoDB/Server/6.0/bin/mongod.exe"
            "/c/Program Files/MongoDB/Server/5.0/bin/mongod.exe"
            "/c/Program Files (x86)/MongoDB/Server/7.0/bin/mongod.exe"
            "/c/Program Files (x86)/MongoDB/Server/6.0/bin/mongod.exe"
            "/c/Program Files (x86)/MongoDB/Server/5.0/bin/mongod.exe"
            "C:/Program Files/MongoDB/Server/7.0/bin/mongod.exe"
            "C:/Program Files/MongoDB/Server/6.0/bin/mongod.exe"
            "C:/Program Files/MongoDB/Server/5.0/bin/mongod.exe"
            "/c/mongodb/bin/mongod.exe"
            "C:/mongodb/bin/mongod.exe"
        )
        
        for path in "${SPECIFIC_PATHS[@]}"; do
            if [ -f "$path" ]; then
                MONGOD_FOUND="$path"
                break
            fi
        done
    fi
    
    if [ -n "$MONGOD_FOUND" ]; then
        echo "✅ Encontrado: $MONGOD_FOUND"
        echo "Iniciando MongoDB em background..."
        # Criar diretório de dados se não existir
        mkdir -p "/c/data/db" 2>/dev/null || mkdir -p "C:/data/db" 2>/dev/null || true
        "$MONGOD_FOUND" --dbpath "C:/data/db" 2>/dev/null &
        sleep 3
        echo ""
        echo "Verificando conexão..."
        if [ -n "$PYTHON_CMD" ]; then
            if PYTHONPATH="$PROJECT_ROOT" $PYTHON_CMD -c "from pymongo import MongoClient; import os; from dotenv import load_dotenv; load_dotenv(); client = MongoClient(os.getenv('MONGO_URI', 'mongodb://localhost:27017/'), serverSelectionTimeoutMS=3000); client.server_info(); print('OK')" 2>/dev/null; then
                echo "✅ MongoDB está acessível!"
                exit 0
            else
                echo "⚠️  MongoDB iniciado, mas ainda não está acessível. Aguarde alguns segundos e tente: just check-mongodb"
                exit 0
            fi
        fi
        exit 0
    fi
    
    # Não encontrado - fornecer instruções detalhadas
    echo "❌ MongoDB não encontrado automaticamente"
    echo ""
    echo "📋 Opções para iniciar o MongoDB:"
    echo ""
    echo "1️⃣  Iniciar através dos Serviços do Windows:"
    echo "   - Pressione Win+R, digite 'services.msc' e pressione Enter"
    echo "   - Procure por 'MongoDB' ou 'MongoDB Server'"
    echo "   - Clique com botão direito e selecione 'Iniciar'"
    echo ""
    echo "2️⃣  Iniciar via linha de comando (como Administrador):"
    echo "   - Abra PowerShell ou CMD como Administrador"
    echo "   - Execute: net start MongoDB"
    echo ""
    echo "3️⃣  Executar manualmente:"
    echo "   - Encontre o caminho do mongod.exe (geralmente em:)"
    echo "     C:\\Program Files\\MongoDB\\Server\\[versão]\\bin\\mongod.exe"
    echo "   - Execute: \"[caminho]\\mongod.exe\" --dbpath C:\\data\\db"
    echo ""
    echo "4️⃣  Instalar MongoDB (se não estiver instalado):"
    echo "   - Baixe em: https://www.mongodb.com/try/download/community"
    echo "   - Durante a instalação, marque 'Install MongoDB as a Service'"
    echo ""
    echo "💡 Dica: Após iniciar, verifique com: just check-mongodb"
    exit 1

# Cria um usuário administrador (requer MongoDB rodando)
create-admin:
    #!/usr/bin/env bash
    echo "👤 Criando usuário administrador..."
    PROJECT_ROOT=$(pwd)
    
    if [ -f "{{venv_dir}}/Scripts/python.exe" ]; then
        PYTHON_CMD="{{python_venv_win}}"
    elif [ -f "{{venv_dir}}/bin/python" ]; then
        PYTHON_CMD="{{python_venv}}"
    else
        PYTHON_CMD=""
        if command -v py &> /dev/null && py --version &> /dev/null; then
            PYTHON_CMD="py"
        elif command -v python3 &> /dev/null; then
            PYTHON_CMD="python3"
        elif command -v {{python}} &> /dev/null && {{python}} --version &> /dev/null 2>&1; then
            PYTHON_CMD="{{python}}"
        fi
    fi
    
    if [ -z "$PYTHON_CMD" ]; then
        echo "❌ Python não encontrado"
        exit 1
    fi
    
    # Verificar se MongoDB está acessível
    if ! PYTHONPATH="$PROJECT_ROOT" $PYTHON_CMD -c "from pymongo import MongoClient; import os; from dotenv import load_dotenv; load_dotenv(); client = MongoClient(os.getenv('MONGO_URI', 'mongodb://localhost:27017/'), serverSelectionTimeoutMS=3000); client.server_info(); print('OK')" 2>/dev/null; then
        echo "❌ MongoDB não está acessível"
        echo ""
        echo "Para iniciar o MongoDB:"
        echo "  - Windows: just start-mongodb"
        echo "  - Linux: sudo systemctl start mongod"
        echo "  - Mac: brew services start mongodb-community"
        echo ""
        echo "Ou verifique o status: just check-mongodb"
        exit 1
    fi
    
    # Inicializar banco se necessário
    echo "   Inicializando banco de dados..."
    PYTHONPATH="$PROJECT_ROOT" $PYTHON_CMD -c "from database.connection import init_db; init_db(); print('✅ Banco inicializado')" 2>/dev/null || true
    
    # Criar administrador
    echo ""
    PYTHONPATH="$PROJECT_ROOT" $PYTHON_CMD scripts/create_admin.py

# Executa o projeto completo: setup, instalação, criação de admin e inicialização
start:
    #!/usr/bin/env bash
    set -euo pipefail
    
    echo "🚀 Iniciando PAICS - Setup Completo"
    echo "===================================="
    echo ""
    
    # 1. Verificar/criar ambiente virtual
    echo "📦 Passo 1/6: Verificando ambiente virtual..."
    if [ ! -d "{{venv_dir}}" ]; then
        echo "   Ambiente virtual não encontrado. Criando..."
        just setup
        sleep 2
    else
        echo "   ✅ Ambiente virtual encontrado"
    fi
    echo ""
    
    # 2. Instalar dependências
    echo "📦 Passo 2/6: Instalando/atualizando dependências..."
    # Corrigir conflito do bson antes de instalar dependências
    just fix-bson
    
    if [ -d "{{venv_dir}}/Scripts" ] || [ -f "{{venv_dir}}/Scripts/activate" ]; then
        echo "   Detectado ambiente Windows"
        just install-venv-win
    elif [ -d "{{venv_dir}}/bin" ] || [ -f "{{venv_dir}}/bin/activate" ]; then
        echo "   Detectado ambiente Unix/Linux"
        just install-venv
    else
        echo "   ⚠️  Ambiente virtual incompleto, tentando instalar dependências do sistema..."
        just install
    fi
    echo ""
    
    # 3. Verificar/criar arquivo .env
    echo "🔧 Passo 3/6: Verificando configuração do .env..."
    if [ ! -f ".env" ]; then
        echo "   Arquivo .env não encontrado. Criando a partir do .env.example..."
        if [ -f ".env.example" ]; then
            cp .env.example .env
            echo "   ✅ Arquivo .env criado"
            echo "   ⚠️  IMPORTANTE: Edite o arquivo .env e adicione sua GOOGLE_API_KEY"
            echo "   Pressione ENTER para continuar ou Ctrl+C para editar o .env agora..."
            read -r
        else
            echo "   ⚠️  .env.example não encontrado. Criando .env básico..."
            {
                echo "GOOGLE_API_KEY=sua_chave_api_aqui"
                echo "GEMINI_MODEL_NAME=gemini-1.5-pro-latest"
                echo "MONGO_URI=mongodb://localhost:27017/"
                echo "MONGO_DB_NAME=paics_db"
                echo "OUTPUT_DIR=laudos_com_ia"
                echo "STREAMLIT_TEMP_DIR=temp_laudos"
            } > .env
            echo "   ✅ Arquivo .env criado com valores padrão"
            echo "   ⚠️  IMPORTANTE: Edite o arquivo .env e adicione sua GOOGLE_API_KEY"
            echo "   Pressione ENTER para continuar ou Ctrl+C para editar o .env agora..."
            read -r
        fi
    else
        echo "   ✅ Arquivo .env encontrado"
        # Verificar se GOOGLE_API_KEY está configurada
        if grep -q "GOOGLE_API_KEY=sua_chave_api_aqui" .env 2>/dev/null || grep -q "GOOGLE_API_KEY=$" .env 2>/dev/null; then
            echo "   ⚠️  GOOGLE_API_KEY não está configurada no .env"
            echo "   Edite o arquivo .env e adicione sua chave antes de continuar"
            echo "   Pressione ENTER para continuar ou Ctrl+C para editar o .env agora..."
            read -r
        else
            echo "   ✅ GOOGLE_API_KEY parece estar configurada"
        fi
    fi
    echo ""
    
    # 4. Verificar MongoDB
    echo "🗄️  Passo 4/6: Verificando MongoDB..."
    echo "   💡 Dica: Use Docker para uma solução mais simples: just docker-mongodb-start"
    # Detectar comando Python do venv
    if [ -f "{{venv_dir}}/Scripts/python.exe" ]; then
        PYTHON_CMD="{{python_venv_win}}"
    elif [ -f "{{venv_dir}}/bin/python" ]; then
        PYTHON_CMD="{{python_venv}}"
    else
        # Tentar diferentes comandos Python (prioridade: py > python3 > python)
        PYTHON_CMD=""
        if command -v py &> /dev/null && py --version &> /dev/null; then
            PYTHON_CMD="py"
        elif command -v python3 &> /dev/null; then
            PYTHON_CMD="python3"
        elif command -v {{python}} &> /dev/null && {{python}} --version &> /dev/null 2>&1; then
            PYTHON_CMD="{{python}}"
        fi
    fi
    
    if [ -n "$PYTHON_CMD" ]; then
        # Tentar conectar ao MongoDB
        if $PYTHON_CMD -c "from pymongo import MongoClient; import os; from dotenv import load_dotenv; load_dotenv(); client = MongoClient(os.getenv('MONGO_URI', 'mongodb://localhost:27017/'), serverSelectionTimeoutMS=2000); client.server_info(); print('OK')" 2>/dev/null; then
            echo "   ✅ MongoDB está rodando e acessível"
        else
            echo "   ⚠️  MongoDB não está acessível ou não está rodando"
            echo ""
            echo "   Opções para iniciar o MongoDB:"
            echo ""
            echo "   🐳 Opção 1 - Docker (RECOMENDADO):"
            echo "      just docker-mongodb-start"
            echo ""
            echo "   💻 Opção 2 - Local:"
            if [ "{{os}}" = "windows" ]; then
                echo "      just start-mongodb"
            else
                echo "      sudo systemctl start mongod  # Linux"
                echo "      brew services start mongodb-community  # Mac"
            fi
            echo ""
            echo "   Verificar status: just check-mongodb"
            echo ""
            echo "   Pressione ENTER para continuar sem MongoDB ou Ctrl+C para iniciar o MongoDB..."
            read -r
        fi
    else
        echo "   ⚠️  Não foi possível verificar MongoDB (Python não encontrado)"
    fi
    echo ""
    
    # 5. Inicializar banco de dados e criar admin
    echo "👤 Passo 5/6: Inicializando banco de dados e criando administrador..."
    if [ -f "{{venv_dir}}/Scripts/python.exe" ]; then
        PYTHON_CMD="{{python_venv_win}}"
    elif [ -f "{{venv_dir}}/bin/python" ]; then
        PYTHON_CMD="{{python_venv}}"
    else
        PYTHON_CMD=""
        if command -v py &> /dev/null && py --version &> /dev/null; then
            PYTHON_CMD="py"
        elif command -v python3 &> /dev/null; then
            PYTHON_CMD="python3"
        elif command -v {{python}} &> /dev/null && {{python}} --version &> /dev/null 2>&1; then
            PYTHON_CMD="{{python}}"
        fi
    fi
    
    if [ -n "$PYTHON_CMD" ]; then
        # Obter diretório do projeto
        PROJECT_ROOT=$(pwd)
        
        # Verificar se MongoDB está acessível antes de tentar inicializar
        echo "   Verificando conexão com MongoDB..."
        if PYTHONPATH="$PROJECT_ROOT" $PYTHON_CMD -c "from pymongo import MongoClient; import os; from dotenv import load_dotenv; load_dotenv(); client = MongoClient(os.getenv('MONGO_URI', 'mongodb://localhost:27017/'), serverSelectionTimeoutMS=3000); client.server_info(); print('OK')" 2>/dev/null; then
            # Inicializar banco de dados
            echo "   Inicializando banco de dados..."
            if PYTHONPATH="$PROJECT_ROOT" $PYTHON_CMD -c "from database.connection import init_db; init_db(); print('✅ Banco de dados inicializado')" 2>/dev/null; then
                echo "   ✅ Banco de dados inicializado"
            else
                echo "   ⚠️  Erro ao inicializar banco (pode já estar inicializado)"
            fi
            
            # Criar administrador
            echo ""
            echo "   Criando usuário administrador..."
            echo "   (Siga as instruções na tela)"
            echo ""
            if PYTHONPATH="$PROJECT_ROOT" $PYTHON_CMD scripts/create_admin.py; then
                echo "   ✅ Administrador criado com sucesso"
            else
                echo "   ⚠️  Erro ao criar administrador (você pode criar depois através do sistema)"
            fi
        else
            echo "   ⚠️  MongoDB não está acessível"
            echo "   ⚠️  Pulando inicialização do banco e criação de administrador"
            echo ""
            echo "   ℹ️  Para iniciar o MongoDB:"
            if [ "{{os}}" = "windows" ]; then
                echo "      just start-mongodb"
            else
                echo "      sudo systemctl start mongod  # Linux"
                echo "      brew services start mongodb-community  # Mac"
            fi
            echo ""
            echo "   ℹ️  Depois, para criar o administrador:"
            echo "      just create-admin"
            echo ""
            echo "   ℹ️  Para verificar o status do MongoDB:"
            echo "      just check-mongodb"
        fi
    else
        echo "   ❌ Python não encontrado. Não é possível criar administrador."
        echo "   ⚠️  Continuando sem criar administrador..."
    fi
    echo ""
    
    # 6. Iniciar Streamlit
    echo "🚀 Passo 6/6: Iniciando aplicação Streamlit..."
    echo ""
    echo "===================================="
    echo "✅ Setup completo!"
    echo "===================================="
    echo ""
    echo "A aplicação será iniciada em: http://localhost:8501"
    echo ""
    echo "Pressione Ctrl+C para encerrar o servidor"
    echo ""
    
    # Aguardar um pouco antes de iniciar
    sleep 2
    
    # Iniciar Streamlit
    if [ -d "{{venv_dir}}/Scripts" ] || [ -f "{{venv_dir}}/Scripts/activate" ]; then
        {{python_venv_win}} -m streamlit run streamlit_app.py
    elif [ -d "{{venv_dir}}/bin" ] || [ -f "{{venv_dir}}/bin/activate" ]; then
        {{python_venv}} -m streamlit run streamlit_app.py
    else
        {{python}} -m streamlit run streamlit_app.py
    fi

