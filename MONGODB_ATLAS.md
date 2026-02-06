# Configurar MongoDB Atlas (plano gratuito) para o PAICS

O PAICS usa as variáveis **`MONGO_URI`** e **`MONGO_DB_NAME`** para conectar ao MongoDB. Com Atlas (plano gratuito M0), você não precisa rodar MongoDB localmente e pode usar o mesmo banco em desenvolvimento e no Railway.

## 1. Criar conta e cluster no Atlas

1. Acesse [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) e crie uma conta (ou faça login).
2. Crie uma **organização** e um **projeto** (pode usar nomes como "PAICS").
3. Em **Build a Database**, escolha **M0 (FREE)** e a região mais próxima (ex.: São Paulo).
4. Dê um nome ao cluster (ex.: `ClusterPAICS`) e clique em **Create**.

## 2. Criar usuário do banco

1. Em **Security** → **Database Access** → **Add New Database User**.
2. Escolha **Password** e defina um **username** (ex.: `paics`) e uma **senha forte** (guarde-a).
3. Em **Database User Privileges**, use **Read and write to any database** (ou **Atlas admin** para simplicidade no free tier).
4. Confirme com **Add User**.

## 3. Liberar acesso de rede (IP)

1. Em **Security** → **Network Access** → **Add IP Address**.
2. Para desenvolvimento e Railway:
   - **Add Current IP Address** (seu IP atual).
   - Para o **Railway** funcionar de qualquer lugar: use **Allow Access from Anywhere** (`0.0.0.0/0`). No free tier isso é aceitável; em produção você pode restringir depois aos IPs do Railway se quiser.
3. Confirme com **Confirm**.

## 4. Obter a connection string

1. No dashboard, clique em **Database** → **Connect** no seu cluster.
2. Escolha **Drivers** (ou **Connect your application**).
3. Copie a URI. Ela será algo como:
   ```text
   mongodb+srv://paics:<password>@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
   ```
4. Substitua **`<password>`** pela senha real do usuário que você criou. Se a senha tiver caracteres especiais (ex.: `@`, `#`), codifique em [URL encoding](https://www.w3schools.com/tags/ref_urlencode.asp) ou use uma senha sem caracteres especiais no usuário.

Opcional: incluir o nome do banco na URI (o PAICS também usa `MONGO_DB_NAME`):

```text
mongodb+srv://paics:minhasenha@cluster0.xxxxx.mongodb.net/paics_db?retryWrites=true&w=majority
```

## 5. Configurar no projeto

### Local (arquivo `.env`)

No `.env` (copie de `.env.example` se ainda não tiver):

```env
MONGO_URI=mongodb+srv://paics:SUA_SENHA@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
MONGO_DB_NAME=paics_db
```

Substitua `SUA_SENHA` e a parte `cluster0.xxxxx.mongodb.net` pela sua URI real.

### Railway (produção)

1. No projeto no [Railway](https://railway.app), abra o serviço do PAICS.
2. Vá em **Variables** e adicione:
   - **`MONGO_URI`**: a connection string completa (com senha).
   - **`MONGO_DB_NAME`**: `paics_db` (ou o nome que preferir).
3. Salve; o Railway fará um novo deploy usando o Atlas.

## 6. Criar o usuário admin do PAICS

Depois da primeira conexão bem-sucedida, crie o usuário administrador do sistema:

```bash
just seed-admin
# ou
python scripts/seed_admin.py
```

Siga as instruções no script (email/senha do admin).

## 7. Verificar conexão

- **Local**: `just check-mongodb` (se o justfile usar `MONGO_URI` do `.env`) ou subir o app e acessar a tela de login.
- **Railway**: após o deploy, acesse a URL do app; se carregar a tela de login, a conexão com o Atlas está ok.

## Resumo das variáveis

| Variável        | Exemplo (Atlas)                                                                 |
|-----------------|----------------------------------------------------------------------------------|
| `MONGO_URI`     | `mongodb+srv://paics:senha@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority` |
| `MONGO_DB_NAME` | `paics_db`                                                                      |

O código em `database/connection.py` já usa essas variáveis; não é necessário alterar código para usar o Atlas.

---

## Conectar pela extensão MongoDB no Cursor / VS Code

1. **Abra a extensão**: ícone do MongoDB na barra lateral ou painel "MongoDB".
2. **Add Connection** (ou "Connect") e cole a **connection string completa**.
3. A string deve estar com a **senha real** no lugar de `<password>` ou `<db_password>`.

### Se não conectar, confira:

- **Senha substituída**  
  A URI precisa ter a senha real, não o texto `<db_password>` ou `<password>`.

- **Senha com caracteres especiais**  
  Se a senha tiver `@`, `#`, `:`, `/`, `%`, etc., é preciso usar **URL encoding** na senha na connection string:
  - `@` → `%40`
  - `#` → `%23`
  - `:` → `%3A`
  - `/` → `%2F`
  - `%` → `%25`  
  Exemplo: senha `ab@12` → na URI use `ab%4012`. Ou crie um usuário no Atlas com senha só letras e números.

- **Acesso de rede no Atlas**  
  Em **Security** → **Network Access** → **Add IP Address**: use **Add Current IP Address** para o seu IP atual. Sem isso, a extensão (que conecta do seu PC) não consegue alcançar o cluster.

- **Formato da URI**  
  Use a string completa, no formato:
  ```text
  mongodb+srv://eliasgalindo_db_user:SUA_SENHA_AQUI@cluster0.huf03qc.mongodb.net/?appName=Cluster0
  ```
  Ou, com nome do banco na URI:
  ```text
  mongodb+srv://eliasgalindo_db_user:SUA_SENHA_AQUI@cluster0.huf03qc.mongodb.net/paics_db?retryWrites=true&w=majority
  ```

- **Testar em outro lugar**  
  No Atlas: **Database** → **Connect** → **MongoDB Compass** ou **Drivers**; use a mesma URI para confirmar que usuário, senha e rede estão corretos.
