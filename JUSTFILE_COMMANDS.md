# 📋 Referência Rápida dos Comandos Just

Este arquivo lista todos os comandos disponíveis no `justfile` do projeto PAICS.

## 🚀 Setup e Instalação

| Comando | Descrição |
|---------|-----------|
| `just init` | ⚡ **Configuração completa** - Cria venv e instala todas as dependências |
| `just setup` | Cria o ambiente virtual Python |
| `just install` | Instala dependências (fora do venv) |
| `just install-venv` | Instala dependências no ambiente virtual (Linux/Mac) |
| `just install-venv-win` | Instala dependências no ambiente virtual (Windows) |
| `just update` | Atualiza todas as dependências para versões mais recentes |

## ▶️ Execução

### 🌐 Interface Web Streamlit

| Comando | Descrição |
|---------|-----------|
| `just streamlit` | 🌐 **Interface Web** - Inicia a aplicação Streamlit (RECOMENDADO) |
| `just streamlit-venv` | Inicia Streamlit usando o ambiente virtual |
| `just streamlit-dev` | Inicia Streamlit em modo desenvolvimento (auto-reload) |
| `just streamlit-port PORT=8501` | Inicia Streamlit em porta específica |

### 📜 Linha de Comando

| Comando | Descrição |
|---------|-----------|
| `just run-interactive` | Executa o script interativo (run.py) |
| `just run` | Executa o script principal (main.py) |
| `just run-interactive-venv` | Executa run.py usando o ambiente virtual |
| `just run-venv` | Executa main.py usando o ambiente virtual |

## 🔍 Verificação e Desenvolvimento

| Comando | Descrição |
|---------|-----------|
| `just check` | ⭐ Verifica configuração completa (deps + API key) |
| `just check-deps` | Verifica se todas as dependências estão instaladas |
| `just check-api-key` | Verifica se a GOOGLE_API_KEY está configurada |
| `just validate` | Valida sintaxe dos arquivos Python |
| `just test-import` | Testa se os módulos podem ser importados |

## 🎨 Formatação e Qualidade de Código

| Comando | Descrição | Requisito |
|---------|-----------|-----------|
| `just format` | Formata o código Python | black (instala automaticamente) |
| `just lint` | Executa linter no código | flake8 (instala automaticamente) |

## 🧹 Limpeza

| Comando | Descrição |
|---------|-----------|
| `just clean` | Remove arquivos temporários (__pycache__, .pyc) |
| `just clean-venv` | Remove o ambiente virtual |
| `just clean-all` | Limpeza completa (arquivos temporários + venv) |

## 📊 Utilitários

| Comando | Descrição |
|---------|-----------|
| `just info` | Mostra informações sobre o projeto e versões |
| `just list-pdfs` | Lista arquivos PDF na pasta atual |
| `just show-output-size` | Mostra tamanho do diretório de saída |
| `just freeze` | Gera requirements.freeze.txt com versões fixas |

## 📝 Exemplos de Uso

### Configuração Inicial Completa

```bash
# 1. Configura o ambiente completo
just init

# 2. Configura a API Key (Linux/Mac)
export GOOGLE_API_KEY="sua_chave_aqui"

# No Windows (PowerShell):
$env:GOOGLE_API_KEY="sua_chave_aqui"

# No Windows (CMD):
set GOOGLE_API_KEY=sua_chave_aqui

# 3. Verifica se está tudo OK
just check

# 4. Executa o projeto
just run-interactive
```

### Workflow Diário

```bash
# Verificar status
just check

# Listar PDFs disponíveis
just list-pdfs

# Executar análise
just run-interactive

# Ver tamanho dos outputs
just show-output-size
```

### Desenvolvimento

```bash
# Validar código
just validate

# Formatar código
just format

# Verificar qualidade
just lint

# Testar importações
just test-import
```

## 💡 Dicas

1. **Primeira vez usando o projeto?** Execute `just init` para configurar tudo automaticamente.

2. **Não sabe qual comando usar?** Execute `just` ou `just --list` para ver todos os comandos disponíveis.

3. **Problemas com dependências?** Execute `just check-deps` para verificar o que está faltando.

4. **Problemas com API Key?** Execute `just check-api-key` para verificar se está configurada.

5. **Quer começar do zero?** Execute `just clean-all` e depois `just init`.

## 🔗 Links Úteis

- [Documentação do Just](https://github.com/casey/just)
- [Instalar Just](https://github.com/casey/just#installation)

