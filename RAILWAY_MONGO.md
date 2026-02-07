# Railway: conectar o PAICS ao MongoDB

No serviço da **aplicação PAICS**, a variável `${{RAILWAY_PRIVATE_DOMAIN}}` é do **próprio PAICS** (ex.: `paics.railway.internal`), não do MongoDB. Por isso não use um `MONGO_URI` montado com essa variável no serviço da app.

## Opção 1 – Referência a MONGO_URL (recomendado)

1. No Railway, abra o **serviço da aplicação PAICS** (não o do MongoDB).
2. Em **Variables**, **remova** a variável **MONGO_URI** que está com o texto `mongodb://${{MONGO_INITDB_ROOT_USERNAME}}:...@${{RAILWAY_PRIVATE_DOMAIN}}:27017`.
3. **Adicione** uma variável por **referência**:
   - **Nome:** `MONGO_URL`
   - **Valor:** clique em **Reference** (ou “Add Reference”) → escolha o **serviço do MongoDB** → selecione a variável **MONGO_URL**.
4. Salve e faça **redeploy** do PAICS.

O código usa `MONGO_URL` quando `MONGO_URI` não está definida ou contém `${{`.

---

## Opção 2 – Referências a MONGOHOST, MONGOUSER, MONGOPASSWORD

Se a Opção 1 não estiver disponível, use referências para cada parte da conexão:

1. No **serviço PAICS**, remova a variável **MONGO_URI** com o template `${{...}}`.
2. Adicione estas variáveis como **Reference** ao **serviço MongoDB**:
   - **MONGOHOST** → referência a **MONGOHOST** do MongoDB (domínio interno do banco).
   - **MONGOUSER** → referência a **MONGOUSER** do MongoDB.
   - **MONGOPASSWORD** → referência a **MONGOPASSWORD** do MongoDB.
3. **MONGOPORT** pode ficar como `27017` (valor fixo) no PAICS, ou como referência a **MONGOPORT** do MongoDB.
4. Mantenha **MONGO_DB_NAME** = `paics_db` no serviço PAICS.
5. Salve e faça **redeploy**.

O código monta a URI com `MONGOHOST`, `MONGOUSER`, `MONGOPASSWORD` e `MONGOPORT` quando não há `MONGO_URI`/`MONGO_URL` válida (sem `${{`).

---

## Resumo

| Onde       | O que fazer |
|-----------|-------------|
| Serviço PAICS | Remover `MONGO_URI` com `${{RAILWAY_PRIVATE_DOMAIN}}`. |
| Serviço PAICS | Adicionar **MONGO_URL** = **Referência** → serviço **MongoDB** → **MONGO_URL**. |
| Ou         | Adicionar **MONGOHOST**, **MONGOUSER**, **MONGOPASSWORD** (e opcionalmente **MONGOPORT**) como **Referência** ao serviço MongoDB. |

Depois do redeploy, a aplicação deve conectar ao MongoDB usando o host interno do serviço do banco.
