# Railway: conectar o PAICS ao MongoDB

No serviço da **aplicação PAICS**, a variável `${{RAILWAY_PRIVATE_DOMAIN}}` é do **próprio PAICS** (ex.: `paics.railway.internal`), não do MongoDB. Por isso não use um `MONGO_URI` montado com essa variável no serviço da app.

## Opção 1 – Referência a MONGO_URL (recomendado)

1. No Railway, abra o **serviço da aplicação PAICS** (não o do MongoDB).
2. Em **Variables**, **remova** a variável **MONGO_URI** que está com o texto `mongodb://${{MONGO_INITDB_ROOT_USERNAME}}:...@${{RAILWAY_PRIVATE_DOMAIN}}:27017`.
3. **Adicione** uma variável por **referência**:
   - **Nome:** `MONGO_URL`
   - **Valor:** clique em **Reference** (ou “Add Reference”) → escolha o **serviço do MongoDB** → selecione a variável **MONGO_URL**.
4. Salve e faça **redeploy** do PAICS.

O código usa **MONGO_URL com prioridade** sobre MONGO_URI. Se MONGO_URL for referência ao MongoDB, a conexão usará o host correto.

**Importante:** Remova também do serviço PAICS as variáveis **MONGO_INITDB_ROOT_USERNAME**, **MONGO_INITDB_ROOT_PASSWORD** e **MONGOHOST** se estiverem como valor fixo (não referência). Elas fazem a app resolver o host para o próprio PAICS.

---

## Opção 2 – Referências a MONGOHOST, MONGOUSER, MONGOPASSWORD (use se Opção 1 ainda der paics.railway.internal)

O Railway pode re-resolver variáveis ao injetar MONGO_URL no PAICS, fazendo o host virar `paics.railway.internal`. Nesse caso, use **só** as variáveis abaixo (referências ao MongoDB):

1. No **serviço PAICS**, **remova** **MONGO_URI** e **MONGO_URL** (para não usar URI errada).
2. Adicione **apenas** estas variáveis como **Reference** ao **serviço MongoDB**:
   - **MONGOHOST** → Referência → MongoDB → **MONGOHOST**
   - **MONGOUSER** → Referência → MongoDB → **MONGOUSER**
   - **MONGOPASSWORD** → Referência → MongoDB → **MONGOPASSWORD**
3. No PAICS, defina **MONGOPORT** = `27017` (valor fixo).
4. Mantenha **MONGO_DB_NAME** = `paics_db`.
5. Salve e faça **redeploy**.

O código ignora qualquer URI que contenha `paics.railway.internal` e monta a conexão com **MONGOHOST** (que, por referência, será o domínio interno do MongoDB).

---

## Resumo

| Onde       | O que fazer |
|-----------|-------------|
| Serviço PAICS | Remover `MONGO_URI` com `${{RAILWAY_PRIVATE_DOMAIN}}`. |
| Serviço PAICS | Adicionar **MONGO_URL** = **Referência** → serviço **MongoDB** → **MONGO_URL**. |
| Ou         | Adicionar **MONGOHOST**, **MONGOUSER**, **MONGOPASSWORD** (e opcionalmente **MONGOPORT**) como **Referência** ao serviço MongoDB. |

Depois do redeploy, a aplicação deve conectar ao MongoDB usando o host interno do serviço do banco.
