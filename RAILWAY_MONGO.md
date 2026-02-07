# Railway: conectar o PAICS ao MongoDB

A aplicação usa **uma única variável** para a connection string do MongoDB: `MONGO_URI` ou `MONGO_URL`.

## Configuração

1. No Railway, abra o **serviço da aplicação PAICS** (não o do MongoDB).
2. Em **Variables**, adicione:
   - **Nome:** `MONGO_URI`
   - **Valor:** clique em **Reference** (ou "Add Reference") → escolha o **serviço do MongoDB** → selecione **MONGO_URL**.

3. Salve e faça **redeploy** do PAICS.

O Railway injeta a connection string completa do MongoDB (ex.: `mongodb://user:pass@mongodb.railway.internal:27017/`). Não é necessário `MONGO_INITDB_ROOT_USERNAME`, `MONGO_INITDB_ROOT_PASSWORD`, `MONGOHOST`, etc.

## Resumo

| Onde        | O que fazer |
|------------|-------------|
| Serviço PAICS | Adicionar **MONGO_URI** = **Referência** → serviço **MongoDB** → **MONGO_URL**. |
| Serviço PAICS | Opcional: **MONGO_DB_NAME** = `paics_db` (padrão). |

Depois do redeploy, a aplicação deve conectar ao MongoDB usando o host interno do serviço do banco.
