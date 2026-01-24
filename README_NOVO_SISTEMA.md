# PAICS - Sistema Completo com Autenticação e Dashboards

## 🎯 Visão Geral

O PAICS agora é um sistema completo de gestão de laudos veterinários com:

- ✅ Sistema de autenticação (Admin e Usuários)
- ✅ Dashboard do Administrador
- ✅ Dashboard dos Usuários
- ✅ Banco de dados MongoDB
- ✅ Banco de dados vetorial (ChromaDB) para aprendizado
- ✅ Knowledge Base para armazenar PDFs, prompts e orientações
- ✅ Painel Financeiro para fechamentos e faturas

## 📋 Requisitos

### Dependências de Software

1. **Python 3.8+**
2. **MongoDB** - Instalar e configurar:
   - Windows: https://www.mongodb.com/try/download/community
   - Linux: `sudo apt-get install mongodb`
   - Mac: `brew install mongodb-community`

3. **ChromaDB** - Instalado automaticamente via pip

### Variáveis de Ambiente

Crie um arquivo `.env` na raiz do projeto com:

```env
# API do Google Gemini
GOOGLE_API_KEY=sua_chave_aqui

# MongoDB
MONGO_URI=mongodb://localhost:27017/
MONGO_DB_NAME=paics_db

# Outras configurações (opcional)
GEMINI_MODEL_NAME=gemini-2.5-flash
OUTPUT_DIR=laudos_com_ia
STREAMLIT_TEMP_DIR=temp_laudos
```

## 🚀 Instalação

### 1. Instalar Dependências

```bash
pip install -r requirements.txt
```

### 2. Iniciar MongoDB

**Windows:**
```bash
# MongoDB geralmente inicia automaticamente como serviço
# Ou execute manualmente:
"C:\Program Files\MongoDB\Server\7.0\bin\mongod.exe"
```

**Linux/Mac:**
```bash
sudo systemctl start mongod
# ou
mongod
```

### 3. Criar Usuário Administrador

```bash
python scripts/create_admin.py
```

Siga as instruções para criar o primeiro administrador.

### 4. Iniciar o Sistema

```bash
streamlit run streamlit_app.py
```

O sistema abrirá automaticamente no navegador em `http://localhost:8501`

## 📖 Como Usar

### Login

1. Acesse a aplicação
2. Se você é **administrador**, use as credenciais criadas pelo script
3. Se você é **usuário**, clique em "Criar Conta" para se registrar

### Dashboard do Administrador

O administrador tem acesso a:

1. **Requisições**: Ver e gerenciar todas as requisições de laudos
   - Filtrar por status, tipo de exame
   - Criar/editar laudos
   - Validar e liberar laudos

2. **Laudos**: Gerenciar todos os laudos
   - Editar laudos
   - Validar laudos (adiciona ao banco de aprendizado)
   - Liberar laudos para usuários

3. **Usuários**: Gerenciar usuários do sistema
   - Ver estatísticas
   - Ativar/desativar usuários

4. **Financeiro**: Painel financeiro completo
   - Gerar fechamentos por período
   - Criar faturas automaticamente
   - Gerenciar status de pagamento

5. **Knowledge Base**: Gerenciar conhecimento do sistema
   - Adicionar PDFs (livros, artigos)
   - Adicionar prompts personalizados
   - Adicionar orientações gerais
   - Buscar conteúdo relevante

### Dashboard do Usuário

Os usuários podem:

1. **Nova Requisição**: Enviar imagens para análise
   - Preencher dados do paciente
   - Upload de múltiplas imagens
   - Acompanhar status da requisição

2. **Meus Laudos**: Ver todos os laudos
   - Filtrar por status, paciente, tutor
   - Visualizar laudos liberados
   - Download em Word/PDF (quando liberado)

## 🗄️ Estrutura do Banco de Dados

### MongoDB Collections

- **users**: Usuários do sistema (admin e user)
- **requisicoes**: Requisições de laudos
- **laudos**: Laudos gerados
- **faturas**: Faturas financeiras
- **knowledge_base**: Conteúdo da knowledge base

### ChromaDB (Banco Vetorial)

- **laudos**: Laudos validados para aprendizado
- **knowledge_base**: Conteúdo da KB indexado vetorialmente

## 🔧 Funcionalidades Avançadas

### Banco de Dados Vetorial

O sistema aprende com os laudos validados:

- Quando um laudo é **validado**, ele é automaticamente adicionado ao banco vetorial
- Ao gerar novos laudos, o sistema pode buscar laudos similares para melhorar a qualidade
- Reduz dependência de modelos externos ao longo do tempo

### Knowledge Base

A knowledge base permite:

- Armazenar PDFs de livros e artigos
- Criar prompts personalizados
- Adicionar orientações do profissional responsável
- Busca semântica usando vetores

### Painel Financeiro

- Geração automática de fechamentos por período
- Criação de faturas por usuário
- Rastreamento de status de pagamento
- Relatórios de exames realizados

## 📁 Estrutura de Arquivos

```
PAICS/
├── auth/                    # Módulo de autenticação
│   ├── __init__.py
│   └── auth_utils.py
├── database/                # Módulo de banco de dados
│   ├── __init__.py
│   ├── connection.py        # Conexão MongoDB
│   └── models.py           # Modelos de dados
├── vector_db/               # Banco de dados vetorial
│   ├── __init__.py
│   └── vector_store.py      # ChromaDB
├── knowledge_base/          # Knowledge Base
│   ├── __init__.py
│   └── kb_manager.py
├── pages/                   # Páginas Streamlit
│   ├── login.py
│   ├── admin_dashboard.py
│   └── user_dashboard.py
├── utils/                   # Utilitários
│   ├── __init__.py
│   └── financeiro.py
├── scripts/                 # Scripts auxiliares
│   └── create_admin.py
├── streamlit_app.py         # App principal
├── main.py                  # Lógica de análise (original)
└── requirements.txt         # Dependências
```

## 🔐 Segurança

- Senhas são hasheadas usando SHA-256 com salt
- Sessões gerenciadas pelo Streamlit
- Verificação de permissões por role
- Validação de dados de entrada

## 🚧 Próximos Passos

- [ ] Integração completa do banco vetorial na geração de laudos
- [ ] Melhorias na interface de upload de imagens
- [ ] Sistema de notificações
- [ ] Exportação de relatórios financeiros
- [ ] API REST para integrações externas
- [ ] Deploy em produção (Docker, cloud, etc.)

## 📝 Notas Importantes

1. **MongoDB deve estar rodando** antes de iniciar o sistema
2. **Crie o primeiro admin** usando o script antes de usar o sistema
3. **Imagens são salvas localmente** - em produção, considere usar S3 ou similar
4. **Banco vetorial** é criado automaticamente na pasta `vector_db/`

## 🐛 Troubleshooting

### Erro de conexão com MongoDB
- Verifique se o MongoDB está rodando: `mongosh` ou `mongo`
- Verifique a URI no `.env`

### Erro ao criar admin
- Certifique-se de que o MongoDB está acessível
- Verifique se o banco foi inicializado corretamente

### Erro ao gerar laudo
- Verifique se a GOOGLE_API_KEY está configurada
- Verifique se há imagens válidas na requisição

## 📞 Suporte

Para problemas ou dúvidas, verifique:
1. Logs do Streamlit no terminal
2. Logs do MongoDB
3. Arquivo `.env` com configurações corretas
