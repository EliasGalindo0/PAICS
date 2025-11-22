# PAICS - Sistema de Análise de Imagens Veterinárias com IA

Sistema automatizado para análise de imagens veterinárias (raio-x e ultrassom) usando Inteligência Artificial (Google Gemini) para geração de laudos técnicos.

## 📋 Requisitos

- Python 3.8 ou superior
- Chave da API do Google Gemini
- Just (opcional, mas recomendado para facilitar os comandos) - [Instalar Just](https://github.com/casey/just)

## 🚀 Instalação

### Método Rápido (com Just)

Se você tem o Just instalado, pode configurar o ambiente com um único comando:

```bash
just init
```

Isso criará o ambiente virtual e instalará todas as dependências automaticamente.

Para ver todos os comandos disponíveis:
```bash
just --list
# ou apenas
just
```

### Método Manual

1. Clone o repositório ou navegue até a pasta do projeto:
```bash
cd PAICS
```

2. Crie um ambiente virtual (recomendado):
```bash
python -m venv venv
```

3. Ative o ambiente virtual:
- **Windows:**
```bash
venv\Scripts\activate
```
- **Linux/Mac:**
```bash
source venv/bin/activate
```

4. Instale as dependências:
```bash
pip install -r requirements.txt
```

5. Configure a chave da API:
   
   **Método 1 - Arquivo .env (Recomendado):**
   - Copie o arquivo `.env.example` para `.env`:
     ```bash
     # Linux/Mac:
     cp .env.example .env
     
     # Windows (CMD):
     copy .env.example .env
     ```
   - Edite o arquivo `.env` e adicione sua chave da API do Google Gemini:
     ```
     GOOGLE_API_KEY=sua_chave_real_aqui
     ```
   
   **Método 2 - Variável de Ambiente do Sistema:**
   - **Windows (PowerShell):**
     ```powershell
     $env:GOOGLE_API_KEY="sua_chave_real_aqui"
     ```
   - **Windows (CMD):**
     ```cmd
     set GOOGLE_API_KEY=sua_chave_real_aqui
     ```
   - **Linux/Mac:**
     ```bash
     export GOOGLE_API_KEY="sua_chave_real_aqui"
     ```

## 📖 Como Usar

### 🌐 Interface Web Streamlit (Recomendado)

O projeto inclui uma interface web moderna e intuitiva usando Streamlit:

1. **Inicie a aplicação Streamlit:**
```bash
# Usando Just (recomendado)
just streamlit

# Ou usando o ambiente virtual
just streamlit-venv

# Ou manualmente
streamlit run streamlit_app.py
```

2. **Acesse a aplicação:**
   - Abra seu navegador em `http://localhost:8501`
   - Faça upload do PDF com as imagens do exame
   - Visualize as imagens extraídas
   - Gere o laudo automaticamente com IA
   - **Edite o laudo** conforme necessário
   - **Baixe o laudo editado** em formato Word

**Funcionalidades da Interface Web:**
- ✅ Upload de PDF diretamente no navegador
- ✅ Visualização das imagens extraídas
- ✅ Geração automática de laudo com IA
- ✅ Editor de texto para editar o laudo gerado
- ✅ Download do laudo editado em formato Word
- ✅ Formulário para informações do paciente
- ✅ Preview do laudo formatado

### 📜 Linha de Comando

#### Usando Just (Recomendado)

1. Execute o script interativo:
```bash
just run-interactive
```

2. Ou execute o script principal:
```bash
just run
```

#### Método Manual

1. Coloque o arquivo PDF do exame na raiz do projeto (ou forneça o caminho completo)

2. Edite o arquivo `main.py` na linha 162 para apontar para o seu arquivo PDF:
```python
pdf_exame = "seu_arquivo.pdf"
```

3. Execute o script:
```bash
python main.py
# ou
python run.py
```

4. O laudo será gerado na pasta `laudos_com_ia/` com o nome `Laudo_AI_[nome_do_arquivo].docx`

## 🛠️ Comandos Úteis (Just)

O projeto inclui um `justfile` com vários comandos úteis:

### Setup e Instalação
- `just init` - Configuração completa do ambiente (cria venv e instala dependências)
- `just setup` - Cria apenas o ambiente virtual
- `just install` - Instala dependências
- `just update` - Atualiza todas as dependências

### Execução
- `just streamlit` - 🌐 **Interface Web** - Inicia a aplicação Streamlit (RECOMENDADO)
- `just streamlit-venv` - Inicia Streamlit usando o ambiente virtual
- `just streamlit-dev` - Inicia Streamlit em modo desenvolvimento (auto-reload)
- `just streamlit-port PORT=8501` - Inicia Streamlit em porta específica
- `just run-interactive` - Executa o script interativo (linha de comando)
- `just run` - Executa o script principal (linha de comando)
- `just run-interactive-venv` - Executa usando o ambiente virtual
- `just run-venv` - Executa o main.py usando o ambiente virtual

### Desenvolvimento
- `just check` - Verifica configuração completa (deps + API key)
- `just check-deps` - Verifica se as dependências estão instaladas
- `just check-api-key` - Verifica se a API key está configurada
- `just format` - Formata o código Python (requer black)
- `just lint` - Executa linter no código (requer flake8)
- `just validate` - Valida sintaxe dos arquivos Python
- `just test-import` - Testa importação dos módulos

### Limpeza
- `just clean` - Remove arquivos temporários (__pycache__, .pyc)
- `just clean-venv` - Remove o ambiente virtual
- `just clean-all` - Limpeza completa

### Utilitários
- `just info` - Mostra informações sobre o projeto
- `just list-pdfs` - Lista arquivos PDF na pasta atual
- `just show-output-size` - Mostra tamanho do diretório de saída

## 📁 Estrutura do Projeto

```
PAICS/
├── main.py                 # Script principal (linha de comando)
├── run.py                  # Script auxiliar interativo (linha de comando)
├── streamlit_app.py        # 🌐 Interface web Streamlit
├── justfile               # Comandos Just para gerenciar o projeto
├── requirements.txt        # Dependências do projeto
├── setup.py               # Configuração do pacote Python
├── .streamlit/            # Configurações do Streamlit
│   └── config.toml        # Configuração de tema e servidor
├── .gitignore             # Arquivos ignorados pelo Git
├── config.example.py      # Exemplo de configuração
├── INSTALL.md             # Guia detalhado de instalação
├── README.md              # Esta documentação
├── laudos_com_ia/         # Pasta de saída (gerada automaticamente)
└── venv/                  # Ambiente virtual (não versionado)
```

## ⚠️ Importante

- Este sistema gera **laudos sugeridos** que devem ser **revisados e validados** por um Médico Veterinário qualificado antes de serem utilizados.
- A IA serve como ferramenta de apoio, não substitui o julgamento clínico profissional.
- Todos os laudos gerados contêm um aviso destacando que são gerados automaticamente.

## 🔧 Dependências

- **PyMuPDF**: Processamento de arquivos PDF
- **google-generativeai**: Integração com a API do Google Gemini
- **python-docx**: Geração de documentos Word
- **Pillow**: Processamento de imagens
- **streamlit**: Framework web para interface de usuário
- **python-dotenv**: Carregamento de variáveis de ambiente do arquivo .env

## 📝 Licença

Este projeto é fornecido como está, para uso interno.

# PAICS
